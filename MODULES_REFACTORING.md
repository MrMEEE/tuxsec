# TuxSec Modules Refactoring Plan

**Date:** 25 November 2025  
**Goal:** Extract all firewalld-specific code into the firewalld module and create a generic module framework for future modules (aide, selinux, clamav, etc.)

## Current Architecture Issues

### 1. **Models in Wrong Location**
- `FirewallZone` and `FirewallRule` models are in `agents/models.py`
- Should be in `modules/firewalld/models.py`
- Agent model has firewalld-specific fields: `firewalld_version`, `available_services`

### 2. **Views Outside Module**
- Extensive firewalld CRUD operations in `agents/views.py`:
  - `FirewallZoneViewSet`, `FirewallRuleViewSet`
  - Zone management views (sync, create, delete)
  - Rule management views (add, remove, enable/disable)
  - Service management views
- Should be in `modules/firewalld/views.py`

### 3. **Hardcoded Connection Manager Methods**
- All three connection managers (SSH, Pull, Push) have hardcoded firewalld methods:
  - `get_zones()`, `get_services()`, `execute_command(module='firewalld')`
- Should use generic `execute_module_action()` instead

### 4. **Module-Specific Logic in Core**
- `sync_agents.py` has firewalld-specific zone syncing
- `dashboard/views.py` checks specifically for firewalld module
- `api_views.py` handles `firewalld_version` field

## New Architecture: Generic Module Framework

### Core Concepts

1. **Module Models Pattern**
   - Each module defines its own models in `modules/<module_name>/models.py`
   - Models inherit from Django models with ForeignKey to Agent
   - Core system remains module-agnostic

2. **Module Views Pattern**
   - Each module provides its own ViewSets and URL patterns
   - Core system includes module URLs dynamically
   - URL structure: `/api/agents/<agent_id>/<module_name>/<resource>/`

3. **Module Data Storage Pattern**
   - Generic `ModuleData` model for simple key-value storage (JSON)
   - Complex modules create their own models (like firewalld zones/rules)
   - Agent model has generic `module_metadata` JSONField

4. **Module Lifecycle Hooks**
   ```python
   class BaseModule:
       def on_enable(self, agent):
           """Called when module is enabled for an agent"""
           pass
       
       def on_disable(self, agent):
           """Called when module is disabled for an agent"""
           pass
       
       def on_sync(self, agent):
           """Called during scheduled sync operations"""
           pass
       
       def on_agent_register(self, agent):
           """Called when new agent registers"""
           pass
   ```

5. **Module API Pattern**
   - Each module exposes actions via `execute_action(agent, action, params)`
   - Connection managers use generic `execute_module_action(module, action, params)`
   - No hardcoded module-specific methods in connection managers

## Refactoring Steps

### Phase 1: Create Generic Module Infrastructure

#### 1.1 Create Generic ModuleData Model
```python
# modules/base/models.py
class ModuleData(models.Model):
    """Generic storage for module-specific data"""
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='module_data')
    module_name = models.CharField(max_length=50)
    data_type = models.CharField(max_length=50)  # e.g., 'zone', 'rule', 'policy'
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [['agent', 'module_name', 'data_type']]
```

#### 1.2 Update Agent Model
```python
# agents/models.py - Remove firewalld-specific fields
class Agent(models.Model):
    # Keep generic fields
    hostname = models.CharField(...)
    os_distribution = models.CharField(...)
    os_version = models.CharField(...)
    
    # Generic module metadata (replaces firewalld_version, available_services)
    module_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Module-specific metadata {module_name: {key: value}}"
    )
    # Example: {'firewalld': {'version': '1.2.0', 'services': ['ssh', 'http']}}
    
    # Keep these - they're generic
    available_modules = models.JSONField(...)
    installed_modules = models.JSONField(...)
```

