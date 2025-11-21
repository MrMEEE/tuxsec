# Agent v0.1.0 Server Integration - Completion Summary

## Overview
Completed full server-side integration for the new TuxSec agent v0.1.0 architecture with two-component design (rootd + agent).

## Completed Work

### 1. ✅ SSH Connection Manager Updates
**Files Modified:**
- `web_ui/agents/connection_managers.py` (SSHConnectionManager class)

**Changes:**
- Replaced all `firewall-cmd` commands with `tuxsec-cli execute module action` format
- Updated command execution: `sudo -u tuxsec tuxsec-cli execute firewalld add_service --param zone=public --param service=http`
- Removed legacy zone/service management code
- Updated all 3 AgentCommand.objects.create() calls in SSHConnectionManager

**Testing Required:**
- SSH connection to agent machine
- Execute firewalld commands via tuxsec-cli
- Verify command results are parsed correctly

---

### 2. ✅ Command Structure Migration
**Files Modified:**
- `web_ui/agents/models.py` (Agent and AgentCommand models)
- `web_ui/agents/migrations/0008_update_agent_command_structure.py` (new)
- `web_ui/agents/connection_managers.py` (all three managers)

**Changes:**
- **Agent Model:**
  - Added `available_modules` JSONField to track agent capabilities
  
- **AgentCommand Model:**
  - Added new fields: `module`, `action`, `params` (JSONField)
  - Kept legacy fields: `command_type`, `parameters` (for backward compatibility)
  - Auto-populates legacy fields in `save()` method
  - Added database indexes: (agent, status), (module, action), (-created_at)

- **Database Migration:**
  - Created migration 0008 with 13 operations
  - Made module/action fields `blank=True` for migration compatibility
  - Applied successfully: `python manage.py migrate agents`

- **Connection Managers:**
  - Updated all 5 AgentCommand.objects.create() calls across three managers
  - Changed from: `command=f"{module}.{command}", parameters=json.dumps(...)`
  - Changed to: `module=module, action=command, params=parameters or {}`
  - Removed json.dumps() wrappers (JSONField handles serialization)

**Data Format:**
```python
# Old Format
{
    'command': 'add_service',
    'parameters': '{"zone": "public", "service": "http"}'
}

# New Format
{
    'module': 'firewalld',
    'action': 'add_service',
    'params': {'zone': 'public', 'service': 'http'}
}
```

---

### 3. ✅ Module Availability Tracking
**Files Modified:**
- `api_server/schemas.py` (AgentHeartbeat schema)
- `api_server/database.py` (Agent model)
- `api_server/routers/agents.py` (heartbeat endpoint)
- `AGENT_SERVER_INTEGRATION.md` (documentation)

**Changes:**
- **API Server:**
  - Added `available_modules` JSON column to Agent model
  - Created `AgentHeartbeat` schema with available_modules list
  - Implemented `POST /api/heartbeat` endpoint
  - Updated `AgentInfo` schema to include available_modules

- **Heartbeat Endpoint:**
  ```python
  POST /api/heartbeat
  {
    "agent_id": "uuid",
    "status": "online",
    "available_modules": ["systeminfo", "firewalld", "selinux"],
    "version": "0.1.0",
    "timestamp": "2025-11-21T10:30:00Z",
    "system_info": {...}
  }
  ```

- **Storage:**
  - API Server: `Agent.available_modules` (PostgreSQL JSON)
  - Web UI: `Agent.available_modules` (SQLite JSONField)

- **Frequency:**
  - Pull mode: Every poll interval (default 60s)
  - Push mode: On startup + every 5 minutes
  - SSH mode: On-demand query via tuxsec-cli

---

### 4. ✅ API Key Authentication
**Files Created:**
- `api_server/auth.py` (authentication dependencies)

**Files Modified:**
- `api_server/database.py` (Agent model)
- `api_server/schemas.py` (AgentRegistration, AgentInfo)
- `api_server/routers/agents.py` (register, heartbeat)
- `api_server/routers/commands.py` (commands, results)
- `AGENT_SERVER_INTEGRATION.md` (authentication documentation)

**Changes:**
- **Agent Model:**
  - Added `api_key` String column to Agent model

- **Authentication Module (auth.py):**
  - `verify_agent_api_key()` - Requires X-API-Key header, returns Agent
  - `verify_agent_api_key_optional()` - Optional authentication
  - Validates API key against database
  - Returns 401 Unauthorized if invalid/missing
  - Verifies agent_id matches authenticated agent (prevents cross-agent access)

