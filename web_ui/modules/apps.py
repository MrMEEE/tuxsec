"""
Django app configuration for modules.
"""

from django.apps import AppConfig


class ModulesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules'
    verbose_name = 'Security Modules'
    
    def ready(self):
        """Initialize module registry when Django starts."""
        from .registry_loader import load_modules
        load_modules()
