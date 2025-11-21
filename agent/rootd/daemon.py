#!/usr/bin/env python3
"""
TuxSec Root Daemon (tuxsec-rootd)

This daemon runs as root and exposes system management capabilities through
a Unix socket. It uses a modular architecture where each module provides
specific functionality (firewalld, SELinux, AIDE, etc.).

Security features:
- Only exposes well-defined module capabilities
- No arbitrary command execution
- Unix socket with strict permissions
- Request validation and sanitization
"""

import os
import sys
import socket
import signal
import logging
import json
import threading
from pathlib import Path
from typing import Optional
import uuid

from .base_module import ModuleRegistry
from .protocol import Message, MessageType, CommandRequest, CommandResponse
from .modules.systeminfo import SystemInfoModule
from .modules.firewalld import FirewalldModule


class RootDaemon:
    """Main daemon class for tuxsec-rootd."""
    
    def __init__(self, socket_path: str = "/var/run/tuxsec/rootd.sock"):
        self.socket_path = socket_path
        self.running = False
        self.server_socket: Optional[socket.socket] = None
        self.registry = ModuleRegistry()
        self.logger = self._setup_logging()
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/var/log/tuxsec/rootd.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        return logging.getLogger('tuxsec-rootd')
    
    def _load_modules(self):
        """Load and register all available modules."""
        self.logger.info("Loading modules...")
        
        # System info module (always loaded)
        systeminfo = SystemInfoModule()
        success, error = self.registry.register_module(systeminfo)
        if not success:
            self.logger.error(f"Failed to load systeminfo module: {error}")
        
        # Firewalld module (optional)
        try:
            firewalld = FirewalldModule()
            success, error = self.registry.register_module(firewalld)
            if not success:
                self.logger.warning(f"Firewalld module not available: {error}")
        except Exception as e:
            self.logger.warning(f"Could not load firewalld module: {e}")
        
        # TODO: Add more modules here (SELinux, AIDE, etc.)
        
        self.logger.info(f"Loaded {len(self.registry.modules)} modules: {', '.join(self.registry.list_modules())}")
    
    def _setup_socket(self):
        """Setup the Unix socket."""
        # Remove existing socket if it exists
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
        
        # Create directory if it doesn't exist
        socket_dir = os.path.dirname(self.socket_path)
        os.makedirs(socket_dir, mode=0o755, exist_ok=True)
        
        # Create Unix socket
        self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server_socket.bind(self.socket_path)
        
        # Set socket permissions (only tuxsec user can connect)
        os.chmod(self.socket_path, 0o660)
        
        # TODO: Change group ownership to 'tuxsec' group
        # os.chown(self.socket_path, -1, tuxsec_gid)
        
        self.server_socket.listen(5)
        self.logger.info(f"Listening on {self.socket_path}")
    
    def start(self):
        """Start the daemon."""
        self.logger.info("Starting tuxsec-rootd...")
        
        # Check if running as root
        if os.geteuid() != 0:
            self.logger.error("This daemon must be run as root")
            sys.exit(1)
        
        # Load modules
        self._load_modules()
        
        # Setup socket
        self._setup_socket()
        
        self.running = True
        self.logger.info("tuxsec-rootd started successfully")
        
        # Main loop
        self._run()
    
    def _run(self):
        """Main event loop."""
        while self.running:
            try:
                # Accept connections
                client_socket, _ = self.server_socket.accept()
                
                # Handle in a thread
                thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket,)
                )
                thread.daemon = True
                thread.start()
                
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error accepting connection: {e}")
    
    def _handle_client(self, client_socket: socket.socket):
        """Handle a client connection."""
        try:
            # Receive data
            data = b""
            while True:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                data += chunk
                
                # Check if we have a complete message (ends with newline)
                if b'\n' in data:
                    break
            
            if not data:
                return
            
            # Decode and parse message
            message_str = data.decode('utf-8').strip()
            message = Message.from_json(message_str)
            
            # Validate message
            if not message.validate():
                response = Message(
                    type=MessageType.ERROR,
                    request_id=message.request_id,
                    data={'error': 'Invalid message format'}
                )
                client_socket.sendall((response.to_json() + '\n').encode('utf-8'))
                return
            
            # Process message
            response = self._process_message(message)
            
            # Send response
            client_socket.sendall((response.to_json() + '\n').encode('utf-8'))
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
            error_response = Message(
                type=MessageType.ERROR,
                request_id="unknown",
                data={'error': 'Invalid JSON'}
            )
            client_socket.sendall((error_response.to_json() + '\n').encode('utf-8'))
        except Exception as e:
            self.logger.error(f"Error handling client: {e}")
        finally:
            client_socket.close()
    
    def _process_message(self, message: Message) -> Message:
        """Process a message and return response."""
        try:
            msg_type = message.type
            
            if msg_type == MessageType.PING:
                return Message(
                    type=MessageType.SUCCESS,
                    request_id=message.request_id,
                    data={'pong': True}
                )
            
            elif msg_type == MessageType.LIST_MODULES:
                modules = self.registry.list_modules()
                return Message(
                    type=MessageType.SUCCESS,
                    request_id=message.request_id,
                    data={'modules': modules}
                )
            
            elif msg_type == MessageType.MODULE_INFO:
                module_name = message.data.get('module')
                if not module_name:
                    return Message(
                        type=MessageType.ERROR,
                        request_id=message.request_id,
                        data={'error': 'Module name is required'}
                    )
                
                module = self.registry.get_module(module_name)
                if not module:
                    return Message(
                        type=MessageType.ERROR,
                        request_id=message.request_id,
                        data={'error': f'Module not found: {module_name}'}
                    )
                
                return Message(
                    type=MessageType.SUCCESS,
                    request_id=message.request_id,
                    data={'module_info': module.get_info().to_dict()}
                )
            
            elif msg_type == MessageType.SYSTEM_INFO:
                # Shortcut to get system info
                module = self.registry.get_module('systeminfo')
                if not module:
                    return Message(
                        type=MessageType.ERROR,
                        request_id=message.request_id,
                        data={'error': 'System info module not available'}
                    )
                
                cmd = CommandRequest(module='systeminfo', action='get_info', parameters={})
                result = module.execute_command(cmd)
                
                return Message(
                    type=MessageType.SUCCESS if result.success else MessageType.ERROR,
                    request_id=message.request_id,
                    data=result.to_dict()
                )
            
            elif msg_type == MessageType.EXECUTE_COMMAND:
                return self._execute_command(message)
            
            else:
                return Message(
                    type=MessageType.ERROR,
                    request_id=message.request_id,
                    data={'error': f'Unknown message type: {msg_type}'}
                )
                
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            return Message(
                type=MessageType.ERROR,
                request_id=message.request_id,
                data={'error': str(e)}
            )
    
    def _execute_command(self, message: Message) -> Message:
        """Execute a module command."""
        try:
            # Parse command request
            command = CommandRequest.from_dict(message.data)
            
            # Validate command
            is_valid, error = command.validate()
            if not is_valid:
                return Message(
                    type=MessageType.ERROR,
                    request_id=message.request_id,
                    data={'error': error}
                )
            
            # Get module
            module = self.registry.get_module(command.module)
            if not module:
                return Message(
                    type=MessageType.ERROR,
                    request_id=message.request_id,
                    data={'error': f'Module not found: {command.module}'}
                )
            
            # Execute command
            self.logger.info(f"Executing: {command.module}.{command.action}")
            result = module.execute_command(command)
            
            return Message(
                type=MessageType.SUCCESS if result.success else MessageType.ERROR,
                request_id=message.request_id,
                data=result.to_dict()
            )
            
        except Exception as e:
            self.logger.error(f"Error executing command: {e}")
            return Message(
                type=MessageType.ERROR,
                request_id=message.request_id,
                data={'error': str(e)}
            )
    
    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signal."""
        self.logger.info("Received shutdown signal")
        self.stop()
    
    def stop(self):
        """Stop the daemon."""
        self.logger.info("Stopping tuxsec-rootd...")
        self.running = False
        
        # Shutdown all modules
        self.registry.shutdown_all()
        
        # Close socket
        if self.server_socket:
            self.server_socket.close()
        
        # Remove socket file
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
        
        self.logger.info("tuxsec-rootd stopped")


def main():
    """Main entry point."""
    daemon = RootDaemon()
    daemon.start()


if __name__ == '__main__':
    main()
