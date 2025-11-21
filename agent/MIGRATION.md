# TuxSec Agent Architecture Migration

## Overview

The TuxSec agent has been completely redesigned with a new two-component architecture that separates privileged operations from network communication for enhanced security.

## What Changed

### Old Architecture (v1.x)

```
[TuxSec Server] <---> [Single Agent Process (root)]
                           |
                      [Direct firewalld access]
```

**Issues:**
- Single process running as root
- Network-facing code with root privileges
- Difficult to add new capabilities securely
- Risk of arbitrary command execution

### New Architecture (v2.0)

```
[TuxSec Server] <---> [Userspace Agent (tuxsec user)]
                           |
                      Unix Socket
                           |
                   [Root Daemon (root)]
                           |
                      [Module System]
                     /      |      \
              firewalld  selinux  aide
```

**Improvements:**
- ✅ Privilege separation - network code is unprivileged
- ✅ Modular plugin system - only load what you need
- ✅ Well-defined API - no arbitrary commands
- ✅ Multiple connection modes - pull, push, SSH
- ✅ Better security boundaries

## Components

### Root Daemon (`tuxsec-rootd`)

**Location:** `/usr/bin/tuxsec-rootd` or `python -m tuxsec_agent.rootd`

**Responsibilities:**
- Runs as root
- Loads capability modules
- Exposes Unix socket at `/var/run/tuxsec/rootd.sock`
- Validates and executes commands
- No network communication

**Modules:**
- `systeminfo` - System information (always loaded)
- `firewalld` - Firewall management (optional)
- More can be added as plugins

### Userspace Agent (`tuxsec-agent`)

**Location:** `/usr/bin/tuxsec-agent` or `python -m tuxsec_agent.userspace`

**Responsibilities:**
- Runs as unprivileged `tuxsec` user
- Handles network communication
- Connects to TuxSec server
- Forwards jobs to root daemon
- Returns results to server

**Connection Modes:**
1. **Pull Mode** - Agent polls server for jobs
2. **Push Mode** - Server pushes jobs to agent
3. **SSH Mode** - Server executes commands via SSH

## Migration Steps

### For Development

1. **Update imports** (if using programmatically):
   ```python
   # Old
   from tuxsec_agent.agent import FirewalldAgent
   
   # New
   from tuxsec_agent.userspace.agent import TuxSecAgent
   from tuxsec_agent.rootd.modules.firewalld import FirewalldModule
   ```

2. **Update configuration** structure - see new `agent.yaml.example`

3. **Test locally**:
   ```bash
   # Terminal 1 - Start root daemon
   sudo python -m tuxsec_agent.rootd
   
   # Terminal 2 - Test CLI
   sudo -u $USER python -m tuxsec_agent.userspace.cli system-info
   ```

### For Production Deployment

1. **Backup existing installation**:
   ```bash
   sudo systemctl stop tuxsec-agent  # Old service
   sudo cp /etc/tuxsec/agent.yaml /etc/tuxsec/agent.yaml.backup
   ```

2. **Install new version**:
   ```bash
   cd tuxsec_agent
   sudo bash install.sh
   ```

3. **Migrate configuration**:
   ```bash
   # Edit new config file
   sudo nano /etc/tuxsec/agent.yaml
   
   # Set mode, server_url, agent_id, api_key
   # Copy from old config if available
   ```

4. **Start new services**:
   ```bash
   sudo systemctl start tuxsec-rootd
   sudo systemctl start tuxsec-agent
   sudo systemctl enable tuxsec-rootd tuxsec-agent
   ```

5. **Verify operation**:
   ```bash
   sudo systemctl status tuxsec-rootd
   sudo systemctl status tuxsec-agent
   sudo -u tuxsec tuxsec-cli system-info
   ```

6. **Remove old service** (if different):
   ```bash
   sudo systemctl disable old-tuxsec-agent
   sudo rm /etc/systemd/system/old-tuxsec-agent.service
   sudo systemctl daemon-reload
   ```

### For TuxSec Server

The server needs to understand the new agent architecture:

1. **Agent Registration**:
   - Still works the same way
   - Agent reports available modules during registration

2. **Job Execution**:
   - Jobs now specify module + action + parameters
   - Example:
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

3. **SSH Mode**:
   - SSH user is now `tuxsec` (not root)
   - Commands executed via `tuxsec-cli`:
     ```bash
     ssh tuxsec@agent-host tuxsec-cli execute firewalld add_service \
       --param zone=public --param service=http
     ```

## Configuration Changes

### Old Format (v1.x)

```yaml
server:
  url: https://server.example.com
  mode: pull
  poll_interval: 30

agent:
  agent_id: abc123
  hostname: myhost

security:
  ssl_cert_path: /path/to/cert
```

### New Format (v2.0)

