# Firewall Service Control TODO

## Feature Request: Add Firewalld Service Start/Stop Controls

### Overview
Add the ability to start and stop the firewalld service directly from the module management interface in the web UI.

### Requirements

#### Backend (Agent Module)
- [ ] Add `start_service` action to firewalld module
  - Command: `systemctl start firewalld`
  - Return success/failure status
  
- [ ] Add `stop_service` action to firewalld module
  - Command: `systemctl stop firewalld`
  - Return success/failure status
  
- [ ] Add `restart_service` action to firewalld module
  - Command: `systemctl restart firewalld`
  - Return success/failure status
  
- [ ] Add `service_status` action to get current service state
  - Command: `systemctl is-active firewalld`
  - Return: active/inactive/failed status

#### Web UI (Module Interface)
- [ ] Add service control buttons to module card
  - Start button (when service is stopped)
  - Stop button (when service is running)
  - Restart button (always available)
  
- [ ] Display current service status badge
  - Green: Active/Running
  - Red: Inactive/Stopped
  - Yellow: Failed/Unknown
  
- [ ] Add confirmation dialog for stop/restart actions
  - Warning message about potential connectivity loss
  - Require explicit confirmation
  
- [ ] Update service status automatically
  - Refresh status after any service action
  - Poll status periodically (every 30 seconds)
  
- [ ] Add audit logging for service control actions
  - Log who started/stopped the service
  - Log timestamp and result
  - Log any errors

#### Connection Manager Integration
- [ ] Add `control_service` method to connection managers
  - Support SSH, agent, and local connection types
  - Handle async execution properly
  
- [ ] Handle service state changes gracefully
  - Update agent status when firewall is stopped
  - Show warning when firewall is stopped
  - Disable zone management when firewall is inactive

### UI Mockup

```
┌─────────────────────────────────────────────────────┐
│ Module: Firewalld Firewall                         │
│                                                     │
│ Status: ● Active                                    │
│                                                     │
│ [Restart Service] [Stop Service]                   │
│                                                     │
│ Enabled on 5 agents                                 │
│ - kessel.outerrim.lan                              │
│ - tatooine.outerrim.lan                            │
│ ...                                                │
└─────────────────────────────────────────────────────┘
```

### Security Considerations
- [ ] Ensure only authenticated users can control services
- [ ] Add permission check (admin/superuser only?)
- [ ] Log all service control attempts
- [ ] Rate limit service control actions
- [ ] Add timeout for service operations (max 30 seconds)

### Testing Checklist
- [ ] Test start action on stopped firewall
- [ ] Test stop action on running firewall
- [ ] Test restart action
- [ ] Test status polling
- [ ] Test error handling (permission denied, service not found)
- [ ] Test concurrent operations (prevent multiple simultaneous actions)
- [ ] Test on different connection types (SSH, agent, local)

### Implementation Priority
Priority: Medium-High

This feature is important for operational management and troubleshooting, allowing administrators to quickly restart or temporarily stop the firewall service without SSH access.

### Estimated Effort
- Backend agent module: 2-3 hours
- Web UI integration: 3-4 hours
- Testing and debugging: 2 hours
- Total: 7-9 hours

### Related Files
- `agent/rootd/modules/firewalld.py` - Add service control actions
- `web_ui/modules/firewalld/module.py` - Module interface
- `web_ui/agents/connection_managers.py` - Add control_service method
- `web_ui/templates/modules/module_detail.html` - Add UI controls (create if needed)
- `web_ui/static/js/module_controls.js` - Add JavaScript for service controls (create if needed)

### Notes
- Consider adding this to other service-based modules (sshd, network-manager, etc.)
- Could be generalized into a "Service Control" mixin for all systemd services
- Should handle cases where systemd is not available (non-systemd systems)
