#!/bin/bash
#
# TuxSec Agent Installer
# 
# This script installs the tuxsec-agent on a Linux system.
# It sets up the necessary users, directories, permissions, and systemd services.
#

set -e

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi

echo "==================================="
echo "TuxSec Agent Installer"
echo "==================================="

# Detect Python
PYTHON=$(command -v python3)
if [ -z "$PYTHON" ]; then
    echo "Error: python3 not found"
    exit 1
fi

echo "Using Python: $PYTHON"

# Create tuxsec user and group if they don't exist
if ! id -u tuxsec > /dev/null 2>&1; then
    echo "Creating tuxsec user..."
    useradd --system --shell /bin/bash --create-home --home-dir /var/lib/tuxsec tuxsec
else
    echo "User tuxsec already exists"
fi

# Create required directories
echo "Creating directories..."
mkdir -p /etc/tuxsec/certs
mkdir -p /var/run/tuxsec
mkdir -p /var/log/tuxsec
mkdir -p /var/lib/tuxsec
mkdir -p /usr/local/bin

# Set permissions
echo "Setting permissions..."
chown root:tuxsec /var/run/tuxsec
chmod 0770 /var/run/tuxsec

chown tuxsec:tuxsec /var/log/tuxsec
chmod 0755 /var/log/tuxsec

chown tuxsec:tuxsec /var/lib/tuxsec
chmod 0755 /var/lib/tuxsec

chown root:root /etc/tuxsec
chmod 0755 /etc/tuxsec

chown root:tuxsec /etc/tuxsec/certs
chmod 0750 /etc/tuxsec/certs

# Install Python package
echo "Installing tuxsec_agent Python package..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Install required Python packages
$PYTHON -m pip install pyyaml httpx aiohttp || {
    echo "Warning: Could not install Python dependencies. Please install manually:"
    echo "  pip install pyyaml httpx aiohttp"
}

# Copy configuration file if it doesn't exist
if [ ! -f /etc/tuxsec/agent.yaml ]; then
    echo "Creating default configuration..."
    cp agent.yaml.example /etc/tuxsec/agent.yaml
    chown root:tuxsec /etc/tuxsec/agent.yaml
    chmod 0640 /etc/tuxsec/agent.yaml
else
    echo "Configuration file already exists: /etc/tuxsec/agent.yaml"
fi

# Install systemd services
echo "Installing systemd services..."
cp systemd/tuxsec-rootd.service /etc/systemd/system/
cp systemd/tuxsec-agent.service /etc/systemd/system/

# Reload systemd
systemctl daemon-reload

# Create CLI symlink
echo "Creating CLI tool..."
cat > /usr/local/bin/tuxsec-cli << 'EOFCLI'
#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib' / 'python3' / 'dist-packages'))
from tuxsec_agent.userspace.cli import main
sys.exit(main())
EOFCLI
chmod +x /usr/local/bin/tuxsec-cli

echo ""
echo "==================================="
echo "Installation Complete!"
echo "==================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Edit the configuration file:"
echo "   sudo nano /etc/tuxsec/agent.yaml"
echo ""
echo "2. Configure the agent mode (pull/push/ssh) and server URL"
echo ""
echo "3. Start the services:"
echo "   sudo systemctl start tuxsec-rootd"
echo "   sudo systemctl start tuxsec-agent"
echo ""
echo "4. Enable services to start on boot:"
echo "   sudo systemctl enable tuxsec-rootd"
echo "   sudo systemctl enable tuxsec-agent"
echo ""
echo "5. Check service status:"
echo "   sudo systemctl status tuxsec-rootd"
echo "   sudo systemctl status tuxsec-agent"
echo ""
echo "6. View logs:"
echo "   sudo journalctl -u tuxsec-rootd -f"
echo "   sudo journalctl -u tuxsec-agent -f"
echo ""
echo "7. Test the CLI (as tuxsec user):"
echo "   sudo -u tuxsec tuxsec-cli system-info"
echo "   sudo -u tuxsec tuxsec-cli list-modules"
echo ""
