"""
Management command to auto-sync firewall configurations from agents.
Run this periodically via cron or as a daemon.
"""
import asyncio
import time
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from agents.models import Agent, FirewallZone, FirewallRule
from agents.connection_managers import get_connection_manager


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
            self.stdout.write(self.style.SUCCESS(
                f'Starting auto-sync daemon (checking every {check_interval} seconds)...'
            ))
            while True:
                self.sync_agents()
                time.sleep(check_interval)
        else:
            self.sync_agents()

    def sync_agents(self):
        """Sync agents that are due for synchronization."""
        now = timezone.now()
        
        # Get agents that need syncing
        agents = Agent.objects.filter(
            sync_interval_seconds__gt=0,  # Only agents with sync enabled
            status__in=['online', 'approved']  # Only active agents
        )
        
        for agent in agents:
            # Check if agent is due for sync
            if agent.last_sync:
                time_since_sync = (now - agent.last_sync).total_seconds()
                if time_since_sync < agent.sync_interval_seconds:
                    continue  # Not due yet
            
            self.stdout.write(
                self.style.WARNING(f'Syncing agent: {agent.hostname}')
            )
            
            try:
                self.sync_agent(agent)
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Successfully synced {agent.hostname}')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Failed to sync {agent.hostname}: {str(e)}')
                )

    def sync_agent(self, agent):
        """Sync a single agent's configuration - sync what's available."""
        # Get the appropriate connection manager
        manager = get_connection_manager(agent)
        
        synced_items = []
        
        # Always try to update agent metadata (system info)
        try:
            status_info = asyncio.run(manager.test_connection())
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
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'  Could not sync system info: {str(e)}')
            )
        
        # Try to get firewall zones if firewalld module is available
        if 'firewalld' in (agent.available_modules or []):
            try:
                zones_data = asyncio.run(manager.get_zones())
                
                if zones_data:
                    # Clear existing zones and rules for this agent
                    FirewallZone.objects.filter(agent=agent).delete()
                    
                    zones_created = 0
                    rules_created = 0
                    
                    # Process each zone
                    for zone_info in zones_data:
                        zone_name = zone_info.get('name', '')
                        zone_details = zone_info.get('details', '')
                        
                        if not zone_name:
                            continue
                        
                        # Parse zone details
                        services = []
                        ports = []
                        interfaces = []
                        sources = []
                        masquerade = False
                        target = 'default'
                        
                        for line in zone_details.split('\n'):
                            line = line.strip()
                            if line.startswith('services:'):
                                services = [s for s in line.replace('services:', '').strip().split() if s]
                            elif line.startswith('ports:'):
                                ports = [p for p in line.replace('ports:', '').strip().split() if p]
                            elif line.startswith('interfaces:'):
                                interfaces = [i for i in line.replace('interfaces:', '').strip().split() if i]
                            elif line.startswith('sources:'):
                                sources = [s for s in line.replace('sources:', '').strip().split() if s]
                            elif line.startswith('masquerade:'):
                                masquerade = 'yes' in line.lower()
                            elif line.startswith('target:'):
                                target = line.replace('target:', '').strip()
                        
                        # Create zone
                        zone = FirewallZone.objects.create(
                            agent=agent,
                            name=zone_name,
                            target=target,
                            interfaces=interfaces,
                            sources=sources,
                            services=services,
                            ports=ports,
                            masquerade=masquerade
                        )
                        zones_created += 1
                        
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
                    
                    synced_items.append(f'{zones_created} zones')
                    synced_items.append(f'{rules_created} rules')
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'  Could not sync firewall zones: {str(e)}')
                )
        
        # Close connection if needed
        if hasattr(manager, 'close') and callable(getattr(manager, 'close')):
            manager.close()
        
        if not synced_items:
            raise Exception('No data could be synced from agent')
        
        self.stdout.write(
            self.style.SUCCESS(f'  Synced: {", ".join(synced_items)}')
        )
