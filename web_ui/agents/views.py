from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
import json
import httpx
import asyncio
from datetime import datetime

from .models import Agent, FirewallZone, FirewallRule, AgentConnection, AgentCommand, DirectRule
from .forms import AgentForm
from .serializers import (
    AgentSerializer, FirewallZoneSerializer, FirewallRuleSerializer,
    AgentConnectionSerializer, AgentCommandSerializer
)
from .connection_managers import get_connection_manager


class AgentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing agents."""
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Agent.objects.all()
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset


class FirewallZoneViewSet(viewsets.ModelViewSet):
    """ViewSet for managing firewall zones."""
    serializer_class = FirewallZoneSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        agent_id = self.kwargs['agent_id']
        return FirewallZone.objects.filter(agent_id=agent_id)
    
    def perform_create(self, serializer):
        agent_id = self.kwargs['agent_id']
        agent = get_object_or_404(Agent, id=agent_id)
        serializer.save(agent=agent)


class FirewallRuleViewSet(viewsets.ModelViewSet):
    """ViewSet for managing firewall rules."""
    serializer_class = FirewallRuleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        agent_id = self.kwargs['agent_id']
        return FirewallRule.objects.filter(agent_id=agent_id)
    
    def perform_create(self, serializer):
        agent_id = self.kwargs['agent_id']
        agent = get_object_or_404(Agent, id=agent_id)
        serializer.save(agent=agent, created_by=self.request.user)


class AgentCommandViewSet(viewsets.ModelViewSet):
    """ViewSet for managing agent commands."""
    serializer_class = AgentCommandSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        agent_id = self.kwargs['agent_id']
        return AgentCommand.objects.filter(agent_id=agent_id)
    
    def perform_create(self, serializer):
        agent_id = self.kwargs['agent_id']
        agent = get_object_or_404(Agent, id=agent_id)
        serializer.save(agent=agent, created_by=self.request.user)


class ConnectionListCreateView(APIView):
    """View for listing and creating agent connections."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        connections = AgentConnection.objects.all()
        serializer = AgentConnectionSerializer(connections, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = AgentConnectionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConnectionDetailView(APIView):
    """View for retrieving, updating, and deleting agent connections."""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, connection_id):
        return get_object_or_404(AgentConnection, id=connection_id)
    
    def get(self, request, connection_id):
        connection = self.get_object(connection_id)
        serializer = AgentConnectionSerializer(connection)
        return Response(serializer.data)
    
    def put(self, request, connection_id):
        connection = self.get_object(connection_id)
        serializer = AgentConnectionSerializer(connection, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, connection_id):
        connection = self.get_object(connection_id)
        connection.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def agent_status(request, agent_id):
    """Get real-time status from an agent."""
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        # Send status request to agent based on connection type
        if agent.connection_type in ['server_to_agent', 'ssh']:
            # Direct communication with agent
            async def get_status():
                async with httpx.AsyncClient() as client:
                    if agent.connection_type == 'ssh':
                        # For SSH, we need to use connection manager
                        # For now, return basic info
                        return {
                            'status': 'connected',
                            'connection_type': 'ssh',
                            'message': 'SSH status check not yet implemented'
                        }
                    else:
                        # Direct HTTPS connection to agent
                        url = f"https://{agent.ip_address}:{agent.agent_port}/api/status"
                        response = await client.get(url, timeout=10, verify=False)
                        return response.json()
            
            # Run async function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(get_status())
            loop.close()
            
            return JsonResponse(result)
        else:
            # For pull mode, create a command and wait for result
            command = AgentCommand.objects.create(
                agent=agent,
                command_type='get_status',
                parameters={},
                created_by=request.user
            )
            
            return JsonResponse({
                'status': 'command_queued',
                'command_id': str(command.id),
                'message': 'Status request queued for agent'
            })
            
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'status': 'error'
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_agent(request, agent_id):
    """Approve a pending agent."""
    agent = get_object_or_404(Agent, id=agent_id)
    
    if agent.status == 'pending':
        agent.status = 'offline'  # Change to offline, ready for connection
    
    agent.save()
    
    return JsonResponse({
        'message': 'Agent approved successfully',
        'agent_id': str(agent.id),
        'status': agent.status
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_agent(request, agent_id):
    """Reject a pending agent."""
    agent = get_object_or_404(Agent, id=agent_id)
    
    if agent.status != 'pending':
        return JsonResponse({
            'error': 'Agent is not in pending status'
        }, status=400)
    
    agent.status = 'rejected'
    agent.save()
    
    return JsonResponse({
        'message': 'Agent rejected',
        'agent_id': str(agent.id)
    })


# Template views for the web interface
# NOTE: agent_list and agent_detail views removed - using dashboard.views versions instead
# - agent_list: /dashboard/agents/ (dashboard.views.agent_list)
# - agent_detail: /dashboard/agents/<id>/ (dashboard.views.agent_detail)


@login_required
@require_http_methods(['POST'])
def agent_module_toggle(request, agent_id, module_name):
    """Toggle module enabled/disabled for a specific agent."""
    from modules.models import Module, AgentModule
    from shared.modules.registry import registry
    
    agent = get_object_or_404(Agent, id=agent_id)
    module_state = get_object_or_404(Module, name=module_name)
    
    # Get or create agent module
    agent_module, created = AgentModule.objects.get_or_create(
        agent=agent,
        module=module_state,
        defaults={'enabled': False, 'available': False}
    )
    
    # Toggle enabled status
    was_enabled = agent_module.enabled
    agent_module.enabled = not agent_module.enabled
    agent_module.save()
    
    module = registry.get(module_name)
    status = "enabled" if agent_module.enabled else "disabled"
    
    # If enabling the module, trigger module-specific initialization
    if agent_module.enabled and not was_enabled and module:
        try:
            # Call module's on_enable hook if it exists
            if hasattr(module, 'on_enable'):
                result = module.on_enable(agent)
                if result and isinstance(result, dict):
                    success_msg = result.get('message', f'Module "{module.display_name}" {status} for {agent.hostname}')
                    messages.success(request, success_msg)
                else:
                    messages.success(request, f'Module "{module.display_name}" {status} for {agent.hostname}')
            else:
                messages.success(request, f'Module "{module.display_name}" {status} for {agent.hostname}')
        except Exception as e:
            messages.warning(request, f'Module "{module.display_name}" {status}, but initialization failed: {str(e)}')
    else:
        messages.success(request, f'Module "{module.display_name if module else module_name}" {status} for {agent.hostname}')
    
    return redirect('agent-detail', agent_id=agent_id)


@login_required
def agent_create(request):
    """Create a new agent."""
    if request.method == 'POST':
        form = AgentForm(request.POST)
        if form.is_valid():
            agent = form.save(commit=False)
            # Manually created agents should be approved by default
            # The "pending" status is for agents that register themselves
            agent.status = 'offline'  # Default to offline, will become online when connection succeeds
            agent.save()
            messages.success(request, f'Agent {agent.hostname} created successfully!')
            return redirect('agent-detail', agent_id=agent.id)
    else:
        form = AgentForm()
    
    return render(request, 'agents/create.html', {'form': form})


@login_required
def agent_edit(request, agent_id):
    """Edit an existing agent."""
    agent = get_object_or_404(Agent, id=agent_id)
    
    if request.method == 'POST':
        form = AgentForm(request.POST, instance=agent)
        if form.is_valid():
            agent = form.save()
            messages.success(request, f'Agent {agent.hostname} updated successfully!')
            return redirect('agent-detail', agent_id=agent.id)
    else:
        form = AgentForm(instance=agent)
    
    return render(request, 'agents/edit.html', {
        'form': form, 
        'agent': agent
    })


@login_required
def agent_quick_add(request):
    """Add a new agent (redirects to standard create form)."""
    # Simply redirect to the standard create form - we only have one form now
    return redirect('agent-create')


@login_required
@require_http_methods(['POST'])
def agent_test_connection(request, agent_id):
    """Test connection to an agent."""
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        # Import connection managers
        from .connection_managers import get_connection_manager
        from datetime import datetime
        
        # Get the appropriate connection manager
        manager = get_connection_manager(agent)
        
        # Test the connection
        result = asyncio.run(manager.test_connection())
        
        # Update agent status based on connection test result
        if result.get('success'):
            agent.status = 'online'
            agent.last_seen = datetime.now()
            agent.save(update_fields=['status', 'last_seen'])
        else:
            agent.status = 'offline'
            agent.save(update_fields=['status'])
        
        # Close connection if needed (for SSH)
        if hasattr(manager, 'close') and callable(getattr(manager, 'close')):
            manager.close()
        
        return JsonResponse(result)
        
    except Exception as e:
        # Mark agent as offline on connection error
        agent.status = 'offline'
        agent.save(update_fields=['status'])
        
        return JsonResponse({
            'success': False,
            'error': f'Connection test failed: {str(e)}'
        })


@login_required
def agent_zones_data(request, agent_id):
    """Get agent zones and rules data for dynamic updates."""
    agent = get_object_or_404(Agent, id=agent_id)
    
    # Get all zones with proper ordering to ensure consistent results
    zones = agent.zones.all().order_by('name')
    
    # Debug: Log the zone count
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"agent_zones_data: Fetched {zones.count()} zones for agent {agent.hostname}")
    
    zones_data = []
    for zone in zones:
        # Ensure services and ports are lists
        services = zone.services if isinstance(zone.services, list) else []
        ports = zone.ports if isinstance(zone.ports, list) else []
        
        # Get permanent status for each service and port
        services_with_status = []
        for service in services:
            if not service:  # Skip empty strings
                continue
            # Check if there's a rule for this service in this zone
            rule = zone.rules.filter(rule_type='service', service=service).first()
            services_with_status.append({
                'name': service,
                'permanent': rule.permanent if rule else True
            })
        
        ports_with_status = []
        for port_spec in ports:
            if not port_spec:  # Skip empty strings
                continue
            # Check if there's a rule for this port in this zone
            if '/' in port_spec:
                port, protocol = port_spec.split('/', 1)
            else:
                port, protocol = port_spec, 'tcp'
            
            rule = zone.rules.filter(rule_type='port', port=port, protocol=protocol).first()
            ports_with_status.append({
                'spec': port_spec,
                'permanent': rule.permanent if rule else True
            })
        
        zones_data.append({
            'id': zone.id,
            'name': zone.name,
            'services': services,  # Ensured list
            'services_with_status': services_with_status,
            'ports': ports,  # Ensured list
            'ports_with_status': ports_with_status,
            'interfaces': zone.interfaces if isinstance(zone.interfaces, list) else [],
            'sources': zone.sources if isinstance(zone.sources, list) else [],
            'masquerade': zone.masquerade,
            'target': zone.target,
            'description': zone.description,
        })
    
    # Also get all rules grouped by service/port name
    rules = agent.rules.all()
    rules_by_name = {}
    
    for rule in rules:
        if rule.rule_type == 'service':
            key = f"service:{rule.service}"
            name = rule.service
        elif rule.rule_type == 'port':
            key = f"port:{rule.port}/{rule.protocol}"
            name = f"{rule.port}/{rule.protocol}"
        else:
            continue
            
        if key not in rules_by_name:
            rules_by_name[key] = {
                'name': name,
                'type': rule.rule_type,
                'zones': [],
                'count': 0
            }
        
        rules_by_name[key]['zones'].append({
            'zone_id': rule.zone.id,
            'zone_name': rule.zone.name,
            'rule_id': str(rule.id)
        })
        rules_by_name[key]['count'] += 1
    
    return JsonResponse({
        'success': True,
        'zones': zones_data,
        'rules_grouped': list(rules_by_name.values()),
        'last_sync': agent.last_sync.isoformat() if agent.last_sync else None,
        'zones_count': zones.count()
    })


@login_required
def agent_status_data(request, agent_id):
    """Get agent status and metadata for dynamic updates."""
    agent = get_object_or_404(Agent, id=agent_id)
    
    return JsonResponse({
        'success': True,
        'status': agent.status,
        'last_seen': agent.last_seen.isoformat() if agent.last_seen else None,
        'last_sync': agent.last_sync.isoformat() if agent.last_sync else None,
        'operating_system': agent.operating_system or '',
        'version': agent.version or '',
        'available_modules': agent.available_modules or [],
    })


@login_required
def agent_available_services(request, agent_id):
    """Get list of available firewalld services for this agent."""
    agent = get_object_or_404(Agent, id=agent_id)
    
    return JsonResponse({
        'success': True,
        'services': agent.available_services if agent.available_services else []
    })


@login_required
@require_http_methods(['POST'])
def agent_sync_firewall(request, agent_id):
    """Bidirectional sync: Push interface changes to agent, then pull current state."""
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        # Get the appropriate connection manager
        manager = get_connection_manager(agent)
        
        # STEP 1: Apply all pending changes from interface to agent
        zones_in_db = FirewallZone.objects.filter(agent=agent)
        
        for zone in zones_in_db:
            # Ensure zone exists on agent (get_zones will tell us)
            pass  # We'll verify after getting zones
        
        # STEP 2: Get current state from agent
        zones_data = asyncio.run(manager.get_zones())
        
        if not zones_data:
            return JsonResponse({
                'success': False,
                'error': 'Failed to retrieve zones from agent'
            })
        
        # STEP 2.5: Get available services from agent and store them
        try:
            available_services = asyncio.run(manager.get_available_services())
            if available_services:
                agent.available_services = available_services
                # Don't save yet, we'll save at the end
        except:
            # If we can't get services, just continue with empty list
            pass
        
        # STEP 3: Build a map of what's on the agent
        agent_zones = {}
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
            
            agent_zones[zone_name] = {
                'target': target,
                'interfaces': interfaces,
                'sources': sources,
                'services': services,
                'ports': ports,
                'masquerade': masquerade
            }
        
        # STEP 4: Sync interface changes to agent
        changes_applied = 0
        for zone in zones_in_db:
            if zone.name not in agent_zones:
                # Zone doesn't exist on agent, skip (we'll handle zone creation separately)
                continue
            
            agent_zone = agent_zones[zone.name]
            
            # Sync services: add missing ones to agent
            for service in zone.services:
                if service not in agent_zone['services']:
                    try:
                        asyncio.run(manager.execute_command('add-service', {
                            'service': service,
                            'zone': zone.name
                        }))
                        changes_applied += 1
                    except:
                        pass  # Continue even if one fails
            
            # Sync ports: add missing ones to agent
            for port_spec in zone.ports:
                if port_spec not in agent_zone['ports']:
                    try:
                        asyncio.run(manager.execute_command('add-port', {
                            'port': port_spec,
                            'zone': zone.name
                        }))
                        changes_applied += 1
                    except:
                        pass
        
        # STEP 5: Re-fetch zones after applying changes
        zones_data = asyncio.run(manager.get_zones())
        
        # STEP 6: Clear and rebuild database with current agent state
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
                    created_by=request.user
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
                    created_by=request.user
                )
                rules_created += 1
        
        # Close connection if needed
        if hasattr(manager, 'close') and callable(getattr(manager, 'close')):
            manager.close()
        
        # Update agent status and sync time
        agent.last_seen = datetime.now()
        agent.last_sync = datetime.now()
        agent.status = 'online'
        agent.save()
        
        message = f'Successfully synced {zones_created} zones and {rules_created} rules'
        if changes_applied > 0:
            message += f'. Applied {changes_applied} changes to agent'
        
        return JsonResponse({
            'success': True,
            'message': message,
            'zones_created': zones_created,
            'rules_created': rules_created,
            'changes_applied': changes_applied
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Sync failed: {str(e)}'
        })


