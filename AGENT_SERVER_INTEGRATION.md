# Agent-Server Integration Documentation

This document explains how the TuxSec Server integrates with the new two-component agent architecture (v0.1.0+).

## Overview

The TuxSec system consists of:
- **Agent** (on managed machines): Two-component architecture with rootd daemon and userspace agent
- **API Server** (FastAPI): Command queuing, agent registration, and API endpoints
- **Web UI** (Django): User interface for managing agents and firewall rules

## Agent Architecture (v0.1.0+)

### Two-Component Design

```
┌─────────────────────────────────────────────────────────────┐
│                    Managed Machine                          │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  tuxsec-agent (unprivileged, user: tuxsec)          │  │
│  │  - Handles server communication                      │  │
│  │  - Three modes: pull, push, SSH                      │  │
│  │  - Uses Unix socket to talk to rootd                 │  │
│  └────────────┬─────────────────────────────────────────┘  │
│               │ Unix Socket                                 │
│               │ /var/run/tuxsec/rootd.sock                  │
│  ┌────────────▼─────────────────────────────────────────┐  │
│  │  tuxsec-rootd (root daemon)                          │  │
│  │  - Exposes modules via Unix socket                   │  │
│  │  - systeminfo: hostname, OS, uptime                  │  │
│  │  - firewalld: zone/service/port/rule management      │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Agent Connection Modes

1. **Pull Mode (agent_to_server)**
   - Agent polls server for commands every N seconds
   - Server queues commands in Redis/Database
   - Agent retrieves and executes commands
   - Agent reports results back to server

2. **Push Mode (server_to_agent)**
   - Agent listens on port (default 8443)
   - Server connects to agent when command needed
   - Server sends command directly
   - Agent responds immediately

3. **SSH Mode**
   - No persistent agent process needed
   - Server connects via SSH when needed
   - Executes `tuxsec-cli` commands
   - Useful for one-off management

### Command Format (New in v0.1.0)

Commands use a module-based structure:

```json
{
  "module": "firewalld",
  "action": "add_service",
  "params": {
    "zone": "public",
    "service": "http",
    "permanent": true
  }
}
```

**Available Modules:**
- `systeminfo`: System information (hostname, OS, uptime)
- `firewalld`: Firewall management (requires tuxsec-agent-firewalld package)

### Authentication

**SSH Mode:**
- Uses SSH keys or password authentication
- Server authenticates to agent machine via SSH
- Commands run as tuxsec user with sudo privileges

**Pull Mode (agent_to_server):**
- Agent authenticates with X-API-Key header
- API key generated during agent registration
- All agent-to-server requests include: `X-API-Key: <api_key>`

**Push Mode (server_to_agent):**
- Server sends X-API-Key header to agent
- Agent validates key against stored server key
- Used when server initiates connection to agent

**API Key Management:**
1. **Registration**: Server generates API key during agent registration
   ```bash
   POST /api/agents/register
   {
     "hostname": "web01.example.com",
     "ip_address": "192.168.1.100",
     "mode": "pull"
   }
   # Response includes api_key (only returned once!)
   ```

2. **Storage**: Agent stores API key in `/etc/tuxsec/config.yaml`

3. **Usage**: Agent includes in all API requests
   ```bash
   curl -H "X-API-Key: $API_KEY" https://server/api/heartbeat
   ```

4. **Rotation**: Update via re-registration with new api_key parameter

## Server Components

### 1. Django Web UI (`web_ui/`)

**Models** (`agents/models.py`):
```python
class Agent(models.Model):
    CONNECTION_TYPES = [
        ('agent_to_server', 'Agent connects to Server'),  # Pull mode
        ('server_to_agent', 'Server connects to Agent'),  # Push mode
        ('ssh', 'SSH Connection'),                        # SSH mode
    ]
    
    # Connection fields
    connection_type = models.CharField(...)
    agent_port = models.IntegerField(default=8444)  # For push mode
    agent_api_key = models.CharField(...)           # Authentication
    
    # SSH fields
    ssh_username = models.CharField(...)
    ssh_private_key = models.TextField(...)
    ssh_password = models.CharField(...)
