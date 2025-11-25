# Quick Reference: Creating a New TuxSec Module

## Minimal Module (5 minutes)

### 1. Create Module Directory
```bash
mkdir -p web_ui/modules/mymodule
cd web_ui/modules/mymodule
touch __init__.py module.py
```

### 2. Create Module Class
**File: `module.py`**
```python
from modules.base.module import BaseModule

class MyModule(BaseModule):
    def get_name(self):
        return "mymodule"
    
    def get_display_name(self):
        return "My Module"
    
    def get_description(self):
        return "Does something useful"
    
    def get_required_packages(self):
        return ['tuxsec-agent-mymodule']
```

### 3. Register Module
**File: `__init__.py`**
```python
from .module import MyModule
__all__ = ['MyModule']
```

**File: `web_ui/modules/__init__.py`** (add import)
```python
from .mymodule import MyModule
module_registry.register(MyModule())
```

**Done!** Module now appears in UI and can be enabled/disabled.

---

## Module with Database (15 minutes)

Add to above:

### 4. Create Models
**File: `models.py`**
```python
from django.db import models
from agents.models import Agent

class MyModuleConfig(models.Model):
    agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        related_name='mymodule_configs'
    )
    setting_name = models.CharField(max_length=100)
    setting_value = models.TextField()
    
    class Meta:
        db_table = 'mymodule_config'
        unique_together = [['agent', 'setting_name']]
```

### 5. Update Module Class
```python
class MyModule(BaseModule):
    # ... previous methods ...
    
    def get_models(self):
        from .models import MyModuleConfig
        return [MyModuleConfig]
```

### 6. Run Migrations
```bash
cd web_ui
python manage.py makemigrations mymodule
python manage.py migrate
```

---

## Module with REST API (30 minutes)

Add to above:

### 7. Create Serializers
**File: `serializers.py`**
```python
from rest_framework import serializers
from .models import MyModuleConfig

class MyModuleConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyModuleConfig
        fields = '__all__'
```

### 8. Create Views
**File: `views.py`**
```python
from rest_framework import viewsets
from .models import MyModuleConfig
from .serializers import MyModuleConfigSerializer

class MyModuleConfigViewSet(viewsets.ModelViewSet):
    serializer_class = MyModuleConfigSerializer
    
    def get_queryset(self):
        agent_id = self.kwargs['agent_id']
        return MyModuleConfig.objects.filter(agent_id=agent_id)
```

### 9. Create URLs
**File: `urls.py`**
```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'configs', views.MyModuleConfigViewSet, basename='mymodule-configs')

urlpatterns = [
    path('', include(router.urls)),
]
```

### 10. Update Module Class
```python
class MyModule(BaseModule):
    # ... previous methods ...
    
    def get_viewsets(self):
        from .views import MyModuleConfigViewSet
        return [MyModuleConfigViewSet]
    
    def get_url_patterns(self):
        from . import urls
        return urls.urlpatterns
```

**API now available at:** `/api/agents/<agent_id>/mymodule/configs/`

---

## Module with Auto-Sync (45 minutes)

Add to above:

### 11. Implement on_enable Hook
```python
class MyModule(BaseModule):
    # ... previous methods ...
    
    def on_enable(self, agent):
        """Sync data when module is enabled"""
        try:
            count = self._sync_from_agent(agent)
            return {
                'message': f'Module enabled and synced {count} items'
            }
        except Exception as e:
            raise Exception(f'Failed to sync: {str(e)}')
    
    def on_sync(self, agent):
        """Sync data during scheduled sync"""
        count = self._sync_from_agent(agent)
        return {'message': f'Synced {count} items'}
    
    def _sync_from_agent(self, agent):
        """Sync configuration from agent"""
        from agents.connection_managers import get_connection_manager
        import asyncio
        
        # Get connection manager for this agent
        manager = get_connection_manager(agent)
        
        # Execute module action on agent
        result = asyncio.run(
            manager.execute_module_action(
                module='mymodule',
                action='get_config',
                params=None
            )
        )
        
        if not result.get('success'):
            raise Exception(result.get('error', 'Unknown error'))
        
        # Store results in database
        from .models import MyModuleConfig
        
        configs = result.get('result', [])
        for config in configs:
            MyModuleConfig.objects.update_or_create(
                agent=agent,
                setting_name=config['name'],
                defaults={'setting_value': config['value']}
            )
        
        return len(configs)
```

---

## Module with Agent-Side Implementation (60 minutes)