def test_ssh_connection(agent):
    """Test SSH connection to agent."""
    import paramiko
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        connect_kwargs = {
            'hostname': agent.ip_address,
            'port': agent.port,
            'username': agent.ssh_username,
            'timeout': 10,
        }
        
        if agent.ssh_key_path:
            connect_kwargs['key_filename'] = agent.ssh_key_path
        elif agent.ssh_password:
            connect_kwargs['password'] = agent.ssh_password
        
        ssh.connect(**connect_kwargs)
        
        # Test firewalld availability
        stdin, stdout, stderr = ssh.exec_command('systemctl is-active firewalld')
        firewalld_status = stdout.read().decode().strip()
        
        ssh.close()
        
        return {
            'success': True,
            'connection_type': 'SSH',
            'firewalld_active': firewalld_status == 'active',
            'message': f'SSH connection successful. Firewalld status: {firewalld_status}'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'SSH connection failed: {str(e)}'
        }


def test_agent_connection(agent):
    """Test HTTP connection to agent."""
    import requests
    
    try:
        url = f"http://{agent.ip_address}:{agent.agent_port}/health"
        headers = {}
        
        if agent.agent_api_key:
            headers['Authorization'] = f'Bearer {agent.agent_api_key}'
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return {
                'success': True,
                'connection_type': 'HTTP Agent',
                'agent_version': data.get('version', 'Unknown'),
                'message': 'Agent connection successful'
            }
        else:
            return {
                'success': False,
                'error': f'Agent returned status code: {response.status_code}'
            }
    except Exception as e:
        return {
            'success': False,
            'error': f'Agent connection failed: {str(e)}'
        }


def test_server_connection(agent):
    """Test if agent has connected to server recently."""
    from datetime import datetime, timedelta
    
    if agent.last_seen:
        time_diff = datetime.now() - agent.last_seen.replace(tzinfo=None)
        if time_diff < timedelta(minutes=5):
            return {
                'success': True,
                'connection_type': 'Agent to Server',
                'last_seen': agent.last_seen.isoformat(),
                'message': 'Agent connected recently'
            }
    
    return {
        'success': False,
        'error': 'Agent has not connected recently or never connected'
    }


