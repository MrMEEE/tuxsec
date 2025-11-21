"""
Management command to sync module states to database.
"""

from django.core.management.base import BaseCommand
from modules.registry_loader import sync_module_states
from modules.models import Module
from shared.modules.registry import registry


class Command(BaseCommand):
    help = 'Sync module states from registry to database'

    def handle(self, *args, **options):
        self.stdout.write('\n=== Syncing Module States ===\n')
        
        # Sync states
        sync_module_states()
        
        # Display status
        self.stdout.write(f'\nModules in registry: {len(registry.get_all())}')
        
        for name in registry.list_module_names():
            m = registry.get(name)
            try:
                state = Module.objects.get(name=name)
                status = "✓ ENABLED" if state.enabled_globally else "○ Disabled"
                self.stdout.write(
                    f'  {status} - {m.display_name} ({name}) v{m.version}'
                )
            except Module.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ {m.display_name} ({name}) - NO DATABASE RECORD')
                )
        
        self.stdout.write(self.style.SUCCESS('\n✓ Sync complete'))
