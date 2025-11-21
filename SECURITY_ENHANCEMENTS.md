# TuxSec Agent - Security Enhancement Recommendations

This document outlines security enhancements identified during architecture review of the TuxSec agent v2.0 design. The agent uses a privilege-separated architecture with a root daemon (tuxsec-rootd) and unprivileged userspace agent (tuxsec-agent) communicating via Unix socket.

## Current Security Posture

**Strengths:**
- Privilege separation between root daemon and userspace agent
- No arbitrary command execution - only predefined module actions
- Unix socket with restricted permissions (0660 root:tuxsec)
- Modular architecture with capability declaration
- Input validation at protocol level

**Areas for Enhancement:**
The following recommendations are categorized by priority and impact.

---

## Critical Priority

### 1. Rate Limiting on Unix Socket
**Risk:** DoS attack through rapid connection attempts to rootd socket  
**Current State:** No rate limiting implemented  
**Recommendation:**
- Implement per-UID rate limiting in rootd daemon
- Limit connections per second per user (e.g., 10/second)
- Track connection attempts and reject excessive rates
- Log rate limit violations

**Implementation Location:** `agent/rootd/daemon.py` - `_handle_client()` method

### 2. Command Audit Logging
**Risk:** Insufficient forensic trail for privileged operations  
**Current State:** General application logging only  
**Recommendation:**
- Create dedicated immutable audit log for all rootd commands
- Log: timestamp, connecting UID/GID, module, action, parameters (sanitized), result status
- Store in `/var/log/audit/tuxsec.log` with append-only permissions
- Integrate with system audit framework (auditd) where available
- Rotate audit logs with retention policy

**Implementation Location:** `agent/rootd/daemon.py` - `_process_message()` method

### 3. Input Validation Hardening
**Risk:** Malformed or malicious input causing unexpected behavior  
**Current State:** Basic JSON parsing and Message validation  
**Recommendation:**
- Add JSON schema validation for all message types
- Enforce maximum message size (e.g., 1MB)
- Validate parameter types, ranges, and formats before module execution
- Implement allowlist-based parameter validation per module action
- Reject messages with unexpected fields

**Implementation Location:** 
- `agent/rootd/protocol.py` - Add schema validation
- `agent/rootd/base_module.py` - Add parameter validation framework

### 4. Socket Connection Authentication
**Risk:** Insufficient verification of connecting process identity  
**Current State:** Only Unix socket permissions (mode 0660)  
**Recommendation:**
- Implement SO_PEERCRED to get connecting process UID/GID/PID
- Verify connecting process is owned by tuxsec user
- Reject connections from unexpected UIDs
- Log connection attempts with credential information
- Consider adding process name verification

**Implementation Location:** `agent/rootd/daemon.py` - `_handle_client()` method

```python
# Example implementation:
import socket, struct
SO_PEERCRED = 17
creds = client_socket.getsockopt(socket.SOL_SOCKET, SO_PEERCRED, struct.calcsize('3i'))
pid, uid, gid = struct.unpack('3i', creds)
# Verify uid matches tuxsec user
```

### 5. Module Capability Restrictions
**Risk:** Modules executing actions outside their declared capabilities  
**Current State:** Modules declare capabilities but no enforcement  
**Recommendation:**
- Implement capability-based access control in ModuleRegistry
- Verify requested action is in module's declared capabilities before execution
- Reject execution of undeclared actions with security event log
- Add capability versioning for future changes

**Implementation Location:** `agent/rootd/base_module.py` - `ModuleRegistry.execute_command()`

---

## High Priority

### 6. Timeout Enforcement
**Risk:** Hung operations preventing daemon from serving other requests  
**Current State:** No timeout on command execution  
**Recommendation:**
- Implement per-command timeout (configurable, default 60s)
- Use threading.Timer or asyncio.timeout
- Kill operations exceeding timeout
- Return timeout error to caller
- Log timeout events for monitoring

**Implementation Location:** `agent/rootd/daemon.py` - `_process_message()` for EXECUTE_COMMAND

### 7. TLS Certificate Validation Enhancement
**Risk:** MitM attacks in pull/push modes  
**Current State:** HTTPS used but basic validation  
**Recommendation:**
- Implement certificate pinning for server certificate
- Require mutual TLS (client certificate) in push mode
- Validate certificate chain completely
- Check certificate revocation (OCSP/CRL)
- Add certificate expiry monitoring/alerting

**Implementation Location:** `agent/userspace/agent.py` - HTTP client configuration