#### 1.3 Update BaseModule Interface
```python
# modules/base/module.py
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

class BaseModule(ABC):
    """Base class for all TuxSec modules"""
    
    @abstractmethod
    def get_name(self) -> str:
        """Return module identifier (e.g., 'firewalld')"""
        pass
    
    @abstractmethod
    def get_display_name(self) -> str:
        """Return human-readable name"""
        pass
    
    def get_models(self) -> List:
        """Return list of Django models this module provides"""
        return []
    
    def get_viewsets(self) -> List:
        """Return list of DRF ViewSets this module provides"""
        return []
    
    def get_url_patterns(self):
        """Return Django URL patterns for this module"""
        return []
    
    def on_enable(self, agent) -> Dict[str, Any]:
        """Called when module is enabled"""
        return {'message': f'{self.get_display_name()} enabled'}
    
    def on_disable(self, agent) -> Dict[str, Any]:
        """Called when module is disabled"""
        return {'message': f'{self.get_display_name()} disabled'}
    
    def on_sync(self, agent) -> Dict[str, Any]:
        """Called during scheduled sync"""
        return {'message': 'No sync needed'}
    
    def execute_action(self, agent, action: str, params: Dict) -> Dict[str, Any]:
        """Execute a module-specific action"""
        raise NotImplementedError(f"Action {action} not implemented")
```

### Phase 2: Refactor Firewalld Module

#### 2.1 Move Models to Firewalld Module
```bash
# Create new files
touch web_ui/modules/firewalld/models.py
touch web_ui/modules/firewalld/admin.py
touch web_ui/modules/firewalld/serializers.py
```

```python
# modules/firewalld/models.py
from django.db import models
from agents.models import Agent

class FirewallZone(models.Model):
    """Firewalld zone configuration"""
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='firewalld_zones')
    name = models.CharField(max_length=100)
    # ... rest of fields ...

class FirewallRule(models.Model):
    """Firewalld rule configuration"""
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='firewalld_rules')
    zone = models.ForeignKey(FirewallZone, on_delete=models.CASCADE, related_name='rules')
    # ... rest of fields ...
```

**Migration Strategy:**
1. Create new tables with different names (`firewalld_zone`, `firewalld_rule`)
2. Copy data from old tables to new tables
3. Update all foreign keys and references
4. Keep old tables temporarily for rollback safety
5. After verification, drop old tables

#### 2.2 Move Views to Firewalld Module
```python
# modules/firewalld/views.py
from rest_framework import viewsets
from .models import FirewallZone, FirewallRule
from .serializers import FirewallZoneSerializer, FirewallRuleSerializer

class FirewallZoneViewSet(viewsets.ModelViewSet):
    serializer_class = FirewallZoneSerializer
    
    def get_queryset(self):
        agent_id = self.kwargs['agent_id']
        return FirewallZone.objects.filter(agent_id=agent_id)

# ... move all zone/rule views here ...
```

#### 2.3 Create Firewalld URL Patterns
```python
# modules/firewalld/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'zones', views.FirewallZoneViewSet, basename='firewalld-zones')
router.register(r'rules', views.FirewallRuleViewSet, basename='firewalld-rules')

urlpatterns = [
    path('', include(router.urls)),
    path('zones/<int:zone_id>/services/', views.zone_services, name='zone-services'),
    path('sync/', views.sync_firewall_config, name='firewalld-sync'),
    # ... all other firewalld-specific endpoints ...
]
```

#### 2.4 Update Firewalld Module Class
```python
# modules/firewalld/module.py
from modules.base.module import BaseModule
from .models import FirewallZone, FirewallRule
from .views import FirewallZoneViewSet, FirewallRuleViewSet
from . import urls as firewalld_urls

class FirewalldModule(BaseModule):
    def get_name(self):
        return "firewalld"
    
    def get_models(self):
        return [FirewallZone, FirewallRule]
    
    def get_viewsets(self):
        return [FirewallZoneViewSet, FirewallRuleViewSet]
    
    def get_url_patterns(self):
        return firewalld_urls.urlpatterns
    
    def on_enable(self, agent):
        """Auto-sync zones when enabled"""
        # Existing implementation...
    
    def on_sync(self, agent):
        """Sync zones/rules during scheduled sync"""
        return self.sync_configuration(agent)
    
    def sync_configuration(self, agent):
        """Sync firewall zones and rules from agent"""
        # Move sync logic from sync_agents.py here
```

