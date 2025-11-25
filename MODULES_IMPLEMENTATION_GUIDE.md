# TuxSec Modules Implementation Guide

**Step-by-step guide to implement the generic module framework**

## Prerequisites

- Backup database: `cd web_ui && python manage.py dumpdata > backup_before_refactor.json`
- Create git branch: `git checkout -b refactor-module-framework`
- Ensure all tests pass before starting

## Phase 1: Create Base Module Infrastructure

### Step 1.1: Create Base Models

```bash
mkdir -p web_ui/modules/base
touch web_ui/modules/base/__init__.py
touch web_ui/modules/base/models.py
```

**File: `web_ui/modules/base/models.py`**
```python
from django.db import models
from agents.models import Agent

class ModuleData(models.Model):
    """
    Generic key-value storage for simple module data.
    Complex modules can create their own models.
    
    Example usage:
        ModuleData.objects.create(
            agent=agent,
            module_name='selinux',
            data_type='policy',
            data={'name': 'targeted', 'enforcing': True}
        )
    """
    agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        related_name='generic_module_data'
    )
    module_name = models.CharField(
        max_length=50,
        help_text="Module identifier (firewalld, aide, selinux, etc.)"
    )
    data_type = models.CharField(
        max_length=50,
        help_text="Type of data (config, status, alert, etc.)"
    )
    data = models.JSONField(
        help_text="Module-specific data as JSON"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'module_data'
        unique_together = [['agent', 'module_name', 'data_type']]
        indexes = [
            models.Index(fields=['agent', 'module_name']),
            models.Index(fields=['module_name', 'data_type']),
        ]
    
    def __str__(self):
        return f"{self.agent.hostname} - {self.module_name}:{self.data_type}"
```

**Migration:**
```bash
cd web_ui
python manage.py makemigrations
python manage.py migrate
```

### Step 1.2: Update Agent Model

**File: `web_ui/agents/models.py`**

Add field:
```python
class Agent(models.Model):
    # ... existing fields ...
    
    # NEW: Generic module metadata replaces module-specific fields
    module_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Module-specific metadata. Format: {module_name: {key: value}}"
    )
    # Example: {
    #   'firewalld': {'version': '1.2.0', 'services_count': 42},
    #   'aide': {'database_version': 3, 'last_check': '2025-11-25T10:00:00Z'}
    # }
```

**Deprecate (keep for now, remove after migration):**
```python
    # DEPRECATED: Use module_metadata['firewalld']['version'] instead
    firewalld_version = models.CharField(max_length=50, blank=True)
    
    # DEPRECATED: Use module_metadata['firewalld']['services'] instead
    available_services = models.JSONField(
        default=list,
        blank=True,
        help_text="List of available firewalld services on this agent"
    )
```

**Migration:**
```bash
python manage.py makemigrations agents --name add_module_metadata
python manage.py migrate agents
```

### Step 1.3: Enhanced BaseModule Class