### 8. Secrets Management
**Risk:** API keys exposed if filesystem compromised  
**Current State:** Plain text in agent.yaml (mode 0640)  
**Recommendation:**
- Support secrets from environment variables
- Integrate with systemd credentials (LoadCredential)
- Support HashiCorp Vault or similar secret managers
- Encrypt sensitive config values at rest
- Implement secure key rotation mechanism

**Implementation Location:** `agent/userspace/agent.py` - `AgentConfig` class

### 9. Memory Safety for Sensitive Data
**Risk:** Secrets lingering in memory after use  
**Current State:** Standard Python string handling  
**Recommendation:**
- Use secure string handling for API keys and credentials
- Explicitly zero sensitive data after use (if possible in Python)
- Limit sensitive data lifetime in memory
- Consider using ctypes to allocate/wipe secure memory regions

**Implementation Location:** Throughout codebase where credentials are handled

### 10. SELinux Policy Hardening
**Risk:** Overly permissive SELinux policy reducing defense in depth  
**Current State:** Basic policy with broad permissions (dac_override)  
**Recommendation:**
- Create specific file contexts for all TuxSec files
- Limit dac_override capability to specific files/operations
- Add explicit deny rules for unexpected access patterns
- Separate policies for rootd vs agent contexts
- Use SELinux booleans for optional features
- Add file transition rules

**Implementation Location:** `agent/selinux/tuxsec.te` and `.fc` files

---

## Medium Priority

### 11. Connection Limiting
**Risk:** Resource exhaustion from too many concurrent connections  
**Current State:** No connection limit  
**Recommendation:**
- Limit concurrent connections to rootd (e.g., 10)
- Queue additional connections or reject with error
- Make limit configurable
- Monitor connection queue depth

**Implementation Location:** `agent/rootd/daemon.py` - socket accept loop

### 12. Command Result Size Limits
**Risk:** Memory exhaustion from large module responses  
**Current State:** No size limits on responses  
**Recommendation:**
- Enforce maximum response size (e.g., 10MB)
- Stream large results instead of buffering in memory
- Add response size to metrics/monitoring
- Implement chunked response protocol for large data

**Implementation Location:** `agent/rootd/daemon.py` - response handling

### 13. Process Isolation with Systemd
**Risk:** Insufficient process sandboxing  
**Current State:** Basic systemd services  
**Recommendation:**
- Add systemd hardening directives:
  - `PrivateTmp=yes`
  - `ProtectSystem=strict`
  - `ProtectHome=yes`
  - `ReadOnlyPaths=/`
  - `ReadWritePaths=/var/log/tuxsec /var/run/tuxsec`
  - `NoNewPrivileges=yes`
  - `ProtectKernelTunables=yes`
  - `ProtectControlGroups=yes`
- Consider seccomp filters to restrict syscalls
- Use CapabilityBoundingSet to limit capabilities

**Implementation Location:** `agent/systemd/*.service` files

### 14. Replay Attack Protection
**Risk:** Replay of captured messages  
**Current State:** UUID request_id but no uniqueness validation  
**Recommendation:**
- Track recently seen request_ids in memory (last N minutes)
- Reject duplicate request_ids
- Add timestamp to messages and reject old messages
- Implement nonce-based challenge-response for sensitive operations

**Implementation Location:** `agent/rootd/daemon.py` - message processing

### 15. Module Restrictions by Connection Mode
**Risk:** Unnecessary capabilities exposed in different connection modes  
**Current State:** All modules available in all modes  
**Recommendation:**
- Configuration to restrict modules by connection mode
- Example: SSH mode allows only read-only operations
- Pull mode allows all operations
- Push mode requires extra authentication for write operations
- Document security model for each mode

**Implementation Location:** `agent/userspace/agent.py` - mode-specific execution

---

## Low Priority

### 16. Logging Sanitization
**Risk:** Sensitive data in log files  
**Current State:** Parameters logged as-is  
**Recommendation:**
- Identify sensitive parameter names (password, key, token, secret)
- Redact or hash sensitive values in logs
- Add configuration for additional sensitive field names
- Maintain security event log separate from debug logs

**Implementation Location:** Throughout logging statements

### 17. Graceful Degradation
**Risk:** Agent failure if rootd becomes unresponsive  
**Current State:** Simple connection check  
**Recommendation:**
- Implement circuit breaker pattern for rootd connections
- Health check with automatic retry and backoff
- Queue commands during temporary outages
- Alert on extended rootd unavailability