### Phase 3: Update Connection Managers

#### 3.1 Remove Hardcoded Firewalld Methods
```python
# agents/connection_managers.py - Before
class SSHConnectionManager:
    async def get_zones(self):
        """Get list of firewalld zones"""
        result = await self.execute_command('list_zones', module='firewalld')
        # ...
    
    async def get_services(self):
        """Get list of firewalld services"""
        result = await self.execute_command('list_services', module='firewalld')
        # ...

# After - Generic module execution
class SSHConnectionManager:
    async def execute_module_action(self, module: str, action: str, params: Optional[Dict] = None):
        """Execute any module action via tuxsec-cli"""
        cmd_parts = ['sudo', '-u', 'tuxsec', 'tuxsec-cli', 'execute', module, action]
        
        if params:
            for key, value in params.items():
                cmd_parts.extend(['--param', f'{key}={value}'])
        
        # Execute and parse response
        stdout, stderr = await self.execute_ssh_command(' '.join(cmd_parts))
        return json.loads(stdout)
```

#### 3.2 Update Module Classes to Use Connection Managers
```python
# modules/firewalld/module.py
class FirewalldModule(BaseModule):
    async def sync_configuration(self, agent):
        """Sync zones using connection manager"""
        from agents.connection_managers import get_connection_manager
        
        manager = get_connection_manager(agent)
        
        # Generic module action call
        zones_result = await manager.execute_module_action(
            module='firewalld',
            action='list_zones',
            params=None
        )
        
        for zone_name in zones_result.get('result', []):
            zone_detail = await manager.execute_module_action(
                module='firewalld',
                action='get_zone',
                params={'zone': zone_name}
            )
            # Process and store...
```

### Phase 4: Update Core System for Module Registration

#### 4.1 Dynamic Module URL Registration
```python
# web_ui/tuxsec/urls.py
from modules.base.registry import module_registry

# Build module URL patterns dynamically
module_patterns = []
for module in module_registry.get_all_modules():
    module_patterns.append(
        path(f'api/agents/<int:agent_id>/{module.get_name()}/', 
             include(module.get_url_patterns()))
    )

urlpatterns = [
    # ... existing patterns ...
] + module_patterns
```

#### 4.2 Update sync_agents for Generic Module Sync
```python
# agents/management/commands/sync_agents.py
from modules.base.registry import module_registry

class Command(BaseCommand):
    def sync_agent(self, agent):
        # ... basic agent sync ...
        
        # Call on_sync for each enabled module
        for module_name in agent.available_modules or []:
            try:
                module = module_registry.get_module(module_name)
                if module and hasattr(module, 'on_sync'):
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

### Phase 5: Create Documentation for New Modules

#### 5.1 Module Development Guide
```markdown
# Creating a New TuxSec Module

## File Structure
```
web_ui/modules/mymodule/
├── __init__.py          # Module registration
├── module.py            # Module class (inherits BaseModule)
├── models.py            # Django models (optional)
├── views.py             # DRF ViewSets and views (optional)
├── serializers.py       # DRF serializers (optional)
├── urls.py              # URL patterns (optional)
├── admin.py             # Django admin (optional)
└── README.md            # Module documentation
```

## Minimal Module Example
```python
# modules/mymodule/module.py
from modules.base.module import BaseModule

class MyModule(BaseModule):
    def get_name(self):
        return "mymodule"
    
    def get_display_name(self):
        return "My Module"
    
    def get_description(self):
        return "Description of what this module does"
    
    def get_required_packages(self):
        return ['mypackage', 'python3-mylib']
    
    def check_availability(self, agent):
        """Check if module can run on agent"""
        return {'available': True, 'error': None}
```

