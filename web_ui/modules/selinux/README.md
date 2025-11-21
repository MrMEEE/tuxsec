# SELinux Module

## Overview

The SELinux module provides management capabilities for Security-Enhanced Linux, allowing you to control SELinux modes, booleans, file contexts, and policies across your infrastructure.

## Requirements

- **System Packages**: `selinux-policy`, `policycoreutils`, `policycoreutils-python-utils`
- **Kernel**: SELinux-enabled kernel

## Capabilities

- `SELINUX`: SELinux management
- `COMPLIANCE`: Security compliance checking

## Available Actions

### Status & Mode Management
- `get_status` - Get comprehensive SELinux status
- `get_mode` - Get current enforcement mode
- `get_enforce_mode` - Get enforcement mode
- `set_enforcing` - Set SELinux to enforcing mode
- `set_permissive` - Set SELinux to permissive mode

### Boolean Management
- `list_booleans` - List all SELinux booleans
- `get_boolean` - Get value of a specific boolean
- `set_boolean` - Set value of an SELinux boolean

### Context Management
- `get_file_context` - Get SELinux context of a file
- `set_file_context` - Set SELinux context for a file
- `restore_context` - Restore default SELinux context

### Policy Management
- `list_modules` - List installed policy modules
- `get_policy_version` - Get current policy version

## Configuration Schema

```json
{
  "type": "object",
  "properties": {
    "default_mode": {
      "type": "string",
      "enum": ["enforcing", "permissive"],
      "description": "Default SELinux mode"
    },
    "autorelabel": {
      "type": "boolean",
      "description": "Automatically relabel filesystem on reboot",
      "default": false
    }
  }
}
```

## Usage Examples

### Check SELinux status

```python
result = module.execute_action('get_status', {})
print(result.data)
```

### Set to enforcing mode

```python
result = module.execute_action('set_enforcing', {})
```

### Manage a boolean

```python
# Get boolean value
result = module.execute_action('get_boolean', {
    'name': 'httpd_can_network_connect'
})

# Set boolean value (persistent)
result = module.execute_action('set_boolean', {
    'name': 'httpd_can_network_connect',
    'value': True,
    'persistent': True
})
```

### List all booleans

```python
result = module.execute_action('list_booleans', {})
if result.success:
    for name, value in result.data['booleans'].items():
        print(f"{name}: {value}")
```

## SELinux Modes

- **Enforcing**: SELinux policy is enforced, access denials are logged
- **Permissive**: SELinux policy is not enforced, but denials are logged
- **Disabled**: SELinux is completely disabled (requires reboot to enable)

## Notes

- Changing mode with `set_enforcing`/`set_permissive` is temporary (runtime only)
- To permanently change mode, edit `/etc/selinux/config` and reboot
- Use `persistent=True` when setting booleans to make them survive reboots
- Always test in permissive mode before enforcing
- Check availability with `module.check_availability()` before use

## Best Practices

1. **Test First**: Always test changes in permissive mode
2. **Monitor Logs**: Check `/var/log/audit/audit.log` for denials
3. **Use Booleans**: Prefer booleans over custom policies when possible
4. **Document Changes**: Keep track of which booleans are modified
5. **Backup Contexts**: Save file contexts before making changes