**Implementation Location:** `agent/userspace/rootd_client.py`

### 18. Forensics Support
**Risk:** Limited command history for incident investigation  
**Current State:** Logs but no structured history  
**Recommendation:**
- Optional command recording mode
- Store full command history with results in structured format
- Implement command history query API
- Add tamper detection for history records

**Implementation Location:** New module or feature in rootd

### 19. Module Code Signing
**Risk:** Module files tampered with on filesystem  
**Current State:** No integrity verification  
**Recommendation:**
- Sign module Python files during build/installation
- Verify signatures before loading modules
- Use GPG or similar signing mechanism
- Reject unsigned or invalid modules

**Implementation Location:** `agent/rootd/base_module.py` - module loading

### 20. Network Namespace Isolation
**Risk:** Push mode listener exposed to network attacks  
**Current State:** Listens on configured interface  
**Recommendation:**
- Run push mode listener in separate network namespace
- Use systemd PrivateNetwork or manual netns setup
- Expose only necessary ports through firewall
- Consider using Unix socket with socat/proxy for network exposure

**Implementation Location:** `agent/systemd/tuxsec-agent.service` for push mode

---

## Defense in Depth Recommendations

### 21. Fail-Safe Defaults
- Add explicit deny rules for undefined module actions
- Default to minimum privilege on any error condition
- Return error rather than continue with partial validation
- Implement positive security model (allowlist vs blocklist)

### 22. Security Headers in Push Mode
- Implement request rate limiting per source IP
- Enforce maximum request size
- Add CORS restrictions
- Implement request signing/HMAC verification
- Add strict TLS configuration (TLS 1.3 only, strong ciphers)

### 23. Principle of Least Privilege Audit
- Review all operations requiring dac_override
- Consider running rootd with capabilities instead of full root:
  - CAP_NET_ADMIN (for firewalld)
  - CAP_DAC_READ_SEARCH (for reading protected files)
  - Drop other capabilities
- Document minimum privilege requirements per module

### 24. Session Management
- Implement session tokens for multi-request conversations
- Add session timeout (idle and absolute)
- Support session revocation
- Track active sessions per connection mode

---

## Implementation Priority Matrix

| Priority | Security Impact | Implementation Effort | ROI |
|----------|----------------|----------------------|-----|
| 1-5 (Critical) | High | Medium | High |
| 6-10 (High) | Medium-High | Medium-High | Medium-High |
| 11-15 (Medium) | Medium | Low-Medium | Medium |
| 16-20 (Low) | Low-Medium | Low-High | Variable |

## Recommended Implementation Order

**Phase 1 (Critical Security Baseline):**
1. Socket connection authentication (#4)
2. Command audit logging (#2)
3. Input validation hardening (#3)
4. Module capability restrictions (#5)
5. Rate limiting (#1)

**Phase 2 (Operational Hardening):**
6. Timeout enforcement (#6)
7. TLS certificate validation (#7)
8. Secrets management (#8)
9. SELinux policy hardening (#10)

**Phase 3 (Defense in Depth):**
10. Connection limiting (#11)
11. Process isolation (#13)
12. Replay attack protection (#14)
13. Logging sanitization (#16)

**Phase 4 (Advanced Features):**
14. Module restrictions by mode (#15)
15. Graceful degradation (#17)
16. Additional low priority items as needed

---

## Testing Recommendations

For each enhancement, implement:
1. Unit tests for new validation/security logic
2. Integration tests for end-to-end flows
3. Security-specific tests (fuzzing, boundary conditions)
4. Performance tests (especially for rate limiting, timeouts)
5. Penetration testing after major security changes

## Monitoring & Alerting

Implement monitoring for:
- Failed authentication attempts
- Rate limit violations
- Timeout events
- Certificate validation failures
- Unusual command patterns
- Security event audit log growth
- Connection queue depth

## Documentation Updates

Update documentation to include:
- Security architecture diagram
- Threat model
- Security configuration best practices
- Incident response procedures
- Security audit procedures

---

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CIS Benchmarks](https://www.cisecurity.org/cis-benchmarks/)
- [SELinux Project](https://github.com/SELinuxProject)
- [systemd Security Hardening](https://www.freedesktop.org/software/systemd/man/systemd.exec.html)

## Review History

- 2025-11-21: Initial security review and recommendations
- Next review: After Phase 1 implementation

---

**Note:** This document should be reviewed and updated as security enhancements are implemented and as new threats are identified.