**File: `web_ui/modules/base/module.py`**
```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from django.db import models as django_models

class BaseModule(ABC):
    """
    Base class for all TuxSec security modules.
    
    Modules extend this class to provide:
    - Module identification and metadata
    - Django models for storing module data
    - REST API views and URL patterns
    - Lifecycle hooks (enable, disable, sync)
    - Action execution methods
    
    Example:
        class MyModule(BaseModule):
            def get_name(self):
                return "mymodule"
            
            def get_display_name(self):
                return "My Security Module"
    """
    
    # ===== Required Methods =====
    
    @abstractmethod
    def get_name(self) -> str:
        """
        Return unique module identifier (lowercase, no spaces).
        Used in URLs, database references, CLI commands.
        
        Returns:
            str: Module name (e.g., 'firewalld', 'aide', 'selinux')
        """
        pass
    
    @abstractmethod
    def get_display_name(self) -> str:
        """
        Return human-readable module name for UI display.
        
        Returns:
            str: Display name (e.g., 'Firewalld Firewall', 'AIDE File Integrity')
        """
        pass
    
    # ===== Optional Metadata Methods =====
    
    def get_description(self) -> str:
        """
        Return module description for UI and documentation.
        
        Returns:
            str: Module description
        """
        return ""
    
    def get_icon(self) -> str:
        """
        Return FontAwesome icon class for UI display.
        
        Returns:
            str: Icon class (e.g., 'fa-fire', 'fa-shield', 'fa-lock')
        """
        return 'fa-puzzle-piece'
    
    def get_category(self) -> str:
        """
        Return module category for grouping in UI.
        
        Returns:
            str: Category (e.g., 'firewall', 'integrity', 'access_control')
        """
        return 'security'
    
    def get_required_packages(self) -> List[str]:
        """
        Return list of RPM packages required on agent.
        
        Returns:
            List[str]: Package names (e.g., ['firewalld', 'python3-firewall'])
        """
        return []
    
    def get_version(self) -> str:
        """
        Return module version.
        
        Returns:
            str: Version string (e.g., '1.0.0')
        """
        return '1.0.0'
    
    # ===== Django Integration Methods =====
    
    def get_models(self) -> List[type]:
        """
        Return list of Django model classes this module provides.
        Models should be registered in module's models.py.
        
        Returns:
            List[type]: Django model classes
        
        Example:
            def get_models(self):
                from .models import FirewallZone, FirewallRule
                return [FirewallZone, FirewallRule]
        """
        return []
    
    def get_viewsets(self) -> List[type]:
        """
        Return list of DRF ViewSet classes for REST API.
        
        Returns:
            List[type]: ViewSet classes
        
        Example:
            def get_viewsets(self):
                from .views import FirewallZoneViewSet
                return [FirewallZoneViewSet]
        """
        return []
    
    def get_url_patterns(self) -> List:
        """
        Return Django URL patterns for this module.
        URLs will be mounted at: /api/agents/<agent_id>/<module_name>/
        
        Returns:
            List: Django URL patterns
        
        Example:
            def get_url_patterns(self):
                from . import urls
                return urls.urlpatterns
        """
        return []
    
    # ===== Lifecycle Hooks =====
    
    def on_enable(self, agent) -> Dict[str, Any]:
        """
        Called when module is enabled for an agent.
        Use this to initialize module data, sync configuration, etc.
        
        Args:
            agent: Agent instance
        
        Returns:
            Dict with 'message' key and optional 'data' key
        
        Example:
            def on_enable(self, agent):
                self.sync_configuration(agent)
                return {'message': 'Module enabled and synced'}
        """
        return {'message': f'{self.get_display_name()} enabled'}
    
    def on_disable(self, agent) -> Dict[str, Any]:
        """
        Called when module is disabled for an agent.
        Use this to clean up module data if needed.
        
        Args:
            agent: Agent instance
        
        Returns:
            Dict with 'message' key
        """
        return {'message': f'{self.get_display_name()} disabled'}
    
    def on_sync(self, agent) -> Dict[str, Any]:
        """
        Called during scheduled sync operations.
        Use this to update module data from agent.
        
        Args:
            agent: Agent instance
        
        Returns:
            Dict with 'message' key and optional 'data' key
        
        Example:
            def on_sync(self, agent):
                count = self.sync_configuration(agent)
                return {'message': f'Synced {count} items'}
        """
        return {'message': 'No sync needed'}
    
    def on_agent_register(self, agent) -> Dict[str, Any]:
        """
        Called when a new agent registers with the system.
        Use this to perform initial setup.
        
        Args:
            agent: Agent instance
        
        Returns:
            Dict with 'message' key
        """
        return {'message': 'No initialization needed'}
    
    # ===== Availability Check =====
    
    def check_availability(self, agent) -> Dict[str, Any]:
        """
        Check if module can run on this agent.
        Called during agent sync to determine if module is available.
        
        Args:
            agent: Agent instance
        
        Returns:
            Dict with 'available' (bool) and optional 'error' (str) keys
        
        Example:
            def check_availability(self, agent):
                if 'firewalld' not in agent.installed_modules:
                    return {
                        'available': False,
                        'error': 'Package firewalld not installed'
                    }
                return {'available': True}
        """
        # Default: check if required packages are installed
        required = self.get_required_packages()
        if not required:
            return {'available': True}
        
        installed = agent.installed_modules or []
        missing = [pkg for pkg in required if pkg not in installed]
        
        if missing:
            return {
                'available': False,
                'error': f'Missing packages: {", ".join(missing)}'
            }
        
        return {'available': True}
    
    # ===== Action Execution =====
    
    def execute_action(self, agent, action: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute a module-specific action.
        Override this to handle custom actions from UI/API.
        
        Args:
            agent: Agent instance
            action: Action name (e.g., 'reload', 'status', 'get_zones')
            params: Optional parameters dict
        
        Returns:
            Dict with action results
        
        Raises:
            NotImplementedError: If action is not supported
        
        Example:
            def execute_action(self, agent, action, params):
                if action == 'reload':
                    return self.reload_configuration(agent)
                elif action == 'status':
                    return self.get_status(agent)
                raise NotImplementedError(f"Action {action} not supported")
        """
        raise NotImplementedError(
            f"Action '{action}' not implemented for module '{self.get_name()}'"
        )
    
    # ===== Configuration Schema =====
    
    def get_configuration_schema(self) -> Dict[str, Any]:
        """
        Return JSON schema for module configuration.
        Used to generate configuration UI forms.
        
        Returns:
            Dict: JSON schema
        
        Example:
            def get_configuration_schema(self):
                return {
                    'type': 'object',
                    'properties': {
                        'default_zone': {
                            'type': 'string',
                            'title': 'Default Zone',
                            'enum': ['public', 'internal', 'dmz']
                        }
                    }
                }
        """
        return {}
```

