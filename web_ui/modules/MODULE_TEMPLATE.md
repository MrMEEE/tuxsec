# Module Template

Use this template to create a new TuxSec module.

## Quick Start

1. **Copy this folder** to `web_ui/modules/your_module_name/`
2. **Edit `module.py`** with your module implementation
3. **Update `__init__.py`** with your module name
4. **Restart Django** - Your module will be auto-discovered!

## File Structure

```
web_ui/modules/your_module_name/
├── __init__.py      # Module package (edit module name)
├── module.py        # Your module implementation
└── README.md        # Module documentation
```

## Steps

### 1. module.py

Implement all required methods:
- `name` - Unique identifier (lowercase, no spaces)
- `display_name` - Human-readable name
- `description` - What the module does
- `version` - Module version
- `capabilities` - List of capabilities from ModuleCapability enum
- `get_required_packages()` - System packages needed
- `check_availability()` - Can module run on this system?
- `get_available_actions()` - List of actions
- `execute_action()` - Execute an action
- `get_status()` - Get current status

### 2. __init__.py

```python
"""
Your Module - Short Description

Longer description here.
"""

from .module import YourModule

__all__ = ['YourModule']
```

### 3. Test Your Module

```python
# In Django shell
from shared.modules.registry import registry
module = registry.get('your_module_name')
print(f"Available: {module.check_availability()}")
print(f"Actions: {module.get_available_actions()}")
result = module.execute_action('get_status', {})
print(result.data)
```

### 4. Enable Your Module

```python
# In Django shell or admin
from modules.models import Module
m = Module.objects.get(name='your_module_name')
m.enabled_globally = True
m.save()
```

## Available Capabilities

- `FIREWALL` - Firewall management
- `SELINUX` - SELinux configuration
- `ANTIVIRUS` - Virus scanning
- `INTRUSION_DETECTION` - IDS/IPS
- `FILE_INTEGRITY` - File integrity monitoring
- `LOG_MONITORING` - Log analysis
- `COMPLIANCE` - Compliance checking
- `BACKUP` - Backup management
- `CUSTOM` - Custom functionality

## Example Actions

Common action patterns:
- `get_status` - Always implement this
- `list_*` - List items (rules, services, etc.)
- `add_*` - Add something
- `remove_*` - Remove something
- `enable_*` - Enable a feature
- `disable_*` - Disable a feature
- `get_*` - Get specific information
- `set_*` - Set a configuration

## Documentation

Create a comprehensive README.md with:
- Overview
- Requirements
- Capabilities
- Available Actions (with parameters)
- Configuration Schema
- Usage Examples
- Best Practices

See `firewalld/README.md` or `selinux/README.md` for examples.