@login_required
@require_http_methods(['POST'])
def rule_add(request, agent_id):
    """Add a new firewall rule to an agent."""
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        data = json.loads(request.body)
        zone_id = data.get('zone_id')
        rule_type = data.get('rule_type')
        
        zone = get_object_or_404(FirewallZone, id=zone_id, agent=agent)
        
        # Create the rule
        rule_data = {
            'agent': agent,
            'zone': zone,
            'rule_type': rule_type,
            'enabled': data.get('enabled', True),
            'permanent': data.get('permanent', True),
            'created_by': request.user
        }
        
        # Add type-specific fields
        if rule_type == 'service':
            rule_data['service'] = data.get('service', '')
        elif rule_type == 'port':
            rule_data['port'] = data.get('port', '')
            rule_data['protocol'] = data.get('protocol', 'tcp')
        elif rule_type == 'rich':
            rule_data['rich_rule'] = data.get('rich_rule', '')
        elif rule_type == 'forward':
            rule_data['port'] = data.get('port', '')
            rule_data['protocol'] = data.get('protocol', 'tcp')
            rule_data['to_port'] = data.get('to_port', '')
            rule_data['to_addr'] = data.get('to_addr', '')
        
        rule = FirewallRule.objects.create(**rule_data)
        
        # Apply the rule to the agent if connection is available
        manager = get_connection_manager(agent)
        
        # Build firewall command based on rule type
        if rule_type == 'service':
            command = f'add-service'
            parameters = {'service': rule.service, 'zone': zone.name}
        elif rule_type == 'port':
            command = f'add-port'
            parameters = {'port': f"{rule.port}/{rule.protocol}", 'zone': zone.name}
        else:
            command = None
            parameters = {}
        
        if command:
            result = asyncio.run(manager.execute_command(command, parameters))
        
        return JsonResponse({
            'success': True,
            'message': f'Rule added successfully',
            'rule_id': str(rule.id)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to add rule: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def rule_delete(request, agent_id, rule_id):
    """Delete a firewall rule from an agent."""
    agent = get_object_or_404(Agent, id=agent_id)
    rule = get_object_or_404(FirewallRule, id=rule_id, agent=agent)
    
    try:
        # Apply the deletion to the agent if connection is available
        manager = get_connection_manager(agent)
        
        # Build firewall command based on rule type
        if rule.rule_type == 'service':
            command = f'remove-service'
            parameters = {'service': rule.service, 'zone': rule.zone.name}
        elif rule.rule_type == 'port':
            command = f'remove-port'
            parameters = {'port': f"{rule.port}/{rule.protocol}", 'zone': rule.zone.name}
        else:
            command = None
            parameters = {}
        
        if command:
            result = asyncio.run(manager.execute_command(command, parameters))
        
        # Delete from database
        rule.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Rule deleted successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to delete rule: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def rules_bulk_delete(request, agent_id):
    """Delete multiple firewall rules (bulk delete by service/port name)."""
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        data = json.loads(request.body)
        rule_ids = data.get('rule_ids', [])
        name = data.get('name', '')
        rule_type = data.get('type', '')
        
        if not rule_ids:
            return JsonResponse({
                'success': False,
                'error': 'No rule IDs provided'
            })
        
        # Get all rules
        rules = FirewallRule.objects.filter(id__in=rule_ids, agent=agent)
        
        if not rules.exists():
            return JsonResponse({
                'success': False,
                'error': 'No matching rules found'
            })
        
        # Get connection manager
        manager = get_connection_manager(agent)
        deleted_count = 0
        errors = []
        
        # Delete each rule
        for rule in rules:
            try:
                # Build firewall command based on rule type
                if rule.rule_type == 'service':
                    command = 'remove-service'
                    parameters = {'service': rule.service, 'zone': rule.zone.name}
                    # Also remove from zone.services
                    if rule.service in rule.zone.services:
                        rule.zone.services.remove(rule.service)
                        rule.zone.save()
                elif rule.rule_type == 'port':
                    command = 'remove-port'
                    port_spec = f"{rule.port}/{rule.protocol}"
                    parameters = {'port': port_spec, 'zone': rule.zone.name}
                    # Also remove from zone.ports
                    if port_spec in rule.zone.ports:
                        rule.zone.ports.remove(port_spec)
                        rule.zone.save()
                else:
                    continue
                
                # Execute command on agent
                try:
                    asyncio.run(manager.execute_command(command, parameters))
                except Exception as cmd_error:
                    errors.append(f"Zone {rule.zone.name}: {str(cmd_error)}")
                
                # Delete from database
                rule.delete()
                deleted_count += 1
                
            except Exception as e:
                errors.append(f"Rule {rule.id}: {str(e)}")
                continue
        
        # Close connection if needed
        if hasattr(manager, 'close') and callable(getattr(manager, 'close')):
            manager.close()
        
        message = f'Successfully deleted {deleted_count} rule(s)'
        if errors:
            message += f'. Errors: {"; ".join(errors[:3])}'
        
        return JsonResponse({
            'success': True,
            'message': message,
            'deleted_count': deleted_count,
            'errors': errors if errors else None
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to delete rules: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def zone_add_service(request, agent_id, zone_id):
    """Add a service to a firewall zone."""
    from .models import AuditLog
    
    agent = get_object_or_404(Agent, id=agent_id)
    zone = get_object_or_404(FirewallZone, id=zone_id, agent=agent)
    
    try:
        data = json.loads(request.body)
        service = data.get('service', '')
        
        if not service:
            return JsonResponse({
                'success': False,
                'error': 'Service name is required'
            })
        
        # Add service to zone
        if service not in zone.services:
            zone.services.append(service)
            zone.save()
        
        # Create a rule for the service
        rule = FirewallRule.objects.create(
            agent=agent,
            zone=zone,
            rule_type='service',
            service=service,
            enabled=True,
            permanent=True,
            created_by=request.user
        )
        
        # Apply to agent
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('add-service', {
            'service': service,
            'zone': zone.name
        }))
        
        # Mark reload required for runtime-only changes
        if not data.get('permanent', True):
            agent.firewall_reload_required = True
            agent.save(update_fields=['firewall_reload_required'])
        
        # Log the action
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='add_service',
            agent=agent,
            params={'zone': zone.name, 'service': service},
            result=result,
            success=True,
            action_category='create',
            severity='info',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Service {service} added to zone {zone.name}'
        })
        
    except Exception as e:
        # Log the failure
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='add_service',
            agent=agent,
            params={'zone': zone.name, 'service': service},
            success=False,
            error_message=str(e),
            action_category='create',
            severity='warning',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': False,
            'error': f'Failed to add service: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def zone_remove_service(request, agent_id, zone_id, service):
    """Remove a service from a firewall zone."""
    from .models import AuditLog
    
    agent = get_object_or_404(Agent, id=agent_id)
    zone = get_object_or_404(FirewallZone, id=zone_id, agent=agent)
    
    try:
        # Remove service from zone
        if service in zone.services:
            zone.services.remove(service)
            zone.save()
        
        # Delete associated rules
        FirewallRule.objects.filter(
            agent=agent,
            zone=zone,
            rule_type='service',
            service=service
        ).delete()
        
        # Apply to agent
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('remove-service', {
            'service': service,
            'zone': zone.name
        }))
        
        # Mark reload required for runtime-only changes
        agent.firewall_reload_required = True
        agent.save(update_fields=['firewall_reload_required'])
        
        # Log the action
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='remove_service',
            agent=agent,
            params={'zone': zone.name, 'service': service},
            result=result,
            success=True,
            action_category='delete',
            severity='info',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Service {service} removed from zone {zone.name}'
        })
        
    except Exception as e:
        # Log the failure
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='remove_service',
            agent=agent,
            params={'zone': zone.name, 'service': service},
            success=False,
            error_message=str(e),
            action_category='delete',
            severity='warning',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': False,
            'error': f'Failed to remove service: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def zone_add_port(request, agent_id, zone_id):
    """Add a port to a firewall zone."""
    agent = get_object_or_404(Agent, id=agent_id)
    zone = get_object_or_404(FirewallZone, id=zone_id, agent=agent)
    
    try:
        data = json.loads(request.body)
        port = data.get('port', '')
        protocol = data.get('protocol', 'tcp')
        port_spec = f"{port}/{protocol}"
        
        if not port:
            return JsonResponse({
                'success': False,
                'error': 'Port is required'
            })
        
        # Add port to zone
        if port_spec not in zone.ports:
            zone.ports.append(port_spec)
            zone.save()
        
        # Create a rule for the port
        rule = FirewallRule.objects.create(
            agent=agent,
            zone=zone,
            rule_type='port',
            port=port,
            protocol=protocol,
            enabled=True,
            permanent=True,
            created_by=request.user
        )
        
        # Apply to agent
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('add-port', {
            'port': port_spec,
            'zone': zone.name
        }))
        
        return JsonResponse({
            'success': True,
            'message': f'Port {port_spec} added to zone {zone.name}'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to add port: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def zone_remove_port(request, agent_id, zone_id):
    """Remove a port from a firewall zone."""
    agent = get_object_or_404(Agent, id=agent_id)
    zone = get_object_or_404(FirewallZone, id=zone_id, agent=agent)
    
    try:
        data = json.loads(request.body)
        port_spec = data.get('port_spec', '')  # e.g., "80/tcp"
        
        if not port_spec:
            return JsonResponse({
                'success': False,
                'error': 'Port specification is required'
            })
        
        # Parse port specification
        if '/' in port_spec:
            port, protocol = port_spec.split('/', 1)
        else:
            port, protocol = port_spec, 'tcp'
        
        # Remove port from zone
        if port_spec in zone.ports:
            zone.ports.remove(port_spec)
            zone.save()
        
        # Delete associated rules
        FirewallRule.objects.filter(
            agent=agent,
            zone=zone,
            rule_type='port',
            port=port,
            protocol=protocol
        ).delete()
        
        # Apply to agent
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('remove-port', {
            'port': port_spec,
            'zone': zone.name
        }))
        
        return JsonResponse({
            'success': True,
            'message': f'Port {port_spec} removed from zone {zone.name}'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to remove port: {str(e)}'
        })


@login_required
@require_http_methods(['GET'])
def zone_list_icmptypes(request, agent_id):
    """List available ICMP types."""
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('list_icmptypes', {}))
        
        if result.get('success'):
            return JsonResponse({
                'success': True,
                'icmptypes': result.get('data', {}).get('icmptypes', [])
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Failed to list ICMP types')
            })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to list ICMP types: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def zone_add_icmp_block(request, agent_id, zone_id):
    """Add ICMP block to a zone."""
    from .models import AuditLog
    
    agent = get_object_or_404(Agent, id=agent_id)
    zone = get_object_or_404(FirewallZone, id=zone_id, agent=agent)
    
    try:
        data = json.loads(request.body)
        icmp_type = data.get('icmp_type', '').strip()
        permanent = data.get('permanent', True)
        
        if not icmp_type:
            return JsonResponse({
                'success': False,
                'error': 'ICMP type is required'
            })
        
        # Add ICMP block via agent
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('add_icmp_block', {
            'zone': zone.name,
            'icmp_type': icmp_type,
            'permanent': permanent
        }))
        
        if not result.get('success'):
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Failed to add ICMP block')
            })
        
        # Update zone model
        if icmp_type not in zone.icmp_blocks:
            zone.icmp_blocks.append(icmp_type)
            zone.save()
        
        # Mark firewall reload required
        agent.firewall_reload_required = True
        agent.save(update_fields=['firewall_reload_required'])
        
        # Log the action
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='add_icmp_block',
            agent=agent,
            params={'zone': zone.name, 'icmp_type': icmp_type, 'permanent': permanent},
            result=result,
            success=True,
            action_category='configure',
            severity='medium',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': True,
            'message': f'ICMP block {icmp_type} added to zone {zone.name}'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to add ICMP block: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def zone_remove_icmp_block(request, agent_id, zone_id, icmp_type):
    """Remove ICMP block from a zone."""
    from .models import AuditLog
    
    agent = get_object_or_404(Agent, id=agent_id)
    zone = get_object_or_404(FirewallZone, id=zone_id, agent=agent)
    
    try:
        permanent = True  # Always make permanent
        
        # Remove ICMP block via agent
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('remove_icmp_block', {
            'zone': zone.name,
            'icmp_type': icmp_type,
            'permanent': permanent
        }))
        
        if not result.get('success'):
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Failed to remove ICMP block')
            })
        
        # Update zone model
        if icmp_type in zone.icmp_blocks:
            zone.icmp_blocks.remove(icmp_type)
            zone.save()
        
        # Mark firewall reload required
        agent.firewall_reload_required = True
        agent.save(update_fields=['firewall_reload_required'])
        
        # Log the action
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='remove_icmp_block',
            agent=agent,
            params={'zone': zone.name, 'icmp_type': icmp_type, 'permanent': permanent},
            result=result,
            success=True,
            action_category='configure',
            severity='medium',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': True,
            'message': f'ICMP block {icmp_type} removed from zone {zone.name}'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to remove ICMP block: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def zone_toggle_icmp_inversion(request, agent_id, zone_id):
    """Toggle ICMP block inversion for a zone."""
    from .models import AuditLog
    
    agent = get_object_or_404(Agent, id=agent_id)
    zone = get_object_or_404(FirewallZone, id=zone_id, agent=agent)
    
    try:
        data = json.loads(request.body)
        enabled = data.get('enabled', False)
        permanent = data.get('permanent', True)
        
        action = 'add_icmp_block_inversion' if enabled else 'remove_icmp_block_inversion'
        
        # Toggle ICMP inversion via agent
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command(action, {
            'zone': zone.name,
            'permanent': permanent
        }))
        
        if not result.get('success'):
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Failed to toggle ICMP inversion')
            })
        
        # Update zone model
        zone.icmp_block_inversion = enabled
        zone.save()
        
        # Mark firewall reload required
        agent.firewall_reload_required = True
        agent.save(update_fields=['firewall_reload_required'])
        
        # Log the action
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action=action,
            agent=agent,
            params={'zone': zone.name, 'enabled': enabled, 'permanent': permanent},
            result=result,
            success=True,
            action_category='configure',
            severity='medium',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': True,
            'message': f'ICMP inversion {"enabled" if enabled else "disabled"} for zone {zone.name}'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to toggle ICMP inversion: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def zone_create(request, agent_id):
    """Create a new firewall zone."""
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        data = json.loads(request.body)
        zone_name = data.get('name', '').strip()
        target = data.get('target', 'default')
        
        if not zone_name:
            return JsonResponse({
                'success': False,
                'error': 'Zone name is required'
            })
        
        # Check if zone already exists
        if FirewallZone.objects.filter(agent=agent, name=zone_name).exists():
            return JsonResponse({
                'success': False,
                'error': f'Zone "{zone_name}" already exists'
            })
        
        # Create zone on agent first
        manager = get_connection_manager(agent)
        
        try:
            # Use firewall-cmd to create new zone
            result = asyncio.run(manager.execute_command('new-zone', {
                'zone': zone_name
            }))
            
            # Set target if specified
            if target and target != 'default':
                asyncio.run(manager.execute_command('set-target', {
                    'zone': zone_name,
                    'target': target
                }))
                
        except Exception as cmd_error:
            return JsonResponse({
                'success': False,
                'error': f'Failed to create zone on agent: {str(cmd_error)}'
            })
        
        # Create zone in database
        zone = FirewallZone.objects.create(
            agent=agent,
            name=zone_name,
            target=target,
            interfaces=[],
            sources=[],
            services=[],
            ports=[],
            masquerade=False
        )
        
        # Close connection if needed
        if hasattr(manager, 'close') and callable(getattr(manager, 'close')):
            manager.close()
        
        return JsonResponse({
            'success': True,
            'message': f'Zone "{zone_name}" created successfully',
            'zone_id': zone.id
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to create zone: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def zone_delete(request, agent_id, zone_id):
    """Delete a firewall zone."""
    agent = get_object_or_404(Agent, id=agent_id)
    zone = get_object_or_404(FirewallZone, id=zone_id, agent=agent)
    
    try:
        zone_name = zone.name
        
        # Delete zone from agent first
        manager = get_connection_manager(agent)
        
        try:
            result = asyncio.run(manager.execute_command('delete-zone', {
                'zone': zone_name
            }))
        except Exception as cmd_error:
            return JsonResponse({
                'success': False,
                'error': f'Failed to delete zone from agent: {str(cmd_error)}'
            })
        
        # Delete from database (this will cascade delete all rules)
        zone.delete()
        
        # Close connection if needed
        if hasattr(manager, 'close') and callable(getattr(manager, 'close')):
            manager.close()
        
        return JsonResponse({
            'success': True,
            'message': f'Zone "{zone_name}" deleted successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to delete zone: {str(e)}'
        })


@login_required
def audit_log_list(request):
    """Display audit logs with filtering."""
    from django.core.paginator import Paginator
    from .models import AuditLog
    
    # Get filter parameters
    module_filter = request.GET.get('module', '')
    action_category_filter = request.GET.get('action_category', '')
    success_filter = request.GET.get('success', '')
    severity_filter = request.GET.get('severity', '')
    user_filter = request.GET.get('user', '')
    agent_filter = request.GET.get('agent', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search_query = request.GET.get('q', '')
    
    # Build queryset
    logs = AuditLog.objects.all().select_related('user', 'agent', 'command')
    
    # Apply filters
    if module_filter:
        logs = logs.filter(module=module_filter)
    
    if action_category_filter:
        logs = logs.filter(action_category=action_category_filter)
    
    if success_filter:
        logs = logs.filter(success=(success_filter.lower() == 'true'))
    
    if severity_filter:
        logs = logs.filter(severity=severity_filter)
    
    if user_filter:
        logs = logs.filter(username__icontains=user_filter)
    
    if agent_filter:
        logs = logs.filter(agent_hostname__icontains=agent_filter)
    
    if date_from:
        from django.utils.dateparse import parse_datetime
        dt_from = parse_datetime(date_from)
        if dt_from:
            logs = logs.filter(timestamp__gte=dt_from)
    
    if date_to:
        from django.utils.dateparse import parse_datetime
        dt_to = parse_datetime(date_to)
        if dt_to:
            logs = logs.filter(timestamp__lte=dt_to)
    
    if search_query:
        from django.db.models import Q
        logs = logs.filter(
            Q(description__icontains=search_query) |
            Q(action__icontains=search_query) |
            Q(error_message__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(logs, 50)  # 50 logs per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get unique values for filter dropdowns
    modules = AuditLog.objects.values_list('module', flat=True).distinct().order_by('module')
    
    context = {
        'page_obj': page_obj,
        'modules': modules,
        'action_categories': AuditLog.ACTION_CATEGORIES,
        'severity_levels': AuditLog.SEVERITY_LEVELS,
        'filters': {
            'module': module_filter,
            'action_category': action_category_filter,
            'success': success_filter,
            'severity': severity_filter,
            'user': user_filter,
            'agent': agent_filter,
            'date_from': date_from,
            'date_to': date_to,
            'q': search_query,
        }
    }
    
    return render(request, 'agents/audit_log_list.html', context)


@login_required
def audit_log_detail(request, audit_id):
    """Display detailed information about a specific audit log entry."""
    from .models import AuditLog
    
    log = get_object_or_404(AuditLog, id=audit_id)
    
    context = {
        'log': log,
    }
    
    return render(request, 'agents/audit_log_detail.html', context)


@login_required
def agent_audit_logs(request, agent_id):
    """Display audit logs for a specific agent (AJAX endpoint)."""
    from django.core.paginator import Paginator
    from .models import AuditLog
    
    agent = get_object_or_404(Agent, id=agent_id)
    
    # Get logs for this agent
    logs = AuditLog.objects.filter(agent=agent).select_related('user', 'command')
    
    # Optional: filter by module
    module_filter = request.GET.get('module', '')
    if module_filter:
        logs = logs.filter(module=module_filter)
    
    # Pagination
    paginator = Paginator(logs, 20)  # 20 logs per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Return JSON for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        logs_data = [{
            'id': str(log.id),
            'timestamp': log.timestamp.isoformat(),
            'username': log.username,
            'module': log.module,
            'action': log.action,
            'success': log.success,
            'description': log.description,
            'severity': log.severity,
            'action_category': log.action_category,
        } for log in page_obj]
        
        return JsonResponse({
            'logs': logs_data,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'total_count': paginator.count,
            'page_number': page_obj.number,
            'total_pages': paginator.num_pages,
        })
    
    # Return HTML for regular requests
    context = {
        'agent': agent,
        'page_obj': page_obj,
    }
    
    return render(request, 'agents/agent_audit_logs.html', context)


@login_required
@require_http_methods(['POST'])
def agent_firewall_reload(request, agent_id):
    """Reload firewall configuration on an agent."""
    from .models import AuditLog
    from django.utils import timezone
    
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        data = json.loads(request.body)
        reload_type = data.get('reload_type', 'reload')  # reload, complete_reload, runtime_to_permanent
        
        # Execute reload command
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command(reload_type, {}))
        
        if result.get('success'):
            # Update agent reload status
            agent.firewall_reload_required = False
            agent.last_firewall_reload = timezone.now()
            agent.save(update_fields=['firewall_reload_required', 'last_firewall_reload'])
            
            # Log the action
            AuditLog.log(
                user=request.user,
                module='firewalld',
                action=reload_type,
                agent=agent,
                params={'reload_type': reload_type},
                result=result,
                success=True,
                action_category='configure',
                severity='info',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Firewall {reload_type.replace("_", " ")} completed successfully'
            })
        else:
            # Log the failure
            AuditLog.log(
                user=request.user,
                module='firewalld',
                action=reload_type,
                agent=agent,
                params={'reload_type': reload_type},
                success=False,
                error_message=result.get('error', 'Unknown error'),
                action_category='configure',
                severity='warning',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error')
            })
        
    except Exception as e:
        # Log the exception
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='reload',
            agent=agent,
            params={'reload_type': reload_type},
            success=False,
            error_message=str(e),
            action_category='configure',
            severity='critical',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': False,
            'error': f'Failed to reload firewall: {str(e)}'
        })


@login_required
@require_http_methods(['GET'])
def agent_check_config(request, agent_id):
    """Check firewall configuration for errors."""
    from .models import AuditLog
    
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        # Execute check config command
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('check_config', {}))
        
        # Log the check
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='check_config',
            agent=agent,
            params={},
            result=result,
            success=result.get('success', False),
            action_category='read',
            severity='info',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to check configuration: {str(e)}'
        })