## Module with Models Example
```python
# modules/mymodule/models.py
from django.db import models
from agents.models import Agent

class MyModuleData(models.Model):
    agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        related_name='mymodule_data'
    )
    name = models.CharField(max_length=100)
    value = models.TextField()
    
    class Meta:
        unique_together = [['agent', 'name']]

# modules/mymodule/module.py
from .models import MyModuleData

class MyModule(BaseModule):
    def get_models(self):
        return [MyModuleData]
    
    def on_enable(self, agent):
        """Initialize module data when enabled"""
        # Sync initial data from agent
        return self.sync_data(agent)
    
    def on_sync(self, agent):
        """Sync data during scheduled sync"""
        return self.sync_data(agent)
    
    def sync_data(self, agent):
        from agents.connection_managers import get_connection_manager
        
        manager = get_connection_manager(agent)
        result = await manager.execute_module_action(
            module='mymodule',
            action='get_data',
            params=None
        )
        
        # Store in database
        for item in result.get('result', []):
            MyModuleData.objects.update_or_create(
                agent=agent,
                name=item['name'],
                defaults={'value': item['value']}
            )
        
        return {'message': f'Synced {len(result.get("result", []))} items'}
```

## Module with REST API Example
```python
# modules/mymodule/serializers.py
from rest_framework import serializers
from .models import MyModuleData

class MyModuleDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyModuleData
        fields = '__all__'

# modules/mymodule/views.py
from rest_framework import viewsets
from .models import MyModuleData
from .serializers import MyModuleDataSerializer

class MyModuleDataViewSet(viewsets.ModelViewSet):
    serializer_class = MyModuleDataSerializer
    
    def get_queryset(self):
        agent_id = self.kwargs['agent_id']
        return MyModuleData.objects.filter(agent_id=agent_id)

# modules/mymodule/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'data', views.MyModuleDataViewSet, basename='mymodule-data')

urlpatterns = [
    path('', include(router.urls)),
]

# modules/mymodule/module.py
from .views import MyModuleDataViewSet
from . import urls as mymodule_urls

class MyModule(BaseModule):
    def get_viewsets(self):
        return [MyModuleDataViewSet]
    
    def get_url_patterns(self):
        return mymodule_urls.urlpatterns
```

## Registration
```python
# modules/mymodule/__init__.py
from .module import MyModule

__all__ = ['MyModule']
```

## Agent-Side Module
```python
# agent/rootd/modules/mymodule.py
from .base import BaseModule

class MyModuleRootd(BaseModule):
    """Agent-side implementation"""
    
    def get_name(self):
        return "mymodule"
    
    def get_actions(self):
        return {
            'get_data': self._get_data,
            'set_value': self._set_value,
        }
    
    def _get_data(self, params):
        """Get module data from system"""
        # Implementation...
        return {'items': [...]}
    
    def _set_value(self, params):
        """Set a value on the system"""
        name = params.get('name')
        value = params.get('value')
        # Implementation...
        return {'success': True}
```

## Migration Guide

### Phase 1: Create Module Structure
1. Create module directory: `web_ui/modules/mymodule/`
2. Create `module.py` with basic implementation
3. Register in `modules/__init__.py`

### Phase 2: Add Models (if needed)
1. Create `models.py`
2. Run `python manage.py makemigrations`
3. Run `python manage.py migrate`

### Phase 3: Add API (if needed)
1. Create `serializers.py`, `views.py`, `urls.py`
2. Update `module.py` to return ViewSets and URL patterns
3. Test API endpoints: `/api/agents/<id>/mymodule/`

### Phase 4: Implement Sync Logic
1. Add `on_sync()` method to module class
2. Implement connection manager calls
3. Test with `python manage.py sync_agents`