### Step 1.4: Update Module Registry

**File: `web_ui/modules/base/registry.py`**
```python
from typing import Dict, List, Optional
from .module import BaseModule

class ModuleRegistry:
    """
    Central registry for all TuxSec modules.
    Modules register themselves on import.
    """
    
    def __init__(self):
        self._modules: Dict[str, BaseModule] = {}
    
    def register(self, module: BaseModule):
        """Register a module instance"""
        name = module.get_name()
        if name in self._modules:
            raise ValueError(f"Module {name} already registered")
        self._modules[name] = module
    
    def get_module(self, name: str) -> Optional[BaseModule]:
        """Get module by name"""
        return self._modules.get(name)
    
    def get_all_modules(self) -> List[BaseModule]:
        """Get all registered modules"""
        return list(self._modules.values())
    
    def get_module_names(self) -> List[str]:
        """Get list of registered module names"""
        return list(self._modules.keys())
    
    def is_registered(self, name: str) -> bool:
        """Check if module is registered"""
        return name in self._modules

# Global registry instance
module_registry = ModuleRegistry()
```

**File: `web_ui/modules/__init__.py`**
```python
from .base.registry import module_registry
from .base.module import BaseModule

# Auto-import all modules to register them
from .firewalld import FirewalldModule
# Future modules:
# from .aide import AideModule
# from .selinux import SelinuxModule
# from .clamav import ClamavModule

# Register modules
module_registry.register(FirewalldModule())

__all__ = ['module_registry', 'BaseModule']
```

## Phase 2: Refactor Firewalld Module

### Step 2.1: Create Firewalld Models