```

**Connection Managers** (`agents/connection_managers.py`):

Three manager classes handle different connection types:

1. **SSHConnectionManager**
   - Uses paramiko for SSH connections
   - Executes `tuxsec-cli` commands on remote host
   - Example: `tuxsec-cli execute firewalld add_service --param zone=public --param service=http`

2. **AgentToServerManager** (Pull Mode)
   - Queues commands in database/Redis
   - Agent polls `/api/agents/{agent_id}/commands` endpoint
   - Server stores results when agent reports back

3. **ServerToAgentManager** (Push Mode)
   - Makes HTTP POST to agent's endpoint
   - Agent must be listening on configured port
   - Immediate response

### 2. API Server (`api_server/`)

**Command Dispatcher** (`command_dispatcher.py`):
- Manages command queue for pull-mode agents
- Stores commands in Redis with expiration
- Tracks command status (pending, running, completed, failed)

**Agent Manager** (`agent_manager.py`):
- Handles agent registration
- Tracks agent heartbeats
- Manages agent metadata

**API Endpoints** (`routers/`):
- `POST /api/commands/` - Queue command for agent
- `GET /api/agents/{agent_id}/commands` - Get pending commands (pull mode)
- `POST /api/agents/{agent_id}/results` - Report command results
- `GET /api/agents/{agent_id}/status` - Get agent status

## Integration Points

### 1. Command Translation

**Server Side (Old Format):**
```python
# Django uses simplified command names
command = 'add_service'
parameters = {'zone': 'public', 'service': 'http', 'permanent': True}
```

**Agent Side (New Format):**
```python
# Agent expects module-based structure
{
    "module": "firewalld",
    "action": "add_service",
    "params": {
        "zone": "public",
        "service": "http",
        "permanent": true
    }
}
```

**Translation happens in connection managers:**

```python
# SSHConnectionManager example
async def execute_command(self, command: str, parameters: Optional[Dict] = None):
    # Build tuxsec-cli command
    cli_command = f"tuxsec-cli execute firewalld {command}"
    
    if parameters:
        for key, value in parameters.items():
            cli_command += f" --param {key}={value}"
    
    # Execute via SSH
    stdout, stderr, exit_code = self._execute_ssh_command(cli_command)
```

### 2. Response Format

**Agent Response Structure:**
```json
{
  "success": true,
  "result": {
    "status": "active",
    "zones": ["public", "trusted"],
    "default_zone": "public"
  },
  "error": null,
  "timestamp": "2025-11-21T10:30:00Z"
}
```

**Server expects:**
```python
{
    'success': bool,
    'result': dict,  # Module-specific data
    'error': str | None,
    'message': str | None
}
```

### 3. Module Discovery and Heartbeat

Agents report available modules during registration and heartbeat:

**Agent Heartbeat (POST /api/heartbeat):**
```json
{
    "agent_id": "uuid",
    "status": "online",
    "available_modules": ["systeminfo", "firewalld", "selinux"],
    "version": "0.1.0",
    "timestamp": "2025-11-21T10:30:00Z",
    "system_info": {
        "os": "Rocky Linux 9.3",
        "kernel": "5.14.0-362.8.1.el9_3.x86_64"
    }
}
```

**Server Storage:**
- API Server: Stores in `Agent.available_modules` (JSON field in PostgreSQL)
- Web UI: Stores in `Agent.available_modules` (JSONField in Django/SQLite)

**Heartbeat Frequency:**
- Pull mode: Agent sends heartbeat every poll interval (default 60s)
- Push mode: Agent sends heartbeat on startup and every 5 minutes
- SSH mode: Server queries via `tuxsec-cli execute systeminfo get_info` on demand

**Module Availability in UI:**
Server checks `agent.available_modules` before showing firewall/SELinux options to users.

## Current Implementation Status

### ✅ Already Implemented (Server)

1. **Three connection modes** in Django models
2. **Connection managers** for each mode
3. **SSH connection testing** with OS detection
4. **Command queueing** for pull mode
5. **API endpoints** for agent communication
6. **Auto-sync** configuration per agent

### ⚠️ Needs Updates (for v0.1.0 Agent)

1. ~~**SSH Commands**~~ ✅ **DONE** - Updated to use `tuxsec-cli`
   - Old: `firewall-cmd --add-service=http`
   - New: `tuxsec-cli execute firewalld add_service --param service=http`

2. ~~**Command Structure**~~ ✅ **DONE** - Added module field to commands
   - Old: `{'command': 'add_service', 'parameters': {...}}`
   - New: `{'module': 'firewalld', 'action': 'add_service', 'params': {...}}`

3. ~~**Module Support**~~ ✅ **DONE** - Track available modules per agent
   - Store systeminfo, firewalld, selinux, aide availability via heartbeat
   - Heartbeat endpoint: POST /api/heartbeat with available_modules list
   - Stored in Agent.available_modules (JSON field)

4. ~~**API Key Auth**~~ ✅ **DONE** - Implement in push/pull modes
   - X-API-Key header validation via verify_agent_api_key dependency
   - Auto-generated during agent registration (secrets.token_urlsafe(32))
   - Secured endpoints: /api/heartbeat, /api/{agent_id}/commands, /api/{agent_id}/results
   - Stored in Agent.api_key field (API server) and agent_api_key (Django)

5. ~~**Response Parsing**~~ ✅ **DONE** - Handle new response format
   - Expect nested result structure
   - Parse module-specific data

## Migration Path

### Phase 1: SSH Mode Support (Immediate)
```python
# Update SSHConnectionManager
class SSHConnectionManager(BaseConnectionManager):
    async def execute_command(self, command: str, parameters: Optional[Dict] = None):
        # Detect if agent has tuxsec-cli
        has_cli = self._check_tuxsec_cli()
        
        if has_cli:
            # Use new agent CLI
            cmd = f"sudo -u tuxsec tuxsec-cli execute firewalld {command}"
            for k, v in (parameters or {}).items():
                cmd += f" --param {k}={v}"
        else:
            # Fall back to direct firewall-cmd (legacy)
            cmd = self._build_firewall_cmd(command, parameters)
        
        return self._execute_ssh_command(cmd)
