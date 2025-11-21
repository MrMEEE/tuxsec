# TuxSec - Central Security Management System

A comprehensive centralized management system for firewalld across multiple servers with **three different agent communication methods**.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-brightgreen.svg)
![Django](https://img.shields.io/badge/django-5.2.7-green.svg)

## 🚀 Overview

This system provides a unified web interface and API for managing firewalld configurations across multiple servers, supporting three distinct communication patterns to accommodate different network architectures and security requirements.

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
- **[Module System](MODULE_SYSTEM.md)**: Plugin-based architecture for security modules

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

- **Modular Architecture**: Plugin-based system for security features (Firewalld, SELinux, ClamAV, AIDE)
- **Per-Agent Module Control**: Enable/disable specific modules on individual agents
- **Visual Network Management**: Drag-and-drop interface for defining network connections
- **Comprehensive Firewall Control**: Support for all firewalld features including rich rules and masquerade
- **SELinux Management**: Control SELinux modes, booleans, and contexts
- **Secure Communication**: Self-signed certificate-based authentication between components
- **Role-Based Access**: Granular user permissions for different server groups
- **Real-time Updates**: Live status monitoring and configuration synchronization
- **Dual Operation Modes**: Support for both agent-initiated (pull) and server-initiated (push) communication
- **Module Action Logging**: Complete audit trail of all module actions

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
```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start API Server
cd api_server
python main.py

# Terminal 3: Start Web UI
cd web_ui
python manage.py runserver

# Terminal 4: Start Celery (for background tasks)
cd web_ui
celery -A tuxsec worker --loglevel=info
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