### 12. Create Agent Module
**File: `agent/rootd/modules/mymodule.py`**
```python
from .base import BaseModule

class MyModuleRootd(BaseModule):
    """Agent-side module implementation"""
    
    def get_name(self):
        return "mymodule"
    
    def get_actions(self):
        return {
            'get_config': self._get_config,
            'set_config': self._set_config,
            'get_status': self._get_status,
        }
    
    def _get_config(self, params):
        """Get current configuration"""
        configs = [
            {'name': 'setting1', 'value': 'value1'},
            {'name': 'setting2', 'value': 'value2'},
        ]
        return configs
    
    def _set_config(self, params):
        """Set configuration value"""
        name = params.get('name')
        value = params.get('value')
        
        # Apply configuration...
        
        return {'success': True}
    
    def _get_status(self, params):
        """Get module status"""
        return {
            'enabled': True,
            'running': True,
            'version': '1.0.0'
        }
```

### 13. Test Agent Module
```bash
# On agent system
sudo -u tuxsec tuxsec-cli execute mymodule get_config
sudo -u tuxsec tuxsec-cli execute mymodule get_status
sudo -u tuxsec tuxsec-cli execute mymodule set_config --param name=setting1 --param value=newvalue
```

---

## Common Patterns

### Pattern 1: Simple Status Module
```python
class StatusModule(BaseModule):
    def get_name(self):
        return "status"
    
    def on_sync(self, agent):
        # Query agent for status
        # Store in module_metadata
        return {'message': 'Status updated'}
```

### Pattern 2: Configuration Manager
```python
class ConfigModule(BaseModule):
    def on_enable(self, agent):
        # Pull config from agent
        # Store in database
        return {'message': 'Config synced'}
    
    def execute_action(self, agent, action, params):
        if action == 'apply':
            # Push config to agent
            return {'message': 'Config applied'}
```

### Pattern 3: Alert/Event Module
```python
class AlertModule(BaseModule):
    def on_sync(self, agent):
        # Pull new alerts from agent
        # Create alert records
        # Send notifications
        return {'message': f'{count} new alerts'}
```

### Pattern 4: File Integrity Module (AIDE)
```python
class AideModule(BaseModule):
    def on_enable(self, agent):
        # Initialize AIDE database
        return {'message': 'Database initialized'}
    
    def on_sync(self, agent):
        # Check for file changes
        # Create alerts for changes
        return {'message': f'{changes} files changed'}
```

---

## Testing Your Module

### 1. Enable Module in UI
```
http://localhost:8001/dashboard/agents/<id>/
Click toggle for your module
Check for success message
```

### 2. Test API Endpoints
```bash
# List resources
curl http://localhost:8001/api/agents/1/mymodule/configs/

# Create resource
curl -X POST http://localhost:8001/api/agents/1/mymodule/configs/ \
  -H "Content-Type: application/json" \
  -d '{"setting_name": "test", "setting_value": "value"}'
```

### 3. Test Sync
```bash
cd web_ui
python manage.py sync_agents
# Should see: [mymodule] Synced X items
```

### 4. Check Database
```bash
cd web_ui
python manage.py shell
>>> from modules.mymodule.models import MyModuleConfig
>>> MyModuleConfig.objects.all()
```

---

## Troubleshooting

### Module Not Appearing in UI
- Check module is registered in `web_ui/modules/__init__.py`
- Restart Django server
- Check browser console for errors

### API Endpoints Not Working
- Check `get_url_patterns()` returns valid patterns
- Check URLs with: `python manage.py show_urls | grep mymodule`
- Restart Django server

### Sync Not Working
- Check `on_sync()` doesn't raise exceptions
- Check agent has module installed: `tuxsec-cli installed-modules`
- Check agent module works: `tuxsec-cli execute mymodule get_status`

### Database Errors
- Run migrations: `python manage.py migrate`
- Check model Meta.db_table is unique
- Check ForeignKey related_name is unique

---

## Next Steps

1. **Read Full Documentation**
   - `MODULES_REFACTORING.md` - Architecture overview
   - `MODULES_IMPLEMENTATION_GUIDE.md` - Detailed implementation

2. **Study Firewalld Module**
   - See `web_ui/modules/firewalld/` for complete example
   - Complex models, views, URLs, sync logic

3. **Create Your Module**
   - Start simple (just module class)
   - Add models as needed
   - Add API endpoints as needed
   - Add sync logic as needed

4. **Test Thoroughly**
   - Enable/disable module
   - Test all API endpoints
   - Test sync operations
   - Test with all three connection modes (SSH, Pull, Push)
