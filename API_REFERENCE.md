# TuxSec API Reference

Complete API documentation for the TuxSec centralized firewall management system.

## 📋 Table of Contents

1. [Authentication](#authentication)
2. [Agent Management](#agent-management)
3. [Zone Management](#zone-management)
4. [Service Management](#service-management)
5. [Policy Management](#policy-management)
6. [Template Management](#template-management)
7. [IPSet Management](#ipset-management)
8. [Direct Rules](#direct-rules)
9. [Lockdown Management](#lockdown-management)
10. [System Operations](#system-operations)
11. [Error Handling](#error-handling)

---

## Authentication

All API requests require authentication using Django session authentication.

### Login
```http
POST /users/login/
Content-Type: application/x-www-form-urlencoded

username=admin&password=yourpassword
```

**Response:**
```json
{
  "success": true,
  "redirect": "/dashboard/"
}
```

### Logout
```http
POST /users/logout/
```

---

## Agent Management

### List Agents
```http
GET /agents/api/agents/
```

**Response:**
```json
[
  {
    "id": "uuid-here",
    "hostname": "firewall01.example.com",
    "ip_address": "192.168.1.10",
    "status": "online",
    "firewalld_version": "1.3.0",
    "last_seen": "2024-01-15T10:30:00Z",
    "zones_count": 10,
    "rules_count": 45
  }
]
```

### Get Agent Details
```http
GET /agents/<agent_id>/
```

**Response:**
```json
{
  "id": "uuid-here",
  "hostname": "firewall01",
  "ip_address": "192.168.1.10",
  "system_info": {
    "os": "Rocky Linux 9.3",
    "kernel": "5.14.0",
    "firewalld_version": "1.3.0"
  },
  "zones": [...],
  "services": [...]
}
```

### Quick Add Agent
```http
POST /agents/quick-add/
Content-Type: application/json

{
  "hostname": "firewall02",
  "ip_address": "192.168.1.11"
}
```

**Response:**
```json
{
  "success": true,
  "agent_id": "new-uuid",
  "message": "Agent added successfully"
}
```

---

## Zone Management

### List Zones
```http
GET /agents/<agent_id>/zones/
```

**Response:**
```json
[
  {
    "id": "zone-uuid",
    "name": "public",
    "target": "default",
    "default": false,
    "services": ["ssh", "http", "https"],
    "ports": ["8080/tcp"],
    "interfaces": ["eth0"],
    "sources": ["192.168.1.0/24"]
  }
]
```

### Create Zone
```http
POST /agents/<agent_id>/zone/create/
Content-Type: application/json

{
  "name": "web-dmz",
  "target": "default"
}
```

**Response:**
```json
{
  "success": true,
  "zone": "web-dmz",
  "message": "Zone created successfully"
}
```

### Delete Zone
```http
POST /agents/<agent_id>/zone/<zone_id>/delete/
```

**Response:**
```json
{
  "success": true,
  "message": "Zone deleted successfully"
}
```

### Set Default Zone
```http
POST /agents/<agent_id>/zone/set-default/
Content-Type: application/json

{
  "zone": "public"
}
```

### Add Service to Zone
```http
POST /agents/<agent_id>/zone/<zone_id>/service/add/
Content-Type: application/json

{
  "service": "http"
}
```

### Remove Service from Zone
```http
POST /agents/<agent_id>/zone/<zone_id>/service/remove/
Content-Type: application/json

{
  "service": "http"
}
```

### Add Port to Zone
```http
POST /agents/<agent_id>/zone/<zone_id>/port/add/
Content-Type: application/json

{
  "port": "8080",
  "protocol": "tcp"
}
```

### Remove Port from Zone
```http
POST /agents/<agent_id>/zone/<zone_id>/port/remove/
Content-Type: application/json

{
  "port": "8080",
  "protocol": "tcp"
}
```

### Add Interface to Zone
```http
POST /agents/<agent_id>/zone/<zone_id>/interface/add/
Content-Type: application/json

{
  "interface": "eth1"
}
```

### Remove Interface from Zone
```http
POST /agents/<agent_id>/zone/<zone_id>/interface/remove/
Content-Type: application/json

{
  "interface": "eth1"
}
```

### Add Source to Zone
```http
POST /agents/<agent_id>/zone/<zone_id>/source/add/
Content-Type: application/json

{
  "source": "192.168.100.0/24"
}
```

**Note:** Source can be:
- IP address: `192.168.1.1`
- CIDR network: `192.168.1.0/24`
- IPSet: `ipset:blacklist`

### Remove Source from Zone
```http
POST /agents/<agent_id>/zone/<zone_id>/source/remove/
Content-Type: application/json

{
  "source": "192.168.100.0/24"
}
```

### Add ICMP Block to Zone
```http
POST /agents/<agent_id>/zone/<zone_id>/icmp-block/add/
Content-Type: application/json

{
  "icmp_type": "echo-request"
}
```

### Remove ICMP Block from Zone
```http
POST /agents/<agent_id>/zone/<zone_id>/icmp-block/remove/
Content-Type: application/json

{
  "icmp_type": "echo-request"
}
```

### List ICMP Types
```http
GET /agents/<agent_id>/zone/<zone_id>/icmp-types/
```

**Response:**
```json
[
  "echo-reply",
  "echo-request",
  "destination-unreachable",
  "time-exceeded",
  "parameter-problem"
]
```

### Toggle ICMP Inversion
```http
POST /agents/<agent_id>/zone/<zone_id>/icmp-inversion/toggle/
```

**Response:**
```json
{
  "success": true,
  "inverted": true
}
```

### Add Helper Module to Zone
```http
POST /agents/<agent_id>/zone/<zone_id>/helper/add/
Content-Type: application/json

{
  "helper": "ftp"
}
```

### Remove Helper Module from Zone
```http
POST /agents/<agent_id>/zone/<zone_id>/helper/remove/
Content-Type: application/json

{
  "helper": "ftp"
}
```

### List Helpers in Zone
```http
GET /agents/<agent_id>/zone/<zone_id>/helpers/
```

**Response:**
```json
["ftp", "tftp"]
```

---

## Service Management

### List All Services
```http
GET /agents/<agent_id>/services/
```

**Response:**
```json
{
  "default": [
    {"name": "http", "ports": ["80/tcp"]},
    {"name": "https", "ports": ["443/tcp"]},
    {"name": "ssh", "ports": ["22/tcp"]}
  ],
  "custom": [
    {"name": "myapp", "ports": ["8080/tcp", "8443/tcp"]}
  ]
}
```

### Create Custom Service
```http
POST /agents/<agent_id>/services/create/
Content-Type: application/json

{
  "name": "myapp",
  "ports": ["8080/tcp", "8443/tcp"]
}
```

**Response:**
```json
{
  "success": true,
  "service": "myapp",
  "message": "Service created successfully"
}
```

### Delete Custom Service
```http
POST /agents/<agent_id>/services/<service_name>/delete/
```

**Response:**
```json
{
  "success": true,
  "message": "Service deleted successfully"
}
```

### Add Port to Service
```http
POST /agents/<agent_id>/services/<service_name>/port/add/
Content-Type: application/json

{
  "port": "9000",
  "protocol": "tcp"
}
```

### Remove Port from Service
```http
POST /agents/<agent_id>/services/<service_name>/port/remove/
Content-Type: application/json

{
  "port": "9000",
  "protocol": "tcp"
}
```

---

## Policy Management

### List Policies
```http
GET /agents/<agent_id>/policies/
```

**Response:**
```json
[
  {
    "id": "policy-uuid",
    "name": "dmz-to-internal",
    "ingress_zones": ["dmz"],
    "egress_zones": ["internal"],
    "target": "ACCEPT",
    "priority": 10,
    "is_active": true
  }
]
```

### Create Policy
```http
POST /agents/<agent_id>/policies/create/
Content-Type: application/json

{
  "name": "dmz-to-internal",
  "ingress_zones": ["dmz"],
  "egress_zones": ["internal"],
  "target": "ACCEPT",
  "priority": 10
}
```

**Parameters:**
- `name` (string, required): Policy name
- `ingress_zones` (array, required): Source zones
- `egress_zones` (array, required): Destination zones
- `target` (string, required): ACCEPT, REJECT, DROP, or CONTINUE
- `priority` (integer, optional): Priority (default: 10)

**Response:**
```json
{
  "success": true,
  "policy_id": "new-uuid",
  "message": "Policy created successfully"
}
```

### Delete Policy
```http
POST /agents/<agent_id>/policies/<policy_id>/delete/
```

**Response:**
```json
{
  "success": true,
  "message": "Policy deleted successfully"
}
```

### Get Policy Details
```http
GET /agents/<agent_id>/policies/<policy_id>/
```

**Response:**
```json
{
  "id": "policy-uuid",
  "name": "dmz-to-internal",
  "ingress_zones": ["dmz"],
  "egress_zones": ["internal"],
  "target": "ACCEPT",
  "priority": 10,
  "is_active": true,
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:00:00Z"
}
```

---

## Template Management

### List Templates
```http
GET /agents/api/templates/
```

**Query Parameters:**
- `category` (optional): Filter by category (server, workstation, dmz, network, custom)
- `search` (optional): Search in name/description

**Response:**
```json
[
  {
    "id": "template-uuid",
    "name": "Basic Web Server",
    "description": "Simple HTTP/HTTPS server configuration",
    "category": "server",
    "is_global": true,
    "usage_count": 15,
    "tags": ["web", "http", "https"],
    "configuration": {
      "custom_services": [...],
      "ipsets": [...],
      "zones": [...],
      "policies": [...]
    }
  }
]
```

### Get Template Details
```http
GET /agents/api/templates/<template_id>/
```

**Response:**
```json
{
  "id": "template-uuid",
  "name": "Basic Web Server",
  "description": "Simple HTTP/HTTPS server configuration",
  "category": "server",
  "is_global": true,
  "created_by": "admin",
  "usage_count": 15,
  "tags": ["web", "http", "https"],
  "configuration": {
    "custom_services": [
      {
        "name": "webapp",
        "ports": ["8080/tcp"]
      }
    ],
    "ipsets": [],
    "zones": [
      {
        "name": "public",
        "services": ["http", "https", "ssh"],
        "ports": [],
        "target": "default"
      }
    ],
    "policies": []
  },
  "created_at": "2024-01-10T08:00:00Z",
  "updated_at": "2024-01-15T10:00:00Z"
}
```

### Create Template
```http
POST /agents/api/templates/
Content-Type: application/json

{
  "name": "My Custom Template",
  "description": "Custom firewall configuration",
  "category": "custom",
  "tags": ["custom", "prod"],
  "configuration": {
    "custom_services": [
      {
        "name": "myapp",
        "ports": ["8080/tcp", "8443/tcp"]
      }
    ],
    "ipsets": [],
    "zones": [
      {
        "name": "public",
        "services": ["myapp", "ssh"],
        "ports": [],
        "target": "default"
      }
    ],
    "policies": []
  }
}
```

**Response:**
```json
{
  "success": true,
  "template_id": "new-uuid",
  "message": "Template created successfully"
}
```

### Update Template
```http
PUT /agents/api/templates/<template_id>/
Content-Type: application/json

{
  "name": "Updated Template Name",
  "description": "Updated description",
  "configuration": {...}
}
```

### Delete Template
```http
DELETE /agents/api/templates/<template_id>/
```

**Response:**
```json
{
  "success": true,
  "message": "Template deleted successfully"
}
```

### Preview Template Changes
```http
POST /agents/api/templates/<template_id>/preview/
Content-Type: application/json

{
  "agent_id": "agent-uuid"
}
```

**Response:**
```json
{
  "agent": {
    "id": "agent-uuid",
    "hostname": "firewall01"
  },
  "changes": {
    "custom_services": {
      "to_create": ["myapp"],
      "existing": ["http", "https"]
    },
    "ipsets": {
      "to_create": [],
      "existing": []
    },
    "zones": {
      "to_modify": ["public"],
      "to_create": []
    },
    "policies": {
      "to_create": [],
      "existing": []
    }
  }
}
```

### Apply Template
```http
POST /agents/api/templates/<template_id>/apply/
Content-Type: application/json

{
  "agent_id": "agent-uuid"
}
```

**Response:**
```json
{
  "success": true,
  "results": {
    "custom_services": {
      "success": 1,
      "failed": 0,
      "details": ["Created service: myapp"]
    },
    "ipsets": {
      "success": 0,
      "failed": 0,
      "details": []
    },
    "zones": {
      "success": 1,
      "failed": 0,
      "details": ["Configured zone: public"]
    },
    "policies": {
      "success": 0,
      "failed": 0,
      "details": []
    }
  },
  "message": "Template applied successfully"
}
```

---

## IPSet Management

### List IPSets
```http
GET /agents/<agent_id>/ipsets/
```

**Response:**
```json
[
  {
    "id": "ipset-uuid",
    "name": "blacklist",
    "type": "hash:ip",
    "entries": ["1.2.3.4", "5.6.7.8"],
    "entry_count": 2
  }
]
```

### Create IPSet
```http
POST /agents/<agent_id>/ipsets/create/
Content-Type: application/json

{
  "name": "whitelist",
  "type": "hash:ip",
  "entries": ["10.0.0.1", "10.0.0.2"]
}
```

**IPSet Types:**
- `hash:ip` - IP addresses
- `hash:net` - Network addresses (CIDR)
- `hash:mac` - MAC addresses
- `hash:ip,port` - IP and port combinations
- `hash:net,port` - Network and port combinations

**Response:**
```json
{
  "success": true,
  "ipset_id": "new-uuid",
  "message": "IPSet created successfully"
}
```

### Add Entry to IPSet
```http
POST /agents/<agent_id>/ipsets/<ipset_id>/entry/add/
Content-Type: application/json

{
  "entry": "10.0.0.3"
}
```

### Remove Entry from IPSet
```http
POST /agents/<agent_id>/ipsets/<ipset_id>/entry/remove/
Content-Type: application/json

{
  "entry": "10.0.0.3"
}
```

### Delete IPSet
```http
POST /agents/<agent_id>/ipsets/<ipset_id>/delete/
```

---

## Direct Rules

### List Direct Rules
```http
GET /agents/<agent_id>/direct-rules/
```

**Response:**
```json
[
  {
    "id": "rule-uuid",
    "ipv": "ipv4",
    "table": "filter",
    "chain": "INPUT",
    "priority": 10,
    "args": ["-p", "tcp", "--dport", "8080", "-j", "ACCEPT"],
    "description": "Allow custom port 8080",
    "is_active": true
  }
]
```

### Create Direct Rule
```http
POST /agents/<agent_id>/direct-rules/create/
Content-Type: application/json

{
  "ipv": "ipv4",
  "table": "filter",
  "chain": "INPUT",
  "priority": 10,
  "args": ["-p", "tcp", "--dport", "8080", "-j", "ACCEPT"],
  "description": "Allow custom port 8080"
}
```

**Parameters:**
- `ipv` (string, required): "ipv4" or "ipv6"
- `table` (string, required): "filter", "nat", "mangle", or "raw"
- `chain` (string, required): Chain name (INPUT, OUTPUT, FORWARD, or custom)
- `priority` (integer, required): Priority 0-999
- `args` (array, required): iptables arguments
- `description` (string, optional): Rule description

**Response:**
```json
{
  "success": true,
  "rule_id": "new-uuid",
  "message": "Direct rule created successfully"
}
```

### Delete Direct Rule
```http
POST /agents/<agent_id>/direct-rules/<rule_id>/delete/
```

**Response:**
```json
{
  "success": true,
  "message": "Direct rule deleted successfully"
}
```

### List Chains for Table
```http
GET /agents/<agent_id>/direct-rules/chains/<table>/
```

**Path Parameters:**
- `table`: "filter", "nat", "mangle", or "raw"

**Response:**
```json
{
  "chains": ["INPUT", "OUTPUT", "FORWARD", "MYCHAIN"]
}
```

---

## Lockdown Management

### Get Lockdown Status
```http
GET /agents/<agent_id>/lockdown/status/
```

**Response:**
```json
{
  "enabled": false
}
```

### Enable/Disable Lockdown
```http
POST /agents/<agent_id>/lockdown/control/
Content-Type: application/json

{
  "action": "enable"
}
```

**Parameters:**
- `action` (string, required): "enable" or "disable"

**Response:**
```json
{
  "success": true,
  "enabled": true,
  "message": "Lockdown mode enabled"
}
```

### List Whitelisted Commands
```http
GET /agents/<agent_id>/lockdown/commands/
```

**Response:**
```json
{
  "commands": [
    "/usr/bin/firewall-cmd",
    "/usr/bin/python3"
  ]
}
```

### Add Whitelisted Command
```http
POST /agents/<agent_id>/lockdown/commands/add/
Content-Type: application/json

{
  "command": "/usr/bin/firewall-cmd"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Command added to whitelist"
}
```

### Remove Whitelisted Command
```http
POST /agents/<agent_id>/lockdown/commands/remove/
Content-Type: application/json

{
  "command": "/usr/bin/firewall-cmd"
}
```

### List Whitelisted Users
```http
GET /agents/<agent_id>/lockdown/users/
```

**Response:**
```json
{
  "users": ["admin", "firewall-manager"]
}
```

### Add Whitelisted User
```http
POST /agents/<agent_id>/lockdown/users/add/
Content-Type: application/json

{
  "user": "admin"
}
```

### Remove Whitelisted User
```http
POST /agents/<agent_id>/lockdown/users/remove/
Content-Type: application/json

{
  "user": "admin"
}
```

---

## System Operations

### Check Firewalld Service Status
```http
GET /agents/<agent_id>/firewalld/service/status/
```

**Response:**
```json
{
  "running": true,
  "enabled": true
}
```

### Control Firewalld Service
```http
POST /agents/<agent_id>/firewalld/service/control/
Content-Type: application/json

{
  "action": "restart"
}
```

**Parameters:**
- `action` (string, required): "start", "stop", or "restart"

**Response:**
```json
{
  "success": true,
  "message": "Firewalld service restarted"
}
```

### Reload Firewall
```http
POST /agents/<agent_id>/firewall/reload/
```

**Response:**
```json
{
  "success": true,
  "message": "Firewall reloaded successfully"
}
```

### Check Firewall Configuration
```http
GET /agents/<agent_id>/firewall/check-config/
```

**Response:**
```json
{
  "valid": true,
  "message": "Configuration is valid"
}
```

### Get Panic Mode Status
```http
GET /agents/<agent_id>/panic/status/
```

**Response:**
```json
{
  "enabled": false
}
```

### Control Panic Mode
```http
POST /agents/<agent_id>/panic/control/
Content-Type: application/json

{
  "action": "enable"
}
```

**Parameters:**
- `action` (string, required): "enable" or "disable"

**Response:**
```json
{
  "success": true,
  "enabled": true,
  "message": "Panic mode enabled - all traffic blocked"
}
```

### Get Log-Denied Status
```http
GET /agents/<agent_id>/log-denied/status/
```

**Response:**
```json
{
  "level": "off"
}
```

### Set Log-Denied Level
```http
POST /agents/<agent_id>/log-denied/control/
Content-Type: application/json

{
  "level": "all"
}
```

**Parameters:**
- `level` (string, required): "off", "all", "unicast", "broadcast", or "multicast"

**Response:**
```json
{
  "success": true,
  "level": "all",
  "message": "Log-denied level set to all"
}
```

---

## Error Handling

All API endpoints return consistent error responses:

### Success Response
```json
{
  "success": true,
  "data": {...},
  "message": "Operation successful"
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error message here",
  "details": "Additional error details"
}
```

### HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful GET request |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid parameters or validation error |
| 401 | Unauthorized | Authentication required |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 500 | Internal Server Error | Server error |

### Common Error Codes

```json
{
  "success": false,
  "error": "AGENT_NOT_FOUND",
  "message": "Agent with ID <uuid> not found"
}
```

```json
{
  "success": false,
  "error": "VALIDATION_ERROR",
  "message": "Invalid zone name",
  "details": "Zone name must be alphanumeric"
}
```

```json
{
  "success": false,
  "error": "CONNECTION_ERROR",
  "message": "Failed to connect to agent",
  "details": "SSH connection timeout"
}
```

```json
{
  "success": false,
  "error": "FIREWALLD_ERROR",
  "message": "Firewalld operation failed",
  "details": "Zone 'public' already exists"
}
```

---

## Rate Limiting

API rate limiting is enforced per user:

- **Default Limit:** 100 requests per minute
- **Burst Limit:** 200 requests per minute
- **Headers:**
  - `X-RateLimit-Limit` - Request limit
  - `X-RateLimit-Remaining` - Remaining requests
  - `X-RateLimit-Reset` - Reset time (Unix timestamp)

**Example:**
```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705320600
```

**Rate Limit Exceeded:**
```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1705320600

{
  "success": false,
  "error": "RATE_LIMIT_EXCEEDED",
  "message": "Too many requests. Please try again later.",
  "retry_after": 30
}
```

---

## Pagination

List endpoints support pagination:

**Query Parameters:**
- `page` (integer, default: 1): Page number
- `page_size` (integer, default: 50): Items per page
- `ordering` (string): Sort field (prefix with `-` for descending)

**Example:**
```http
GET /agents/api/agents/?page=2&page_size=20&ordering=-created_at
```

**Response:**
```json
{
  "count": 100,
  "next": "http://api.example.com/agents/?page=3",
  "previous": "http://api.example.com/agents/?page=1",
  "results": [...]
}
```

---

## Audit Logging

All operations are automatically logged in the audit log:

### View Audit Log
```http
GET /agents/<agent_id>/audit-log/
```

**Query Parameters:**
- `action` (string): Filter by action type
- `user` (string): Filter by username
- `start_date` (ISO date): Filter from date
- `end_date` (ISO date): Filter to date
- `severity` (string): low, medium, high, critical

**Response:**
```json
{
  "logs": [
    {
      "id": "log-uuid",
      "timestamp": "2024-01-15T10:30:00Z",
      "user": "admin",
      "ip_address": "192.168.1.100",
      "module": "firewalld",
      "action": "zone_create",
      "action_category": "configure",
      "severity": "medium",
      "agent": "firewall01",
      "params": {"zone": "web-dmz"},
      "success": true,
      "error_message": null
    }
  ]
}
```

---

## WebSocket API

Real-time updates via WebSocket connection.

### Connect
```javascript
const ws = new WebSocket('ws://localhost:8001/ws/dashboard/');

ws.onopen = () => {
  console.log('Connected to dashboard updates');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Update:', data);
};
```

### Message Types

**Agent Status Update:**
```json
{
  "type": "agent_status",
  "agent_id": "uuid",
  "status": "online",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Configuration Change:**
```json
{
  "type": "config_change",
  "agent_id": "uuid",
  "module": "zone",
  "action": "service_added",
  "details": {"zone": "public", "service": "http"}
}
```

**Sync Completion:**
```json
{
  "type": "sync_complete",
  "agent_id": "uuid",
  "zones_updated": 10,
  "rules_updated": 45
}
```

---

## Best Practices

1. **Authentication:** Always include authentication cookies in requests
2. **Error Handling:** Check `success` field in all responses
3. **Validation:** Validate input before sending to API
4. **Rate Limiting:** Implement exponential backoff for retries
5. **Idempotency:** Most POST operations are idempotent (safe to retry)
6. **Audit Log:** Review audit logs regularly for security monitoring
7. **Reload:** Firewall automatically reloads after configuration changes
8. **Testing:** Test configuration changes in non-production first
9. **Backup:** Keep backups of working configurations
10. **Documentation:** Refer to inline API documentation for details

---

## SDK Examples

### Python
```python
import requests

class TuxSecClient:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.session = requests.Session()
        self.login(username, password)
    
    def login(self, username, password):
        response = self.session.post(
            f'{self.base_url}/users/login/',
            data={'username': username, 'password': password}
        )
        response.raise_for_status()
    
    def list_agents(self):
        response = self.session.get(f'{self.base_url}/agents/api/agents/')
        return response.json()
    
    def create_zone(self, agent_id, zone_name, target='default'):
        response = self.session.post(
            f'{self.base_url}/agents/{agent_id}/zone/create/',
            json={'name': zone_name, 'target': target}
        )
        return response.json()
    
    def add_service_to_zone(self, agent_id, zone_id, service):
        response = self.session.post(
            f'{self.base_url}/agents/{agent_id}/zone/{zone_id}/service/add/',
            json={'service': service}
        )
        return response.json()

# Usage
client = TuxSecClient('http://localhost:8001', 'admin', 'password')
agents = client.list_agents()
print(f'Found {len(agents)} agents')

# Create zone and add service
result = client.create_zone(agents[0]['id'], 'web-dmz')
if result['success']:
    client.add_service_to_zone(agents[0]['id'], 'web-dmz', 'http')
```

### JavaScript
```javascript
class TuxSecClient {
  constructor(baseURL) {
    this.baseURL = baseURL;
  }

  async login(username, password) {
    const response = await fetch(`${this.baseURL}/users/login/`, {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: `username=${username}&password=${password}`,
      credentials: 'include'
    });
    return response.json();
  }

  async listAgents() {
    const response = await fetch(`${this.baseURL}/agents/api/agents/`, {
      credentials: 'include'
    });
    return response.json();
  }

  async createZone(agentId, zoneName, target = 'default') {
    const response = await fetch(
      `${this.baseURL}/agents/${agentId}/zone/create/`,
      {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name: zoneName, target}),
        credentials: 'include'
      }
    );
    return response.json();
  }
}

// Usage
const client = new TuxSecClient('http://localhost:8001');
await client.login('admin', 'password');
const agents = await client.listAgents();
console.log(`Found ${agents.length} agents`);
```

---

## Support

For additional help:
- **Documentation:** [FEATURES.md](FEATURES.md)
- **Project README:** [README.md](README.md)
- **Issues:** File issues on project repository
- **Logs:** Check `/var/log/tuxsec/` for detailed logs

**Version:** 1.0.0  
**Last Updated:** 2024-01-15
