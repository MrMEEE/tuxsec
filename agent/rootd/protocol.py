#!/usr/bin/env python3
"""
Protocol definitions for communication between userspace and root components.

This defines the wire protocol and message formats for the Unix socket communication.
All communication is JSON-based with strict validation.
"""

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, Any, Optional, List
import json


class MessageType(str, Enum):
    """Types of messages that can be sent over the socket."""
    # Query messages
    PING = "ping"
    LIST_MODULES = "list_modules"
    MODULE_INFO = "module_info"
    SYSTEM_INFO = "system_info"
    
    # Command messages
    EXECUTE_COMMAND = "execute_command"
    
    # Response messages
    SUCCESS = "success"
    ERROR = "error"


@dataclass
class Message:
    """Base message structure for socket communication."""
    type: str
    request_id: str
    data: Dict[str, Any]
    
    def to_json(self) -> str:
        """Serialize message to JSON."""
        return json.dumps(asdict(self))
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        """Deserialize message from JSON."""
        data = json.loads(json_str)
        return cls(
            type=data['type'],
            request_id=data['request_id'],
            data=data['data']
        )
    
    def validate(self) -> bool:
        """Validate message structure."""
        if not self.type or not self.request_id:
            return False
        if not isinstance(self.data, dict):
            return False
        return True


@dataclass
class CommandRequest:
    """Request to execute a module command."""
    module: str
    action: str
    parameters: Dict[str, Any]
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """Validate command request."""
        if not self.module:
            return False, "Module name is required"
        if not self.action:
            return False, "Action is required"
        if not isinstance(self.parameters, dict):
            return False, "Parameters must be a dictionary"
        return True, None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'module': self.module,
            'action': self.action,
            'parameters': self.parameters
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CommandRequest':
        """Create from dictionary."""
        return cls(
            module=data.get('module', ''),
            action=data.get('action', ''),
            parameters=data.get('parameters', {})
        )


@dataclass
class CommandResponse:
    """Response from executing a module command."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {'success': self.success}
        if self.data is not None:
            result['data'] = self.data
        if self.error is not None:
            result['error'] = self.error
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CommandResponse':
        """Create from dictionary."""
        return cls(
            success=data.get('success', False),
            data=data.get('data'),
            error=data.get('error')
        )


@dataclass
class ModuleCapability:
    """Describes a capability/action that a module provides."""
    name: str
    description: str
    parameters: List[Dict[str, str]]  # List of {name, type, description, required}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'description': self.description,
            'parameters': self.parameters
        }


@dataclass
class ModuleInfo:
    """Information about a module."""
    name: str
    version: str
    description: str
    capabilities: List[ModuleCapability]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'capabilities': [cap.to_dict() for cap in self.capabilities]
        }
