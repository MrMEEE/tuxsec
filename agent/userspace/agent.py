#!/usr/bin/env python3
"""
TuxSec Agent - Userspace Component

This component runs as an unprivileged user (tuxsec) and acts as the bridge
between the TuxSec server and the root daemon.

Supports three connection modes:
1. Pull mode: Initiates connections to server and polls for jobs
2. Push mode: Opens a port and accepts connections from server
3. SSH mode: Accepts jobs through SSH commands from server

All privileged operations are delegated to the root daemon via Unix socket.
"""

import os
import sys
import asyncio
import signal
import argparse
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import yaml
import httpx

from .rootd_client import RootDaemonClient


class AgentConfig:
    """Agent configuration."""
    
    def __init__(self, config_file: str = "/etc/tuxsec/agent.yaml"):
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if not os.path.exists(self.config_file):
            # Return default config
            return {
                'mode': 'pull',  # pull, push, or ssh
                'server_url': 'https://tuxsec.example.com',
                'agent_id': None,
                'api_key': None,
                'poll_interval': 30,
                'listen_host': '0.0.0.0',
                'listen_port': 8443,
                'ssl_cert': '/etc/tuxsec/certs/agent.crt',
                'ssl_key': '/etc/tuxsec/certs/agent.key',
                'ca_cert': '/etc/tuxsec/certs/ca.crt',
                'log_level': 'INFO',
                'log_file': '/var/log/tuxsec/agent.log',
            }
        
        with open(self.config_file, 'r') as f:
            return yaml.safe_load(f)
    
    def get(self, key: str, default=None):
        """Get configuration value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value."""
        self.config[key] = value
    
    def save(self):
        """Save configuration to file."""
        with open(self.config_file, 'w') as f:
            yaml.dump(self.config, f)


