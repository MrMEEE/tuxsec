"""
Management command to auto-sync firewall configurations from agents.
Run this periodically via cron or as a daemon.
"""
import asyncio
import time
import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import connection
from agents.models import Agent
from modules.firewalld.models import FirewallZone, FirewallRule
from agents.connection_managers import get_connection_manager

# Set up logging
logger = logging.getLogger('agents.sync')


class Command(BaseCommand):
    help = 'Auto-sync firewall configurations from agents based on their sync_interval_seconds'

    def add_arguments(self, parser):
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run as daemon (continuous loop)',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=10,
            help='Check interval in seconds when running as daemon (default: 10)',
        )

    def handle(self, *args, **options):
        daemon_mode = options['daemon']
        check_interval = options['interval']

        if daemon_mode:
            msg = f'Starting auto-sync daemon (checking every {check_interval} seconds)...'
            self.stdout.write(self.style.SUCCESS(msg))
            logger.info(msg)
            self.stdout.flush()
            
            while True:
                try:
                    self.sync_agents()
                    # Close database connections to prevent leaks in daemon mode
                    connection.close()
                except Exception as e:
                    error_msg = f'Error in sync loop: {str(e)}'
                    self.stdout.write(self.style.ERROR(error_msg))
                    logger.error(error_msg, exc_info=True)
                    self.stdout.flush()
                    connection.close()
                
                time.sleep(check_interval)
        else:
            self.sync_agents()

    def sync_agents(self):
        """Sync agents that are due for synchronization."""
        now = timezone.now()
        
        # Get agents that need syncing
        agents = Agent.objects.filter(
            sync_interval_seconds__gt=0,  # Only agents with sync enabled
            status__in=['online', 'approved', 'offline']  # Try syncing offline agents too
        )
        
        for agent in agents:
            # Check if agent is due for sync
            if agent.last_sync:
                time_since_sync = (now - agent.last_sync).total_seconds()
                if time_since_sync < agent.sync_interval_seconds:
                    continue  # Not due yet
            
            msg = f'Syncing agent: {agent.hostname}'
            self.stdout.write(self.style.WARNING(msg))
            logger.info(msg)
            
            try:
                self.sync_agent(agent)
                success_msg = f'✓ Successfully synced {agent.hostname}'
                self.stdout.write(self.style.SUCCESS(success_msg))
                logger.info(success_msg)
            except Exception as e:
                error_msg = f'✗ Failed to sync {agent.hostname}: {str(e)}'
                self.stdout.write(self.style.ERROR(error_msg))
                logger.error(error_msg, exc_info=True)

    def sync_agent(self, agent):
        """Sync a single agent's configuration - sync what's available."""
        # Get the appropriate connection manager
        manager = get_connection_manager(agent)
        
        synced_items = []
        
        # Always try to update agent metadata (system info)
        try:
            # Use a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                status_info = loop.run_until_complete(manager.test_connection())
            finally:
                loop.close()
                asyncio.set_event_loop(None)
            
            if status_info.get('success'):
                agent.status = 'online'
                agent.last_seen = timezone.now()
                agent.last_sync = timezone.now()
                
                # Update OS and version if available
                if status_info.get('operating_system'):
                    agent.operating_system = status_info['operating_system']
                if status_info.get('agent_version'):
                    agent.version = status_info['agent_version']
                if status_info.get('modules'):
                    agent.available_modules = status_info['modules']
                
                agent.save()
                synced_items.append('system info')
            else:
                # Connection test failed
                agent.status = 'offline'
                agent.save()
                self.stdout.write(
                    self.style.WARNING(f'  Connection test failed: {status_info.get("error", "Unknown error")}')
                )
                logger.warning(f'  Connection test failed for {agent.hostname}: {status_info.get("error")}')
        except Exception as e:
            # Connection attempt threw an exception
            agent.status = 'offline'
            agent.save()
            error_msg = f'  Could not connect to agent: {str(e)}'
            self.stdout.write(self.style.WARNING(error_msg))
            logger.error(error_msg, exc_info=True)
        
        # Try to get firewall zones if firewalld module is available
        if 'firewalld' in (agent.available_modules or []):
            try:
                # Use a new event loop in the main thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    zones_data = loop.run_until_complete(manager.get_zones())
                    debug_msg = f'  get_zones() returned: {zones_data} (type: {type(zones_data)}, length: {len(zones_data) if isinstance(zones_data, (list, dict)) else "N/A"})'
                    self.stdout.write(self.style.WARNING(debug_msg))
                    logger.debug(debug_msg)
                finally:
                    loop.close()
                    # Reset to no event loop
                    asyncio.set_event_loop(None)
                
                if zones_data:
                    debug_msg = f'  zones_data type: {type(zones_data)}, length: {len(zones_data) if isinstance(zones_data, (list, dict)) else "N/A"}'
                    self.stdout.write(self.style.WARNING(debug_msg))
                    logger.debug(debug_msg)
                    
                    debug_msg2 = f'  zones_data content: {zones_data}'
                    self.stdout.write(self.style.WARNING(debug_msg2))
                    logger.debug(debug_msg2)
                    
                    # Use atomic transaction to prevent race conditions during zone updates
                    from django.db import transaction
                    
                    with transaction.atomic():
                        # Instead of deleting all zones, we'll update existing ones and create new ones
                        # This preserves zone IDs and prevents UI flickering
                        
                        zones_created = 0
                        zones_updated = 0
                        rules_created = 0
                        
                        # Get existing zones for this agent
                        existing_zones = {zone.name: zone for zone in agent.zones.all()}
                        processed_zone_names = set()
                        
                        # Process each zone (zones_data is a list of zone names)
                        for zone_name in zones_data:
                            logger.debug(f'  Processing zone: {zone_name}')
                            
                            # Skip if not a string
                            if not isinstance(zone_name, str):
                                logger.warning(f'  Skipping non-string zone: {zone_name} (type: {type(zone_name)})')
                                continue
                            
                            processed_zone_names.add(zone_name)
                            logger.debug(f'  Added {zone_name} to processed_zone_names')
                            
                            # Get zone details using a new event loop
                            try:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                
                                try:
                                    zone_result = loop.run_until_complete(
                                        manager.execute_command('get_zone', {'zone': zone_name}, module='firewalld')
                                    )
                                    logger.debug(f'  get_zone({zone_name}) returned: success={zone_result.get("success")}')
                                finally:
                                    loop.close()
                                    asyncio.set_event_loop(None)
                                
                                if not zone_result.get('success'):
                                    logger.warning(f'  Failed to get zone {zone_name}: {zone_result.get("error")}')
                                    continue
                                
                                zone_config = zone_result.get('result', {})
                                logger.debug(f'  Zone config for {zone_name}: {len(str(zone_config))} chars')
                            except Exception as e:
                                error_msg = f'    Could not get details for zone {zone_name}: {e}'
                                self.stdout.write(self.style.WARNING(error_msg))
                                logger.error(error_msg, exc_info=True)
                                continue
                            
                            # Parse the config text (format: {zone: "name", config: "text block"})
                            config_text = zone_config.get('config', '')
                            
                            # Extract configuration by parsing the text
                            services = []
                            ports = []
                            interfaces = []
                            sources = []
                            masquerade = False
                            target = 'default'
                            
                            for line in config_text.split('\n'):
                                line = line.strip()
                                if line.startswith('services:'):
                                    services = [s for s in line.replace('services:', '').strip().split() if s]
                                elif line.startswith('ports:'):
                                    port_line = line.replace('ports:', '').strip()
                                    ports = [p for p in port_line.split() if p]
                                elif line.startswith('interfaces:'):
                                    interfaces = [i for i in line.replace('interfaces:', '').strip().split() if i]
                                elif line.startswith('sources:'):
                                    source_line = line.replace('sources:', '').strip()
                                    sources = [s for s in source_line.split() if s]
                                elif line.startswith('masquerade:'):
                                    masquerade = 'yes' in line.lower()
                                elif line.startswith('target:'):
                                    target = line.replace('target:', '').strip()
                            
                            # Update existing zone or create new one
                            zone, created = FirewallZone.objects.update_or_create(
                                agent=agent,
                                name=zone_name,
                                defaults={
                                    'target': target,
                                    'interfaces': interfaces,
                                    'sources': sources,
                                    'services': services,
                                    'ports': ports,
                                    'masquerade': masquerade
                                }
                            )
                            
                            action = "Created" if created else "Updated"
                            logger.debug(f'  {action} zone: {zone_name} (ID: {zone.id})')
                            
                            if created:
                                zones_created += 1
                            else:
                                zones_updated += 1
                            
                            # Delete existing rules for this zone before creating new ones
                            zone.rules.all().delete()
                            
                            # Create rules for services
                            for service in services:
                                FirewallRule.objects.create(
                                    agent=agent,
                                    zone=zone,
                                    rule_type='service',
                                    service=service,
                                    enabled=True,
                                    permanent=True,
                                )
                                rules_created += 1
                            
                            # Create rules for ports
                            for port_spec in ports:
                                # Parse port specification (e.g., "80/tcp", "8080-8090/udp")
                                if '/' in port_spec:
                                    port, protocol = port_spec.split('/', 1)
                                else:
                                    port, protocol = port_spec, 'tcp'
                                
                                FirewallRule.objects.create(
                                    agent=agent,
                                    zone=zone,
                                    rule_type='port',
                                    port=port,
                                    protocol=protocol,
                                    enabled=True,
                                    permanent=True,
                                )
                                rules_created += 1
                        
                        # Delete zones that no longer exist on the agent
                        zones_deleted = 0
                        logger.debug(f'  Checking for zones to delete...')
                        logger.debug(f'  Existing zones: {list(existing_zones.keys())}')
                        logger.debug(f'  Processed zones: {list(processed_zone_names)}')
                        
                        for existing_zone_name, existing_zone_obj in existing_zones.items():
                            if existing_zone_name not in processed_zone_names:
                                logger.info(f'  Deleting zone {existing_zone_name} (no longer on agent)')
                                existing_zone_obj.delete()
                                zones_deleted += 1
                        
                        logger.info(f'  Sync summary: {zones_created} created, {zones_updated} updated, {zones_deleted} deleted')
                        
                        # End of transaction - all zones and rules updated/created atomically
                    
                    if zones_created > 0:
                        synced_items.append(f'{zones_created} zones created')
                    if zones_updated > 0:
                        synced_items.append(f'{zones_updated} zones updated')
                    if zones_deleted > 0:
                        synced_items.append(f'{zones_deleted} zones deleted')
                    synced_items.append(f'{rules_created} rules')
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'  Could not sync firewall zones: {str(e)}')
                )
                logger.error(f'  Failed to sync firewall zones: {str(e)}', exc_info=True)
        
        # Close connection if needed
        if hasattr(manager, 'close') and callable(getattr(manager, 'close')):
            manager.close()
        
        if not synced_items:
            raise Exception('No data could be synced from agent')
        
        self.stdout.write(
            self.style.SUCCESS(f'  Synced: {", ".join(synced_items)}')
        )
