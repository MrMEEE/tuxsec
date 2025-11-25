"""
Connection managers for different agent communication types.
"""
import asyncio
import json
import paramiko
import requests
import subprocess
from io import StringIO
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from asgiref.sync import sync_to_async
from .models import Agent, AgentCommand


class BaseConnectionManager:
    """Base class for agent connection managers."""
    
    def __init__(self, agent: Agent):
        self.agent = agent
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to the agent."""
        raise NotImplementedError
    
    async def execute_command(self, command: str, parameters: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a firewalld command on the agent."""
        raise NotImplementedError
    
    async def get_firewall_status(self) -> Dict[str, Any]:
        """Get current firewall status from the agent."""
        raise NotImplementedError
    
    async def get_zones(self) -> List[Dict[str, Any]]:
        """Get firewall zones from the agent."""
        raise NotImplementedError
    
    async def get_rules(self) -> List[Dict[str, Any]]:
        """Get firewall rules from the agent."""
        raise NotImplementedError
    
    async def get_available_services(self) -> List[str]:
        """Get list of available firewalld services."""
        raise NotImplementedError


class SSHConnectionManager(BaseConnectionManager):
    """SSH-based connection manager."""
    
    def __init__(self, agent: Agent):
        super().__init__(agent)
        self.ssh_client = None
    
    def _get_ssh_connection(self):
        """Get SSH connection to the agent."""
        if self.ssh_client is None:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            connect_kwargs = {
                'hostname': self.agent.ip_address,
                'port': self.agent.port,
                'username': self.agent.ssh_username,
                'timeout': 30,
            }
            
            # Handle SSH private key (stored as string content in database)
            if self.agent.ssh_private_key:
                try:
                    # Load key from string
                    key_file = StringIO(self.agent.ssh_private_key)
                    pkey = paramiko.RSAKey.from_private_key(key_file)
                    connect_kwargs['pkey'] = pkey
                except Exception as e:
                    # Try DSA key if RSA fails
                    try:
                        key_file = StringIO(self.agent.ssh_private_key)
                        pkey = paramiko.DSSKey.from_private_key(key_file)
                        connect_kwargs['pkey'] = pkey
                    except Exception:
                        # Try ECDSA key
                        try:
                            key_file = StringIO(self.agent.ssh_private_key)
                            pkey = paramiko.ECDSAKey.from_private_key(key_file)
                            connect_kwargs['pkey'] = pkey
                        except Exception:
                            # Try Ed25519 key
                            try:
                                key_file = StringIO(self.agent.ssh_private_key)
                                pkey = paramiko.Ed25519Key.from_private_key(key_file)
                                connect_kwargs['pkey'] = pkey
                            except Exception:
                                raise ValueError(f"Could not load SSH private key: {e}")
            elif self.agent.ssh_password:
                connect_kwargs['password'] = self.agent.ssh_password
            
            self.ssh_client.connect(**connect_kwargs)
        
        return self.ssh_client
    
    def _execute_ssh_command(self, command: str) -> Tuple[str, str, int]:
        """Execute command via SSH."""
        ssh = self._get_ssh_connection()
        stdin, stdout, stderr = ssh.exec_command(command)
        
        exit_code = stdout.channel.recv_exit_status()
        stdout_text = stdout.read().decode('utf-8', errors='ignore')
        stderr_text = stderr.read().decode('utf-8', errors='ignore')
        
        return stdout_text, stderr_text, exit_code
    
    def _has_tuxsec_cli(self) -> bool:
        """Check if the new tuxsec-cli is available on the agent."""
        try:
            stdout, stderr, exit_code = self._execute_ssh_command('which tuxsec-cli 2>/dev/null')
            return exit_code == 0 and 'tuxsec-cli' in stdout
        except Exception:
            return False
    
    def _check_tuxsec_rootd(self) -> bool:
        """Check if tuxsec-rootd service is running."""
        try:
            stdout, stderr, exit_code = self._execute_ssh_command('systemctl is-active tuxsec-rootd 2>/dev/null')
            return exit_code == 0 and stdout.strip() == 'active'
        except Exception:
            return False
    
    def _detect_os_info(self) -> Optional[str]:
        """Detect operating system from /etc files."""
        try:
            # Try /etc/os-release first (most modern distros)
            stdout, stderr, exit_code = self._execute_ssh_command('cat /etc/os-release 2>/dev/null')
            if exit_code == 0 and stdout:
                # Parse PRETTY_NAME or NAME and VERSION
                for line in stdout.split('\n'):
                    if line.startswith('PRETTY_NAME='):
                        return line.split('=', 1)[1].strip('"')
                    
            # Try /etc/redhat-release (RHEL, CentOS, Fedora)
            stdout, stderr, exit_code = self._execute_ssh_command('cat /etc/redhat-release 2>/dev/null')
            if exit_code == 0 and stdout:
                return stdout.strip()
            
            # Try /etc/lsb-release (Ubuntu, Debian)
            stdout, stderr, exit_code = self._execute_ssh_command('cat /etc/lsb-release 2>/dev/null')
            if exit_code == 0 and stdout:
                for line in stdout.split('\n'):
                    if line.startswith('DISTRIB_DESCRIPTION='):
                        return line.split('=', 1)[1].strip('"')
            
            # Try /etc/issue as last resort
            stdout, stderr, exit_code = self._execute_ssh_command('cat /etc/issue 2>/dev/null | head -n1')
            if exit_code == 0 and stdout:
                # Clean up escape sequences and extra text
                os_info = stdout.strip().split('\\')[0].strip()
                if os_info and os_info != '':
                    return os_info
            
            return None
        except Exception as e:
            # If detection fails, return None rather than raising
            return None
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test SSH connection to new agent (v0.1.0+)."""
        try:
            # Test basic connectivity
            stdout, stderr, exit_code = self._execute_ssh_command('echo "test"')
            
            if exit_code != 0:
                return {
                    'success': False,
                    'error': f'SSH test command failed: {stderr}'
                }
            
            # Check if tuxsec-cli is available
            has_cli = self._has_tuxsec_cli()
            if not has_cli:
                return {
                    'success': False,
                    'error': 'tuxsec-cli not found. Please install TuxSec agent v0.1.0+'
                }
            
            # Check if tuxsec-rootd is running
            rootd_running = self._check_tuxsec_rootd()
            if not rootd_running:
                return {
                    'success': False,
                    'error': 'tuxsec-rootd service is not running. Start it with: systemctl start tuxsec-rootd'
                }
            
            # Get system info
            stdout, stderr, exit_code = self._execute_ssh_command('tuxsec-cli system-info')
            if exit_code == 0 and stdout.strip():
                try:
                    system_info = json.loads(stdout)
                    
                    # Format OS string from distribution info
                    os_string = "Unknown"
                    if system_info.get('distribution'):
                        dist = system_info['distribution']
                        os_string = f"{dist.get('name', 'Unknown')} {dist.get('version', '')}"
                    
                    # Get agent version from tuxsec-agent package
                    agent_version_cmd = 'rpm -q tuxsec-agent --qf "%{VERSION}-%{RELEASE}" 2>/dev/null || echo "unknown"'
                    version_stdout, _, version_exit = self._execute_ssh_command(agent_version_cmd)
                    agent_version = version_stdout.strip() if version_exit == 0 else "unknown"
                    
                    # Get available modules
                    modules_stdout, _, modules_exit = self._execute_ssh_command('tuxsec-cli list-modules 2>/dev/null')
                    available_modules = []
                    if modules_exit == 0:
                        # Parse module list (format: "Available modules:\n  - module1\n  - module2")
                        for line in modules_stdout.split('\n'):
                            line = line.strip()
                            if line.startswith('- '):
                                available_modules.append(line[2:])
                    
                    # Get installed module packages
                    installed_stdout, _, installed_exit = self._execute_ssh_command('tuxsec-cli installed-modules 2>/dev/null')
                    installed_modules = []
                    if installed_exit == 0:
                        try:
                            installed_data = json.loads(installed_stdout)
                            installed_modules = installed_data.get('modules', [])
                        except json.JSONDecodeError:
                            pass
                    
                    # Update agent metadata
                    self.agent.operating_system = os_string
                    self.agent.version = agent_version
                    self.agent.available_modules = available_modules
                    self.agent.installed_modules = installed_modules
                    await sync_to_async(self.agent.save)(update_fields=['operating_system', 'version', 'available_modules', 'installed_modules'])
                    
                    return {
                        'success': True,
                        'connection_type': 'SSH (tuxsec-cli)',
                        'agent_version': agent_version,
                        'hostname': system_info.get('hostname'),
                        'operating_system': os_string,
                        'uptime': system_info.get('uptime_seconds'),
                        'modules': available_modules,
                        'message': 'TuxSec agent connection successful'
                    }
                except json.JSONDecodeError as e:
                    return {
                        'success': False,
                        'error': f'Failed to parse system info JSON: {str(e)}'
                    }
            
            return {
                'success': True,
                'connection_type': 'SSH (tuxsec-cli)',
                'message': 'SSH connection successful'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'SSH connection failed: {str(e)}'
            }
    
    async def execute_command(self, command: str, parameters: Optional[Dict] = None, module: str = 'firewalld') -> Dict[str, Any]:
        """Execute command via tuxsec-cli (new agent v0.1.0+)."""
        try:
            # Normalize command names (handle both hyphen and underscore)
            command = command.replace('-', '_')
            
            # Build tuxsec-cli command
            # Note: No sudo needed - SSH connection is already as tuxsec user
            cmd_parts = ['tuxsec-cli', 'execute', module, command]
            
            # Add parameters
            if parameters:
                for key, value in parameters.items():
                    # Convert boolean to lowercase string
                    if isinstance(value, bool):
                        value = str(value).lower()
                    cmd_parts.extend(['--param', f'{key}={value}'])
            
            cli_cmd = ' '.join(cmd_parts)
            stdout, stderr, exit_code = self._execute_ssh_command(cli_cmd)
            
            # Parse JSON response from tuxsec-cli
            if exit_code == 0 and stdout.strip():
                try:
                    result = json.loads(stdout)
                    
                    # Check if response has the {success, result, error} wrapper
                    if 'success' in result or 'result' in result or 'error' in result:
                        # Wrapped format: {success: bool, result: any, error: str}
                        success = result.get('success', False)
                        output = result.get('result', {})
                        error = result.get('error')
                    else:
                        # Direct rootd response format - treat entire response as result
                        success = True
                        output = result
                        error = None
                    
                    # Log the command (wrap database call for async context)
                    from asgiref.sync import sync_to_async
                    await sync_to_async(AgentCommand.objects.create)(
                        agent=self.agent,
                        module=module,
                        action=command,
                        params=parameters or {},
                        result=output,
                        status='completed' if success else 'failed'
                    )
                    
                    return {
                        'success': success,
                        'result': output,
                        'error': error,
                        'output': output  # For backward compatibility
                    }
                except json.JSONDecodeError:
                    # If not JSON, treat as plain text output
                    from asgiref.sync import sync_to_async
                    await sync_to_async(AgentCommand.objects.create)(
                        agent=self.agent,
                        module=module,
                        action=command,
                        params=parameters or {},
                        result={'output': stdout},
                        status='completed'
                    )
                    return {
                        'success': True,
                        'output': stdout,
                        'result': {'output': stdout}
                    }
            else:
                # Command failed
                from asgiref.sync import sync_to_async
                await sync_to_async(AgentCommand.objects.create)(
                    agent=self.agent,
                    module=module,
                    action=command,
                    params=parameters or {},
                    result={'error': stderr},
                    status='failed'
                )
                return {
                    'success': False,
                    'error': stderr,
                    'output': stderr
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_firewall_status(self) -> Dict[str, Any]:
        """Get firewall status via tuxsec-cli."""
        return await self.execute_command('get_status', module='firewalld')
    
    async def get_zones(self) -> List[Dict[str, Any]]:
        """Get firewall zones via tuxsec-cli."""
        result = await self.execute_command('list_zones', module='firewalld')
        if result.get('success'):
            zones_data = result.get('result', {}).get('zones', [])
            return zones_data if isinstance(zones_data, list) else []
        return []
    
    async def get_rules(self) -> List[Dict[str, Any]]:
        """Get firewall rules via tuxsec-cli."""
        # Get all zones first
        zones_result = await self.get_zones()
        rules = []
        
        # For each zone, get its configuration
        for zone in zones_result:
            zone_name = zone if isinstance(zone, str) else zone.get('name')
            if zone_name:
                zone_result = await self.execute_command('get_zone', {'zone': zone_name}, module='firewalld')
                if zone_result.get('success'):
                    zone_config = zone_result.get('result', {})
                    rules.append({
                        'zone': zone_name,
                        'config': zone_config
                    })
        
        return rules
    
    async def get_available_services(self) -> List[str]:
        """Get list of available firewalld services via tuxsec-cli."""
        result = await self.execute_command('list_services', module='firewalld')
        if result.get('success'):
            services = result.get('result', {}).get('services', [])
            return services if isinstance(services, list) else []
        return []


class AgentToServerManager(BaseConnectionManager):
    """Pull mode - Agent polls server for commands (agent_to_server connection type)."""
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test if agent has connected recently."""
        if self.agent.last_seen:
            time_diff = datetime.now() - self.agent.last_seen.replace(tzinfo=None)
            if time_diff < timedelta(minutes=5):
                return {
                    'success': True,
                    'connection_type': 'Pull Mode (Agent to Server)',
                    'last_seen': self.agent.last_seen.isoformat(),
                    'message': 'Agent connected recently'
                }
        
        return {
            'success': False,
            'error': 'Agent has not connected recently or never connected'
        }
    
    async def execute_command(self, command: str, parameters: Optional[Dict] = None, module: str = 'firewalld') -> Dict[str, Any]:
        """Queue command for agent to execute on next poll."""
        try:
            # Create a pending command
            agent_command = AgentCommand.objects.create(
                agent=self.agent,
                module=module,
                action=command,
                params=parameters or {},
                status='pending'
            )
            
            return {
                'success': True,
                'message': 'Command queued for agent',
                'command_id': str(agent_command.id)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_firewall_status(self) -> Dict[str, Any]:
        """Queue get_status command."""
        return await self.execute_command('get_status', module='firewalld')
    
    async def get_zones(self) -> List[Dict[str, Any]]:
        """Queue list_zones command."""
        result = await self.execute_command('list_zones', module='firewalld')
        # Note: This queues the command, actual results come later
        return []
    
    async def get_rules(self) -> List[Dict[str, Any]]:
        """Queue command to get rules."""
        # Note: This queues commands, actual results come later
        return []
    
    async def get_available_services(self) -> List[str]:
        """Queue command to get services."""
        result = await self.execute_command('list_services', module='firewalld')
        return []


class ServerToAgentManager(BaseConnectionManager):
    """Push mode - Server connects to agent (server_to_agent connection type)."""
    
    def __init__(self, agent: Agent):
        super().__init__(agent)
        self.base_url = f"https://{agent.ip_address}:{agent.agent_port}"
        self.headers = {}
        
        if agent.agent_api_key:
            self.headers['X-API-Key'] = agent.agent_api_key
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test HTTPS connection to agent."""
        try:
            response = requests.get(
                f"{self.base_url}/health", 
                headers=self.headers,
                verify=False,  # TODO: Implement cert verification
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'connection_type': 'Push Mode (Server to Agent)',
                    'agent_version': data.get('version', 'Unknown'),
                    'modules': data.get('modules', []),
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
    
    async def execute_command(self, command: str, parameters: Optional[Dict] = None, module: str = 'firewalld') -> Dict[str, Any]:
        """Execute command on agent via HTTPS POST."""
        try:
            payload = {
                'module': module,
                'action': command,
                'params': parameters or {}
            }
            
            response = requests.post(
                f"{self.base_url}/execute",
                json=payload,
                headers=self.headers,
                verify=False,  # TODO: Implement cert verification
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Log the command
                AgentCommand.objects.create(
                    agent=self.agent,
                    module=module,
                    action=command,
                    params=parameters or {},
                    result=data.get('result', {}),
                    status='completed' if data.get('success') else 'failed'
                )
                
                return data
            else:
                return {
                    'success': False,
                    'error': f'HTTP request failed with status: {response.status_code}'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_firewall_status(self) -> Dict[str, Any]:
        """Get firewall status from agent."""
        return await self.execute_command('get_status', module='firewalld')
    
    async def get_zones(self) -> List[Dict[str, Any]]:
        """Get firewall zones from agent."""
        result = await self.execute_command('list_zones', module='firewalld')
        if result.get('success'):
            zones = result.get('result', {}).get('zones', [])
            return zones if isinstance(zones, list) else []
        return []
    
    async def get_rules(self) -> List[Dict[str, Any]]:
        """Get firewall rules from agent."""
        zones_result = await self.get_zones()
        rules = []
        
        for zone in zones_result:
            zone_name = zone if isinstance(zone, str) else zone.get('name')
            if zone_name:
                zone_result = await self.execute_command('get_zone', {'zone': zone_name}, module='firewalld')
                if zone_result.get('success'):
                    zone_config = zone_result.get('result', {})
                    rules.append({
                        'zone': zone_name,
                        'config': zone_config
                    })
        
        return rules
    
    async def get_available_services(self) -> List[str]:
        """Get list of available firewalld services from agent."""
        result = await self.execute_command('list_services', module='firewalld')
        if result.get('success'):
            services = result.get('result', {}).get('services', [])
            return services if isinstance(services, list) else []
        return []


def get_connection_manager(agent: Agent) -> BaseConnectionManager:
    """Factory function to get the appropriate connection manager for an agent."""
    if agent.connection_type == 'ssh':
        return SSHConnectionManager(agent)
    elif agent.connection_type == 'server_to_agent':
        return ServerToAgentManager(agent)
    else:  # agent_to_server (pull mode)
        return AgentToServerManager(agent)