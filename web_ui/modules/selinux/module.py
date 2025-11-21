"""
SELinux security module implementation.
"""

import subprocess
import shutil
from typing import Dict, List, Any
from shared.modules.base import BaseModule, ModuleCapability, ModuleResult


class SELinuxModule(BaseModule):
    """
    Module for managing SELinux (Security-Enhanced Linux) configuration.
    """
    
    @property
    def name(self) -> str:
        return "selinux"
    
    @property
    def display_name(self) -> str:
        return "SELinux"
    
    @property
    def description(self) -> str:
        return "Manage SELinux modes, booleans, contexts, and policies"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def capabilities(self) -> List[ModuleCapability]:
        return [ModuleCapability.SELINUX, ModuleCapability.COMPLIANCE]
    
    def get_required_packages(self) -> List[str]:
        return ['selinux-policy', 'policycoreutils', 'policycoreutils-python-utils']
    
    def check_availability(self) -> bool:
        """Check if SELinux is available."""
        # Check if selinuxenabled command exists
        if not shutil.which('getenforce'):
            return False
        
        try:
            # Check if SELinux is available on the system
            result = subprocess.run(
                ['getenforce'],
                capture_output=True,
                text=True,
                timeout=5
            )
            # SELinux is available if the command succeeds (even if disabled)
            return result.returncode == 0
        except Exception:
            return False
    
    def get_available_actions(self) -> List[str]:
        return [
            # Status
            'get_status',
            'get_mode',
            'get_enforce_mode',
            
            # Mode management
            'set_enforcing',
            'set_permissive',
            
            # Booleans
            'list_booleans',
            'get_boolean',
            'set_boolean',
            
            # Contexts
            'get_file_context',
            'set_file_context',
            'restore_context',
            
            # Policy
            'list_modules',
            'get_policy_version',
        ]
    
    def execute_action(self, action: str, parameters: Dict[str, Any]) -> ModuleResult:
        """Execute an SELinux action."""
        try:
            if action == 'get_status':
                return self.get_status()
            elif action == 'get_mode':
                return self._get_mode()
            elif action == 'set_enforcing':
                return self._set_enforcing()
            elif action == 'set_permissive':
                return self._set_permissive()
            elif action == 'list_booleans':
                return self._list_booleans()
            elif action == 'get_boolean':
                return self._get_boolean(parameters.get('name'))
            elif action == 'set_boolean':
                return self._set_boolean(
                    parameters.get('name'),
                    parameters.get('value'),
                    parameters.get('persistent', False)
                )
            else:
                return ModuleResult(
                    success=False,
                    message=f"Unknown action: {action}",
                    error=f"Action '{action}' is not supported"
                )
        
        except Exception as e:
            return ModuleResult(
                success=False,
                message=f"Error executing action {action}",
                error=str(e)
            )
    
    def get_status(self) -> Dict[str, Any]:
        """Get current SELinux status."""
        try:
            # Get enforcement mode
            result = subprocess.run(
                ['getenforce'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            mode = result.stdout.strip() if result.returncode == 0 else "Unknown"
            
            # Try to get more detailed status
            status = {
                'mode': mode,
                'enabled': mode.lower() not in ['disabled', 'unknown'],
            }
            
            # Get SELinux status details if available
            result = subprocess.run(
                ['sestatus'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Parse sestatus output
                for line in result.stdout.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip().lower().replace(' ', '_')
                        value = value.strip()
                        status[key] = value
            
            return status
        
        except Exception as e:
            return {'error': str(e), 'enabled': False}
    
    def _get_mode(self) -> ModuleResult:
        """Get current SELinux mode."""
        result = subprocess.run(
            ['getenforce'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            mode = result.stdout.strip()
            return ModuleResult(
                success=True,
                message=f"SELinux mode: {mode}",
                data={'mode': mode}
            )
        else:
            return ModuleResult(
                success=False,
                message="Failed to get SELinux mode",
                error=result.stderr
            )
    
    def _set_enforcing(self) -> ModuleResult:
        """Set SELinux to enforcing mode."""
        result = subprocess.run(
            ['setenforce', '1'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            return ModuleResult(
                success=True,
                message="SELinux set to enforcing mode",
                data={'mode': 'Enforcing'}
            )
        else:
            return ModuleResult(
                success=False,
                message="Failed to set enforcing mode",
                error=result.stderr
            )
    
    def _set_permissive(self) -> ModuleResult:
        """Set SELinux to permissive mode."""
        result = subprocess.run(
            ['setenforce', '0'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            return ModuleResult(
                success=True,
                message="SELinux set to permissive mode",
                data={'mode': 'Permissive'}
            )
        else:
            return ModuleResult(
                success=False,
                message="Failed to set permissive mode",
                error=result.stderr
            )
    
    def _list_booleans(self) -> ModuleResult:
        """List all SELinux booleans."""
        result = subprocess.run(
            ['getsebool', '-a'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            booleans = {}
            for line in result.stdout.strip().split('\n'):
                if ' --> ' in line:
                    name, value = line.split(' --> ')
                    booleans[name.strip()] = value.strip()
            
            return ModuleResult(
                success=True,
                message=f"Found {len(booleans)} SELinux booleans",
                data={'booleans': booleans}
            )
        else:
            return ModuleResult(
                success=False,
                message="Failed to list booleans",
                error=result.stderr
            )
    
    def _get_boolean(self, name: str) -> ModuleResult:
        """Get value of a specific SELinux boolean."""
        if not name:
            return ModuleResult(success=False, message="Boolean name required", error="Missing name")
        
        result = subprocess.run(
            ['getsebool', name],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            value = result.stdout.strip().split(' --> ')[1] if ' --> ' in result.stdout else 'unknown'
            return ModuleResult(
                success=True,
                message=f"Boolean {name}: {value}",
                data={'name': name, 'value': value}
            )
        else:
            return ModuleResult(
                success=False,
                message=f"Failed to get boolean {name}",
                error=result.stderr
            )
    
    def _set_boolean(self, name: str, value: bool, persistent: bool) -> ModuleResult:
        """Set value of an SELinux boolean."""
        if not name:
            return ModuleResult(success=False, message="Boolean name required", error="Missing name")
        
        cmd = ['setsebool']
        if persistent:
            cmd.append('-P')
        cmd.extend([name, '1' if value else '0'])
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            return ModuleResult(
                success=True,
                message=f"Set boolean {name} to {'on' if value else 'off'}",
                data={'name': name, 'value': value, 'persistent': persistent}
            )
        else:
            return ModuleResult(
                success=False,
                message=f"Failed to set boolean {name}",
                error=result.stderr
            )
    
    def get_configuration_schema(self) -> Dict[str, Any]:
        """Get configuration schema for SELinux module."""
        return {
            "type": "object",
            "properties": {
                "default_mode": {
                    "type": "string",
                    "enum": ["enforcing", "permissive"],
                    "description": "Default SELinux mode"
                },
                "autorelabel": {
                    "type": "boolean",
                    "description": "Automatically relabel filesystem on reboot",
                    "default": False
                }
            }
        }
