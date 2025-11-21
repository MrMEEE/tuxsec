#!/usr/bin/env python3
"""
Firewalld Module - Manages firewall configuration.

This module provides firewalld management capabilities including:
- Zone management
- Service management  
- Port management
- Rich rules
- Query operations
"""

from typing import List, Optional, Dict, Any
import subprocess
from ..base_module import BaseModule
from ..protocol import ModuleCapability, CommandRequest, CommandResponse


class FirewalldModule(BaseModule):
    """Manages firewalld configuration."""
    
    @property
    def name(self) -> str:
        return "firewalld"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "Manages firewalld zones, services, ports, and rules"
    
    def get_capabilities(self) -> List[ModuleCapability]:
        return [
            # Query operations
            ModuleCapability(
                name="get_status",
                description="Get firewalld running status",
                parameters=[]
            ),
            ModuleCapability(
                name="get_version",
                description="Get firewalld version",
                parameters=[]
            ),
            ModuleCapability(
                name="list_zones",
                description="List all zones",
                parameters=[]
            ),
            ModuleCapability(
                name="get_zone",
                description="Get zone configuration",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"}
                ]
            ),
            ModuleCapability(
                name="get_default_zone",
                description="Get default zone",
                parameters=[]
            ),
            ModuleCapability(
                name="list_services",
                description="List available services",
                parameters=[]
            ),
            
            # Zone operations
            ModuleCapability(
                name="set_default_zone",
                description="Set default zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"}
                ]
            ),
            
            # Service operations
            ModuleCapability(
                name="add_service",
                description="Add service to zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "service", "type": "string", "description": "Service name", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make permanent", "required": "false"}
                ]
            ),
            ModuleCapability(
                name="remove_service",
                description="Remove service from zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "service", "type": "string", "description": "Service name", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make permanent", "required": "false"}
                ]
            ),
            
            # Port operations
            ModuleCapability(
                name="add_port",
                description="Add port to zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "port", "type": "string", "description": "Port/protocol (e.g., 8080/tcp)", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make permanent", "required": "false"}
                ]
            ),
            ModuleCapability(
                name="remove_port",
                description="Remove port from zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "port", "type": "string", "description": "Port/protocol (e.g., 8080/tcp)", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make permanent", "required": "false"}
                ]
            ),
            
            # Rich rule operations
            ModuleCapability(
                name="add_rich_rule",
                description="Add rich rule to zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "rule", "type": "string", "description": "Rich rule", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make permanent", "required": "false"}
                ]
            ),
            ModuleCapability(
                name="remove_rich_rule",
                description="Remove rich rule from zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "rule", "type": "string", "description": "Rich rule", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make permanent", "required": "false"}
                ]
            ),
            
            # Control operations
            ModuleCapability(
                name="reload",
                description="Reload firewalld configuration",
                parameters=[]
            ),
        ]
    
    def initialize(self) -> tuple[bool, Optional[str]]:
        """Initialize the firewalld module."""
        # Check if firewalld is available
        success, stdout, stderr = self._run_command(['which', 'firewall-cmd'], timeout=5)
        if not success:
            return False, "firewall-cmd not found. Is firewalld installed?"
        
        # Check if firewalld service is running
        success, stdout, stderr = self._run_command(['systemctl', 'is-active', 'firewalld'], timeout=5)
        if not success:
            self.logger.warning("firewalld service is not active")
        
        self.logger.info("Firewalld module initialized")
        return True, None
    
    def shutdown(self):
        """Cleanup on shutdown."""
        self.logger.info("Firewalld module shutting down")
    
    def execute_command(self, command: CommandRequest) -> CommandResponse:
        """Execute a firewalld command."""
        # Validate command
        is_valid, error = self.validate_command(command)
        if not is_valid:
            return CommandResponse(success=False, error=error)
        
        try:
            action = command.action
            params = command.parameters
            
            # Query operations
            if action == "get_status":
                return self._get_status()
            elif action == "get_version":
                return self._get_version()
            elif action == "list_zones":
                return self._list_zones()
            elif action == "get_zone":
                return self._get_zone(params.get('zone'))
            elif action == "get_default_zone":
                return self._get_default_zone()
            elif action == "list_services":
                return self._list_services()
            
            # Zone operations
            elif action == "set_default_zone":
                return self._set_default_zone(params.get('zone'))
            
            # Service operations
            elif action == "add_service":
                return self._add_service(
                    params.get('zone'),
                    params.get('service'),
                    params.get('permanent', False)
                )
            elif action == "remove_service":
                return self._remove_service(
                    params.get('zone'),
                    params.get('service'),
                    params.get('permanent', False)
                )
            
            # Port operations
            elif action == "add_port":
                return self._add_port(
                    params.get('zone'),
                    params.get('port'),
                    params.get('permanent', False)
                )
            elif action == "remove_port":
                return self._remove_port(
                    params.get('zone'),
                    params.get('port'),
                    params.get('permanent', False)
                )
            
            # Rich rule operations
            elif action == "add_rich_rule":
                return self._add_rich_rule(
                    params.get('zone'),
                    params.get('rule'),
                    params.get('permanent', False)
                )
            elif action == "remove_rich_rule":
                return self._remove_rich_rule(
                    params.get('zone'),
                    params.get('rule'),
                    params.get('permanent', False)
                )
            
            # Control operations
            elif action == "reload":
                return self._reload()
            
            else:
                return CommandResponse(success=False, error=f"Unknown action: {action}")
                
        except Exception as e:
            self.logger.error(f"Error executing command {command.action}: {e}")
            return CommandResponse(success=False, error=str(e))
    
    def _get_status(self) -> CommandResponse:
        """Get firewalld status."""
        success, stdout, stderr = self._run_command(['systemctl', 'is-active', 'firewalld'])
        is_active = stdout.strip() == 'active'
        
        return CommandResponse(
            success=True,
            data={'active': is_active, 'status': stdout.strip()}
        )
    
    def _get_version(self) -> CommandResponse:
        """Get firewalld version."""
        success, stdout, stderr = self._run_command(['firewall-cmd', '--version'])
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(success=True, data={'version': stdout.strip()})
    
    def _list_zones(self) -> CommandResponse:
        """List all zones."""
        success, stdout, stderr = self._run_command(['firewall-cmd', '--get-zones'])
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        zones = stdout.strip().split()
        return CommandResponse(success=True, data={'zones': zones})
    
    def _get_zone(self, zone: str) -> CommandResponse:
        """Get zone configuration."""
        if not zone:
            return CommandResponse(success=False, error="Zone name is required")
        
        # Get zone info
        success, stdout, stderr = self._run_command(['firewall-cmd', '--zone', zone, '--list-all'])
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(success=True, data={'zone': zone, 'config': stdout})
    
    def _get_default_zone(self) -> CommandResponse:
        """Get default zone."""
        success, stdout, stderr = self._run_command(['firewall-cmd', '--get-default-zone'])
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(success=True, data={'default_zone': stdout.strip()})
    
    def _list_services(self) -> CommandResponse:
        """List available services."""
        success, stdout, stderr = self._run_command(['firewall-cmd', '--get-services'])
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        services = stdout.strip().split()
        return CommandResponse(success=True, data={'services': services})
    
    def _set_default_zone(self, zone: str) -> CommandResponse:
        """Set default zone."""
        if not zone:
            return CommandResponse(success=False, error="Zone name is required")
        
        success, stdout, stderr = self._run_command(['firewall-cmd', '--set-default-zone', zone])
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(success=True, data={'default_zone': zone})
    
    def _add_service(self, zone: str, service: str, permanent: bool) -> CommandResponse:
        """Add service to zone."""
        if not zone or not service:
            return CommandResponse(success=False, error="Zone and service are required")
        
        cmd = ['firewall-cmd', f'--zone={zone}', f'--add-service={service}']
        if permanent:
            cmd.append('--permanent')
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(
            success=True,
            data={'zone': zone, 'service': service, 'permanent': permanent}
        )
    
    def _remove_service(self, zone: str, service: str, permanent: bool) -> CommandResponse:
        """Remove service from zone."""
        if not zone or not service:
            return CommandResponse(success=False, error="Zone and service are required")
        
        cmd = ['firewall-cmd', f'--zone={zone}', f'--remove-service={service}']
        if permanent:
            cmd.append('--permanent')
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(
            success=True,
            data={'zone': zone, 'service': service, 'permanent': permanent}
        )
    
    def _add_port(self, zone: str, port: str, permanent: bool) -> CommandResponse:
        """Add port to zone."""
        if not zone or not port:
            return CommandResponse(success=False, error="Zone and port are required")
        
        cmd = ['firewall-cmd', f'--zone={zone}', f'--add-port={port}']
        if permanent:
            cmd.append('--permanent')
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(
            success=True,
            data={'zone': zone, 'port': port, 'permanent': permanent}
        )
    
    def _remove_port(self, zone: str, port: str, permanent: bool) -> CommandResponse:
        """Remove port from zone."""
        if not zone or not port:
            return CommandResponse(success=False, error="Zone and port are required")
        
        cmd = ['firewall-cmd', f'--zone={zone}', f'--remove-port={port}']
        if permanent:
            cmd.append('--permanent')
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(
            success=True,
            data={'zone': zone, 'port': port, 'permanent': permanent}
        )
    
    def _add_rich_rule(self, zone: str, rule: str, permanent: bool) -> CommandResponse:
        """Add rich rule to zone."""
        if not zone or not rule:
            return CommandResponse(success=False, error="Zone and rule are required")
        
        cmd = ['firewall-cmd', f'--zone={zone}', f'--add-rich-rule={rule}']
        if permanent:
            cmd.append('--permanent')
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(
            success=True,
            data={'zone': zone, 'rule': rule, 'permanent': permanent}
        )
    
    def _remove_rich_rule(self, zone: str, rule: str, permanent: bool) -> CommandResponse:
        """Remove rich rule from zone."""
        if not zone or not rule:
            return CommandResponse(success=False, error="Zone and rule are required")
        
        cmd = ['firewall-cmd', f'--zone={zone}', f'--remove-rich-rule={rule}']
        if permanent:
            cmd.append('--permanent')
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(
            success=True,
            data={'zone': zone, 'rule': rule, 'permanent': permanent}
        )
    
    def _reload(self) -> CommandResponse:
        """Reload firewalld."""
        success, stdout, stderr = self._run_command(['firewall-cmd', '--reload'])
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(success=True, data={'reloaded': True})
