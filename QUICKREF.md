# TuxSec Agent - Quick Reference

## Installation

### From RPM
```bash
# Build RPMs
make rpm

# Install base package
sudo dnf install build/rpmbuild/RPMS/noarch/tuxsec-agent-*.rpm

# Install firewalld module (optional)
sudo dnf install build/rpmbuild/RPMS/noarch/tuxsec-agent-firewalld-*.rpm

# Install SELinux policy (optional, recommended)
sudo dnf install build/rpmbuild/RPMS/noarch/tuxsec-agent-selinux-*.rpm
```

### Setup
```bash
# Run interactive setup wizard
sudo tuxsec-setup

# Or manually edit config
sudo nano /etc/tuxsec/agent.yaml
```

## Service Management

```bash
# Start services
sudo systemctl start tuxsec-rootd tuxsec-agent

# Stop services
sudo systemctl stop tuxsec-rootd tuxsec-agent

# Restart services
sudo systemctl restart tuxsec-rootd tuxsec-agent

# Enable on boot
sudo systemctl enable tuxsec-rootd tuxsec-agent

# Check status
sudo systemctl status tuxsec-rootd
sudo systemctl status tuxsec-agent

# View logs
sudo journalctl -u tuxsec-rootd -f
sudo journalctl -u tuxsec-agent -f
```

## CLI Commands

### System Information
```bash
# Get all system info
sudo -u tuxsec tuxsec-cli system-info

# Get just hostname
sudo -u tuxsec tuxsec-cli execute systeminfo get_hostname

# Get OS info
sudo -u tuxsec tuxsec-cli execute systeminfo get_os_info

# Get uptime
sudo -u tuxsec tuxsec-cli execute systeminfo get_uptime
```

### Module Management
```bash
# List available modules
sudo -u tuxsec tuxsec-cli list-modules

# Get module capabilities
sudo -u tuxsec tuxsec-cli module-info firewalld
sudo -u tuxsec tuxsec-cli module-info systeminfo
```

### Firewalld Operations

**Query:**
```bash
# Get firewalld status
sudo -u tuxsec tuxsec-cli execute firewalld get_status

# Get version
sudo -u tuxsec tuxsec-cli execute firewalld get_version

# List zones
sudo -u tuxsec tuxsec-cli execute firewalld list_zones

# Get zone details
sudo -u tuxsec tuxsec-cli execute firewalld get_zone --param zone=public

# Get default zone
sudo -u tuxsec tuxsec-cli execute firewalld get_default_zone

# List available services
sudo -u tuxsec tuxsec-cli execute firewalld list_services
```

**Services:**
```bash
# Add service to zone
sudo -u tuxsec tuxsec-cli execute firewalld add_service \
  --param zone=public \
  --param service=http \
  --param permanent=true

# Remove service from zone
sudo -u tuxsec tuxsec-cli execute firewalld remove_service \
  --param zone=public \
  --param service=http \
  --param permanent=true
```

**Ports:**
```bash
# Add port
sudo -u tuxsec tuxsec-cli execute firewalld add_port \
  --param zone=public \
  --param port=8080/tcp \
  --param permanent=true

# Remove port
sudo -u tuxsec tuxsec-cli execute firewalld remove_port \
  --param zone=public \
  --param port=8080/tcp \
  --param permanent=true
```

**Rich Rules:**
```bash
# Add rich rule
sudo -u tuxsec tuxsec-cli execute firewalld add_rich_rule \
  --param zone=public \
  --param rule='rule family="ipv4" source address="192.168.1.0/24" accept' \
  --param permanent=true

# Remove rich rule
sudo -u tuxsec tuxsec-cli execute firewalld remove_rich_rule \
  --param zone=public \
  --param rule='rule family="ipv4" source address="192.168.1.0/24" accept' \
  --param permanent=true
```

**Control:**
```bash
# Reload firewalld
sudo -u tuxsec tuxsec-cli execute firewalld reload

# Set default zone
sudo -u tuxsec tuxsec-cli execute firewalld set_default_zone \
  --param zone=public
```

## Configuration File

Location: `/etc/tuxsec/agent.yaml`

### Pull Mode
```yaml
mode: pull
server_url: https://tuxsec.example.com
agent_id: your-agent-id
api_key: your-api-key
poll_interval: 30
ssl_cert: /etc/tuxsec/certs/agent.crt
ssl_key: /etc/tuxsec/certs/agent.key
ca_cert: /etc/tuxsec/certs/ca.crt
log_level: INFO
log_file: /var/log/tuxsec/agent.log
```

