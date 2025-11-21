#!/usr/bin/env python3
"""
Client library for communicating with tuxsec-rootd.

This provides a simple Python interface for the userspace component to
communicate with the root daemon through the Unix socket.
"""

import socket
import json
import uuid
from typing import Dict, Any, Optional, List
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from rootd.protocol import (
    Message, MessageType, CommandRequest, CommandResponse,
    ModuleInfo
)


class RootDaemonClient:
    """Client for communicating with tuxsec-rootd."""
    
    def __init__(self, socket_path: str = "/var/run/tuxsec/rootd.sock"):
        self.socket_path = socket_path
    
    def _send_request(self, message: Message) -> Message:
        """Send a request to the daemon and get response."""
        try:
            # Connect to Unix socket
            client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client_socket.connect(self.socket_path)
            
            # Send message
            client_socket.sendall((message.to_json() + '\n').encode('utf-8'))
            
            # Receive response
            data = b""
            while True:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                data += chunk
                
                if b'\n' in data:
                    break
            
            client_socket.close()
            
            if not data:
                raise Exception("No response from daemon")
            
            # Parse response
            response_str = data.decode('utf-8').strip()
            response = Message.from_json(response_str)
            
            return response
            
        except FileNotFoundError:
            raise Exception(f"Socket not found: {self.socket_path}. Is tuxsec-rootd running?")
        except ConnectionRefusedError:
            raise Exception("Connection refused. Is tuxsec-rootd running?")
        except Exception as e:
            raise Exception(f"Error communicating with daemon: {e}")
    
    def ping(self) -> bool:
        """Ping the daemon to check if it's alive."""
        try:
            message = Message(
                type=MessageType.PING,
                request_id=str(uuid.uuid4()),
                data={}
            )
            response = self._send_request(message)
            return response.type == MessageType.SUCCESS
        except Exception:
            return False
    
    def list_modules(self) -> List[str]:
        """List all available modules."""
        message = Message(
            type=MessageType.LIST_MODULES,
            request_id=str(uuid.uuid4()),
            data={}
        )
        response = self._send_request(message)
        
        if response.type == MessageType.ERROR:
            raise Exception(response.data.get('error', 'Unknown error'))
        
        return response.data.get('modules', [])
    
    def get_module_info(self, module_name: str) -> Dict[str, Any]:
        """Get information about a module."""
        message = Message(
            type=MessageType.MODULE_INFO,
            request_id=str(uuid.uuid4()),
            data={'module': module_name}
        )
        response = self._send_request(message)
        
        if response.type == MessageType.ERROR:
            raise Exception(response.data.get('error', 'Unknown error'))
        
        return response.data.get('module_info', {})
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information."""
        message = Message(
            type=MessageType.SYSTEM_INFO,
            request_id=str(uuid.uuid4()),
            data={}
        )
        response = self._send_request(message)
        
        if response.type == MessageType.ERROR:
            raise Exception(response.data.get('error', 'Unknown error'))
        
        result = response.data
        if result.get('success'):
            return result.get('data', {})
        else:
            raise Exception(result.get('error', 'Unknown error'))
    
    def execute_command(self, module: str, action: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a command on a module.
        
        Args:
            module: Module name
            action: Action to perform
            parameters: Action parameters
            
        Returns:
            Command result data
            
        Raises:
            Exception if command fails
        """
        if parameters is None:
            parameters = {}
        
        command = CommandRequest(
            module=module,
            action=action,
            parameters=parameters
        )
        
        message = Message(
            type=MessageType.EXECUTE_COMMAND,
            request_id=str(uuid.uuid4()),
            data=command.to_dict()
        )
        
        response = self._send_request(message)
        
        if response.type == MessageType.ERROR:
            error_msg = response.data.get('error', 'Unknown error')
            raise Exception(f"Command failed: {error_msg}")
        
        result = CommandResponse.from_dict(response.data)
        
        if not result.success:
            raise Exception(f"Command failed: {result.error}")
        
        return result.data or {}
