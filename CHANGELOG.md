# Changelog

All notable changes to TuxSec Agent will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.4] - 2025-11-21

### Added
- 

### Changed
- 

### Fixed
- 

### Security
- 

## [0.1.3] - 2025-11-21

### Added
- 

### Changed
- 

### Fixed
- 

### Security
- 

## [0.1.2] - 2025-11-21

### Added
- 

### Changed
- 

### Fixed
- 

### Security
- 

## [0.1.1] - 2025-11-21

### Added
- 

### Changed
- 

### Fixed
- 

### Security
- 

## [0.1.0] - 2025-11-21

### Added
- **Complete agent redesign** with two-component architecture for enhanced security
  - Root daemon (`tuxsec-rootd`) running as root with minimal privileges
  - Userspace agent (`tuxsec-agent`) running as unprivileged `tuxsec` user
  - Unix domain socket IPC for secure inter-process communication
- **Modular plugin system** for extending agent capabilities
  - `BaseModule` abstract class for creating new modules
  - `ModuleRegistry` for dynamic module loading and management
  - Built-in system info module (hostname, OS info, uptime)
  - Firewalld module for firewall management (optional package)
- **Three connection modes** for flexible deployment
  - **Pull mode**: Agent polls TuxSec server for commands
  - **Push mode**: Agent listens for connections from TuxSec server
  - **SSH mode**: Server executes commands via SSH (stateless)
- **CLI tool** (`tuxsec-cli`) for local management and SSH mode execution
  - Execute module actions directly
  - Query system information
  - List available modules and capabilities
- **Interactive setup wizard** (`tuxsec-setup`) for easy configuration
  - Mode selection (pull/push/SSH)
  - SSL certificate configuration
  - Server connection settings
  - Colored output for better UX
- **RPM packaging** with split packages
  - `tuxsec-agent`: Base package with daemon, agent, CLI, setup
  - `tuxsec-agent-firewalld`: Firewall management module
  - `tuxsec-agent-selinux`: SELinux policy module
- **SELinux policy** for proper security contexts
  - Custom types: `tuxsec_rootd_t`, `tuxsec_agent_t`, `tuxsec_var_run_t`
  - File contexts for executables, configs, logs, sockets
  - Policy interfaces for module integration
- **Systemd service files** with security hardening
  - `tuxsec-rootd.service`: Root daemon service
  - `tuxsec-agent.service`: Userspace agent service with `DynamicUser` option
- **Comprehensive documentation**
  - Architecture guide (ARCHITECTURE.md)
  - Packaging guide (PACKAGING.md)
  - Quick reference card (QUICKREF.md)
  - Migration guide (MIGRATION.md)
- **Build automation** with Makefile
  - `make rpm`: Build all RPM packages
  - `make selinux`: Build SELinux policy
  - `make all`: Complete build process

### Changed
- **Agent folder restructure**: `tuxsec_agent/` renamed to `agent/`
- **Improved security model** with privilege separation
- **Enhanced logging** with structured output and log rotation
- **Better error handling** with detailed error messages

### Security
- Unix domain socket restricted to `root:tuxsec` with 0660 permissions
- Userspace agent runs as unprivileged user
- SELinux mandatory access control policies
- SSL/TLS certificate validation for server connections
- API key authentication

### Deprecated
- Legacy agent implementations (will be removed in 3.0.0)

## [1.0.0] - 2024-XX-XX

### Added
- Initial release
- Basic firewalld agent with SSH connectivity
- HTTP-based agent with polling
- Django web UI for agent management
- FastAPI server for agent communication
- Agent registration and authentication

---

[Unreleased]: https://github.com/MrMEEE/tuxsec/compare/v0.1.4...HEAD
[0.1.4]: https://github.com/MrMEEE/tuxsec/releases/tag/v0.1.4
[0.1.3]: https://github.com/MrMEEE/tuxsec/releases/tag/v0.1.3
[0.1.2]: https://github.com/MrMEEE/tuxsec/releases/tag/v0.1.2
[0.1.1]: https://github.com/MrMEEE/tuxsec/releases/tag/v0.1.1
[0.1.0]: https://github.com/MrMEEE/tuxsec/releases/tag/v0.1.0
