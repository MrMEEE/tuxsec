# TuxSec Shared Modules

This package provides the core module system for TuxSec. It includes:

## Components

### base.py
- `BaseModule`: Abstract base class for all modules
- `ModuleCapability`: Enum of available capabilities
- `ModuleCommand`: Command structure for module execution
- `ModuleResult`: Standardized result format

### registry.py
- `ModuleRegistry`: Singleton registry for module management
- Module discovery and lifecycle management
- Query modules by name or capability

## Usage

### Registering a Module

```python
from shared.modules.registry import registry
from shared.modules.base import BaseModule

class MyModule(BaseModule):
    # Implement required methods
    pass

registry.register(MyModule())
```

### Using a Module

```python
from shared.modules.registry import registry

module = registry.get('firewalld')
if module and module.enabled:
    result = module.execute_action('get_status', {})
    print(result.data)
```

### Query Modules

```python
# Get all modules
all_modules = registry.get_all()

# Get enabled modules
enabled = registry.get_enabled()

# Get modules by capability
firewall_modules = registry.get_by_capability(ModuleCapability.FIREWALL)
```

## Module Interface

All modules must implement:

- `name`: Unique identifier
- `display_name`: Human-readable name
- `description`: What the module does
- `version`: Module version
- `capabilities`: List of capabilities
- `get_required_packages()`: System packages needed
- `check_availability()`: Can module run on this system?
- `get_available_actions()`: List of supported actions
- `execute_action()`: Execute an action
- `get_status()`: Get current module status

## See Also

- `/MODULE_SYSTEM.md`: Complete module system documentation
- `/web_ui/modules/`: Django integration
- `/web_ui/modules/implementations/`: Module implementations
