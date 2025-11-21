# TuxSec Agent

The TuxSec Agent provides secure, modular system management for Linux servers. It uses a two-component architecture that separates privileged operations from network communication.

## Architecture Overview

The agent consists of two main components:

### 1. Root Daemon (`tuxsec-rootd`)

- **Runs as:** root
- **Purpose:** Executes privileged operations in a controlled manner
- **Communication:** Unix socket (`/var/run/tuxsec/rootd.sock`)
- **Security:** No arbitrary command execution - only predefined module operations

The root daemon exposes system management capabilities through a modular plugin system. Each module provides specific functionality (firewall management, SELinux, AIDE, etc.) with well-defined actions.

**Built-in modules:**
- `systeminfo` - System information (always available)
- `firewalld` - Firewall management (optional)
- More modules can be added as plugins

### 2. Userspace Agent (`tuxsec-agent`)

- **Runs as:** unprivileged user (`tuxsec`)
- **Purpose:** Bridge between TuxSec server and root daemon
- **Communication:** HTTPS/SSH with server, Unix socket with root daemon

The userspace agent handles all network communication and delegates privileged operations to the root daemon.

**Connection modes:**

1. **Pull Mode** - Agent initiates connections to server
   - Polls server for pending jobs
   - Executes jobs through root daemon
   - Reports results back to server

2. **Push Mode** - Server initiates connections to agent
   - Agent listens on configured port (default: 8443)
   - Server pushes jobs to agent
   - Agent executes through root daemon and returns results

3. **SSH Mode** - Server connects via SSH
   - Server uses SSH to connect as `tuxsec` user
   - Commands executed through `tuxsec-cli` tool
   - CLI communicates with root daemon

## Installation

### Prerequisites

- Linux system with systemd
- Python 3.8 or higher
- Root access for installation

### Quick Install

```bash
cd tuxsec_agent
sudo bash install.sh
```

This will:
- Create `tuxsec` user and group
- Set up required directories
- Install systemd services
- Create default configuration

### Manual Installation

1. **Create user:**
   ```bash
   sudo useradd --system --shell /bin/bash --create-home --home-dir /var/lib/tuxsec tuxsec
   ```

2. **Create directories:**
   ```bash
   sudo mkdir -p /etc/tuxsec/certs
   sudo mkdir -p /var/run/tuxsec
   sudo mkdir -p /var/log/tuxsec
   sudo mkdir -p /var/lib/tuxsec
   ```

3. **Set permissions:**
   ```bash
   sudo chown root:tuxsec /var/run/tuxsec
   sudo chmod 0770 /var/run/tuxsec
   sudo chown tuxsec:tuxsec /var/log/tuxsec
   ```

4. **Install Python dependencies:**
   ```bash
   pip install pyyaml httpx aiohttp
   ```

5. **Copy configuration:**
   ```bash
   sudo cp agent.yaml.example /etc/tuxsec/agent.yaml
   sudo chown root:tuxsec /etc/tuxsec/agent.yaml
   sudo chmod 0640 /etc/tuxsec/agent.yaml
   ```

6. **Install systemd services:**
   ```bash
   sudo cp systemd/*.service /etc/systemd/system/
   sudo systemctl daemon-reload
   ```

## Configuration

Edit `/etc/tuxsec/agent.yaml`:

```yaml
# Connection mode: pull, push, or ssh
mode: pull

# Server connection (for pull mode)
server_url: https://tuxsec.example.com
agent_id: null  # Set during registration
api_key: null   # Set during registration

# Pull mode settings
poll_interval: 30  # Seconds between polls

# Push mode settings
listen_host: 0.0.0.0
listen_port: 8443

# SSL/TLS certificates
ssl_cert: /etc/tuxsec/certs/agent.crt
ssl_key: /etc/tuxsec/certs/agent.key
ca_cert: /etc/tuxsec/certs/ca.crt

# Logging
log_level: INFO
log_file: /var/log/tuxsec/agent.log
```

## Usage

### Starting Services

```bash
# Start root daemon
sudo systemctl start tuxsec-rootd

# Start userspace agent
sudo systemctl start tuxsec-agent

# Enable on boot
sudo systemctl enable tuxsec-rootd tuxsec-agent
```

### Checking Status

```bash
# Check services
sudo systemctl status tuxsec-rootd
sudo systemctl status tuxsec-agent

# View logs
sudo journalctl -u tuxsec-rootd -f
sudo journalctl -u tuxsec-agent -f

# Or check log files
sudo tail -f /var/log/tuxsec/rootd.log
sudo tail -f /var/log/tuxsec/agent.log
```

### Using the CLI

The `tuxsec-cli` tool provides command-line access to the agent (useful for SSH mode):