### Phase 5: Add Agent-Side Module
1. Create `agent/rootd/modules/mymodule.py`
2. Implement actions
3. Test with `tuxsec-cli execute mymodule action`
```

## Migration Timeline

### Week 1: Infrastructure Setup
- [ ] Create `modules/base/models.py` with ModuleData model
- [ ] Update `modules/base/module.py` with enhanced BaseModule
- [ ] Update Agent model (add module_metadata, remove firewalld fields)
- [ ] Create migration strategy document

### Week 2: Firewalld Module Refactoring
- [ ] Create `modules/firewalld/models.py` (new tables)
- [ ] Create `modules/firewalld/views.py` (move from agents/views.py)
- [ ] Create `modules/firewalld/urls.py`
- [ ] Update `modules/firewalld/module.py` with new methods
- [ ] Create data migration script

### Week 3: Connection Manager Updates
- [ ] Add generic `execute_module_action()` to all connection managers
- [ ] Remove hardcoded firewalld methods
- [ ] Update firewalld module to use generic methods
- [ ] Test all three connection modes

### Week 4: Core System Updates
- [ ] Update `sync_agents.py` to call module `on_sync()` hooks
- [ ] Update Django URL routing for dynamic module registration
- [ ] Update dashboard/views.py to be module-agnostic
- [ ] Update api_views.py to use module_metadata

### Week 5: Testing and Migration
- [ ] Run data migration (old tables → new tables)
- [ ] Test all firewalld functionality
- [ ] Test module enable/disable with auto-sync
- [ ] Verify scheduled sync works
- [ ] Performance testing

### Week 6: Documentation and Cleanup
- [ ] Create module development guide
- [ ] Document API patterns
- [ ] Create example module
- [ ] Remove deprecated code
- [ ] Drop old tables after verification

## Benefits of New Architecture

### For TuxSec Project
- **Modularity**: Each module is self-contained
- **Maintainability**: Module code stays with module logic
- **Scalability**: Easy to add new modules (aide, selinux, clamav)
- **Testing**: Modules can be tested independently
- **Documentation**: Each module documents its own API

### For Module Developers
- **Clear Structure**: Standard pattern to follow
- **Minimal Boilerplate**: BaseModule provides defaults
- **Flexible**: Can use simple JSONField or complex models
- **Documented**: Clear examples and patterns

### For Users
- **Consistent UI**: All modules follow same patterns
- **Better Organization**: Module-specific endpoints under `/api/agents/<id>/<module>/`
- **Flexible**: Can enable/disable modules independently

## Example: Future AIDE Module

```python
# modules/aide/models.py
class AideDatabase(models.Model):
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='aide_databases')
    database_path = models.CharField(max_length=255)
    last_updated = models.DateTimeField()
    file_count = models.IntegerField()

class AideAlert(models.Model):
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='aide_alerts')
    file_path = models.CharField(max_length=512)
    change_type = models.CharField(max_length=50)  # added, removed, changed
    detected_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)

# modules/aide/module.py
class AideModule(BaseModule):
    def get_name(self):
        return "aide"
    
    def get_display_name(self):
        return "AIDE File Integrity"
    
    def get_models(self):
        return [AideDatabase, AideAlert]
    
    def on_enable(self, agent):
        """Initialize AIDE database when enabled"""
        # Run initial database creation
        return self.initialize_database(agent)
    
    def on_sync(self, agent):
        """Check for file changes during sync"""
        return self.check_integrity(agent)
```

## Rollback Strategy

If issues occur during migration:

1. **Database Rollback**: Keep old tables until verified
2. **Code Rollback**: Git branch for each phase
3. **API Compatibility**: Maintain old endpoints temporarily
4. **Gradual Migration**: Move one module at a time

## Success Criteria

- [ ] All firewalld functionality works with new architecture
- [ ] No hardcoded module logic in core system
- [ ] Documentation complete for module developers
- [ ] Example module created and tested
- [ ] Performance is equal or better than before
- [ ] Migration completed without data loss
