# Module Detection Deployment Guide

## What's New

The system now detects which TuxSec module packages are installed on each agent and displays warnings in the web interface when a globally-enabled module is missing from an agent.

## Changes Made

### Agent Side (Requires RPM rebuild and deployment)

1. **systeminfo module** (`agent/rootd/modules/systeminfo.py`):
   - Added `list_modules` action that queries RPM for `tuxsec-agent-*` packages
   - Returns list of installed module names (e.g., `['systeminfo', 'firewalld']`)

2. **RootDaemon Client** (`agent/userspace/rootd_client.py`):
   - Added `list_installed_modules()` method to query installed modules

3. **CLI** (`agent/userspace/cli.py`):
   - Added `installed-modules` command that outputs JSON list of installed modules
   - Usage: `tuxsec-cli installed-modules` → `{"modules": ["systeminfo", "firewalld"]}`

### Server Side (Already deployed)

1. **Agent Model** (`web_ui/agents/models.py`):
   - Added `installed_modules` JSONField to store list of installed module packages
   - Migration `0009_add_installed_modules.py` created and applied

2. **SSH Connection Manager** (`web_ui/agents/connection_managers.py`):
   - Now calls `tuxsec-cli installed-modules` during connection test
   - Stores result in `agent.installed_modules`

3. **Agent Detail View** (`web_ui/agents/views.py`):
   - Compares globally-enabled modules with agent's installed modules
   - Sets `available=False` and adds error message for missing modules

4. **Agent Detail Template** (`web_ui/templates/dashboard/agent_detail.html`):
   - Shows "Not Installed" badge for missing modules
   - Displays installation command: `dnf install tuxsec-agent-{module}`
   - Disables toggle switch for non-installed modules

## Deployment Steps

### 1. Build New Agent RPM

```bash
cd /home/mj/Ansible/tuxsec
# Update version in spec file if needed
make rpm
```

### 2. Deploy to Agents

```bash
# Copy RPM to agent
scp build/rpmbuild/RPMS/*/tuxsec-agent-0.1.10-*.rpm user@agent:/tmp/

# Install on agent
ssh user@agent
sudo dnf update /tmp/tuxsec-agent-0.1.10-*.rpm

# Restart services
sudo systemctl restart tuxsec-rootd
sudo systemctl restart tuxsec-agent  # if using pull/push mode
```

### 3. Test on Agent

```bash
# Test the new command
tuxsec-cli installed-modules

# Expected output:
# {"modules": ["systeminfo"]}

# If firewalld module is installed:
# {"modules": ["systeminfo", "firewalld"]}
```

### 4. Trigger Sync

The next scheduled sync (every 3 seconds for your test agent) will automatically:
1. Query installed modules using `tuxsec-cli installed-modules`
2. Update the agent's `installed_modules` field
3. Update module availability status

Or manually trigger:
```bash
cd /home/mj/Ansible/tuxsec/web_ui
../.venv/bin/python manage.py sync_agents
```

### 5. Verify in Web UI

1. Go to agent detail page
2. Check the "Modules" section
3. If firewalld is enabled globally but not installed on agent, you should see:
   - **Firewalld** 🔴 Not Installed
   - Error message: "Module package 'tuxsec-agent-firewalld' not installed"
   - Install command: `dnf install tuxsec-agent-firewalld`
   - Toggle switch will be disabled

## Example Scenarios

### Scenario 1: Module enabled globally but not installed on agent
- **Server**: firewalld module enabled globally
- **Agent**: Only has `tuxsec-agent` base package (systeminfo only)
- **Result**: Module shows as "Not Installed" with red badge, toggle disabled

### Scenario 2: Module installed and available
- **Server**: firewalld module enabled globally  
- **Agent**: Has both `tuxsec-agent` and `tuxsec-agent-firewalld` packages
- **Result**: Module shows normally, toggle can be used to enable/disable

### Scenario 3: Module not enabled globally
- **Server**: firewalld module disabled globally
- **Agent**: Has firewalld module installed
- **Result**: Module doesn't appear in agent's module list (only globally-enabled modules shown)

## Testing

Test the full workflow:

```bash
# 1. Enable firewalld module globally (if not already)
# Go to Settings → Modules → enable Firewalld

# 2. Check agent without firewalld module installed
# Should show "Not Installed" badge

# 3. Install firewalld module on agent
ssh tuxsec@agent
sudo dnf install tuxsec-agent-firewalld

# 4. Wait for next sync or trigger manually
cd /home/mj/Ansible/tuxsec/web_ui
../.venv/bin/python manage.py sync_agents

# 5. Refresh agent detail page
# Module should now show as available
```

## Troubleshooting

### Module still shows as "Not Installed" after installing package

1. Verify package is actually installed:
   ```bash
   ssh tuxsec@agent "rpm -qa | grep tuxsec-agent"
   ```

2. Test CLI command:
   ```bash
   ssh tuxsec@agent "tuxsec-cli installed-modules"
   ```

3. Check if sync is running:
   ```bash
   ps aux | grep sync_agents
   ```

4. Manually trigger sync and check output:
   ```bash
   cd /home/mj/Ansible/tuxsec/web_ui
   ../.venv/bin/python manage.py sync_agents
   ```

### CLI command not found

Agent needs the updated RPM with the new CLI code. Rebuild and redeploy.

### Empty modules list

Check if RPM query works on agent:
```bash
ssh tuxsec@agent "rpm -qa --qf '%{NAME}\n' 'tuxsec-agent-*'"
```
