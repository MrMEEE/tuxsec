# TuxSec Module System

## Overview

TuxSec uses a modular plugin-based architecture that allows you to enable/disable different security features independently. Each module provides specific security functionality and can be managed globally or per-agent.

## Architecture

### Components

1. **Base Module System** (`shared/modules/`)
   - `base.py`: Abstract base class defining the module interface
   - `registry.py`: Central registry for managing modules
   - Module classes define capabilities, actions, and requirements

2. **Django Models** (`web_ui/modules/models.py`)
   - `Module`: Global module configuration and metadata
   - `AgentModule`: Per-agent module status and configuration
   - `ModuleAction`: Audit log of module actions

3. **Module Implementations** (`web_ui/modules/{module_name}/`)
   - Each module has its own folder with `module.py` and `__init__.py`
   - Modules are auto-discovered and loaded at Django startup
   - Optional `README.md` for module-specific documentation

### Module Folder Structure

```
web_ui/modules/
├── __init__.py
├── models.py
├── admin.py
├── apps.py
├── registry_loader.py       # Auto-discovers modules
├── firewalld/                # Firewalld module
│   ├── __init__.py
│   ├── module.py             # FirewalldModule class
│   └── README.md             # Module documentation
├── selinux/                  # SELinux module
│   ├── __init__.py
│   ├── module.py             # SELinuxModule class
│   └── README.md
└── mymodule/                 # Your custom module
    ├── __init__.py
    ├── module.py
    └── README.md
```

## Available Modules

### Firewalld Module
- **Name**: `firewalld`
- **Capability**: Firewall management
- **Actions**: Zone management, service/port configuration, rich rules
- **Requirements**: `firewalld`, `python3-firewall`

### SELinux Module
- **Name**: `selinux`
- **Capabilities**: SELinux management, compliance
- **Actions**: Mode management, booleans, contexts, policy
- **Requirements**: `selinux-policy`, `policycoreutils`

### Planned Modules
- **ClamAV**: Antivirus scanning and management
- **AIDE**: File integrity monitoring
- **Auditd**: Audit log monitoring
- **Fail2ban**: Intrusion prevention

## Creating a New Module

### 1. Create Module Folder Structure

Create a new folder in `web_ui/modules/` with the following structure:

```
web_ui/modules/mymodule/
├── __init__.py      # Module package initialization
├── module.py        # Main module implementation
└── README.md        # Module documentation (optional)
```

### 2. Implement Module Class

Create `web_ui/modules/mymodule/module.py`:

```python
from typing import Dict, List, Any
from shared.modules.base import BaseModule, ModuleCapability, ModuleResult


class MyModule(BaseModule):
    @property
    def name(self) -> str:
        return "mymodule"
    
    @property
    def display_name(self) -> str:
        return "My Security Module"
    
    @property
    def description(self) -> str:
        return "Description of what this module does"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def capabilities(self) -> List[ModuleCapability]:
        return [ModuleCapability.CUSTOM]
    
    def get_required_packages(self) -> List[str]:
        return ['required-package']
    
    def check_availability(self) -> bool:
        # Check if module can run on this system
        return True
    
    def get_available_actions(self) -> List[str]:
        return ['action1', 'action2', 'get_status']
    
    def execute_action(self, action: str, parameters: Dict[str, Any]) -> ModuleResult:
        if action == 'get_status':
            return self.get_status()
        # Implement other actions...
        
    def get_status(self) -> Dict[str, Any]:
        return {'running': True, 'info': 'Module status'}
```

### 3. Create Package Init File

Create `web_ui/modules/mymodule/__init__.py`:

```python
"""
My Module - Short Description

Longer description of what this module does.
"""

from .module import MyModule

__all__ = ['MyModule']
```

### 4. Auto-Discovery

The module will be **automatically discovered and loaded** on Django startup. No manual registration needed!

The registry loader scans all folders in `web_ui/modules/` and loads any that contain a `module.py` file.

### 5. Database Sync

The module will be automatically synced to the database with its metadata on startup.

## Module Capabilities

Modules can declare one or more capabilities:

- `FIREWALL`: Firewall management
- `SELINUX`: SELinux configuration
- `ANTIVIRUS`: Virus scanning
- `INTRUSION_DETECTION`: IDS/IPS functionality
- `FILE_INTEGRITY`: File integrity monitoring
- `LOG_MONITORING`: Log analysis and monitoring
- `COMPLIANCE`: Compliance checking
- `BACKUP`: Backup management
- `CUSTOM`: Custom functionality

