# Firewalld Module

## Overview

The Firewalld module provides comprehensive firewall management capabilities using the firewalld service. It allows you to manage zones, services, ports, rich rules, and more across your infrastructure.

## Requirements

- **System Packages**: `firewalld`, `python3-firewall`
- **Service**: firewalld must be installed and running

## Capabilities

- `FIREWALL`: Primary firewall management capability

## Available Actions

### Zone Management
- `list_zones` - List all available zones
- `get_zones` - Get all zones
- `get_default_zone` - Get the default zone
- `set_default_zone` - Set the default zone
- `get_active_zones` - Get currently active zones
- `get_zone_info` - Get detailed information about a specific zone

### Service Management
- `list_services` - List all services
- `add_service` - Add a service to a zone
- `remove_service` - Remove a service from a zone
- `query_service` - Check if a service is enabled in a zone

### Port Management
- `list_ports` - List all open ports
- `add_port` - Add a port to a zone
- `remove_port` - Remove a port from a zone
- `query_port` - Check if a port is open in a zone

### Rich Rules
- `list_rich_rules` - List all rich rules
- `add_rich_rule` - Add a rich rule to a zone
- `remove_rich_rule` - Remove a rich rule from a zone

### Masquerading
- `query_masquerade` - Check if masquerading is enabled
- `add_masquerade` - Enable masquerading in a zone
- `remove_masquerade` - Disable masquerading in a zone

### Interface Management
- `add_interface` - Add a network interface to a zone
- `remove_interface` - Remove a network interface from a zone
- `change_interface` - Move an interface to a different zone
- `query_interface` - Check which zone an interface is in

### Source Management
- `add_source` - Add a source address to a zone
- `remove_source` - Remove a source address from a zone
- `query_source` - Check if a source is in a zone

### Configuration
- `reload` - Reload firewalld configuration
- `runtime_to_permanent` - Make runtime changes permanent
- `get_status` - Get current firewalld status

## Configuration Schema

```json
{
  "type": "object",
  "properties": {
    "default_zone": {
      "type": "string",
      "description": "Default firewall zone"
    },
    "auto_reload": {
      "type": "boolean",
      "description": "Automatically reload after changes",
      "default": true
    }
  }
}
```

## Usage Examples

### Add a service to a zone

```python
result = module.execute_action('add_service', {
    'zone': 'public',
    'service': 'http',
    'permanent': True
})
```

### Add a port

```python
result = module.execute_action('add_port', {
    'zone': 'public',
    'port': '8080',
    'protocol': 'tcp',
    'permanent': True
})
```

### Add a rich rule

```python
result = module.execute_action('add_rich_rule', {
    'zone': 'public',
    'rule': 'rule family="ipv4" source address="192.168.1.0/24" accept',
    'permanent': True
})
```

## Notes

- Most actions support both runtime and permanent modes
- Use `permanent=True` to make changes persist across reboots
- After making changes, run `reload` to apply permanent rules
- Check availability with `module.check_availability()` before use