### Push Mode
```yaml
mode: push
server_url: https://tuxsec.example.com
agent_id: your-agent-id
api_key: your-api-key
listen_host: 0.0.0.0
listen_port: 8443
ssl_cert: /etc/tuxsec/certs/agent.crt
ssl_key: /etc/tuxsec/certs/agent.key
ca_cert: /etc/tuxsec/certs/ca.crt
log_level: INFO
log_file: /var/log/tuxsec/agent.log
```

### SSH Mode
```yaml
mode: ssh
server_url: https://tuxsec.example.com
log_level: INFO
log_file: /var/log/tuxsec/agent.log
```

## File Locations

```
/usr/bin/tuxsec-rootd              # Root daemon executable
/usr/bin/tuxsec-agent              # Userspace agent executable
/usr/bin/tuxsec-cli                # CLI tool
/usr/bin/tuxsec-setup              # Setup wizard

/etc/tuxsec/agent.yaml             # Configuration file
/etc/tuxsec/certs/                 # SSL certificates

/var/run/tuxsec/rootd.sock         # Unix socket
/var/log/tuxsec/                   # Log files
/var/lib/tuxsec/                   # Data directory

/usr/lib/systemd/system/tuxsec-rootd.service   # Root daemon service
/usr/lib/systemd/system/tuxsec-agent.service   # Userspace agent service
```

## User and Permissions

- **tuxsec user**: Unprivileged user running userspace agent
- **tuxsec group**: Group for socket access

```bash
# Check user exists
id tuxsec

# Check group membership
groups tuxsec

# Check directory permissions
ls -la /etc/tuxsec/
ls -la /var/run/tuxsec/
ls -la /var/log/tuxsec/
```

## Troubleshooting

### Root Daemon Won't Start
```bash
# Check logs
sudo journalctl -u tuxsec-rootd -n 50

# Verify socket directory
sudo ls -la /var/run/tuxsec/

# Check if already running
sudo systemctl status tuxsec-rootd
```

### Agent Can't Connect to Root Daemon
```bash
# Check socket exists
sudo ls -l /var/run/tuxsec/rootd.sock

# Check socket permissions (should be 0660 root:tuxsec)
sudo ls -l /var/run/tuxsec/rootd.sock

# Test connection
sudo -u tuxsec tuxsec-cli system-info
```

### Firewalld Module Not Available
```bash
# Check if firewalld is installed
rpm -qa | grep firewalld

# Check if firewalld is running
sudo systemctl status firewalld

# Check if module is installed
rpm -qa | grep tuxsec-agent-firewalld

# Check root daemon logs
sudo journalctl -u tuxsec-rootd | grep firewalld
```

### SELinux Denials
```bash
# Check SELinux status
getenforce

# Check for denials
sudo ausearch -m avc -ts recent | grep tuxsec

# Check if policy is loaded
semodule -l | grep tuxsec

# Relabel files
sudo restorecon -R /usr/bin/tuxsec-*
sudo restorecon -R /etc/tuxsec/
sudo restorecon -R /var/log/tuxsec/
sudo restorecon -R /var/run/tuxsec/
```

### Permission Denied Errors
```bash
# Fix socket directory permissions
sudo chown root:tuxsec /var/run/tuxsec
sudo chmod 0770 /var/run/tuxsec

# Fix log directory permissions
sudo chown tuxsec:tuxsec /var/log/tuxsec
sudo chmod 0755 /var/log/tuxsec

# Fix config permissions
sudo chown root:tuxsec /etc/tuxsec/agent.yaml
sudo chmod 0640 /etc/tuxsec/agent.yaml
```

## Building from Source

```bash
# Clone repository
git clone https://github.com/MrMEEE/tuxsec.git
cd tuxsec

# Build RPMs
make rpm

# Build SELinux policy
make selinux

# Build everything
make all
```

## Uninstalling

```bash
# Remove packages
sudo dnf remove tuxsec-agent tuxsec-agent-firewalld tuxsec-agent-selinux

# Optional: Remove configuration and logs
sudo rm -rf /etc/tuxsec /var/log/tuxsec /var/lib/tuxsec
```

## Getting Help

- **Documentation**: See [agent/README.md](agent/README.md)
- **Architecture**: See [agent/ARCHITECTURE.md](agent/ARCHITECTURE.md)
- **Packaging**: See [PACKAGING.md](PACKAGING.md)
- **Migration**: See [agent/MIGRATION.md](agent/MIGRATION.md)
- **Issues**: https://github.com/MrMEEE/tuxsec/issues

## Version

Current version: **2.0.0**

```bash
# Check installed version
rpm -q tuxsec-agent

# Check Python package version
python3 -c "import agent; print(agent.__version__)"
```