## Enabling/Disabling Modules

### Global Enable/Disable

Modules can be enabled globally for all agents:

```python
from modules.models import Module

module = Module.objects.get(name='firewalld')
module.enabled_globally = True
module.save()
```

### Per-Agent Enable/Disable

Modules can be enabled/disabled for specific agents:

```python
from modules.models import AgentModule

agent_module = AgentModule.objects.get(agent=agent, module=module)
agent_module.enabled = True
agent_module.save()
```

### Auto-Enable for New Agents

```python
module.auto_enable_new_agents = True
module.save()
```

## Module Configuration

### Global Configuration Schema

Each module defines a JSON schema for valid configuration:

```python
def get_configuration_schema(self) -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "option1": {"type": "string"},
            "option2": {"type": "boolean", "default": True}
        }
    }
```

### Per-Agent Configuration

Agents can have custom configuration overrides:

```python
agent_module.configuration = {
    "option1": "custom_value",
    "option2": False
}
agent_module.save()
```

## Module Actions

### Executing Actions

Actions are executed through the module interface:

```python
from shared.modules.registry import registry

module = registry.get('firewalld')
result = module.execute_action('get_zones', {})

if result.success:
    print(result.data)
else:
    print(result.error)
```

### Action Logging

All actions are logged in the `ModuleAction` model:

```python
from modules.models import ModuleAction

action = ModuleAction.objects.create(
    agent_module=agent_module,
    action='add_service',
    parameters={'zone': 'public', 'service': 'http'},
    success=True,
    initiated_by='admin'
)
```

## Agent Integration

### Module Discovery

Agents should report which modules are available:

```json
{
  "modules": {
    "firewalld": {
      "available": true,
      "version": "1.0.0",
      "status": {"running": true}
    },
    "selinux": {
      "available": true,
      "version": "1.0.0",
      "status": {"mode": "Enforcing"}
    }
  }
}
```

### Module Commands

Commands sent to agents include the module name:

```json
{
  "module": "firewalld",
  "action": "add_service",
  "parameters": {
    "zone": "public",
    "service": "http",
    "permanent": true
  }
}
```

## API Endpoints

### List All Modules
```
GET /api/modules/
```

### Get Module Details
```
GET /api/modules/{module_name}/
```

### Enable/Disable Module Globally
```
POST /api/modules/{module_name}/enable/
POST /api/modules/{module_name}/disable/
```

### Agent-Specific Module Management
```
GET /api/agents/{agent_id}/modules/
POST /api/agents/{agent_id}/modules/{module_name}/enable/
POST /api/agents/{agent_id}/modules/{module_name}/disable/
```

### Execute Module Action
```
POST /api/agents/{agent_id}/modules/{module_name}/execute/
{
  "action": "add_service",
  "parameters": {"zone": "public", "service": "http"}
}
```

## Web UI

### Module Management Page
- View all available modules
- Enable/disable modules globally
- Configure module settings
- View module statistics

### Agent Detail Page
- View modules available on this agent
- Enable/disable per-agent
- Configure agent-specific settings
- View module action history

## Best Practices

1. **Module Independence**: Modules should be self-contained and not depend on other modules
2. **Error Handling**: Always return proper `ModuleResult` with error information
3. **Availability Checks**: Implement thorough `check_availability()` methods
4. **Action Validation**: Validate parameters before executing actions
5. **Logging**: Log important events and errors
6. **Configuration Schema**: Define clear configuration schemas
7. **Documentation**: Document all actions and their parameters

## Testing

### Test Module Availability
```python
from shared.modules.registry import registry

module = registry.get('firewalld')
print(f"Available: {module.check_availability()}")
```

### Test Module Actions
```python
result = module.execute_action('get_zones', {})
assert result.success
assert 'zones' in result.data
```

## Future Enhancements

1. **Module Dependencies**: Support for modules that depend on others
2. **Module Versioning**: Handle multiple versions of the same module
3. **Module Marketplace**: Share and download community modules
4. **Module Policies**: Define rules for automatic module actions
5. **Module Metrics**: Collect performance and usage metrics
6. **Module Scheduling**: Schedule periodic module actions
