"""
Module registry loader for Django.
"""

import logging
import os
import importlib
from pathlib import Path
from shared.modules.registry import registry

logger = logging.getLogger(__name__)


def discover_modules():
    """
    Discover all modules by scanning the modules directory.
    
    Each module should be in its own folder with a module.py file
    containing a class that inherits from BaseModule.
    """
    modules_dir = Path(__file__).parent
    module_folders = []
    
    # Find all directories that contain a module.py file
    for item in modules_dir.iterdir():
        if item.is_dir() and not item.name.startswith('_'):
            module_file = item / 'module.py'
            if module_file.exists():
                module_folders.append(item.name)
    
    return module_folders


def load_modules():
    """
    Load and register all available modules.
    
    This is called when Django starts up.
    Modules are loaded from the filesystem and registered in memory.
    Database only stores enable/disable state.
    """
    # Skip during migrations
    import sys
    if 'makemigrations' in sys.argv or 'migrate' in sys.argv:
        return
    
    # Discover available modules
    module_folders = discover_modules()
    logger.info(f"Discovered {len(module_folders)} modules: {', '.join(module_folders)}")
    
    # Load each module
    for module_name in module_folders:
        try:
            # Import the module package
            module_package = importlib.import_module(f'modules.{module_name}')
            
            # Try to find the module class
            # Convention: module should export a class ending with 'Module'
            module_class = None
            for attr_name in dir(module_package):
                if attr_name.endswith('Module') and not attr_name.startswith('_'):
                    module_class = getattr(module_package, attr_name)
                    break
            
            if module_class:
                # Instantiate and register
                instance = module_class()
                registry.register(instance)
                logger.info(f"✓ Loaded module: {instance.display_name} ({module_name})")
            else:
                logger.warning(f"✗ No module class found in {module_name}")
                
        except Exception as e:
            logger.error(f"✗ Failed to load module {module_name}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    
    logger.info(f"Module registry initialized with {len(registry.get_all())} modules")


def ensure_module_state_exists(module_name: str):
    """
    Ensure a database record exists for a module's enable/disable state.
    Creates a disabled entry if it doesn't exist.
    
    Args:
        module_name: The module identifier from registry
    """
    from .models import Module as ModuleModel
    
    ModuleModel.objects.get_or_create(
        name=module_name,
        defaults={
            'enabled_globally': False,
            'auto_enable_new_agents': False,
        }
    )


def sync_module_states():
    """
    Ensure database has state records for all registered modules.
    Call this after modules are loaded or when checking module states.
    """
    from .models import Module as ModuleModel
    
    for module_name in registry.list_module_names():
        ensure_module_state_exists(module_name)