@login_required
@require_http_methods(['GET'])
def agent_firewalld_service_status(request, agent_id):
    """Get firewalld service status."""
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('service_status', {}))
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to get service status: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def agent_firewalld_service_control(request, agent_id):
    """Control firewalld service (start/stop/restart)."""
    from .models import AuditLog
    from django.utils import timezone
    
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        data = json.loads(request.body)
        action = data.get('action')  # start_service, stop_service, restart_service
        
        if action not in ['start_service', 'stop_service', 'restart_service']:
            return JsonResponse({
                'success': False,
                'error': 'Invalid action. Must be start_service, stop_service, or restart_service'
            })
        
        # Execute service control command
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command(action, {}))
        
        # Log the action
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action=action,
            agent=agent,
            params={'action': action},
            result=result,
            success=result.get('success', False),
            action_category='configure',
            severity='high' if action == 'stop_service' else 'medium',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        if result.get('success'):
            return JsonResponse({
                'success': True,
                'message': result.get('data', {}).get('message', f'Service {action.replace("_service", "")}ed successfully'),
                'data': result.get('data', {})
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error')
            })
        
    except Exception as e:
        # Log the exception
        from .models import AuditLog
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action=action if 'action' in locals() else 'service_control',
            agent=agent,
            params={'action': action if 'action' in locals() else 'unknown'},
            success=False,
            error_message=str(e),
            action_category='configure',
            severity='critical',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': False,
            'error': f'Failed to control service: {str(e)}'
        })


@login_required
@require_http_methods(['GET'])
def agent_panic_status(request, agent_id):
    """Get panic mode status."""
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('query_panic', {}))
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to get panic status: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def agent_panic_control(request, agent_id):
    """Control panic mode (enable/disable)."""
    from .models import AuditLog
    
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        data = json.loads(request.body)
        action = data.get('action')  # panic_on, panic_off
        
        if action not in ['panic_on', 'panic_off']:
            return JsonResponse({
                'success': False,
                'error': 'Invalid action. Must be panic_on or panic_off'
            })
        
        # Execute panic mode command
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command(action, {}))
        
        # Log the action with CRITICAL severity
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action=action,
            agent=agent,
            params={'action': action},
            result=result,
            success=result.get('success', False),
            action_category='configure',
            severity='critical',  # Panic mode is always critical
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        if result.get('success'):
            return JsonResponse({
                'success': True,
                'message': result.get('data', {}).get('message', f'Panic mode {action.replace("panic_", "")}'),
                'data': result.get('data', {})
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error')
            })
        
    except Exception as e:
        # Log the exception
        from .models import AuditLog
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action=action if 'action' in locals() else 'panic_control',
            agent=agent,
            params={'action': action if 'action' in locals() else 'unknown'},
            success=False,
            error_message=str(e),
            action_category='configure',
            severity='critical',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': False,
            'error': f'Failed to control panic mode: {str(e)}'
        })


@login_required
@require_http_methods(['GET'])
def agent_log_denied_status(request, agent_id):
    """Get log denied packets setting for an agent."""
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('get_log_denied', {}))
        
        if result.get('success'):
            return JsonResponse({
                'success': True,
                'data': result.get('data', {})
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error')
            })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to get log denied status: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def agent_log_denied_control(request, agent_id):
    """Set log denied packets setting for an agent."""
    from .models import AuditLog
    
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        data = json.loads(request.body)
        value = data.get('value', '').strip().lower()
        
        valid_values = ['all', 'unicast', 'broadcast', 'multicast', 'off']
        if value not in valid_values:
            return JsonResponse({
                'success': False,
                'error': f'Invalid value. Must be one of: {", ".join(valid_values)}'
            })
        
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('set_log_denied', {'value': value}))
        
        # Log the action
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='set_log_denied',
            agent=agent,
            params={'value': value},
            success=result.get('success', False),
            error_message=result.get('error'),
            action_category='configure',
            severity='medium',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        if result.get('success'):
            return JsonResponse({
                'success': True,
                'message': result.get('data', {}).get('message', f'Log denied set to: {value}'),
                'data': result.get('data', {})
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error')
            })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        })
    except Exception as e:
        # Log the exception
        from .models import AuditLog
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='set_log_denied',
            agent=agent,
            params={'value': value if 'value' in locals() else 'unknown'},
            success=False,
            error_message=str(e),
            action_category='configure',
            severity='medium',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': False,
            'error': f'Failed to set log denied: {str(e)}'
        })


@login_required
def agent_services_page(request, agent_id):
    """Render the services management page for an agent."""
    agent = get_object_or_404(Agent, id=agent_id)
    return render(request, 'agents/services_list.html', {'agent': agent})


@login_required
@require_http_methods(['GET'])
def agent_list_services(request, agent_id):
    """List all available firewalld services for an agent."""
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('list_services', {}))
        
        if result.get('success'):
            return JsonResponse({
                'success': True,
                'data': result.get('data', {})
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error')
            })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to list services: {str(e)}'
        })


@login_required
@require_http_methods(['GET'])
def agent_service_detail(request, agent_id, service_name):
    """Get detailed information about a specific service."""
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('get_service_info', {'service': service_name}))
        
        if result.get('success'):
            return JsonResponse({
                'success': True,
                'data': result.get('data', {})
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error')
            })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to get service info: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def agent_service_create(request, agent_id):
    """Create a new custom service."""
    from .models import AuditLog, CustomService
    
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        data = json.loads(request.body)
        service_name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        
        if not service_name:
            return JsonResponse({
                'success': False,
                'error': 'Service name is required'
            })
        
        # Validate service name
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', service_name):
            return JsonResponse({
                'success': False,
                'error': 'Service name can only contain letters, numbers, hyphens, and underscores'
            })
        
        # Create service on agent
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('new_service', {'service': service_name}))
        
        # Log the action
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='new_service',
            agent=agent,
            params={'service': service_name, 'description': description},
            success=result.get('success', False),
            error_message=result.get('error'),
            action_category='create',
            severity='medium',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        if result.get('success'):
            # Create CustomService record
            custom_service = CustomService.objects.create(
                agent=agent,
                name=service_name,
                description=description,
                created_by=request.user
            )
            
            return JsonResponse({
                'success': True,
                'message': result.get('data', {}).get('message', f'Service {service_name} created'),
                'service_id': str(custom_service.id)
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error')
            })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        })
    except Exception as e:
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='new_service',
            agent=agent,
            params={'service': service_name if 'service_name' in locals() else 'unknown'},
            success=False,
            error_message=str(e),
            action_category='create',
            severity='medium',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': False,
            'error': f'Failed to create service: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def agent_service_delete(request, agent_id, service_name):
    """Delete a custom service."""
    from .models import AuditLog, CustomService
    
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        # Delete service on agent
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('delete_service', {'service': service_name}))
        
        # Log the action
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='delete_service',
            agent=agent,
            params={'service': service_name},
            success=result.get('success', False),
            error_message=result.get('error'),
            action_category='delete',
            severity='medium',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        if result.get('success'):
            # Delete CustomService record if it exists
            CustomService.objects.filter(agent=agent, name=service_name).delete()
            
            return JsonResponse({
                'success': True,
                'message': result.get('data', {}).get('message', f'Service {service_name} deleted')
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error')
            })
        
    except Exception as e:
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='delete_service',
            agent=agent,
            params={'service': service_name},
            success=False,
            error_message=str(e),
            action_category='delete',
            severity='medium',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': False,
            'error': f'Failed to delete service: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def agent_service_add_port(request, agent_id, service_name):
    """Add a port to a service definition."""
    from .models import AuditLog
    
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        data = json.loads(request.body)
        port = data.get('port', '').strip()
        protocol = data.get('protocol', 'tcp').strip().lower()
        
        if not port:
            return JsonResponse({
                'success': False,
                'error': 'Port is required'
            })
        
        if protocol not in ['tcp', 'udp']:
            return JsonResponse({
                'success': False,
                'error': 'Protocol must be tcp or udp'
            })
        
        # Add port to service
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('service_add_port', {
            'service': service_name,
            'port': port,
            'protocol': protocol
        }))
        
        # Log the action
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='service_add_port',
            agent=agent,
            params={'service': service_name, 'port': port, 'protocol': protocol},
            success=result.get('success', False),
            error_message=result.get('error'),
            action_category='update',
            severity='low',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        if result.get('success'):
            return JsonResponse({
                'success': True,
                'message': result.get('data', {}).get('message', f'Port {port}/{protocol} added')
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error')
            })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to add port: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def agent_service_remove_port(request, agent_id, service_name):
    """Remove a port from a service definition."""
    from .models import AuditLog
    
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        data = json.loads(request.body)
        port = data.get('port', '').strip()
        protocol = data.get('protocol', 'tcp').strip().lower()
        
        if not port:
            return JsonResponse({
                'success': False,
                'error': 'Port is required'
            })
        
        # Remove port from service
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('service_remove_port', {
            'service': service_name,
            'port': port,
            'protocol': protocol
        }))
        
        # Log the action
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='service_remove_port',
            agent=agent,
            params={'service': service_name, 'port': port, 'protocol': protocol},
            success=result.get('success', False),
            error_message=result.get('error'),
            action_category='update',
            severity='low',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        if result.get('success'):
            return JsonResponse({
                'success': True,
                'message': result.get('data', {}).get('message', f'Port {port}/{protocol} removed')
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error')
            })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to remove port: {str(e)}'
        })


@login_required
def agent_ipsets_page(request, agent_id):
    """Render the IPSets management page for an agent."""
    agent = get_object_or_404(Agent, id=agent_id)
    return render(request, 'agents/ipsets_list.html', {'agent': agent})


@login_required
@require_http_methods(['GET'])
def agent_list_ipsets(request, agent_id):
    """List all IPSets for an agent."""
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('list_ipsets', {}))
        
        if result.get('success'):
            return JsonResponse({
                'success': True,
                'data': result.get('data', {})
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error')
            })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to list IPSets: {str(e)}'
        })


@login_required
@require_http_methods(['GET'])
def agent_ipset_detail(request, agent_id, ipset_name):
    """Get detailed information about a specific IPSet."""
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('get_ipset_info', {'ipset': ipset_name}))
        
        if result.get('success'):
            return JsonResponse({
                'success': True,
                'data': result.get('data', {})
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error')
            })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to get IPSet info: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def agent_ipset_create(request, agent_id):
    """Create a new IPSet."""
    from .models import AuditLog, IPSet
    
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        data = json.loads(request.body)
        ipset_name = data.get('name', '').strip()
        ipset_type = data.get('type', '').strip()
        description = data.get('description', '').strip()
        
        if not ipset_name or not ipset_type:
            return JsonResponse({
                'success': False,
                'error': 'IPSet name and type are required'
            })
        
        # Validate IPSet name
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', ipset_name):
            return JsonResponse({
                'success': False,
                'error': 'IPSet name can only contain letters, numbers, hyphens, and underscores'
            })
        
        # Create IPSet on agent
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('new_ipset', {
            'ipset': ipset_name,
            'type': ipset_type
        }))
        
        # Log the action
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='new_ipset',
            agent=agent,
            params={'ipset': ipset_name, 'type': ipset_type, 'description': description},
            success=result.get('success', False),
            error_message=result.get('error'),
            action_category='create',
            severity='medium',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        if result.get('success'):
            # Create IPSet record in database
            ipset = IPSet.objects.create(
                agent=agent,
                name=ipset_name,
                ipset_type=ipset_type,
                description=description,
                created_by=request.user
            )
            
            return JsonResponse({
                'success': True,
                'message': result.get('data', {}).get('message', f'IPSet {ipset_name} created'),
                'ipset_id': str(ipset.id)
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error')
            })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        })
    except Exception as e:
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='new_ipset',
            agent=agent,
            params={'ipset': ipset_name if 'ipset_name' in locals() else 'unknown'},
            success=False,
            error_message=str(e),
            action_category='create',
            severity='medium',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': False,
            'error': f'Failed to create IPSet: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def agent_ipset_delete(request, agent_id, ipset_name):
    """Delete an IPSet."""
    from .models import AuditLog, IPSet
    
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        # Delete IPSet on agent
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('delete_ipset', {'ipset': ipset_name}))
        
        # Log the action
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='delete_ipset',
            agent=agent,
            params={'ipset': ipset_name},
            success=result.get('success', False),
            error_message=result.get('error'),
            action_category='delete',
            severity='medium',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        if result.get('success'):
            # Delete IPSet record from database
            IPSet.objects.filter(agent=agent, name=ipset_name).delete()
            
            return JsonResponse({
                'success': True,
                'message': result.get('data', {}).get('message', f'IPSet {ipset_name} deleted')
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error')
            })
        
    except Exception as e:
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='delete_ipset',
            agent=agent,
            params={'ipset': ipset_name},
            success=False,
            error_message=str(e),
            action_category='delete',
            severity='medium',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': False,
            'error': f'Failed to delete IPSet: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def agent_ipset_add_entry(request, agent_id, ipset_name):
    """Add entry to an IPSet."""
    from .models import AuditLog
    
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        data = json.loads(request.body)
        entry = data.get('entry', '').strip()
        
        if not entry:
            return JsonResponse({
                'success': False,
                'error': 'Entry is required'
            })
        
        # Add entry to IPSet
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('ipset_add_entry', {
            'ipset': ipset_name,
            'entry': entry
        }))
        
        # Log the action
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='ipset_add_entry',
            agent=agent,
            params={'ipset': ipset_name, 'entry': entry},
            success=result.get('success', False),
            error_message=result.get('error'),
            action_category='update',
            severity='low',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        if result.get('success'):
            return JsonResponse({
                'success': True,
                'message': result.get('data', {}).get('message', f'Entry {entry} added')
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error')
            })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to add entry: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def agent_ipset_remove_entry(request, agent_id, ipset_name):
    """Remove entry from an IPSet."""
    from .models import AuditLog
    
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        data = json.loads(request.body)
        entry = data.get('entry', '').strip()
        
        if not entry:
            return JsonResponse({
                'success': False,
                'error': 'Entry is required'
            })
        
        # Remove entry from IPSet
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('ipset_remove_entry', {
            'ipset': ipset_name,
            'entry': entry
        }))
        
        # Log the action
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='ipset_remove_entry',
            agent=agent,
            params={'ipset': ipset_name, 'entry': entry},
            success=result.get('success', False),
            error_message=result.get('error'),
            action_category='update',
            severity='low',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        if result.get('success'):
            return JsonResponse({
                'success': True,
                'message': result.get('data', {}).get('message', f'Entry {entry} removed')
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error')
            })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to remove entry: {str(e)}'
        })