```bash
# Get system information
sudo -u tuxsec tuxsec-cli system-info

# List available modules
sudo -u tuxsec tuxsec-cli list-modules

# Get module information
sudo -u tuxsec tuxsec-cli module-info firewalld

# Execute commands
sudo -u tuxsec tuxsec-cli execute systeminfo get_hostname
sudo -u tuxsec tuxsec-cli execute firewalld list_zones
sudo -u tuxsec tuxsec-cli execute firewalld add_service --param zone=public --param service=http
```

## Module Development

To create a new module, inherit from `BaseModule`:

```python
from tuxsec_agent.rootd.base_module import BaseModule
from tuxsec_agent.rootd.protocol import ModuleCapability, CommandRequest, CommandResponse

class MyModule(BaseModule):
    @property
    def name(self) -> str:
        return "mymodule"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "My custom module"
    
    def get_capabilities(self) -> List[ModuleCapability]:
        return [
            ModuleCapability(
                name="my_action",
                description="Perform an action",
                parameters=[
                    {"name": "param1", "type": "string", "description": "Parameter 1", "required": "true"}
                ]
            )
        ]
    
    def initialize(self) -> tuple[bool, Optional[str]]:
        # Initialize module
        return True, None
    
    def shutdown(self):
        # Cleanup
        pass
    
    def execute_command(self, command: CommandRequest) -> CommandResponse:
        # Execute command
        if command.action == "my_action":
            # Do something
            return CommandResponse(success=True, data={"result": "OK"})
        
        return CommandResponse(success=False, error="Unknown action")
```

Register the module in `tuxsec_agent/rootd/daemon.py`:

```python
from .modules.mymodule import MyModule

# In _load_modules method:
mymodule = MyModule()
self.registry.register_module(mymodule)
```

## Security

### Privilege Separation

- Root daemon only executes well-defined module operations
- No arbitrary command execution
- Userspace agent runs as unprivileged user
- Unix socket permissions restrict access

### Network Communication

- TLS/SSL for all network communication (pull/push modes)
- API key authentication
- Certificate-based authentication for SSH mode

### File Permissions

- `/var/run/tuxsec/rootd.sock` - 0660 root:tuxsec
- `/etc/tuxsec/agent.yaml` - 0640 root:tuxsec
- `/var/log/tuxsec/` - 0755 tuxsec:tuxsec

## Troubleshooting

### Root daemon won't start

Check if socket directory exists and has correct permissions:
```bash
sudo ls -la /var/run/tuxsec/
sudo mkdir -p /var/run/tuxsec
sudo chown root:tuxsec /var/run/tuxsec
sudo chmod 0770 /var/run/tuxsec
```

### Userspace agent can't connect to root daemon

Check that root daemon is running:
```bash
sudo systemctl status tuxsec-rootd
```

Verify socket permissions:
```bash
sudo ls -l /var/run/tuxsec/rootd.sock
```

Test connection:
```bash
sudo -u tuxsec tuxsec-cli system-info
```

### Module not available

Check if module initialized successfully:
```bash
sudo journalctl -u tuxsec-rootd | grep -i module
```

For firewalld module, ensure firewalld is installed:
```bash
sudo dnf install firewalld  # RHEL/Fedora
sudo apt install firewalld  # Debian/Ubuntu
```

### Permission denied errors

Ensure tuxsec user is in correct group:
```bash
sudo usermod -a -G tuxsec tuxsec
```

Check file ownership:
```bash
sudo ls -la /etc/tuxsec/
sudo ls -la /var/log/tuxsec/
sudo ls -la /var/run/tuxsec/
```

## Architecture Diagrams

### Pull Mode
```
[TuxSec Server] <--- HTTPS --- [tuxsec-agent (unprivileged)]
                                        |
                                   Unix Socket
                                        |
                               [tuxsec-rootd (root)]
                                        |
                                   [Firewalld, SELinux, etc.]
```

### Push Mode
```
[TuxSec Server] --- HTTPS ---> [tuxsec-agent (unprivileged)]
                                        |
                                   Unix Socket
                                        |
                               [tuxsec-rootd (root)]
                                        |
                                   [Firewalld, SELinux, etc.]
```

### SSH Mode
```
[TuxSec Server] --- SSH ---> [tuxsec user shell]
                                     |
                                [tuxsec-cli]
                                     |
                                Unix Socket
                                     |
                            [tuxsec-rootd (root)]
                                     |
                                [Firewalld, SELinux, etc.]
```

## License

See LICENSE file in the repository root.

## Contributing

Contributions welcome! Please submit pull requests or open issues on GitHub.

## Support

For support, please open an issue on the GitHub repository or contact the maintainers.
