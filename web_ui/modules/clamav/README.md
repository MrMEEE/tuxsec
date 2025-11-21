# ClamAV Antivirus Module

## Overview
The ClamAV module provides comprehensive antivirus scanning and malware protection capabilities using the open-source ClamAV antivirus engine.

## Features
- **Virus Signature Updates**: Automatic and manual signature database updates
- **File & Directory Scanning**: On-demand scanning of files and directories
- **Real-time Protection**: On-access scanning for real-time threat detection
- **Daemon Management**: Control ClamAV daemon (clamd) service
- **Quarantine Management**: Isolate, restore, or delete infected files
- **Scan History**: Track scanning activities and results
- **Statistics**: Monitor detection rates and system protection status

## Required Packages
- `clamav` - Core ClamAV antivirus engine
- `clamav-daemon` - ClamAV daemon for scanning
- `clamav-freshclam` - Automatic signature update tool

## Available Actions

### Database Management
- **update_signatures**: Update virus signature database using freshclam
- **get_signature_version**: Get current signature database version and date

### Scanning Operations
- **scan_file**: Scan a specific file for malware
  - Parameters: `path` (string) - File path to scan
- **scan_directory**: Recursively scan a directory
  - Parameters: `path` (string) - Directory path to scan
- **quick_scan**: Quick scan of common locations (/home, /tmp, /var)
- **full_system_scan**: Full system scan (may take hours depending on disk size)

### Daemon Control
- **start_daemon**: Start the ClamAV daemon (clamd)
- **stop_daemon**: Stop the ClamAV daemon
- **restart_daemon**: Restart the ClamAV daemon
- **get_daemon_status**: Get daemon status, version, and runtime info

### Configuration
- **get_config**: Retrieve current ClamAV configuration
- **set_config**: Update ClamAV configuration settings
  - Parameters: `key` (string), `value` (string)
- **enable_on_access_scan**: Enable real-time on-access scanning
- **disable_on_access_scan**: Disable on-access scanning

### Quarantine Management
- **list_quarantine**: List all files currently in quarantine
- **restore_from_quarantine**: Restore a quarantined file to original location
  - Parameters: `file_id` (string) - Quarantine file identifier
- **delete_from_quarantine**: Permanently delete a quarantined file
  - Parameters: `file_id` (string) - Quarantine file identifier

### Statistics and Reporting
- **get_scan_history**: Retrieve history of recent scans with results
- **get_statistics**: Get scanning statistics (files scanned, threats found, etc.)
- **get_last_update**: Get timestamp of last signature database update

## Usage Examples

### Update Virus Signatures
```python
module.execute_action("update_signatures", {})
```

### Scan a Directory
```python
module.execute_action("scan_directory", {
    "path": "/home/user/Downloads"
})
```

### Enable Real-time Protection
```python
module.execute_action("enable_on_access_scan", {})
```

### Check Daemon Status
```python
status = module.get_status(agent_id)
print(f"Daemon running: {status['daemon_running']}")
print(f"Last update: {status['last_update']}")
```

## Configuration Files
- `/etc/clamav/clamd.conf` - Daemon configuration
- `/etc/clamav/freshclam.conf` - Update configuration
- `/var/lib/clamav/` - Signature database location

## Notes
- Full system scans can be resource-intensive and time-consuming
- On-access scanning requires kernel support and may impact performance
- Signature updates should be run regularly (daily recommended)
- Quarantine location is typically `/var/lib/clamav/quarantine/`