@login_required
@require_http_methods(['GET'])
def agent_list_helpers(request, agent_id):
    """List all available helper modules."""
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('list_helpers', {}))
        
        if result.get('success'):
            return JsonResponse({
                'success': True,
                'data': result.get('data', {})
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Failed to list helpers')
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to list helpers: {str(e)}'
        })


@login_required
@require_http_methods(['GET'])
def zone_list_helpers(request, agent_id, zone_name):
    """List helper modules enabled in a zone."""
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('zone_list_helpers', {
            'zone': zone_name
        }))
        
        if result.get('success'):
            return JsonResponse({
                'success': True,
                'data': result.get('data', {})
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Failed to list helpers')
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to list helpers: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def zone_add_helper(request, agent_id, zone_name):
    """Add helper module to zone."""
    from .models import AuditLog
    
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        data = json.loads(request.body)
        helper = data.get('helper', '').strip()
        permanent = data.get('permanent', False)
        
        if not helper:
            return JsonResponse({
                'success': False,
                'error': 'Helper name is required'
            })
        
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('zone_add_helper', {
            'zone': zone_name,
            'helper': helper,
            'permanent': permanent
        }))
        
        # Log the action
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='zone_add_helper',
            agent=agent,
            params={'zone': zone_name, 'helper': helper, 'permanent': permanent},
            success=result.get('success', False),
            error_message=result.get('error'),
            action_category='update',
            severity='medium',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        if result.get('success'):
            return JsonResponse({
                'success': True,
                'message': result.get('data', {}).get('message', f'Helper {helper} added')
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error')
            })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to add helper: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def zone_remove_helper(request, agent_id, zone_name):
    """Remove helper module from zone."""
    from .models import AuditLog
    
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        data = json.loads(request.body)
        helper = data.get('helper', '').strip()
        permanent = data.get('permanent', False)
        
        if not helper:
            return JsonResponse({
                'success': False,
                'error': 'Helper name is required'
            })
        
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('zone_remove_helper', {
            'zone': zone_name,
            'helper': helper,
            'permanent': permanent
        }))
        
        # Log the action
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='zone_remove_helper',
            agent=agent,
            params={'zone': zone_name, 'helper': helper, 'permanent': permanent},
            success=result.get('success', False),
            error_message=result.get('error'),
            action_category='update',
            severity='medium',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        if result.get('success'):
            return JsonResponse({
                'success': True,
                'message': result.get('data', {}).get('message', f'Helper {helper} removed')
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error')
            })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to remove helper: {str(e)}'
        })


@login_required
@require_http_methods(['GET'])
def agent_policies_page(request, agent_id):
    """Render the policies management page."""
    agent = get_object_or_404(Agent, id=agent_id)
    return render(request, 'agents/policies_list.html', {'agent': agent})


@login_required
@require_http_methods(['GET'])
def agent_list_policies(request, agent_id):
    """List all firewall policies."""
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('list_policies', {}))
        
        if result.get('success'):
            return JsonResponse({
                'success': True,
                'data': result.get('data', {})
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Failed to list policies')
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to list policies: {str(e)}'
        })


@login_required
@require_http_methods(['GET'])
def agent_policy_detail(request, agent_id, policy_name):
    """Get detailed information about a policy."""
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('policy_get_info', {
            'policy': policy_name
        }))
        
        if result.get('success'):
            return JsonResponse({
                'success': True,
                'data': result.get('data', {})
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Failed to get policy info')
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to get policy info: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def agent_policy_create(request, agent_id):
    """Create a new firewall policy."""
    from .models import AuditLog, FirewallPolicy
    
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        data = json.loads(request.body)
        policy_name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        ingress_zone = data.get('ingress_zone', '').strip()
        egress_zone = data.get('egress_zone', '').strip()
        target = data.get('target', 'CONTINUE').strip()
        
        if not policy_name:
            return JsonResponse({
                'success': False,
                'error': 'Policy name is required'
            })
        
        if not ingress_zone or not egress_zone:
            return JsonResponse({
                'success': False,
                'error': 'Both ingress and egress zones are required'
            })
        
        # Validate target
        valid_targets = ['ACCEPT', 'REJECT', 'DROP', 'CONTINUE']
        if target not in valid_targets:
            return JsonResponse({
                'success': False,
                'error': f'Invalid target. Must be one of: {", ".join(valid_targets)}'
            })
        
        manager = get_connection_manager(agent)
        
        # Create policy
        result = asyncio.run(manager.execute_command('policy_add', {
            'policy': policy_name,
            'permanent': True
        }))
        
        if not result.get('success'):
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Failed to create policy')
            })
        
        # Set ingress zone
        result = asyncio.run(manager.execute_command('policy_set_ingress_zone', {
            'policy': policy_name,
            'zone': ingress_zone,
            'permanent': True
        }))
        
        if not result.get('success'):
            return JsonResponse({
                'success': False,
                'error': f'Failed to set ingress zone: {result.get("error")}'
            })
        
        # Set egress zone
        result = asyncio.run(manager.execute_command('policy_set_egress_zone', {
            'policy': policy_name,
            'zone': egress_zone,
            'permanent': True
        }))
        
        if not result.get('success'):
            return JsonResponse({
                'success': False,
                'error': f'Failed to set egress zone: {result.get("error")}'
            })
        
        # Set target
        result = asyncio.run(manager.execute_command('policy_set_target', {
            'policy': policy_name,
            'target': target,
            'permanent': True
        }))
        
        if not result.get('success'):
            return JsonResponse({
                'success': False,
                'error': f'Failed to set target: {result.get("error")}'
            })
        
        # Store in database
        policy = FirewallPolicy.objects.create(
            agent=agent,
            name=policy_name,
            description=description,
            ingress_zones=[ingress_zone],
            egress_zones=[egress_zone],
            target=target,
            created_by=request.user
        )
        
        # Log the action
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='policy_create',
            agent=agent,
            params={'policy': policy_name, 'ingress_zone': ingress_zone, 'egress_zone': egress_zone, 'target': target},
            success=True,
            action_category='create',
            severity='high',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Policy {policy_name} created successfully',
            'policy_id': str(policy.id)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to create policy: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def agent_policy_delete(request, agent_id, policy_name):
    """Delete a firewall policy."""
    from .models import AuditLog, FirewallPolicy
    
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('policy_delete', {
            'policy': policy_name,
            'permanent': True
        }))
        
        # Delete from database
        try:
            policy = FirewallPolicy.objects.get(agent=agent, name=policy_name)
            policy.delete()
        except FirewallPolicy.DoesNotExist:
            pass
        
        # Log the action
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='policy_delete',
            agent=agent,
            params={'policy': policy_name},
            success=result.get('success', False),
            error_message=result.get('error'),
            action_category='delete',
            severity='high',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        if result.get('success'):
            return JsonResponse({
                'success': True,
                'message': result.get('data', {}).get('message', f'Policy {policy_name} deleted')
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error')
            })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to delete policy: {str(e)}'
        })


# Template Management Views

@login_required
@require_http_methods(['GET'])
def template_list(request):
    """List all firewall templates."""
    from .models import FirewallTemplate
    
    # Filter by category if provided
    category = request.GET.get('category')
    search = request.GET.get('search', '').strip()
    
    templates = FirewallTemplate.objects.filter(is_active=True)
    
    # Apply filters
    if category:
        templates = templates.filter(category=category)
    
    if search:
        templates = templates.filter(
            models.Q(name__icontains=search) |
            models.Q(description__icontains=search) |
            models.Q(tags__icontains=search)
        )
    
    # Only show global templates or user's own templates
    templates = templates.filter(
        models.Q(is_global=True) | models.Q(created_by=request.user)
    )
    
    template_data = []
    for template in templates:
        template_data.append({
            'id': str(template.id),
            'name': template.name,
            'description': template.description,
            'category': template.category,
            'is_global': template.is_global,
            'usage_count': template.usage_count,
            'zones_count': len(template.get_zones()),
            'policies_count': template.get_policies_count(),
            'services_count': template.get_services_count(),
            'tags': template.tags,
            'created_at': template.created_at.isoformat(),
            'updated_at': template.updated_at.isoformat(),
            'created_by': template.created_by.username if template.created_by else None,
        })
    
    return JsonResponse({
        'success': True,
        'templates': template_data,
        'count': len(template_data)
    })


@login_required
@require_http_methods(['GET'])
def template_detail(request, template_id):
    """Get detailed information about a template."""
    from .models import FirewallTemplate
    
    try:
        template = FirewallTemplate.objects.get(id=template_id, is_active=True)
        
        # Check permissions
        if not template.is_global and template.created_by != request.user:
            return JsonResponse({
                'success': False,
                'error': 'Permission denied'
            }, status=403)
        
        return JsonResponse({
            'success': True,
            'template': {
                'id': str(template.id),
                'name': template.name,
                'description': template.description,
                'category': template.category,
                'configuration': template.configuration,
                'is_global': template.is_global,
                'usage_count': template.usage_count,
                'tags': template.tags,
                'created_at': template.created_at.isoformat(),
                'updated_at': template.updated_at.isoformat(),
                'created_by': template.created_by.username if template.created_by else None,
            }
        })
    except FirewallTemplate.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Template not found'
        }, status=404)


@login_required
@require_http_methods(['POST'])
def template_create(request):
    """Create a new firewall template."""
    from .models import FirewallTemplate, AuditLog
    
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        category = data.get('category', 'custom')
        configuration = data.get('configuration', {})
        tags = data.get('tags', [])
        is_global = data.get('is_global', False)
        
        if not name:
            return JsonResponse({
                'success': False,
                'error': 'Template name is required'
            })
        
        # Check if template name already exists
        if FirewallTemplate.objects.filter(name=name).exists():
            return JsonResponse({
                'success': False,
                'error': 'A template with this name already exists'
            })
        
        # Create template
        template = FirewallTemplate.objects.create(
            name=name,
            description=description,
            category=category,
            configuration=configuration,
            tags=tags,
            is_global=is_global,
            created_by=request.user
        )
        
        # Validate configuration
        errors = template.validate_configuration()
        if errors:
            template.delete()
            return JsonResponse({
                'success': False,
                'error': 'Invalid configuration',
                'validation_errors': errors
            })
        
        # Log the action
        AuditLog.log(
            user=request.user,
            module='templates',
            action='template_create',
            params={'template_id': str(template.id), 'name': name},
            success=True,
            action_category='create',
            severity='low',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Template "{name}" created successfully',
            'template_id': str(template.id)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to create template: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def template_update(request, template_id):
    """Update an existing firewall template."""
    from .models import FirewallTemplate, AuditLog
    
    try:
        template = FirewallTemplate.objects.get(id=template_id)
        
        # Check permissions
        if not template.created_by == request.user:
            return JsonResponse({
                'success': False,
                'error': 'Permission denied'
            }, status=403)
        
        data = json.loads(request.body)
        
        # Update fields
        if 'name' in data:
            name = data['name'].strip()
            if name and name != template.name:
                # Check if new name already exists
                if FirewallTemplate.objects.filter(name=name).exclude(id=template_id).exists():
                    return JsonResponse({
                        'success': False,
                        'error': 'A template with this name already exists'
                    })
                template.name = name
        
        if 'description' in data:
            template.description = data['description'].strip()
        
        if 'category' in data:
            template.category = data['category']
        
        if 'configuration' in data:
            template.configuration = data['configuration']
            # Validate configuration
            errors = template.validate_configuration()
            if errors:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid configuration',
                    'validation_errors': errors
                })
        
        if 'tags' in data:
            template.tags = data['tags']
        
        if 'is_global' in data:
            template.is_global = data['is_global']
        
        template.save()
        
        # Log the action
        AuditLog.log(
            user=request.user,
            module='templates',
            action='template_update',
            params={'template_id': str(template.id), 'name': template.name},
            success=True,
            action_category='update',
            severity='low',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Template "{template.name}" updated successfully'
        })
        
    except FirewallTemplate.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Template not found'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to update template: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def template_delete(request, template_id):
    """Delete a firewall template."""
    from .models import FirewallTemplate, AuditLog
    
    try:
        template = FirewallTemplate.objects.get(id=template_id)
        
        # Check permissions
        if not template.created_by == request.user:
            return JsonResponse({
                'success': False,
                'error': 'Permission denied'
            }, status=403)
        
        template_name = template.name
        template.is_active = False
        template.save()
        
        # Log the action
        AuditLog.log(
            user=request.user,
            module='templates',
            action='template_delete',
            params={'template_id': str(template.id), 'name': template_name},
            success=True,
            action_category='delete',
            severity='medium',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Template "{template_name}" deleted successfully'
        })
        
    except FirewallTemplate.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Template not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to delete template: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def template_duplicate(request, template_id):
    """Duplicate an existing firewall template."""
    from .models import FirewallTemplate, AuditLog
    
    try:
        original = FirewallTemplate.objects.get(id=template_id, is_active=True)
        
        # Check permissions
        if not original.is_global and original.created_by != request.user:
            return JsonResponse({
                'success': False,
                'error': 'Permission denied'
            }, status=403)
        
        # Generate unique name
        new_name = f"{original.name} (Copy)"
        counter = 1
        while FirewallTemplate.objects.filter(name=new_name).exists():
            counter += 1
            new_name = f"{original.name} (Copy {counter})"
        
        # Create duplicate
        duplicate = FirewallTemplate.objects.create(
            name=new_name,
            description=original.description,
            category=original.category,
            configuration=original.configuration.copy(),
            tags=original.tags.copy() if original.tags else [],
            is_global=False,  # Duplicates are always private
            created_by=request.user
        )
        
        # Log the action
        AuditLog.log(
            user=request.user,
            module='templates',
            action='template_duplicate',
            params={'original_id': str(original.id), 'duplicate_id': str(duplicate.id), 'name': new_name},
            success=True,
            action_category='create',
            severity='low',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Template duplicated as "{new_name}"',
            'template_id': str(duplicate.id)
        })
        
    except FirewallTemplate.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Template not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to duplicate template: {str(e)}'
        })


