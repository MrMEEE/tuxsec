# TuxSec Agent - RPM Packaging Guide

This guide explains how to build and install the TuxSec Agent RPM packages.

## Package Structure

The TuxSec Agent is split into multiple RPM packages:

### Core Package

- **tuxsec-agent** (base package)
  - Root daemon (`tuxsec-rootd`)
  - Userspace agent (`tuxsec-agent`)
  - CLI tool (`tuxsec-cli`)
  - Setup wizard (`tuxsec-setup`)
  - System info module (built-in)
  - Configuration files and directories
  - Systemd service files

### Module Packages

- **tuxsec-agent-firewalld**
  - Firewall management module
  - Requires: `firewalld`

### Policy Packages

- **tuxsec-agent-selinux**
  - SELinux policy module
  - File contexts
  - Security rules for socket and port access

## Building RPMs

### Prerequisites

Install build dependencies:

```bash
# RHEL/Fedora
sudo dnf install rpm-build python3-devel python3-setuptools systemd-rpm-macros selinux-policy-devel git

# Fedora additional
sudo dnf builddep tuxsec-agent.spec
```

### Build Process

#### 1. Quick Build (All Packages)

```bash
make all
```

This will:
- Clean previous builds
- Create source tarball
- Build all RPM packages
- Build SELinux policy module

#### 2. Step-by-Step Build

**Create source tarball:**
```bash
make tarball
```

**Build source RPM:**
```bash
make srpm
```

**Build binary RPMs:**
```bash
make rpm
```

**Build SELinux policy:**
```bash
make selinux
```

#### 3. Development Installation

For local development/testing without RPM:

```bash
# Install in development mode (editable)
make dev-install

# Or regular installation
make install
```

### Build Output

RPM packages will be created in: `build/rpmbuild/RPMS/noarch/`

- `tuxsec-agent-2.0.0-1.el9.noarch.rpm` (base package)
- `tuxsec-agent-firewalld-2.0.0-1.el9.noarch.rpm` (firewalld module)
- `tuxsec-agent-selinux-2.0.0-1.el9.noarch.rpm` (SELinux policy)

## Installing RPMs

### Base Installation

Install the base package:

```bash
sudo dnf install build/rpmbuild/RPMS/noarch/tuxsec-agent-*.rpm
```

This will:
- Create `tuxsec` user and group
- Install Python package
- Install executables in `/usr/bin/`
- Create directories with correct permissions
- Install systemd service files
- Copy default configuration

### Optional Modules

Install firewalld module:

```bash
sudo dnf install build/rpmbuild/RPMS/noarch/tuxsec-agent-firewalld-*.rpm
```

Install SELinux policy:

```bash
sudo dnf install build/rpmbuild/RPMS/noarch/tuxsec-agent-selinux-*.rpm
```

### Post-Installation Setup

After installing, run the setup wizard:

```bash
sudo tuxsec-setup
```

This interactive tool will:
- Confirm user and directory setup
- Ask for connection mode (pull/push/ssh)
- Configure server URL and credentials
- Set up SSL certificates
- Configure logging
- Save configuration to `/etc/tuxsec/agent.yaml`
- Optionally enable and start services

Or manually configure:

```bash
# Edit configuration
sudo nano /etc/tuxsec/agent.yaml

# Enable services
sudo systemctl enable tuxsec-rootd tuxsec-agent

# Start services
sudo systemctl start tuxsec-rootd tuxsec-agent
```

## Verifying Installation

### Check Services

```bash
# Check service status
systemctl status tuxsec-rootd
systemctl status tuxsec-agent

# View logs
journalctl -u tuxsec-rootd -f
journalctl -u tuxsec-agent -f
```

### Test Functionality

```bash
# Test CLI as tuxsec user
sudo -u tuxsec tuxsec-cli system-info

# List available modules
sudo -u tuxsec tuxsec-cli list-modules

# Test firewalld module (if installed)
sudo -u tuxsec tuxsec-cli execute firewalld get_status
```

### Verify SELinux (if installed)

```bash
# Check if policy is loaded
semodule -l | grep tuxsec

# Verify file contexts
ls -Z /usr/bin/tuxsec-*
ls -Z /etc/tuxsec/
ls -Z /var/log/tuxsec/
ls -Z /var/run/tuxsec/
```

## Upgrading

To upgrade to a newer version:

```bash
# Upgrade all packages
sudo dnf upgrade tuxsec-agent*.rpm

# Services will be restarted automatically
```

Configuration files will be preserved (marked as `%config(noreplace)`).

## Uninstalling

### Remove Packages

