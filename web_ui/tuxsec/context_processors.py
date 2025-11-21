"""
Context processors for making data available to all templates.
"""

from shared.modules.registry import registry
from modules.models import Module


def modules_context(request):
    """
    Add enabled modules to template context for dynamic navigation.
    """
    enabled_modules = []
    
    try:
        # Get all module names from registry
        for module_name in registry.list_module_names():
            module = registry.get(module_name)
            
            # Check if enabled in database
            try:
                state = Module.objects.get(name=module_name)
                if state.enabled_globally:
                    enabled_modules.append({
                        'name': module_name,
                        'display_name': module.display_name,
                        'icon': get_module_icon(module_name),
                    })
            except Module.DoesNotExist:
                pass
    except Exception:
        # If there's any error (e.g., during migrations), return empty list
        pass
    
    return {
        'enabled_modules': enabled_modules,
    }


def get_module_icon(module_name):
    """Get Font Awesome icon for a module."""
    icons = {
        'firewalld': 'fa-fire',
        'selinux': 'fa-shield-alt',
        'clamav': 'fa-virus-slash',
        'aide': 'fa-file-shield',
    }
    return icons.get(module_name, 'fa-puzzle-piece')