@login_required
@require_http_methods(['GET'])
def templates_page(request):
    """Render the templates management page."""
    return render(request, 'agents/templates_list.html')


@login_required
@require_http_methods(['POST'])
def template_preview(request, agent_id, template_id):
    """Preview changes that will be made when applying a template to an agent."""
    from .models import FirewallTemplate
    
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        template = FirewallTemplate.objects.get(id=template_id, is_active=True)
        
        # Check permissions
        if not template.is_global and template.created_by != request.user:
            return JsonResponse({
                'success': False,
                'error': 'Permission denied'
            }, status=403)
        
        # Get current agent configuration
        manager = get_connection_manager(agent)
        
        # Get current zones
        zones_result = asyncio.run(manager.execute_command('list_zones', {}))
        current_zones = zones_result.get('data', {}).get('zones', []) if zones_result.get('success') else []
        
        # Analyze changes
        changes = {
            'zones_to_configure': [],
            'zones_to_create': [],
            'services_to_add': [],
            'policies_to_create': [],
            'custom_services_to_create': [],
            'ipsets_to_create': [],
        }
        
        # Check zones
        template_zones = template.configuration.get('zones', {})
        for zone_name, zone_config in template_zones.items():
            if zone_name in current_zones:
                changes['zones_to_configure'].append({
                    'zone': zone_name,
                    'services': zone_config.get('services', []),
                    'ports': zone_config.get('ports', []),
                    'interfaces': zone_config.get('interfaces', []),
                    'sources': zone_config.get('sources', []),
                })
            else:
                changes['zones_to_create'].append(zone_name)
        
        # Custom services
        for service in template.configuration.get('custom_services', []):
            changes['custom_services_to_create'].append(service.get('name'))
        
        # Policies
        for policy in template.configuration.get('policies', []):
            changes['policies_to_create'].append(policy.get('name'))
        
        # IPSets
        for ipset in template.configuration.get('ipsets', []):
            changes['ipsets_to_create'].append(ipset.get('name'))
        
        return JsonResponse({
            'success': True,
            'template': {
                'id': str(template.id),
                'name': template.name,
                'description': template.description,
            },
            'changes': changes
        })
        
    except FirewallTemplate.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Template not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to preview template: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def template_apply(request, agent_id, template_id):
    """Apply a firewall template to an agent."""
    from .models import FirewallTemplate, AuditLog, CustomService, IPSet, FirewallPolicy
    
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        template = FirewallTemplate.objects.get(id=template_id, is_active=True)
        
        # Check permissions
        if not template.is_global and template.created_by != request.user:
            return JsonResponse({
                'success': False,
                'error': 'Permission denied'
            }, status=403)
        
        manager = get_connection_manager(agent)
        results = {
            'zones': {'success': 0, 'failed': 0, 'errors': []},
            'services': {'success': 0, 'failed': 0, 'errors': []},
            'policies': {'success': 0, 'failed': 0, 'errors': []},
            'ipsets': {'success': 0, 'failed': 0, 'errors': []},
        }
        
        # Apply custom services first
        for service_config in template.configuration.get('custom_services', []):
            service_name = service_config.get('name')
            try:
                # Check if service already exists
                existing = CustomService.objects.filter(agent=agent, name=service_name).first()
                if existing:
                    results['services']['failed'] += 1
                    results['services']['errors'].append(f"Service '{service_name}' already exists")
                    continue
                
                # Create service on agent
                result = asyncio.run(manager.execute_command('new_service', {
                    'service': service_name,
                    'permanent': True
                }))
                
                if result.get('success'):
                    # Add ports if specified
                    for port_proto in service_config.get('ports', []):
                        port, protocol = port_proto.split('/')
                        asyncio.run(manager.execute_command('service_add_port', {
                            'service': service_name,
                            'port': port,
                            'protocol': protocol,
                            'permanent': True
                        }))
                    
                    # Store in database
                    CustomService.objects.create(
                        agent=agent,
                        name=service_name,
                        description=service_config.get('description', ''),
                        ports=service_config.get('ports', []),
                        created_by=request.user
                    )
                    
                    results['services']['success'] += 1
                else:
                    results['services']['failed'] += 1
                    results['services']['errors'].append(f"Service '{service_name}': {result.get('error')}")
            except Exception as e:
                results['services']['failed'] += 1
                results['services']['errors'].append(f"Service '{service_name}': {str(e)}")
        
        # Apply IPSets
        for ipset_config in template.configuration.get('ipsets', []):
            ipset_name = ipset_config.get('name')
            try:
                # Check if IPSet already exists
                existing = IPSet.objects.filter(agent=agent, name=ipset_name).first()
                if existing:
                    results['ipsets']['failed'] += 1
                    results['ipsets']['errors'].append(f"IPSet '{ipset_name}' already exists")
                    continue
                
                # Create IPSet on agent
                result = asyncio.run(manager.execute_command('new_ipset', {
                    'ipset': ipset_name,
                    'type': ipset_config.get('type'),
                    'permanent': True
                }))
                
                if result.get('success'):
                    # Add entries if specified
                    for entry in ipset_config.get('entries', []):
                        asyncio.run(manager.execute_command('ipset_add_entry', {
                            'ipset': ipset_name,
                            'entry': entry
                        }))
                    
                    # Store in database
                    IPSet.objects.create(
                        agent=agent,
                        name=ipset_name,
                        ipset_type=ipset_config.get('type'),
                        description=ipset_config.get('description', ''),
                        entries=ipset_config.get('entries', []),
                        created_by=request.user
                    )
                    
                    results['ipsets']['success'] += 1
                else:
                    results['ipsets']['failed'] += 1
                    results['ipsets']['errors'].append(f"IPSet '{ipset_name}': {result.get('error')}")
            except Exception as e:
                results['ipsets']['failed'] += 1
                results['ipsets']['errors'].append(f"IPSet '{ipset_name}': {str(e)}")
        
        # Apply zone configurations
        for zone_name, zone_config in template.configuration.get('zones', {}).items():
            try:
                # Add services to zone
                for service in zone_config.get('services', []):
                    result = asyncio.run(manager.execute_command('add_service_to_zone', {
                        'zone': zone_name,
                        'service': service,
                        'permanent': True
                    }))
                    if result.get('success'):
                        results['zones']['success'] += 1
                    else:
                        results['zones']['failed'] += 1
                        results['zones']['errors'].append(f"Zone '{zone_name}' service '{service}': {result.get('error')}")
                
                # Add ports to zone
                for port_config in zone_config.get('ports', []):
                    result = asyncio.run(manager.execute_command('add_port_to_zone', {
                        'zone': zone_name,
                        'port': port_config.get('port'),
                        'protocol': port_config.get('protocol', 'tcp'),
                        'permanent': True
                    }))
                    if not result.get('success'):
                        results['zones']['errors'].append(f"Zone '{zone_name}' port: {result.get('error')}")
                
                # Add interfaces
                for interface in zone_config.get('interfaces', []):
                    result = asyncio.run(manager.execute_command('zone_add_interface', {
                        'zone': zone_name,
                        'interface': interface,
                        'permanent': True
                    }))
                    if not result.get('success'):
                        results['zones']['errors'].append(f"Zone '{zone_name}' interface '{interface}': {result.get('error')}")
                
                # Add sources
                for source in zone_config.get('sources', []):
                    result = asyncio.run(manager.execute_command('zone_add_source', {
                        'zone': zone_name,
                        'source': source,
                        'permanent': True
                    }))
                    if not result.get('success'):
                        results['zones']['errors'].append(f"Zone '{zone_name}' source '{source}': {result.get('error')}")
                
                # Add ICMP blocks
                for icmp_type in zone_config.get('icmp_blocks', []):
                    result = asyncio.run(manager.execute_command('zone_add_icmp_block', {
                        'zone': zone_name,
                        'icmp_type': icmp_type,
                        'permanent': True
                    }))
                    if not result.get('success'):
                        results['zones']['errors'].append(f"Zone '{zone_name}' ICMP block '{icmp_type}': {result.get('error')}")
                
                # Add helpers
                for helper in zone_config.get('helpers', []):
                    result = asyncio.run(manager.execute_command('zone_add_helper', {
                        'zone': zone_name,
                        'helper': helper,
                        'permanent': True
                    }))
                    if not result.get('success'):
                        results['zones']['errors'].append(f"Zone '{zone_name}' helper '{helper}': {result.get('error')}")
                
                # Set target if specified
                if 'target' in zone_config and zone_config['target'] != 'default':
                    result = asyncio.run(manager.execute_command('set_zone_target', {
                        'zone': zone_name,
                        'target': zone_config['target'],
                        'permanent': True
                    }))
                    if not result.get('success'):
                        results['zones']['errors'].append(f"Zone '{zone_name}' target: {result.get('error')}")
                
                # Set masquerade
                if zone_config.get('masquerade'):
                    result = asyncio.run(manager.execute_command('zone_add_masquerade', {
                        'zone': zone_name,
                        'permanent': True
                    }))
                    if not result.get('success'):
                        results['zones']['errors'].append(f"Zone '{zone_name}' masquerade: {result.get('error')}")
                
            except Exception as e:
                results['zones']['failed'] += 1
                results['zones']['errors'].append(f"Zone '{zone_name}': {str(e)}")
        
        # Apply policies
        for policy_config in template.configuration.get('policies', []):
            policy_name = policy_config.get('name')
            try:
                # Check if policy already exists
                existing = FirewallPolicy.objects.filter(agent=agent, name=policy_name).first()
                if existing:
                    results['policies']['failed'] += 1
                    results['policies']['errors'].append(f"Policy '{policy_name}' already exists")
                    continue
                
                # Create policy
                result = asyncio.run(manager.execute_command('policy_add', {
                    'policy': policy_name,
                    'permanent': True
                }))
                
                if result.get('success'):
                    # Set ingress zone
                    asyncio.run(manager.execute_command('policy_set_ingress_zone', {
                        'policy': policy_name,
                        'zone': policy_config.get('ingress_zone'),
                        'permanent': True
                    }))
                    
                    # Set egress zone
                    asyncio.run(manager.execute_command('policy_set_egress_zone', {
                        'policy': policy_name,
                        'zone': policy_config.get('egress_zone'),
                        'permanent': True
                    }))
                    
                    # Set target
                    asyncio.run(manager.execute_command('policy_set_target', {
                        'policy': policy_name,
                        'target': policy_config.get('target', 'CONTINUE'),
                        'permanent': True
                    }))
                    
                    # Store in database
                    FirewallPolicy.objects.create(
                        agent=agent,
                        name=policy_name,
                        ingress_zones=[policy_config.get('ingress_zone')],
                        egress_zones=[policy_config.get('egress_zone')],
                        target=policy_config.get('target', 'CONTINUE'),
                        created_by=request.user
                    )
                    
                    results['policies']['success'] += 1
                else:
                    results['policies']['failed'] += 1
                    results['policies']['errors'].append(f"Policy '{policy_name}': {result.get('error')}")
            except Exception as e:
                results['policies']['failed'] += 1
                results['policies']['errors'].append(f"Policy '{policy_name}': {str(e)}")
        
        # Reload firewall
        reload_result = asyncio.run(manager.execute_command('reload_firewall', {}))
        
        # Increment template usage count
        template.increment_usage()
        
        # Log the action
        AuditLog.log(
            user=request.user,
            module='templates',
            action='template_apply',
            agent=agent,
            params={'template_id': str(template.id), 'template_name': template.name},
            success=True,
            action_category='update',
            severity='high',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Template "{template.name}" applied successfully',
            'results': results,
            'reload_success': reload_result.get('success', False)
        })
        
    except FirewallTemplate.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Template not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to apply template: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def zone_create(request, agent_id):
    """Create a new firewall zone."""
    from .models import AuditLog
    
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        data = json.loads(request.body)
        zone_name = data.get('name', '').strip()
        permanent = data.get('permanent', True)
        
        if not zone_name:
            return JsonResponse({
                'success': False,
                'error': 'Zone name is required'
            })
        
        # Validate zone name (alphanumeric, hyphens, underscores)
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', zone_name):
            return JsonResponse({
                'success': False,
                'error': 'Zone name can only contain letters, numbers, hyphens, and underscores'
            })
        
        # Create zone on agent
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('new_zone', {
            'zone': zone_name,
            'permanent': permanent
        }))
        
        if result.get('success'):
            # Create zone in database
            zone = FirewallZone.objects.create(
                agent=agent,
                name=zone_name,
                description=data.get('description', ''),
                target=data.get('target', 'default'),
                services=[],
                ports=[],
                protocols=[],
                source_ports=[],
                interfaces=[],
                sources=[]
            )
            
            # Apply template settings if provided
            template = data.get('template')
            if template:
                template_settings = get_zone_template_settings(template)
                if template_settings:
                    # Apply services from template
                    for service in template_settings.get('services', []):
                        asyncio.run(manager.execute_command('add_service', {
                            'zone': zone_name,
                            'service': service,
                            'permanent': permanent
                        }))
                        zone.services.append(service)
                    
                    # Apply target from template
                    if template_settings.get('target'):
                        zone.target = template_settings['target']
                    
                    zone.save()
            
            # Mark reload required if not permanent
            if not permanent:
                agent.firewall_reload_required = True
                agent.save(update_fields=['firewall_reload_required'])
            
            # Log the action
            AuditLog.log(
                user=request.user,
                module='firewalld',
                action='create_zone',
                agent=agent,
                params={'zone': zone_name, 'permanent': permanent, 'template': template},
                result=result,
                success=True,
                action_category='create',
                severity='info',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Zone {zone_name} created successfully',
                'zone_id': zone.id
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error')
            })
        
    except Exception as e:
        # Log the failure
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='create_zone',
            agent=agent,
            params={'zone': zone_name if 'zone_name' in locals() else 'unknown'},
            success=False,
            error_message=str(e),
            action_category='create',
            severity='warning',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': False,
            'error': f'Failed to create zone: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def zone_delete(request, agent_id, zone_id):
    """Delete a firewall zone."""
    from .models import AuditLog
    
    agent = get_object_or_404(Agent, id=agent_id)
    zone = get_object_or_404(FirewallZone, id=zone_id, agent=agent)
    
    try:
        data = json.loads(request.body)
        permanent = data.get('permanent', True)
        
        # Delete zone on agent
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('delete_zone', {
            'zone': zone.name,
            'permanent': permanent
        }))
        
        if result.get('success'):
            zone_name = zone.name
            
            # Delete zone from database
            zone.delete()
            
            # Mark reload required if not permanent
            if not permanent:
                agent.firewall_reload_required = True
                agent.save(update_fields=['firewall_reload_required'])
            
            # Log the action
            AuditLog.log(
                user=request.user,
                module='firewalld',
                action='delete_zone',
                agent=agent,
                params={'zone': zone_name, 'permanent': permanent},
                result=result,
                success=True,
                action_category='delete',
                severity='warning',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Zone {zone_name} deleted successfully'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error')
            })
        
    except Exception as e:
        # Log the failure
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='delete_zone',
            agent=agent,
            params={'zone': zone.name},
            success=False,
            error_message=str(e),
            action_category='delete',
            severity='warning',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': False,
            'error': f'Failed to delete zone: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def set_default_zone(request, agent_id):
    """Set the default zone for an agent."""
    from .models import AuditLog
    
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        data = json.loads(request.body)
        zone_name = data.get('zone', '').strip()
        
        if not zone_name:
            return JsonResponse({
                'success': False,
                'error': 'Zone name is required'
            })
        
        # Set default zone on agent
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('set_default_zone', {
            'zone': zone_name
        }))
        
        if result.get('success'):
            # Log the action
            AuditLog.log(
                user=request.user,
                module='firewalld',
                action='set_default_zone',
                agent=agent,
                params={'zone': zone_name},
                result=result,
                success=True,
                action_category='configure',
                severity='info',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Default zone set to {zone_name}'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error')
            })
        
    except Exception as e:
        # Log the failure
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='set_default_zone',
            agent=agent,
            params={'zone': zone_name if 'zone_name' in locals() else 'unknown'},
            success=False,
            error_message=str(e),
            action_category='configure',
            severity='warning',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': False,
            'error': f'Failed to set default zone: {str(e)}'
        })