- **Secured Endpoints:**
  - `POST /api/heartbeat` - Agent health reporting
  - `GET /api/{agent_id}/commands` - Command retrieval (pull mode)
  - `POST /api/{agent_id}/results/{command_id}` - Result submission

- **Agent Registration:**
  - Auto-generates API key: `secrets.token_urlsafe(32)` (43 chars)
  - Returns API key only during initial registration
  - Agents must store key in `/etc/tuxsec/config.yaml`
  - Can rotate by re-registering with new api_key parameter

- **Usage:**
  ```bash
  curl -H "X-API-Key: $API_KEY" https://server/api/heartbeat
  ```

---

### 5. ✅ Response Format Updates
**Files Modified:**
- `web_ui/agents/connection_managers.py` (all three managers)

**Changes:**
- All connection managers now parse responses as:
  ```json
  {
    "success": true,
    "result": {...},
    "error": null,
    "timestamp": "2025-11-21T10:30:00Z"
  }
  ```

- Success determined by `data.get('success')` boolean
- Result stored directly as dict (no JSON encoding)
- Error field captured from response

---

## Documentation Updates

### AGENT_SERVER_INTEGRATION.md
**New Sections:**
- Authentication (SSH, Pull, Push modes)
- API Key Management (generation, storage, usage, rotation)
- Module Discovery and Heartbeat (detailed process)

**Updated Sections:**
- Current Implementation Status
  - Marked SSH Commands, Command Structure, Module Support, API Key Auth, Response Parsing as ✅ DONE
  - Only remaining work: actual integration testing

---

## Commits Made

1. **c4e88c6** - Complete AgentCommand model updates to module-based structure
2. **cf84007** - Add module availability tracking via heartbeat endpoint
3. **bdc8446** - Implement API key authentication for agent endpoints

---

## Testing Requirements

### 6. ⚠️ Integration Testing (Todo #6 - In Progress)

**SSH Mode Testing:**
```bash
# Test connection
ssh -i /path/to/key tuxsec@agent.example.com

# Test tuxsec-cli
sudo -u tuxsec tuxsec-cli execute systeminfo get_info
sudo -u tuxsec tuxsec-cli execute firewalld list_services --param zone=public

# Test from Django
# Create agent with connection_type='ssh'
# Add SSH credentials
# Execute command via UI
```

**Pull Mode Testing:**
```bash
# 1. Register agent
curl -X POST http://server:8000/api/agents/register \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "web01.example.com",
    "ip_address": "192.168.1.100",
    "mode": "pull",
    "operating_system": "Rocky Linux 9",
    "version": "0.1.0"
  }'
# Save returned api_key!

# 2. Send heartbeat
curl -X POST http://server:8000/api/heartbeat \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "uuid",
    "status": "online",
    "available_modules": ["systeminfo", "firewalld"],
    "version": "0.1.0"
  }'

# 3. Poll for commands
curl -H "X-API-Key: $API_KEY" \
  http://server:8000/api/uuid/commands

# 4. Submit results
curl -X POST http://server:8000/api/uuid/results/command-id \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "success": true,
    "result": {"status": "active"},
    "error": null
  }'
```

**Push Mode Testing:**
```bash
# 1. Agent registers with mode=push
# 2. Agent starts HTTPS server on port 8443
# 3. Server sends command to agent
curl -X POST https://agent:8443/api/execute \
  -H "X-API-Key: $SERVER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "module": "firewalld",
    "action": "add_service",
    "params": {"zone": "public", "service": "http"}
  }'
```

---

## Database Schema Changes

### API Server (PostgreSQL/SQLite)
```sql
-- Agent table
ALTER TABLE agents ADD COLUMN available_modules JSON;
ALTER TABLE agents ADD COLUMN api_key VARCHAR;
```

