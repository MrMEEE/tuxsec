"""
Module registry for managing available TuxSec modules.
"""

from typing import Dict, List, Optional, Type
import logging
from .base import BaseModule, ModuleCapability

logger = logging.getLogger(__name__)


class ModuleRegistry:
    """
    Central registry for all TuxSec modules.
    
    Manages module registration, discovery, and lifecycle.
    """
    
    _instance = None
    _modules: Dict[str, BaseModule] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def register(self, module: BaseModule) -> bool:
        """
        Register a module with the registry.
        
        Args:
            module: Module instance to register
            
        Returns:
            True if registered successfully, False if already registered
        """
        if module.name in self._modules:
            logger.warning(f"Module {module.name} is already registered")
            return False
        
        self._modules[module.name] = module
        logger.info(f"Registered module: {module.display_name} ({module.name})")
        return True
    
    def unregister(self, module_name: str) -> bool:
        """
        Unregister a module from the registry.
        
        Args:
            module_name: Name of the module to unregister
            
        Returns:
            True if unregistered successfully, False if not found
        """
        if module_name in self._modules:
            del self._modules[module_name]
            logger.info(f"Unregistered module: {module_name}")
            return True
        return False
    
    def get(self, module_name: str) -> Optional[BaseModule]:
        """
        Get a module by name.
        
        Args:
            module_name: Name of the module
            
        Returns:
            Module instance or None if not found
        """
        return self._modules.get(module_name)
    
    def get_all(self) -> Dict[str, BaseModule]:
        """Get all registered modules."""
        return self._modules.copy()
    
    def get_enabled(self) -> Dict[str, BaseModule]:
        """Get all enabled modules."""
        return {
            name: module 
            for name, module in self._modules.items() 
            if module.enabled
        }
    
    def get_by_capability(self, capability: ModuleCapability) -> List[BaseModule]:
        """
        Get all modules that provide a specific capability.
        
        Args:
            capability: The capability to search for
            
        Returns:
            List of modules with that capability
        """
        return [
            module 
            for module in self._modules.values() 
            if capability in module.capabilities
        ]
    
    def list_module_names(self) -> List[str]:
        """Get list of all registered module names."""
        return list(self._modules.keys())
    
    def enable_module(self, module_name: str) -> bool:
        """
        Enable a module by name.
        
        Args:
            module_name: Name of the module to enable
            
        Returns:
            True if enabled successfully
        """
        module = self.get(module_name)
        if module:
            return module.enable()
        return False
    
    def disable_module(self, module_name: str) -> bool:
        """
        Disable a module by name.
        
        Args:
            module_name: Name of the module to disable
            
        Returns:
            True if disabled successfully
        """
        module = self.get(module_name)
        if module:
            return module.disable()
        return False
    
    def check_module_availability(self, module_name: str) -> bool:
        """
        Check if a module is available on the current system.
        
        Args:
            module_name: Name of the module to check
            
        Returns:
            True if available
        """
        module = self.get(module_name)
        if module:
            return module.check_availability()
        return False
    
    def get_module_info(self, module_name: str) -> Optional[Dict]:
        """
        Get information about a module.
        
        Args:
            module_name: Name of the module
            
        Returns:
            Dictionary with module information
        """
        module = self.get(module_name)
        if not module:
            return None
        
        return {
            "name": module.name,
            "display_name": module.display_name,
            "description": module.description,
            "version": module.version,
            "capabilities": [cap.value for cap in module.capabilities],
            "enabled": module.enabled,
            "available": module.check_availability(),
            "required_packages": module.get_required_packages(),
            "actions": module.get_available_actions(),
        }
    
    def get_all_module_info(self) -> List[Dict]:
        """Get information about all registered modules."""
        return [
            self.get_module_info(name) 
            for name in self.list_module_names()
        ]
    
    def clear(self):
        """Clear all registered modules (useful for testing)."""
        self._modules.clear()


# Global registry instance
registry = ModuleRegistry()