@login_required
def zone_detail(request, agent_id, zone_id):
    """Display detailed zone view with tabs."""
    agent = get_object_or_404(Agent, id=agent_id)
    zone = get_object_or_404(FirewallZone, id=zone_id, agent=agent)
    
    # Get available services for dropdown
    try:
        manager = get_connection_manager(agent)
        services_result = asyncio.run(manager.execute_command('list_services', {}))
        available_services = services_result.get('data', {}).get('services', []) if services_result.get('success') else []
    except Exception:
        available_services = []
    
    # Get helpers for zone
    helpers = []
    try:
        manager = get_connection_manager(agent)
        helpers_result = asyncio.run(manager.execute_command('zone_list_helpers', {'zone': zone.name}))
        helpers = helpers_result.get('data', {}).get('helpers', []) if helpers_result.get('success') else []
    except Exception:
        pass
    
    context = {
        'agent': agent,
        'zone': zone,
        'available_services': available_services,
    }
    
    # Add helpers to zone object for template
    zone.helpers = helpers
    
    return render(request, 'agents/zone_detail.html', context)


def get_zone_template_settings(template_name):
    """Get predefined settings for zone templates."""
    templates = {
        'dmz': {
            'target': 'default',
            'services': ['ssh'],
            'description': 'DMZ zone for publicly accessible services'
        },
        'internal': {
            'target': 'default',
            'services': ['ssh', 'mdns', 'samba-client', 'dhcpv6-client'],
            'description': 'Internal zone for trusted network'
        },
        'external': {
            'target': 'default',
            'services': ['ssh'],
            'description': 'External zone for untrusted network'
        },
        'public': {
            'target': 'default',
            'services': ['ssh', 'dhcpv6-client'],
            'description': 'Public zone with limited services'
        },
        'work': {
            'target': 'default',
            'services': ['ssh', 'dhcpv6-client'],
            'description': 'Work zone for office network'
        },
        'home': {
            'target': 'default',
            'services': ['ssh', 'mdns', 'samba-client', 'dhcpv6-client'],
            'description': 'Home zone for home network'
        },
        'trusted': {
            'target': 'ACCEPT',
            'services': [],
            'description': 'Trusted zone - all traffic accepted'
        },
        'block': {
            'target': '%%REJECT%%',
            'services': [],
            'description': 'Block zone - all traffic rejected'
        },
        'drop': {
            'target': 'DROP',
            'services': [],
            'description': 'Drop zone - all traffic dropped'
        }
    }
    
    return templates.get(template_name.lower())


@login_required
@require_http_methods(['POST'])
def zone_add_interface(request, agent_id, zone_id):
    """Add interface to zone."""
    from .models import AuditLog
    
    agent = get_object_or_404(Agent, id=agent_id)
    zone = get_object_or_404(FirewallZone, id=zone_id, agent=agent)
    
    try:
        data = json.loads(request.body)
        interface = data.get('interface', '').strip()
        permanent = data.get('permanent', True)
        
        if not interface:
            return JsonResponse({
                'success': False,
                'error': 'Interface name is required'
            })
        
        # Add interface to zone on agent
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('add_interface', {
            'zone': zone.name,
            'interface': interface,
            'permanent': permanent
        }))
        
        if result.get('success'):
            # Update zone in database
            if interface not in zone.interfaces:
                zone.interfaces.append(interface)
                zone.save()
            
            # Mark reload required if not permanent
            if not permanent:
                agent.firewall_reload_required = True
                agent.save(update_fields=['firewall_reload_required'])
            
            # Log the action
            AuditLog.log(
                user=request.user,
                module='firewalld',
                action='add_interface',
                agent=agent,
                params={'zone': zone.name, 'interface': interface, 'permanent': permanent},
                result=result,
                success=True,
                action_category='configure',
                severity='info',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Interface {interface} added to zone {zone.name}'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error')
            })
        
    except Exception as e:
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='add_interface',
            agent=agent,
            params={'zone': zone.name, 'interface': interface if 'interface' in locals() else 'unknown'},
            success=False,
            error_message=str(e),
            action_category='configure',
            severity='warning',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': False,
            'error': f'Failed to add interface: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def zone_remove_interface(request, agent_id, zone_id, interface):
    """Remove interface from zone."""
    from .models import AuditLog
    
    agent = get_object_or_404(Agent, id=agent_id)
    zone = get_object_or_404(FirewallZone, id=zone_id, agent=agent)
    
    try:
        permanent = request.POST.get('permanent', 'true').lower() == 'true'
        
        # Remove interface from zone on agent
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('remove_interface', {
            'zone': zone.name,
            'interface': interface,
            'permanent': permanent
        }))
        
        if result.get('success'):
            # Update zone in database
            if interface in zone.interfaces:
                zone.interfaces.remove(interface)
                zone.save()
            
            # Mark reload required if not permanent
            if not permanent:
                agent.firewall_reload_required = True
                agent.save(update_fields=['firewall_reload_required'])
            
            # Log the action
            AuditLog.log(
                user=request.user,
                module='firewalld',
                action='remove_interface',
                agent=agent,
                params={'zone': zone.name, 'interface': interface, 'permanent': permanent},
                result=result,
                success=True,
                action_category='configure',
                severity='info',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Interface {interface} removed from zone {zone.name}'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error')
            })
        
    except Exception as e:
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='remove_interface',
            agent=agent,
            params={'zone': zone.name, 'interface': interface},
            success=False,
            error_message=str(e),
            action_category='configure',
            severity='warning',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': False,
            'error': f'Failed to remove interface: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def zone_add_source(request, agent_id, zone_id):
    """Add source to zone."""
    from .models import AuditLog
    
    agent = get_object_or_404(Agent, id=agent_id)
    zone = get_object_or_404(FirewallZone, id=zone_id, agent=agent)
    
    try:
        data = json.loads(request.body)
        source = data.get('source', '').strip()
        permanent = data.get('permanent', True)
        
        if not source:
            return JsonResponse({
                'success': False,
                'error': 'Source is required'
            })
        
        # Add source to zone on agent
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('add_source', {
            'zone': zone.name,
            'source': source,
            'permanent': permanent
        }))
        
        if result.get('success'):
            # Update zone in database
            if source not in zone.sources:
                zone.sources.append(source)
                zone.save()
            
            # Mark reload required if not permanent
            if not permanent:
                agent.firewall_reload_required = True
                agent.save(update_fields=['firewall_reload_required'])
            
            # Log the action
            AuditLog.log(
                user=request.user,
                module='firewalld',
                action='add_source',
                agent=agent,
                params={'zone': zone.name, 'source': source, 'permanent': permanent},
                result=result,
                success=True,
                action_category='configure',
                severity='info',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Source {source} added to zone {zone.name}'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error')
            })
        
    except Exception as e:
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='add_source',
            agent=agent,
            params={'zone': zone.name, 'source': source if 'source' in locals() else 'unknown'},
            success=False,
            error_message=str(e),
            action_category='configure',
            severity='warning',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': False,
            'error': f'Failed to add source: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def zone_remove_source(request, agent_id, zone_id, source):
    """Remove source from zone."""
    from .models import AuditLog
    
    agent = get_object_or_404(Agent, id=agent_id)
    zone = get_object_or_404(FirewallZone, id=zone_id, agent=agent)
    
    try:
        permanent = request.POST.get('permanent', 'true').lower() == 'true'
        
        # Remove source from zone on agent
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('remove_source', {
            'zone': zone.name,
            'source': source,
            'permanent': permanent
        }))
        
        if result.get('success'):
            # Update zone in database
            if source in zone.sources:
                zone.sources.remove(source)
                zone.save()
            
            # Mark reload required if not permanent
            if not permanent:
                agent.firewall_reload_required = True
                agent.save(update_fields=['firewall_reload_required'])
            
            # Log the action
            AuditLog.log(
                user=request.user,
                module='firewalld',
                action='remove_source',
                agent=agent,
                params={'zone': zone.name, 'source': source, 'permanent': permanent},
                result=result,
                success=True,
                action_category='configure',
                severity='info',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Source {source} removed from zone {zone.name}'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error')
            })
        
    except Exception as e:
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='remove_source',
            agent=agent,
            params={'zone': zone.name, 'source': source},
            success=False,
            error_message=str(e),
            action_category='configure',
            severity='warning',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': False,
            'error': f'Failed to remove source: {str(e)}'
        })


# Direct Rules Management Views

@login_required
@require_http_methods(['GET'])
def agent_direct_rules_page(request, agent_id):
    """Render the direct rules management page."""
    agent = get_object_or_404(Agent, id=agent_id)
    return render(request, 'agents/direct_rules.html', {'agent': agent})


