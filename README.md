# TuxSec - Central Security Management System

A comprehensive centralized management system for firewalld across multiple servers with **three different agent communication methods**.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-brightgreen.svg)
![Django](https://img.shields.io/badge/django-5.2.7-green.svg)

## 🚀 Overview

This system provides a unified web interface and API for managing firewalld configurations across multiple servers, supporting three distinct communication patterns to accommodate different network architectures and security requirements.

## 🎯 Quick Start

```bash
# Clone and setup
git clone <repository-url>
cd tuxsec
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Initialize database
cd web_ui && python manage.py migrate && python manage.py createsuperuser && cd ..

# Start all services
./start.sh

# Access Web UI at http://127.0.0.1:8001
```

**Management Scripts:**
- `./start.sh` - Start API Server, Web UI, and Sync Scheduler
- `./stop.sh` - Stop all services
- `./status.sh` - Check service status

## ⚠️ Agent Architecture v2.0

**New Secure Agent Architecture!** The TuxSec agent has been completely redesigned with a two-component architecture:

- **Root Daemon** (`tuxsec-rootd`): Privileged component that executes system operations through a modular plugin system
- **Userspace Agent** (`tuxsec-agent`): Unprivileged component that handles network communication

**Key Benefits:**
- ✅ Privilege separation - network code runs unprivileged
- ✅ Modular plugins - only load what you need
- ✅ No arbitrary commands - well-defined API only
- ✅ Multiple modes - pull, push, and SSH

**See [tuxsec_agent/README.md](tuxsec_agent/README.md) for the new architecture documentation.**

## 🔧 Three Communication Methods

### 1. **Pull Mode (Agent-to-Server)**
- **How it works**: Agent polls server for jobs and executes them
- **Best for**: Agents behind firewalls/NAT, no incoming connections needed
- **Security**: Agent runs as unprivileged user, delegates to root daemon via Unix socket

### 2. **Push Mode (Server-to-Agent)**
- **How it works**: Server pushes jobs directly to agent's HTTPS endpoint
- **Best for**: Direct network access, real-time command execution
- **Security**: TLS/SSL encrypted, API key authentication

### 3. **SSH Mode**
- **How it works**: Server connects via SSH and executes CLI commands
- **Best for**: Existing SSH infrastructure, minimal setup
- **Security**: SSH key authentication, commands through tuxsec-cli tool

## 🏗️ System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Django Web UI │    │   FastAPI Server │    │   Agent (v2.0)  │
│                 │    │                  │    │                 │
│ • Agent Mgmt    │◄──►│ • REST API       │◄──►│ tuxsec-agent    │
│ • Firewall Rules│    │ • WebSocket      │    │ (unprivileged)  │
│ • Real-time UI  │    │ • Authentication │    │        │        │
│ • User Auth     │    │ • Command Queue  │    │  Unix Socket    │
│ • Module Mgmt   │    │ • Job Dispatch   │    │        ▼        │
└─────────────────┘    └──────────────────┘    │ tuxsec-rootd    │
                                                │    (root)       │
                                                │   ┌──────────┐  │
                                                │   │ Modules: │  │
                                                │   │ firewalld│  │
                                                │   │ selinux  │  │
                                                │   │ aide     │  │
                                                │   └──────────┘  │
                                                └─────────────────┘
```

## 📦 Components

- **[Web UI](web_ui/)**: Django-based management interface with dynamic forms
- **[API Server](api_server/)**: FastAPI REST API for programmatic access
- **[Agent v2.0](agent/)**: **NEW** Two-component secure agent with module system
- **[Shared](shared/)**: Common models, utilities, and configuration

## 🔌 Module System

TuxSec uses a **modular plugin architecture** for security features. Each module is self-contained with its own models, views, and sync logic.

**Current Modules:**
- **firewalld** - Firewall management (zones, rules, services)
- **systeminfo** - System information and monitoring
- **venv** - Python virtual environment management

**Coming Soon:**
- **aide** - File integrity monitoring
- **selinux** - SELinux policy management
- **clamav** - Antivirus scanning

### 📚 Complete Module Documentation

**Start Here:** 
- � **[Documentation Index](MODULES_INDEX.md)** - Complete guide to all module documentation

**Quick Links:**
- 📊 **[Summary](MODULES_SUMMARY.md)** - High-level overview and project status (5 min)
- 🏗️ **[Architecture](MODULES_REFACTORING.md)** - Complete refactoring plan and architecture (30 min)
- � **[Implementation Guide](MODULES_IMPLEMENTATION_GUIDE.md)** - Step-by-step instructions (45 min)
- ⚡ **[Quick Reference](MODULES_QUICK_REFERENCE.md)** - Fast module creation guide (15 min)
- 📸 **[Visual Guide](MODULES_VISUAL_GUIDE.md)** - Architecture diagrams and flows (10 min)

**Creating Your First Module:**
```bash
# See MODULES_QUICK_REFERENCE.md for complete examples

# 1. Create module structure
mkdir -p web_ui/modules/mymodule
cd web_ui/modules/mymodule

# 2. Create module.py (5 minutes)
cat > module.py << 'EOF'
from modules.base.module import BaseModule

class MyModule(BaseModule):
    def get_name(self):
        return "mymodule"
    
    def get_display_name(self):
        return "My Security Module"
EOF

# 3. Register in modules/__init__.py
# 4. Enable in Web UI - Done!

# See documentation for adding database, REST API, auto-sync, etc.
```

## 🎁 Agent Packages

The TuxSec agent is available as RPM packages:

- **tuxsec-agent** - Base package (root daemon, userspace agent, CLI, setup tool)
- **tuxsec-agent-firewalld** - Firewall management module
- **tuxsec-agent-selinux** - SELinux policy module

**Build RPMs:**
```bash
make rpm
```

**Install:**
```bash
sudo dnf install build/rpmbuild/RPMS/noarch/tuxsec-agent-*.rpm
sudo tuxsec-setup  # Interactive configuration wizard
```

**See [PACKAGING.md](PACKAGING.md) for complete build and installation instructions.**

## Features

TuxSec provides **19 comprehensive firewall management features** covering all aspects of firewalld configuration:

### 🔐 Core Security Features
- **Audit Log System** - Complete audit trail with filtering and search
- **Smart Reload Operations** - Intelligent configuration validation and reload
- **Panic Mode** - Emergency firewall shutdown blocking all traffic
- **Lockdown Whitelist** - Restrict firewall modifications to authorized users/applications

### 🛡️ Firewall Zone Management
- **Zone Management** - Create custom zones, modify defaults, set targets
- **Tabbed Zone Interface** - Organized UI with General/Advanced/Forwarding/Settings tabs
- **Interface & Source Bindings** - Bind network interfaces and IPs to zones

### 🔥 Firewall Services & Rules
- **Custom Service Management** - Create and manage custom services with multiple ports
- **Policy Matrix** - Zone-to-zone traffic policies with rich rules
- **ICMP Block Management** - Block specific ICMP message types per zone
- **Helper Module Management** - Netfilter connection tracking helpers (FTP, SIP, etc.)
- **Firewalld Service Control** - Start, stop, restart firewalld service
- **Log Denied Packets** - Configure logging levels for denied traffic

### 🗂️ Advanced Features
- **IPSet Management** - Efficient IP address list management with 5 types
- **Direct Rules Management** - Direct iptables rule management with passthrough

### 📋 Configuration Templates
- **Template System** - Complete template management with 4 phases:
  - Phase 1: Database model for reusable configurations
  - Phase 2: CRUD views for template management
  - Phase 3: Apply logic with preview and rollback
  - Phase 4: Full-featured UI with grid view and filtering

**8 Pre-configured Templates:**
- Basic Web Server, Database Server, DMZ Web Server, Office Workstation
- Home Network, NAT Gateway, High Security Server, Container Host

### 📊 Technical Implementation
- **87 agent capabilities** across all firewall operations
- **100+ backend API views** with validation and error handling
- **120+ URL routes** for complete functionality
- **18 database migrations** with comprehensive models
- **Real-time sync** with configurable intervals (default: 3 seconds)

### 📚 Documentation
- **[FEATURES.md](FEATURES.md)** - Complete feature documentation with usage examples
- **[API_REFERENCE.md](API_REFERENCE.md)** - Full API reference with request/response examples
- **[agent/README.md](agent/README.md)** - Agent architecture v2.0 modular design
- **[AUTOSYNC_AND_RULES.md](AUTOSYNC_AND_RULES.md)** - Auto-sync configuration guide


## Quick Start

### Prerequisites
- Python 3.9+
- Redis server
- PostgreSQL database
- Root/sudo access on managed servers

### Installation

1. Clone and setup the project:
```bash
git clone <repository-url>
cd tuxsec
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. Setup environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Initialize the database:
```bash
cd web_ui
python manage.py migrate
python manage.py createsuperuser
```

4. Start the services:

**Option 1: Use the management scripts (recommended):**
```bash
# Start all services (API Server, Web UI, and Sync Scheduler)
./start.sh

# Check status of all services
./status.sh

# Stop all services
./stop.sh
```

**Option 2: Start services manually:**
```bash
# Terminal 1: Start Redis (if using Redis for caching)
redis-server

# Terminal 2: Start API Server
cd api_server
python main.py

# Terminal 3: Start Web UI
cd web_ui
python manage.py runserver 127.0.0.1:8001

# Terminal 4: Start Sync Agents Scheduler
cd web_ui
python manage.py sync_agents --daemon
```

### Agent Installation

On each server to be managed:

1. Copy the agent files:
```bash
scp -r tuxsec_agent/ root@target-server:/opt/tuxsec-agent/
```

2. Install dependencies:
```bash
ssh root@target-server
cd /opt/firewalld-agent
pip install -r requirements.txt
```

3. Configure and start the agent:
```bash
# Edit agent configuration
cp config.yaml.example config.yaml
# Configure server URL and mode (pull/push)

# Start the agent
python agent.py
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/tuxsec_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key
API_SECRET_KEY=your-api-secret-key

# API Server
API_HOST=0.0.0.0
API_PORT=8000

# Web UI
WEB_HOST=0.0.0.0
WEB_PORT=8080

# SSL/TLS
SSL_CERT_PATH=./certs/server.crt
SSL_KEY_PATH=./certs/server.key
CA_CERT_PATH=./certs/ca.crt
```

### Agent Configuration

Each agent uses a `config.yaml` file:

```yaml
server:
  url: "https://your-central-server:8000"
  mode: "pull"  # or "push"
  poll_interval: 30

security:
  cert_path: "./certs/agent.crt"
  key_path: "./certs/agent.key"
  ca_cert_path: "./certs/ca.crt"

logging:
  level: "INFO"
  file: "/var/log/firewalld-agent.log"
```

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black .
flake8 .
mypy .
```

### Pre-commit Hooks
```bash
pre-commit install
```

## API Documentation

Once the API server is running, visit:
- API docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

## Web Interface

Access the web UI at: http://localhost:8080

### Default Admin User
- Username: admin
- Password: (set during createsuperuser)

## Security Considerations

- All communication between components uses TLS with self-signed certificates
- Agents authenticate using client certificates
- Web UI supports role-based access control
- API endpoints require proper authentication tokens
- Firewall rules are validated before application

## Troubleshooting

### Common Issues

1. **Agent connection failed**: Check certificate paths and server URL
2. **Database connection error**: Verify PostgreSQL is running and credentials are correct
3. **Permission denied on firewall operations**: Ensure agent runs with appropriate privileges
4. **Redis connection failed**: Verify Redis server is running

### Log Locations
- API Server: `./logs/api_server.log`
- Web UI: `./logs/web_ui.log`
- Agent: `/var/log/firewalld-agent.log` (configurable)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

[Your License Here]

## Support

For issues and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review the API documentation