**File: `web_ui/modules/firewalld/models.py`**
```python
from django.db import models
from agents.models import Agent

class FirewallZone(models.Model):
    """Firewalld zone configuration (new table name)"""
    agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        related_name='firewalld_zones'  # Changed from 'zones'
    )
    name = models.CharField(max_length=100)
    target = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)
    services = models.JSONField(default=list, blank=True)
    ports = models.JSONField(default=list, blank=True)
    protocols = models.JSONField(default=list, blank=True)
    masquerade = models.BooleanField(default=False)
    forward_ports = models.JSONField(default=list, blank=True)
    interfaces = models.JSONField(default=list, blank=True)
    sources = models.JSONField(default=list, blank=True)
    rich_rules = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'firewalld_zone'  # New table name
        unique_together = [['agent', 'name']]
        ordering = ['name']
    
    def __str__(self):
        return f"{self.agent.hostname} - {self.name}"

class FirewallRule(models.Model):
    """Firewalld rule configuration (new table name)"""
    agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        related_name='firewalld_rules'  # Changed from 'rules'
    )
    zone = models.ForeignKey(
        FirewallZone,
        on_delete=models.CASCADE,
        related_name='rules'
    )
    rule_type = models.CharField(max_length=20)
    service = models.CharField(max_length=100, blank=True)
    port = models.CharField(max_length=20, blank=True)
    protocol = models.CharField(max_length=10, blank=True)
    source = models.CharField(max_length=100, blank=True)
    destination = models.CharField(max_length=100, blank=True)
    rich_rule = models.TextField(blank=True)
    enabled = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'firewalld_rule'  # New table name
        ordering = ['zone', 'rule_type', 'service']
    
    def __str__(self):
        return f"{self.agent.hostname} - {self.zone.name} - {self.rule_type}"
```

**Migration:**
```bash
cd web_ui
python manage.py makemigrations firewalld --name create_firewalld_models
python manage.py migrate firewalld
```

### Step 2.2: Data Migration Script

**File: `web_ui/modules/firewalld/migrate_data.py`**
```python
#!/usr/bin/env python
"""
Migrate data from old agents.FirewallZone/FirewallRule tables
to new firewalld.FirewallZone/FirewallRule tables.
"""
from django.db import transaction

def migrate_firewalld_data():
    """Copy data from old tables to new tables"""
    from agents.models import (
        FirewallZone as OldZone,
        FirewallRule as OldRule
    )
    from modules.firewalld.models import (
        FirewallZone as NewZone,
        FirewallRule as NewRule
    )
    
    zones_migrated = 0
    rules_migrated = 0
    
    with transaction.atomic():
        # Map old zone IDs to new zone objects
        zone_mapping = {}
        
        # Migrate zones
        for old_zone in OldZone.objects.all():
            new_zone = NewZone.objects.create(
                agent=old_zone.agent,
                name=old_zone.name,
                target=old_zone.target,
                description=old_zone.description,
                services=old_zone.services,
                ports=old_zone.ports,
                protocols=old_zone.protocols,
                masquerade=old_zone.masquerade,
                forward_ports=old_zone.forward_ports,
                interfaces=old_zone.interfaces,
                sources=old_zone.sources,
                rich_rules=old_zone.rich_rules,
                created_at=old_zone.created_at,
                updated_at=old_zone.updated_at,
            )
            zone_mapping[old_zone.id] = new_zone
            zones_migrated += 1
        
        # Migrate rules
        for old_rule in OldRule.objects.all():
            new_zone = zone_mapping.get(old_rule.zone_id)
            if not new_zone:
                print(f"Warning: Zone not found for rule {old_rule.id}")
                continue
            
            NewRule.objects.create(
                agent=old_rule.agent,
                zone=new_zone,
                rule_type=old_rule.rule_type,
                service=old_rule.service,
                port=old_rule.port,
                protocol=old_rule.protocol,
                source=old_rule.source,
                destination=old_rule.destination,
                rich_rule=old_rule.rich_rule,
                enabled=old_rule.enabled,
                description=old_rule.description,
                created_at=old_rule.created_at,
                updated_at=old_rule.updated_at,
            )
            rules_migrated += 1
    
    print(f"✓ Migrated {zones_migrated} zones")
    print(f"✓ Migrated {rules_migrated} rules")
    return zones_migrated, rules_migrated

if __name__ == '__main__':
    import django
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tuxsec.settings')
    django.setup()
    
    migrate_firewalld_data()
```

**Run migration:**
```bash
cd web_ui
python modules/firewalld/migrate_data.py
```