```

### Phase 2: Pull/Push Mode Updates
```python
# Add module field to command queue
async def queue_command(agent_id, module, action, params):
    command = {
        'command_id': str(uuid.uuid4()),
        'agent_id': agent_id,
        'module': module,        # NEW
        'action': action,        # Renamed from command_type
        'params': params,        # Renamed from parameters
        'created_at': datetime.now().isoformat()
    }
    await redis_client.lpush(f"agent_commands:{agent_id}", json.dumps(command))
```

### Phase 3: Module Discovery
```python
# Agent heartbeat endpoint
@router.post("/agents/{agent_id}/heartbeat")
async def agent_heartbeat(agent_id: str, heartbeat: AgentHeartbeat):
    # Update agent metadata
    agent.version = heartbeat.version
    agent.modules = heartbeat.modules  # ['systeminfo', 'firewalld']
    agent.last_seen = datetime.now()
    agent.save()
    
    # Return pending commands
    commands = await get_pending_commands(agent_id)
    return {'commands': commands}
```

## Testing

### Test SSH Mode with New Agent

```python
# In Django shell
from agents.models import Agent
from agents.connection_managers import SSHConnectionManager

agent = Agent.objects.get(hostname='testhost')
manager = SSHConnectionManager(agent)

# Test connection
result = await manager.test_connection()
print(result)  # Should show tuxsec-cli available

# Execute command
result = await manager.execute_command('get_status')
print(result)  # Should return firewalld status
```

### Test Pull Mode

```python
# Queue a command
from api_server.command_dispatcher import CommandDispatcher

dispatcher = CommandDispatcher(db_manager, redis_client)
command = AgentCommand(
    command_id=str(uuid.uuid4()),
    agent_id=agent.id,
    module='firewalld',
    action='add_service',
    params={'zone': 'public', 'service': 'http'}
)
await dispatcher.send_command(command)

# Agent will pick it up on next poll
```

## Security Considerations

1. **Unix Socket Permissions**
   - rootd socket: 0660 root:tuxsec
   - Only tuxsec user can connect

2. **API Authentication**
   - Pull/Push modes: API key in X-API-Key header
   - SSH mode: SSH key or password auth

3. **SSL/TLS**
   - All HTTP communication uses HTTPS
   - Certificate validation enforced

4. **SELinux**
   - Custom policy for socket access
   - Port access for push mode
   - DBus access for firewalld

## Configuration Examples

### Agent Config (Pull Mode)
```yaml
# /etc/tuxsec/agent.yaml
mode: pull
server_url: https://tuxsec.example.com
agent_id: "550e8400-e29b-41d4-a716-446655440000"
api_key: "secret-api-key"
poll_interval: 30
ssl_cert: /etc/tuxsec/certs/agent.crt
ssl_key: /etc/tuxsec/certs/agent.key
```

### Agent Config (Push Mode)
```yaml
# /etc/tuxsec/agent.yaml
mode: push
server_url: https://tuxsec.example.com
agent_id: "550e8400-e29b-41d4-a716-446655440000"
api_key: "secret-api-key"
listen_host: 0.0.0.0
listen_port: 8443
ssl_cert: /etc/tuxsec/certs/agent.crt
ssl_key: /etc/tuxsec/certs/agent.key
```

### Django Agent Model (Push Mode)
```python
agent = Agent.objects.create(
    hostname='webserver01',
    ip_address='192.168.1.100',
    connection_type='server_to_agent',
    agent_port=8443,
    agent_api_key='secret-api-key',
    status='approved'
)
```

### Django Agent Model (SSH Mode)
```python
agent = Agent.objects.create(
    hostname='webserver01',
    ip_address='192.168.1.100',
    connection_type='ssh',
    ssh_username='tuxsec',
    ssh_private_key='-----BEGIN RSA PRIVATE KEY-----\n...',
    status='approved'
)
```

## Troubleshooting

### Agent not connecting (Pull Mode)
1. Check agent logs: `journalctl -u tuxsec-agent -f`
2. Verify network connectivity: `curl https://tuxsec.example.com`
3. Check API key matches: Compare agent.yaml and Django model
4. Verify agent_id is correct: Must match UUID in Django

### Server can't reach agent (Push Mode)
1. Check agent is listening: `netstat -tlnp | grep 8443`
2. Verify firewall allows connections: `firewall-cmd --list-ports`
3. Test connectivity: `curl https://agent-host:8443/health`
4. Check certificates are valid

### SSH commands failing
1. Verify tuxsec-cli installed: `ssh user@host "which tuxsec-cli"`
2. Check tuxsec user exists: `ssh user@host "id tuxsec"`
3. Test rootd socket: `ssh user@host "sudo -u tuxsec tuxsec-cli system-info"`
4. Check rootd is running: `ssh user@host "systemctl status tuxsec-rootd"`

## References

- [Agent Architecture](agent/ARCHITECTURE.md) - Detailed agent design
- [Agent README](agent/README.md) - Agent installation and usage
- [Quick Reference](QUICKREF.md) - Common commands
- [Packaging Guide](PACKAGING.md) - RPM building and distribution
