#!/usr/bin/env python3
"""
System Info Module - Always available, provides basic system information.

This module is built-in and cannot be disabled. It provides read-only
system information without requiring any privileged operations.
"""

import os
import platform
import socket
from typing import List, Optional
from datetime import datetime
from ..base_module import BaseModule
from ..protocol import ModuleCapability, CommandRequest, CommandResponse


class SystemInfoModule(BaseModule):
    """Provides system information."""
    
    @property
    def name(self) -> str:
        return "systeminfo"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "Provides basic system information (hostname, OS, kernel, etc.)"
    
    def get_capabilities(self) -> List[ModuleCapability]:
        return [
            ModuleCapability(
                name="get_info",
                description="Get comprehensive system information",
                parameters=[]
            ),
            ModuleCapability(
                name="get_hostname",
                description="Get system hostname",
                parameters=[]
            ),
            ModuleCapability(
                name="get_os_info",
                description="Get operating system information",
                parameters=[]
            ),
            ModuleCapability(
                name="get_kernel_version",
                description="Get kernel version",
                parameters=[]
            ),
            ModuleCapability(
                name="get_uptime",
                description="Get system uptime",
                parameters=[]
            ),
        ]
    
    def initialize(self) -> tuple[bool, Optional[str]]:
        """Initialize the module."""
        # System info module doesn't need initialization
        self.logger.info("System info module initialized")
        return True, None
    
    def shutdown(self):
        """Cleanup on shutdown."""
        self.logger.info("System info module shutting down")
    
    def execute_command(self, command: CommandRequest) -> CommandResponse:
        """Execute a system info command."""
        # Validate command
        is_valid, error = self.validate_command(command)
        if not is_valid:
            return CommandResponse(success=False, error=error)
        
        try:
            if command.action == "get_info":
                return self._get_all_info()
            elif command.action == "get_hostname":
                return self._get_hostname()
            elif command.action == "get_os_info":
                return self._get_os_info()
            elif command.action == "get_kernel_version":
                return self._get_kernel_version()
            elif command.action == "get_uptime":
                return self._get_uptime()
            else:
                return CommandResponse(
                    success=False,
                    error=f"Unknown action: {command.action}"
                )
        except Exception as e:
            self.logger.error(f"Error executing command {command.action}: {e}")
            return CommandResponse(success=False, error=str(e))
    
    def _get_all_info(self) -> CommandResponse:
        """Get all system information."""
        info = {
            'hostname': socket.gethostname(),
            'fqdn': socket.getfqdn(),
            'os': {
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor(),
            },
            'kernel': platform.release(),
            'python_version': platform.python_version(),
            'uptime_seconds': self._get_uptime_seconds(),
        }
        
        # Try to get distribution info
        try:
            import distro
            info['distribution'] = {
                'name': distro.name(),
                'version': distro.version(),
                'codename': distro.codename(),
            }
        except ImportError:
            # distro not available, try platform
            try:
                dist_info = platform.freedesktop_os_release()
                info['distribution'] = {
                    'name': dist_info.get('NAME', 'Unknown'),
                    'version': dist_info.get('VERSION', 'Unknown'),
                    'id': dist_info.get('ID', 'Unknown'),
                }
            except Exception:
                info['distribution'] = {'name': 'Unknown'}
        
        return CommandResponse(success=True, data=info)
    
    def _get_hostname(self) -> CommandResponse:
        """Get system hostname."""
        return CommandResponse(
            success=True,
            data={
                'hostname': socket.gethostname(),
                'fqdn': socket.getfqdn()
            }
        )
    
    def _get_os_info(self) -> CommandResponse:
        """Get OS information."""
        info = {
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
        }
        
        # Try to get distribution info
        try:
            import distro
            info['distribution'] = distro.name()
            info['distribution_version'] = distro.version()
            info['distribution_codename'] = distro.codename()
        except ImportError:
            try:
                dist_info = platform.freedesktop_os_release()
                info['distribution'] = dist_info.get('NAME', 'Unknown')
                info['distribution_version'] = dist_info.get('VERSION', 'Unknown')
            except Exception:
                pass
        
        return CommandResponse(success=True, data=info)
    
    def _get_kernel_version(self) -> CommandResponse:
        """Get kernel version."""
        return CommandResponse(
            success=True,
            data={'kernel_version': platform.release()}
        )
    
    def _get_uptime(self) -> CommandResponse:
        """Get system uptime."""
        uptime_seconds = self._get_uptime_seconds()
        
        days = uptime_seconds // 86400
        hours = (uptime_seconds % 86400) // 3600
        minutes = (uptime_seconds % 3600) // 60
        
        return CommandResponse(
            success=True,
            data={
                'uptime_seconds': uptime_seconds,
                'uptime_days': days,
                'uptime_hours': hours,
                'uptime_minutes': minutes,
                'uptime_formatted': f"{days}d {hours}h {minutes}m"
            }
        )
    
    def _get_uptime_seconds(self) -> int:
        """Get uptime in seconds."""
        try:
            with open('/proc/uptime', 'r') as f:
                uptime = float(f.readline().split()[0])
                return int(uptime)
        except Exception:
            return 0