```yaml
mode: pull
server_url: https://server.example.com
agent_id: abc123
api_key: secret_key
poll_interval: 30

listen_host: 0.0.0.0
listen_port: 8443

ssl_cert: /etc/tuxsec/certs/agent.crt
ssl_key: /etc/tuxsec/certs/agent.key
ca_cert: /etc/tuxsec/certs/ca.crt

log_level: INFO
log_file: /var/log/tuxsec/agent.log
```

## API Changes

### Module Commands

**Old:** Direct firewalld calls
```python
agent.add_service_to_zone("public", "http")
```

**New:** Module-based commands
```python
# Via CLI
tuxsec-cli execute firewalld add_service \
  --param zone=public \
  --param service=http \
  --param permanent=true

# Via Python
from tuxsec_agent.userspace.rootd_client import RootDaemonClient
client = RootDaemonClient()
result = client.execute_command(
    module="firewalld",
    action="add_service",
    parameters={"zone": "public", "service": "http", "permanent": True}
)
```

### Available Actions

**System Info Module:**
- `get_info` - All system information
- `get_hostname` - Hostname only
- `get_os_info` - OS details
- `get_kernel_version` - Kernel version
- `get_uptime` - System uptime

**Firewalld Module:**
- `get_status` - Firewalld status
- `get_version` - Firewalld version
- `list_zones` - List all zones
- `get_zone` - Get zone details
- `get_default_zone` - Get default zone
- `list_services` - List available services
- `set_default_zone` - Set default zone
- `add_service` - Add service to zone
- `remove_service` - Remove service from zone
- `add_port` - Add port to zone
- `remove_port` - Remove port from zone
- `add_rich_rule` - Add rich rule
- `remove_rich_rule` - Remove rich rule
- `reload` - Reload firewalld

## Testing

### Test Root Daemon

```bash
# Start daemon
sudo python -m tuxsec_agent.rootd

# In another terminal, test commands
sudo -u tuxsec tuxsec-cli system-info
sudo -u tuxsec tuxsec-cli list-modules
sudo -u tuxsec tuxsec-cli module-info firewalld
sudo -u tuxsec tuxsec-cli execute firewalld get_status
```

### Test Userspace Agent

```bash
# Configure agent.yaml with mode=pull and server details
sudo nano /etc/tuxsec/agent.yaml

# Start agent
python -m tuxsec_agent.userspace.agent --config /etc/tuxsec/agent.yaml

# Monitor logs
tail -f /var/log/tuxsec/agent.log
```

### Test Full Stack

```bash
# Start both services
sudo systemctl start tuxsec-rootd
sudo systemctl start tuxsec-agent

# Check status
sudo systemctl status tuxsec-rootd
sudo systemctl status tuxsec-agent

# View logs
sudo journalctl -u tuxsec-rootd -f
sudo journalctl -u tuxsec-agent -f
```

## Troubleshooting

### "Cannot connect to tuxsec-rootd"

**Cause:** Root daemon not running or socket permissions incorrect

**Fix:**
```bash
sudo systemctl start tuxsec-rootd
sudo ls -l /var/run/tuxsec/rootd.sock
# Should be: srw-rw---- root tuxsec
```

### "Permission denied" on socket

**Cause:** User not in `tuxsec` group

**Fix:**
```bash
sudo usermod -a -G tuxsec YOUR_USERNAME
# Log out and back in
```

### "Module not found: firewalld"

**Cause:** Firewalld not installed or module initialization failed

**Fix:**
```bash
# Install firewalld
sudo dnf install firewalld  # RHEL/Fedora
sudo apt install firewalld  # Debian/Ubuntu

# Check logs
sudo journalctl -u tuxsec-rootd | grep firewalld
```

### Agent won't start

**Cause:** Configuration error or missing dependencies

**Fix:**
```bash
# Check config
sudo nano /etc/tuxsec/agent.yaml

# Install dependencies
pip install pyyaml httpx aiohttp

# Check logs
sudo journalctl -u tuxsec-agent -e
```

## Rollback

If you need to rollback to the old version:

1. Stop new services:
   ```bash
   sudo systemctl stop tuxsec-agent tuxsec-rootd
   sudo systemctl disable tuxsec-agent tuxsec-rootd
   ```

2. Restore old configuration:
   ```bash
   sudo cp /etc/tuxsec/agent.yaml.backup /etc/tuxsec/agent.yaml
   ```

3. Reinstall old version:
   ```bash
   git checkout v1.x
   # Follow old installation instructions
   ```

## Benefits Summary

- **Security:** Privilege separation, no root network code
- **Modularity:** Only load modules you need
- **Flexibility:** Three connection modes (pull/push/SSH)
- **Safety:** No arbitrary command execution
- **Maintainability:** Clear separation of concerns
- **Extensibility:** Easy to add new modules

## Questions?

See the main README.md or open an issue on GitHub.
