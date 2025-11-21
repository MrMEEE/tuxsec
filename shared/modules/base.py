"""
Base module class and interfaces for TuxSec modules.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field


class ModuleCapability(str, Enum):
    """Capabilities that a module can provide."""
    FIREWALL = "firewall"
    SELINUX = "selinux"
    ANTIVIRUS = "antivirus"
    INTRUSION_DETECTION = "intrusion_detection"
    FILE_INTEGRITY = "file_integrity"
    LOG_MONITORING = "log_monitoring"
    COMPLIANCE = "compliance"
    BACKUP = "backup"
    CUSTOM = "custom"


class ModuleCommand(BaseModel):
    """Command to be executed by a module on an agent."""
    module_name: str
    action: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    timeout: int = 30  # seconds


class ModuleResult(BaseModel):
    """Result of a module command execution."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class BaseModule(ABC):
    """
    Base class for all TuxSec modules.
    
    Each module provides specific security functionality and can be
    enabled/disabled globally or per-agent.
    """
    
    def __init__(self):
        self._enabled = False
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for the module."""
        pass
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name for the module."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what the module does."""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Module version."""
        pass
    
    @property
    @abstractmethod
    def capabilities(self) -> List[ModuleCapability]:
        """List of capabilities this module provides."""
        pass
    
    @property
    def enabled(self) -> bool:
        """Whether this module is currently enabled."""
        return self._enabled
    
    @abstractmethod
    def get_required_packages(self) -> List[str]:
        """
        Return list of system packages required by this module.
        
        Returns:
            List of package names (e.g., ['firewalld', 'python3-firewall'])
        """
        pass
    
    @abstractmethod
    def check_availability(self) -> bool:
        """
        Check if the module can run on the current system.
        
        Returns:
            True if all requirements are met, False otherwise
        """
        pass
    
    @abstractmethod
    def get_available_actions(self) -> List[str]:
        """
        Get list of actions this module supports.
        
        Returns:
            List of action names (e.g., ['get_zones', 'add_service', 'reload'])
        """
        pass
    
    @abstractmethod
    def execute_action(self, action: str, parameters: Dict[str, Any]) -> ModuleResult:
        """
        Execute a module-specific action.
        
        Args:
            action: Name of the action to execute
            parameters: Dictionary of parameters for the action
            
        Returns:
            ModuleResult with execution results
        """
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status/configuration of the module.
        
        Returns:
            Dictionary with current module status
        """
        pass
    
    def enable(self) -> bool:
        """Enable this module."""
        if self.check_availability():
            self._enabled = True
            return True
        return False
    
    def disable(self) -> bool:
        """Disable this module."""
        self._enabled = False
        return True
    
    def validate_action(self, action: str) -> bool:
        """Check if an action is supported by this module."""
        return action in self.get_available_actions()
    
    def get_configuration_schema(self) -> Dict[str, Any]:
        """
        Get JSON schema for module configuration.
        
        Returns:
            JSON Schema describing valid configuration options
        """
        return {
            "type": "object",
            "properties": {},
            "additionalProperties": False
        }
    
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """
        Validate a configuration dictionary against the module's schema.
        
        Args:
            config: Configuration to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Default implementation - can be overridden
        return True
