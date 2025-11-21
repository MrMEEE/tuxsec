#!/usr/bin/env python3
"""
Base module class for tuxsec-rootd modules.

All modules must inherit from BaseModule and implement the required methods.
Modules are loaded dynamically and can be enabled/disabled at runtime.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging
from .protocol import ModuleCapability, ModuleInfo, CommandRequest, CommandResponse


class BaseModule(ABC):
    """Base class for all rootd modules."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"tuxsec-rootd.module.{self.name}")
        self._initialized = False
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Module name (must be unique)."""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Module version."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Module description."""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[ModuleCapability]:
        """
        Return list of capabilities this module provides.
        Each capability describes an action the module can perform.
        """
        pass
    
    @abstractmethod
    def initialize(self) -> tuple[bool, Optional[str]]:
        """
        Initialize the module. Called once on startup.
        Returns: (success, error_message)
        """
        pass
    
    @abstractmethod
    def shutdown(self):
        """Cleanup on module shutdown."""
        pass
    
    @abstractmethod
    def execute_command(self, command: CommandRequest) -> CommandResponse:
        """
        Execute a command on this module.
        
        Args:
            command: The command request containing action and parameters
            
        Returns:
            CommandResponse with success status and data or error
        """
        pass
    
    def is_initialized(self) -> bool:
        """Check if module is initialized."""
        return self._initialized
    
    def get_info(self) -> ModuleInfo:
        """Get module information."""
        return ModuleInfo(
            name=self.name,
            version=self.version,
            description=self.description,
            capabilities=self.get_capabilities()
        )
    
    def validate_command(self, command: CommandRequest) -> tuple[bool, Optional[str]]:
        """
        Validate a command before execution.
        
        Args:
            command: The command to validate
            
        Returns:
            (is_valid, error_message)
        """
        # Check if action is in capabilities
        capabilities = {cap.name for cap in self.get_capabilities()}
        if command.action not in capabilities:
            return False, f"Unknown action '{command.action}' for module '{self.name}'"
        
        return True, None
    
    def _run_command(self, cmd: List[str], timeout: int = 30) -> tuple[bool, str, str]:
        """
        Helper method to run shell commands safely.
        
        Args:
            cmd: Command as list of strings
            timeout: Timeout in seconds
            
        Returns:
            (success, stdout, stderr)
        """
        import subprocess
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            success = result.returncode == 0
            return success, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return False, "", str(e)


class ModuleRegistry:
    """Registry for managing available modules."""
    
    def __init__(self):
        self.modules: Dict[str, BaseModule] = {}
        self.logger = logging.getLogger("tuxsec-rootd.registry")
    
    def register_module(self, module: BaseModule) -> tuple[bool, Optional[str]]:
        """
        Register a new module.
        
        Args:
            module: The module instance to register
            
        Returns:
            (success, error_message)
        """
        if module.name in self.modules:
            return False, f"Module '{module.name}' is already registered"
        
        # Initialize the module
        success, error = module.initialize()
        if not success:
            return False, f"Failed to initialize module '{module.name}': {error}"
        
        module._initialized = True
        self.modules[module.name] = module
        self.logger.info(f"Registered module: {module.name} v{module.version}")
        return True, None
    
    def unregister_module(self, module_name: str) -> bool:
        """Unregister a module."""
        if module_name not in self.modules:
            return False
        
        module = self.modules[module_name]
        module.shutdown()
        del self.modules[module_name]
        self.logger.info(f"Unregistered module: {module_name}")
        return True
    
    def get_module(self, module_name: str) -> Optional[BaseModule]:
        """Get a module by name."""
        return self.modules.get(module_name)
    
    def list_modules(self) -> List[str]:
        """List all registered module names."""
        return list(self.modules.keys())
    
    def get_all_modules_info(self) -> List[ModuleInfo]:
        """Get information about all registered modules."""
        return [module.get_info() for module in self.modules.values()]
    
    def shutdown_all(self):
        """Shutdown all modules."""
        for module in self.modules.values():
            try:
                module.shutdown()
            except Exception as e:
                self.logger.error(f"Error shutting down module {module.name}: {e}")
        self.modules.clear()