### Step 2.3: Move Views to Module

(This is a large file - see MODULES_REFACTORING.md for complete structure)

### Step 2.4: Update Firewalld Module Class

Update `web_ui/modules/firewalld/module.py` to use new patterns:
- Change imports to use new models
- Update `get_models()` to return new models
- Update `get_viewsets()` to return new viewsets
- Keep existing `on_enable()` sync logic

## Phase 3: Update Connection Managers

### Step 3.1: Add Generic Module Execution

**File: `web_ui/agents/connection_managers.py`**

Add to all three connection manager classes (SSH, Pull, Push):

```python
async def execute_module_action(
    self,
    module: str,
    action: str,
    params: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Execute a module action via tuxsec-cli.
    
    Args:
        module: Module name (firewalld, aide, selinux, etc.)
        action: Action name (list_zones, get_status, etc.)
        params: Optional parameters dict
    
    Returns:
        Dict with 'success', 'result', 'error' keys
    """
    return await self.execute_command(action, parameters=params, module=module)
```

### Step 3.2: Update Firewalld Module to Use Generic Method

Update all calls in `modules/firewalld/module.py` from:
```python
result = await manager.execute_command('list_zones', module='firewalld')
```

To:
```python
result = await manager.execute_module_action('firewalld', 'list_zones')
```

## Phase 4: Update Core System

### Step 4.1: Dynamic URL Registration

**File: `web_ui/tuxsec/urls.py`**

```python
from django.urls import path, include
from modules import module_registry

# Build module URL patterns dynamically
module_url_patterns = []
for module in module_registry.get_all_modules():
    module_name = module.get_name()
    module_patterns = module.get_url_patterns()
    
    if module_patterns:
        module_url_patterns.append(
            path(
                f'api/agents/<int:agent_id>/{module_name}/',
                include((module_patterns, module_name))
            )
        )

urlpatterns = [
    # ... existing patterns ...
    path('api/agents/', include('agents.urls')),
] + module_url_patterns
```

### Step 4.2: Update sync_agents Command

**File: `web_ui/agents/management/commands/sync_agents.py`**

```python
from modules import module_registry

class Command(BaseCommand):
    def sync_agent(self, agent):
        # ... existing sync logic ...
        
        # Call on_sync for each available module
        for module_name in agent.available_modules or []:
            module = module_registry.get_module(module_name)
            if not module:
                continue
            
            try:
                if hasattr(module, 'on_sync'):
                    result = module.on_sync(agent)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  [{module_name}] {result.get('message', 'Synced')}"
                        )
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  [{module_name}] Error: {str(e)}")
                )
```

## Testing Checklist

### Phase 1 Testing
- [ ] ModuleData model created and migrations run
- [ ] Agent.module_metadata field added
- [ ] BaseModule class loads without errors
- [ ] Module registry works

### Phase 2 Testing  
- [ ] New firewalld models created
- [ ] Data migration completed successfully
- [ ] Old and new data match
- [ ] Firewalld views work with new models

### Phase 3 Testing
- [ ] Generic module execution works in SSH mode
- [ ] Generic module execution works in Pull mode
- [ ] Generic module execution works in Push mode

### Phase 4 Testing
- [ ] Module URLs registered correctly
- [ ] Can access `/api/agents/<id>/firewalld/zones/`
- [ ] sync_agents calls module on_sync hooks
- [ ] Module enable/disable triggers hooks

## Rollback Plan

If critical issues occur:

1. **Database**: Restore from backup
   ```bash
   python manage.py flush
   python manage.py loaddata backup_before_refactor.json
   ```

2. **Code**: Revert git branch
   ```bash
   git checkout main
   ```

3. **Gradual**: Keep both old and new tables during transition

## Next Steps After Completion

1. Create example module (e.g., simple status checker)
2. Document module development process
3. Remove deprecated Agent fields (firewalld_version, available_services)
4. Drop old tables (agents_firewallzone, agents_firewallrule)
5. Create modules for aide, selinux, clamav