```bash
# Remove all packages
sudo dnf remove tuxsec-agent tuxsec-agent-firewalld tuxsec-agent-selinux

# Or remove just base package (removes modules as dependencies)
sudo dnf remove tuxsec-agent
```

### Clean Up (Optional)

RPM uninstall preserves configuration and logs:

```bash
# Remove configuration
sudo rm -rf /etc/tuxsec

# Remove logs
sudo rm -rf /var/log/tuxsec

# Remove data directory
sudo rm -rf /var/lib/tuxsec

# Remove user (optional, not recommended if you plan to reinstall)
sudo userdel tuxsec
```

## Customizing the Build

### Modifying Version

Edit `Makefile`:
```makefile
VERSION = 2.0.1
RELEASE = 1
```

Also update `agent/__init__.py`:
```python
__version__ = "2.0.1"
```

### Adding New Modules

1. Create module in `agent/rootd/modules/mymodule.py`

2. Add to SPEC file:

```spec
%package -n tuxsec-agent-mymodule
Summary:        TuxSec Agent mymodule module
Requires:       tuxsec-agent = %{version}-%{release}
Requires:       mymodule-package

%description -n tuxsec-agent-mymodule
Description of mymodule

%files -n tuxsec-agent-mymodule
%{python3_sitelib}/agent/rootd/modules/mymodule.py
%{python3_sitelib}/agent/rootd/modules/__pycache__/mymodule.*
```

3. Rebuild:
```bash
make clean
make rpm
```

### Modifying SELinux Policy

1. Edit `agent/selinux/tuxsec.te`

2. Increment version in the policy:
```
policy_module(tuxsec, 1.0.1)
```

3. Rebuild policy:
```bash
make selinux
```

4. Update and reinstall:
```bash
sudo semodule -u agent/selinux/tuxsec.pp
```

## Building for Different Distributions

### RHEL/CentOS Stream/Rocky/Alma

The SPEC file is designed for RHEL-based distributions:

```bash
# RHEL 9
make rpm

# RHEL 8 (may need to adjust Python version)
# Edit SPEC file to change python3_version if needed
make rpm
```

### Fedora

Works out of the box:

```bash
make rpm
```

### OpenSUSE/SUSE

May need to adjust:
- systemd macro names
- Python package names
- Dependency names

## Troubleshooting Build Issues

### Missing Build Dependencies

```bash
# Install missing dependencies from SPEC file
sudo dnf builddep tuxsec-agent.spec
```

### Python Module Not Found

```bash
# Ensure setuptools is installed
sudo dnf install python3-setuptools python3-devel
```

### SELinux Policy Build Fails

```bash
# Install SELinux development tools
sudo dnf install selinux-policy-devel checkpolicy policycoreutils-python-utils

# Check policy syntax
checkmodule -M -m agent/selinux/tuxsec.te
```

### RPM Build Fails

```bash
# Check the build log
less build/rpmbuild/BUILD/build.log

# Verify tarball creation
make tarball
tar -tzf build/tuxsec-agent-2.0.0.tar.gz
```

## Creating a YUM/DNF Repository

To distribute RPMs through a repository:

```bash
# Create repository directory
mkdir -p /var/www/html/repos/tuxsec

# Copy RPMs
cp build/rpmbuild/RPMS/noarch/*.rpm /var/www/html/repos/tuxsec/

# Create repository metadata
createrepo /var/www/html/repos/tuxsec/

# Update metadata (after adding new RPMs)
createrepo --update /var/www/html/repos/tuxsec/
```

Client configuration:

```bash
# Create repo file
sudo tee /etc/yum.repos.d/tuxsec.repo << EOF
[tuxsec]
name=TuxSec Repository
baseurl=http://your-server/repos/tuxsec/
enabled=1
gpgcheck=0
EOF

# Install
sudo dnf install tuxsec-agent
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Build RPM

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    container: fedora:latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Install dependencies
        run: |
          dnf install -y rpm-build python3-devel systemd-rpm-macros selinux-policy-devel make git
      
      - name: Build RPM
        run: make rpm
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: rpm-packages
          path: build/rpmbuild/RPMS/noarch/*.rpm
```

## Summary

Key commands:

```bash
# Build everything
make all

# Install base package
sudo dnf install build/rpmbuild/RPMS/noarch/tuxsec-agent-*.rpm

# Run setup wizard
sudo tuxsec-setup

# Start services
sudo systemctl start tuxsec-rootd tuxsec-agent

# Test
sudo -u tuxsec tuxsec-cli system-info
```

For questions or issues, see the main [README.md](README.md) or open an issue on GitHub.