class TuxSecAgent:
    """Main agent class."""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.rootd_client = RootDaemonClient()
        self.running = False
        self.logger = self._setup_logging()
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging."""
        log_level = getattr(logging, self.config.get('log_level', 'INFO'))
        log_file = self.config.get('log_file', '/var/log/tuxsec/agent.log')
        
        # Create log directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, mode=0o755, exist_ok=True)
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        return logging.getLogger('tuxsec-agent')
    
    async def start(self):
        """Start the agent."""
        self.logger.info("Starting tuxsec-agent...")
        
        # Check if running as root (should NOT be)
        if os.geteuid() == 0:
            self.logger.error("This agent should NOT be run as root. Run as 'tuxsec' user.")
            sys.exit(1)
        
        # Check connection to root daemon
        if not self.rootd_client.ping():
            self.logger.error("Cannot connect to tuxsec-rootd. Is it running?")
            sys.exit(1)
        
        self.logger.info("Connected to tuxsec-rootd")
        
        # Get system info
        try:
            system_info = self.rootd_client.get_system_info()
            self.logger.info(f"System: {system_info.get('hostname')} - {system_info.get('os', {}).get('system')}")
        except Exception as e:
            self.logger.warning(f"Could not get system info: {e}")
        
        self.running = True
        
        # Start based on mode
        mode = self.config.get('mode', 'pull')
        
        if mode == 'pull':
            await self._run_pull_mode()
        elif mode == 'push':
            await self._run_push_mode()
        elif mode == 'ssh':
            await self._run_ssh_mode()
        else:
            self.logger.error(f"Unknown mode: {mode}")
            sys.exit(1)
    
    async def _run_pull_mode(self):
        """Run in pull mode - initiate connections to server."""
        self.logger.info("Running in PULL mode")
        
        server_url = self.config.get('server_url')
        agent_id = self.config.get('agent_id')
        api_key = self.config.get('api_key')
        poll_interval = self.config.get('poll_interval', 30)
        
        if not agent_id or not api_key:
            self.logger.error("agent_id and api_key are required for pull mode")
            sys.exit(1)
        
        async with httpx.AsyncClient() as client:
            while self.running:
                try:
                    # Check in with server and get pending commands
                    response = await client.post(
                        f"{server_url}/agents/api/checkin/",
                        headers={'X-API-Key': api_key},
                        json={
                            'agent_id': agent_id,
                            'api_key': api_key,
                            'status': 'online',
                        },
                        timeout=10.0
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Update poll interval if server provides one
                        server_interval = data.get('sync_interval')
                        if server_interval and server_interval != poll_interval:
                            poll_interval = server_interval
                            self.logger.info(f"Updated poll interval to {poll_interval} seconds")
                        
                        # Process pending commands
                        commands = data.get('commands', [])
                        for cmd in commands:
                            await self._execute_command(cmd, client)
                    
                    # Wait before next poll
                    await asyncio.sleep(poll_interval)
                    
                except Exception as e:
                    self.logger.error(f"Error in pull mode: {e}")
                    await asyncio.sleep(poll_interval)
    
    async def _run_push_mode(self):
        """Run in push mode - listen for connections from server."""
        self.logger.info("Running in PUSH mode")
        
        listen_host = self.config.get('listen_host', '0.0.0.0')
        listen_port = self.config.get('listen_port', 8443)
        
        from aiohttp import web
        
        app = web.Application()
        app.router.add_post('/execute', self._handle_push_request)
        app.router.add_get('/health', self._handle_health_check)
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        # TODO: Setup SSL context
        site = web.TCPSite(runner, listen_host, listen_port)
        await site.start()
        
        self.logger.info(f"Listening on {listen_host}:{listen_port}")
        
        # Keep running
        while self.running:
            await asyncio.sleep(1)
        
        await runner.cleanup()
    
    async def _run_ssh_mode(self):
        """Run in SSH mode - wait for SSH commands."""
        self.logger.info("Running in SSH mode")
        self.logger.info("Agent ready to accept SSH commands")
        
        # In SSH mode, the agent just stays running and waits for
        # commands to come through the CLI interface
        while self.running:
            await asyncio.sleep(1)
    
    async def _handle_push_request(self, request):
        """Handle incoming push request."""
        from aiohttp import web
        
        try:
            # TODO: Verify API key
            
            data = await request.json()
            job = data.get('job')
            
            if not job:
                return web.json_response({'error': 'No job provided'}, status=400)
            
            result = await self._execute_job(job)
            
            return web.json_response(result)
            
        except Exception as e:
            self.logger.error(f"Error handling push request: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def _handle_health_check(self, request):
        """Handle health check request."""
        from aiohttp import web
        
        # Check connection to rootd
        is_healthy = self.rootd_client.ping()
        
        return web.json_response({
            'status': 'healthy' if is_healthy else 'unhealthy',
            'rootd_connected': is_healthy
        })
    
    async def _execute_command(self, command: Dict[str, Any], client: Optional[httpx.AsyncClient] = None) -> Dict[str, Any]:
        """Execute a command from the server."""
        command_id = command.get('id')
        module = command.get('module')
        action = command.get('action')
        params = command.get('params', {})
        
        self.logger.info(f"Executing command {command_id}: {module}.{action}")
        
        try:
            # Execute command through rootd
            result = self.rootd_client.execute_command(module, action, params)
            
            response = {
                'command_id': command_id,
                'success': True,
                'output': result
            }
            
            # Report result back to server if client provided
            if client:
                await self._report_command_result(response, client)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error executing command {command_id}: {e}")
            
            response = {
                'command_id': command_id,
                'success': False,
                'error': str(e)
            }
            
            # Report error back to server if client provided
            if client:
                await self._report_command_result(response, client)
            
            return response
    
    async def _report_command_result(self, result: Dict[str, Any], client: httpx.AsyncClient):
        """Report command result back to server via next checkin."""
        # Results will be sent with next checkin - store locally for now
        # In a production system, you might want to store these in a queue
        pass
    
    def execute_command_sync(self, module: str, action: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a command synchronously (for SSH mode)."""
        if parameters is None:
            parameters = {}
        
        try:
            result = self.rootd_client.execute_command(module, action, parameters)
            return {
                'success': True,
                'result': result
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signal."""
        self.logger.info("Received shutdown signal")
        self.running = False
    
    def stop(self):
        """Stop the agent."""
        self.logger.info("Stopping tuxsec-agent...")
        self.running = False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='TuxSec Agent')
    parser.add_argument(
        '--config',
        default='/etc/tuxsec/agent.yaml',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--mode',
        choices=['pull', 'push', 'ssh'],
        help='Agent mode (overrides config file)'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = AgentConfig(args.config)
    
    # Override mode if specified
    if args.mode:
        config.set('mode', args.mode)
    
    # Create and start agent
    agent = TuxSecAgent(config)
    
    # Run event loop
    try:
        asyncio.run(agent.start())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