### Django Web UI (SQLite)
```sql
-- Agent model (via migration 0008)
ALTER TABLE agents_agent ADD COLUMN available_modules TEXT;  -- JSONField

-- AgentCommand model
ALTER TABLE agents_agentcommand ADD COLUMN module VARCHAR(100) DEFAULT 'firewalld';
ALTER TABLE agents_agentcommand ADD COLUMN action VARCHAR(100);
ALTER TABLE agents_agentcommand ADD COLUMN params TEXT;  -- JSONField

-- Indexes
CREATE INDEX idx_agent_status ON agents_agentcommand(agent_id, status);
CREATE INDEX idx_module_action ON agents_agentcommand(module, action);
CREATE INDEX idx_created_desc ON agents_agentcommand(created_at DESC);
```

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                     TuxSec Server                               │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Django Web UI (port 8001)                               │  │
│  │  - User interface                                        │  │
│  │  - Agent management                                      │  │
│  │  - Connection managers (SSH, Pull, Push)                │  │
│  │  - Uses tuxsec-cli for SSH mode                         │  │
│  └────────────┬─────────────────────────────────────────────┘  │
│               │                                                 │
│  ┌────────────▼─────────────────────────────────────────────┐  │
│  │  FastAPI Server (port 8000)                              │  │
│  │  - Agent registration                                    │  │
│  │  - Command queuing                                       │  │
│  │  - Heartbeat endpoint                                    │  │
│  │  - API key authentication                                │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                          │
                          │ HTTP(S) + X-API-Key
                          │
┌─────────────────────────▼─────────────────────────────────────┐
│                  Managed Machine (Agent)                      │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  tuxsec-agent (unprivileged user: tuxsec)           │    │
│  │  - Server communication (Pull/Push mode)            │    │
│  │  - Heartbeat every 60s                               │    │
│  │  - Reports available_modules                         │    │
│  │  - Sends X-API-Key header                            │    │
│  └────────────┬─────────────────────────────────────────┘    │
│               │ Unix Socket: /var/run/tuxsec/rootd.sock      │
│  ┌────────────▼─────────────────────────────────────────┐    │
│  │  tuxsec-rootd (root daemon)                          │    │
│  │  - systeminfo module                                 │    │
│  │  - firewalld module (if installed)                   │    │
│  │  - selinux module (future)                           │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
│  [OR via SSH]                                                 │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  tuxsec-cli (CLI tool)                               │    │
│  │  - Executed via SSH by Django                        │    │
│  │  - Talks to rootd via Unix socket                    │    │
│  │  - Returns JSON responses                            │    │
│  └──────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────────┘
```

---

## Next Steps

1. **Complete Integration Testing** (Todo #6)
   - Set up test agent machine with v0.1.0 RPMs
   - Test SSH mode command execution
   - Test Pull mode command queueing
   - Test Push mode direct communication
   - Verify module discovery works for all modes

2. **Agent Development**
   - Implement heartbeat in agent
   - Add X-API-Key header to all requests
   - Store API key from registration response
   - Implement pull mode command polling
   - Implement push mode HTTPS server

3. **Future Enhancements**
   - Add SELinux module support
   - Add AIDE module support
   - Implement certificate-based authentication (in addition to API keys)
   - Add command timeout handling
   - Implement command result pagination

---

## Migration for Existing Deployments

### Database Migrations
```bash
# Django Web UI
cd web_ui
python manage.py migrate agents

# API Server (no Alembic yet, tables auto-created)
# Manually add columns if database already exists:
# ALTER TABLE agents ADD COLUMN available_modules JSON;
# ALTER TABLE agents ADD COLUMN api_key VARCHAR;
```

### Agent Updates
```bash
# Update to v0.1.0 RPMs
dnf update tuxsec-agent tuxsec-agent-firewalld

# Configure API key (obtained from server registration)
cat > /etc/tuxsec/config.yaml <<EOF
agent:
  server_url: https://tuxsec-server.example.com
  api_key: <API_KEY_FROM_REGISTRATION>
  mode: pull
  poll_interval: 60
EOF

# Restart services
systemctl restart tuxsec-rootd
systemctl restart tuxsec-agent
```

### Server Updates
```bash
# Pull latest code
git pull origin main

# Update dependencies
pip install -r requirements.txt
pip install -r web_ui/requirements.txt
pip install -r api_server/requirements.txt

# Run migrations
cd web_ui && python manage.py migrate

# Restart services
systemctl restart tuxsec-web-ui
systemctl restart tuxsec-api-server
```

---

## Summary

All server-side integration work is complete for agent v0.1.0:
- ✅ SSH connection updated to use tuxsec-cli
- ✅ Command structure migrated to module/action/params format
- ✅ Module availability tracking implemented
- ✅ API key authentication fully functional
- ✅ Response parsing updated for new format
- ⚠️ Integration testing pending (requires v0.1.0 agent deployment)

The server is now ready to communicate with the new two-component agent architecture!