@login_required
@require_http_methods(['GET'])
def agent_list_direct_rules(request, agent_id):
    """List all direct rules from agent."""
    from .models import AuditLog
    
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        # Get rules from agent
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('direct_get_all_rules', {}))
        
        if result.get('success'):
            rules = result.get('data', {}).get('rules', [])
            
            # Also get rules from database for additional info
            db_rules = DirectRule.objects.filter(agent=agent, is_active=True)
            db_rules_dict = {
                f"{r.ipv}_{r.table}_{r.chain}_{r.priority}": {
                    'id': str(r.id),
                    'description': r.description
                }
                for r in db_rules
            }
            
            # Merge agent rules with database info
            for rule in rules:
                key = f"{rule['ipv']}_{rule['table']}_{rule['chain']}_{rule['priority']}"
                if key in db_rules_dict:
                    rule['id'] = db_rules_dict[key]['id']
                    rule['description'] = db_rules_dict[key]['description']
            
            return JsonResponse({
                'success': True,
                'rules': rules
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Failed to list direct rules')
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to list direct rules: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def agent_direct_rule_create(request, agent_id):
    """Create a new direct rule."""
    from .models import AuditLog, DirectRule
    
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        data = json.loads(request.body)
        ipv = data.get('ipv')
        table = data.get('table')
        chain = data.get('chain')
        priority = data.get('priority')
        args = data.get('args', [])
        description = data.get('description', '')
        
        if not all([ipv, table, chain, priority is not None]):
            return JsonResponse({
                'success': False,
                'error': 'All fields are required: ipv, table, chain, priority, args'
            })
        
        # Validate ipv
        if ipv not in ['ipv4', 'ipv6']:
            return JsonResponse({
                'success': False,
                'error': 'IP version must be ipv4 or ipv6'
            })
        
        # Validate table
        if table not in ['filter', 'nat', 'mangle', 'raw']:
            return JsonResponse({
                'success': False,
                'error': 'Table must be one of: filter, nat, mangle, raw'
            })
        
        # Validate priority
        priority = int(priority)
        if not (0 <= priority <= 999):
            return JsonResponse({
                'success': False,
                'error': 'Priority must be between 0 and 999'
            })
        
        # Add rule on agent
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('direct_add_rule', {
            'ipv': ipv,
            'table': table,
            'chain': chain,
            'priority': priority,
            'args': args
        }))
        
        if result.get('success'):
            # Store in database
            direct_rule = DirectRule.objects.create(
                agent=agent,
                ipv=ipv,
                table=table,
                chain=chain,
                priority=priority,
                args=args,
                description=description,
                created_by=request.user
            )
            
            # Reload firewall
            asyncio.run(manager.execute_command('reload', {}))
            
            AuditLog.log(
                user=request.user,
                module='firewalld',
                action='direct_rule_create',
                agent=agent,
                params={
                    'ipv': ipv,
                    'table': table,
                    'chain': chain,
                    'priority': priority,
                    'args': args
                },
                success=True,
                action_category='configure',
                severity='medium',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': True,
                'rule': {
                    'id': str(direct_rule.id),
                    'ipv': direct_rule.ipv,
                    'table': direct_rule.table,
                    'chain': direct_rule.chain,
                    'priority': direct_rule.priority,
                    'args': direct_rule.args,
                    'description': direct_rule.description
                }
            })
        else:
            AuditLog.log(
                user=request.user,
                module='firewalld',
                action='direct_rule_create',
                agent=agent,
                params={'ipv': ipv, 'table': table, 'chain': chain, 'priority': priority},
                success=False,
                error_message=result.get('error'),
                action_category='configure',
                severity='warning',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Failed to create direct rule')
            })
            
    except Exception as e:
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='direct_rule_create',
            agent=agent,
            params=data if 'data' in locals() else {},
            success=False,
            error_message=str(e),
            action_category='configure',
            severity='warning',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': False,
            'error': f'Failed to create direct rule: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def agent_direct_rule_delete(request, agent_id, rule_id):
    """Delete a direct rule."""
    from .models import AuditLog, DirectRule
    
    agent = get_object_or_404(Agent, id=agent_id)
    direct_rule = get_object_or_404(DirectRule, id=rule_id, agent=agent)
    
    try:
        # Remove rule from agent
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('direct_remove_rule', {
            'ipv': direct_rule.ipv,
            'table': direct_rule.table,
            'chain': direct_rule.chain,
            'priority': direct_rule.priority,
            'args': direct_rule.args
        }))
        
        if result.get('success'):
            # Remove from database
            direct_rule.is_active = False
            direct_rule.save()
            
            # Reload firewall
            asyncio.run(manager.execute_command('reload', {}))
            
            AuditLog.log(
                user=request.user,
                module='firewalld',
                action='direct_rule_delete',
                agent=agent,
                params={
                    'ipv': direct_rule.ipv,
                    'table': direct_rule.table,
                    'chain': direct_rule.chain,
                    'priority': direct_rule.priority
                },
                success=True,
                action_category='configure',
                severity='medium',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Direct rule deleted successfully'
            })
        else:
            AuditLog.log(
                user=request.user,
                module='firewalld',
                action='direct_rule_delete',
                agent=agent,
                params={'rule_id': str(rule_id)},
                success=False,
                error_message=result.get('error'),
                action_category='configure',
                severity='warning',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Failed to delete direct rule')
            })
            
    except Exception as e:
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='direct_rule_delete',
            agent=agent,
            params={'rule_id': str(rule_id)},
            success=False,
            error_message=str(e),
            action_category='configure',
            severity='warning',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': False,
            'error': f'Failed to delete direct rule: {str(e)}'
        })


@login_required
@require_http_methods(['GET'])
def agent_list_chains(request, agent_id):
    """List all chains for a specific table."""
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        ipv = request.GET.get('ipv', 'ipv4')
        table = request.GET.get('table', 'filter')
        
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('direct_get_all_chains', {
            'ipv': ipv,
            'table': table
        }))
        
        if result.get('success'):
            chains = result.get('data', {}).get('chains', [])
            return JsonResponse({
                'success': True,
                'chains': chains
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Failed to list chains')
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to list chains: {str(e)}'
        })


# Lockdown Whitelist Management Views

@login_required
@require_http_methods(['GET'])
def agent_lockdown_status(request, agent_id):
    """Get lockdown mode status."""
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('lockdown_get_status', {}))
        
        if result.get('success'):
            return JsonResponse({
                'success': True,
                'enabled': result.get('data', {}).get('enabled', False),
                'status': result.get('data', {}).get('status', 'disabled')
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Failed to get lockdown status')
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to get lockdown status: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def agent_lockdown_control(request, agent_id):
    """Enable or disable lockdown mode."""
    from .models import AuditLog
    
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        data = json.loads(request.body)
        action = data.get('action')
        
        if action not in ['enable', 'disable']:
            return JsonResponse({
                'success': False,
                'error': 'Action must be enable or disable'
            })
        
        # Execute command
        manager = get_connection_manager(agent)
        command = 'lockdown_enable' if action == 'enable' else 'lockdown_disable'
        result = asyncio.run(manager.execute_command(command, {}))
        
        if result.get('success'):
            # Reload firewall
            asyncio.run(manager.execute_command('reload', {}))
            
            AuditLog.log(
                user=request.user,
                module='firewalld',
                action=f'lockdown_{action}',
                agent=agent,
                params={'action': action},
                success=True,
                action_category='security',
                severity='high',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': True,
                'enabled': action == 'enable',
                'message': result.get('data', {}).get('message', f'Lockdown {action}d')
            })
        else:
            AuditLog.log(
                user=request.user,
                module='firewalld',
                action=f'lockdown_{action}',
                agent=agent,
                params={'action': action},
                success=False,
                error_message=result.get('error'),
                action_category='security',
                severity='warning',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': False,
                'error': result.get('error', f'Failed to {action} lockdown')
            })
            
    except Exception as e:
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='lockdown_control',
            agent=agent,
            params=data if 'data' in locals() else {},
            success=False,
            error_message=str(e),
            action_category='security',
            severity='warning',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': False,
            'error': f'Failed to control lockdown: {str(e)}'
        })


@login_required
@require_http_methods(['GET'])
def agent_lockdown_list_commands(request, agent_id):
    """List whitelisted commands."""
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('lockdown_list_commands', {}))
        
        if result.get('success'):
            return JsonResponse({
                'success': True,
                'commands': result.get('data', {}).get('commands', [])
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Failed to list commands')
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to list commands: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def agent_lockdown_add_command(request, agent_id):
    """Add command to whitelist."""
    from .models import AuditLog
    
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        data = json.loads(request.body)
        command = data.get('command', '').strip()
        
        if not command:
            return JsonResponse({
                'success': False,
                'error': 'Command is required'
            })
        
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('lockdown_add_command', {
            'command': command
        }))
        
        if result.get('success'):
            # Reload firewall
            asyncio.run(manager.execute_command('reload', {}))
            
            AuditLog.log(
                user=request.user,
                module='firewalld',
                action='lockdown_add_command',
                agent=agent,
                params={'command': command},
                success=True,
                action_category='security',
                severity='medium',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': True,
                'message': result.get('data', {}).get('message', 'Command added to whitelist')
            })
        else:
            AuditLog.log(
                user=request.user,
                module='firewalld',
                action='lockdown_add_command',
                agent=agent,
                params={'command': command},
                success=False,
                error_message=result.get('error'),
                action_category='security',
                severity='warning',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Failed to add command')
            })
            
    except Exception as e:
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='lockdown_add_command',
            agent=agent,
            params=data if 'data' in locals() else {},
            success=False,
            error_message=str(e),
            action_category='security',
            severity='warning',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': False,
            'error': f'Failed to add command: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def agent_lockdown_remove_command(request, agent_id):
    """Remove command from whitelist."""
    from .models import AuditLog
    
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        data = json.loads(request.body)
        command = data.get('command', '').strip()
        
        if not command:
            return JsonResponse({
                'success': False,
                'error': 'Command is required'
            })
        
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('lockdown_remove_command', {
            'command': command
        }))
        
        if result.get('success'):
            # Reload firewall
            asyncio.run(manager.execute_command('reload', {}))
            
            AuditLog.log(
                user=request.user,
                module='firewalld',
                action='lockdown_remove_command',
                agent=agent,
                params={'command': command},
                success=True,
                action_category='security',
                severity='medium',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': True,
                'message': result.get('data', {}).get('message', 'Command removed from whitelist')
            })
        else:
            AuditLog.log(
                user=request.user,
                module='firewalld',
                action='lockdown_remove_command',
                agent=agent,
                params={'command': command},
                success=False,
                error_message=result.get('error'),
                action_category='security',
                severity='warning',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Failed to remove command')
            })
            
    except Exception as e:
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='lockdown_remove_command',
            agent=agent,
            params=data if 'data' in locals() else {},
            success=False,
            error_message=str(e),
            action_category='security',
            severity='warning',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': False,
            'error': f'Failed to remove command: {str(e)}'
        })


@login_required
@require_http_methods(['GET'])
def agent_lockdown_list_users(request, agent_id):
    """List whitelisted users."""
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('lockdown_list_users', {}))
        
        if result.get('success'):
            return JsonResponse({
                'success': True,
                'users': result.get('data', {}).get('users', [])
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Failed to list users')
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to list users: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def agent_lockdown_add_user(request, agent_id):
    """Add user to whitelist."""
    from .models import AuditLog
    
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        data = json.loads(request.body)
        user = data.get('user', '').strip()
        
        if not user:
            return JsonResponse({
                'success': False,
                'error': 'User is required'
            })
        
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('lockdown_add_user', {
            'user': user
        }))
        
        if result.get('success'):
            # Reload firewall
            asyncio.run(manager.execute_command('reload', {}))
            
            AuditLog.log(
                user=request.user,
                module='firewalld',
                action='lockdown_add_user',
                agent=agent,
                params={'user': user},
                success=True,
                action_category='security',
                severity='medium',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': True,
                'message': result.get('data', {}).get('message', 'User added to whitelist')
            })
        else:
            AuditLog.log(
                user=request.user,
                module='firewalld',
                action='lockdown_add_user',
                agent=agent,
                params={'user': user},
                success=False,
                error_message=result.get('error'),
                action_category='security',
                severity='warning',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Failed to add user')
            })
            
    except Exception as e:
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='lockdown_add_user',
            agent=agent,
            params=data if 'data' in locals() else {},
            success=False,
            error_message=str(e),
            action_category='security',
            severity='warning',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': False,
            'error': f'Failed to add user: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def agent_lockdown_remove_user(request, agent_id):
    """Remove user from whitelist."""
    from .models import AuditLog
    
    agent = get_object_or_404(Agent, id=agent_id)
    
    try:
        data = json.loads(request.body)
        user = data.get('user', '').strip()
        
        if not user:
            return JsonResponse({
                'success': False,
                'error': 'User is required'
            })
        
        manager = get_connection_manager(agent)
        result = asyncio.run(manager.execute_command('lockdown_remove_user', {
            'user': user
        }))
        
        if result.get('success'):
            # Reload firewall
            asyncio.run(manager.execute_command('reload', {}))
            
            AuditLog.log(
                user=request.user,
                module='firewalld',
                action='lockdown_remove_user',
                agent=agent,
                params={'user': user},
                success=True,
                action_category='security',
                severity='medium',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': True,
                'message': result.get('data', {}).get('message', 'User removed from whitelist')
            })
        else:
            AuditLog.log(
                user=request.user,
                module='firewalld',
                action='lockdown_remove_user',
                agent=agent,
                params={'user': user},
                success=False,
                error_message=result.get('error'),
                action_category='security',
                severity='warning',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Failed to remove user')
            })
            
    except Exception as e:
        AuditLog.log(
            user=request.user,
            module='firewalld',
            action='lockdown_remove_user',
            agent=agent,
            params=data if 'data' in locals() else {},
            success=False,
            error_message=str(e),
            action_category='security',
            severity='warning',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': False,
            'error': f'Failed to remove user: {str(e)}'
        })


