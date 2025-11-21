# AIDE File Integrity Module

## Overview
The AIDE (Advanced Intrusion Detection Environment) module provides comprehensive file integrity monitoring and intrusion detection capabilities. It creates a database of file attributes and can detect unauthorized changes to system files.

## Features
- **File Integrity Monitoring**: Track changes to critical system files
- **Intrusion Detection**: Detect unauthorized modifications
- **Flexible Rule System**: Define what to monitor for each path
- **Change Detection**: Monitor permissions, ownership, timestamps, checksums, and more
- **Database Management**: Initialize, update, backup, and restore integrity databases
- **Historical Tracking**: Maintain history of integrity checks and changes
- **Customizable Monitoring**: Add/remove paths and configure check rules

## Required Packages
- `aide` - Advanced Intrusion Detection Environment

## Available Actions

### Database Management
- **initialize_database**: Initialize AIDE database (required for first-time setup)
  - Creates baseline database of current system state
- **update_database**: Update database with current system state
  - Updates baseline after verified system changes
- **get_database_info**: Get information about current database
  - Shows database version, creation date, file count

### Scanning and Checking
- **check_integrity**: Run full integrity check against database
  - Compares current system state to database
  - Reports all detected changes
- **compare_databases**: Compare two database versions
  - Parameters: `old_db` (string), `new_db` (string)
- **quick_check**: Quick check of critical system paths only
  - Faster check of /bin, /sbin, /etc, /boot

### Configuration
- **get_config**: Retrieve current AIDE configuration
- **set_config**: Update AIDE configuration settings
  - Parameters: `key` (string), `value` (string)
- **add_watch_path**: Add a path to monitor
  - Parameters: `path` (string), `rules` (optional)
- **remove_watch_path**: Remove a path from monitoring
  - Parameters: `path` (string)
- **list_watch_paths**: List all currently monitored paths
- **set_check_rules**: Set integrity check rules for a specific path
  - Parameters: `path` (string), `rules` (string)

### Reporting
- **get_last_check_report**: Get detailed report from last integrity check
- **get_check_history**: Get history of all integrity checks with summaries
- **get_changes_summary**: Get summary of changes detected
  - Groups changes by type (added, removed, modified)
- **export_report**: Export integrity report to file
  - Parameters: `filename` (string), `format` (optional: text/html/json)

### Database Backup/Restore
- **backup_database**: Create backup of current database
  - Parameters: `name` (optional) - Backup identifier
- **restore_database**: Restore database from backup
  - Parameters: `backup_id` (string)
- **list_backups**: List all available database backups

### Advanced Operations
- **verify_config**: Verify AIDE configuration syntax
- **get_statistics**: Get statistics about monitored files
  - Total files, directories, total size, etc.
- **reset_baseline**: Reset baseline (reinitialize database)
  - Use after verified system changes to create new baseline

## Check Rules
AIDE uses rule strings to define what to monitor for each path. Common rule flags:

- `p` - Permissions
- `i` - Inode
- `n` - Number of links
- `u` - User (owner)
- `g` - Group
- `s` - Size
- `b` - Block count
- `m` - Modification time
- `a` - Access time
- `c` - Creation time
- `md5` - MD5 checksum
- `sha256` - SHA256 checksum
- `sha512` - SHA512 checksum

### Default Rules for Critical Paths
```
/bin:      p+i+n+u+g+s+b+m+c+md5+sha256
/sbin:     p+i+n+u+g+s+b+m+c+md5+sha256
/usr/bin:  p+i+n+u+g+s+b+m+c+md5+sha256
/usr/sbin: p+i+n+u+g+s+b+m+c+md5+sha256
/etc:      p+i+n+u+g+s+b+m+c+md5+sha256
/boot:     p+i+n+u+g+s+b+m+c+md5+sha256
```

## Usage Examples

### Initial Setup
```python
# Initialize database (first time)
module.execute_action("initialize_database", {})

# Verify configuration
module.execute_action("verify_config", {})
```

### Run Integrity Check
```python
# Full integrity check
result = module.execute_action("check_integrity", {})

# Quick check of critical paths only
result = module.execute_action("quick_check", {})
```

### Add Custom Monitoring
```python
# Add a path with custom rules
module.execute_action("add_watch_path", {
    "path": "/opt/myapp",
    "rules": "p+i+n+u+g+s+md5+sha256"
})

# List all monitored paths
paths = module.execute_action("list_watch_paths", {})
```

### After System Changes
```python
# Update database after verified changes
module.execute_action("update_database", {})

# Or reset baseline completely
module.execute_action("reset_baseline", {})
```

### Review Changes
```python
# Get last check report
report = module.execute_action("get_last_check_report", {})

# Get summary of changes
summary = module.execute_action("get_changes_summary", {})
```

## Change Detection Types
AIDE can detect the following types of changes:
- Added files (new files not in database)
- Removed files (files in database but missing)
- Modified files (content changes)
- Permission changes
- Ownership changes (user/group)
- Timestamp changes (mtime, atime, ctime)
- Size changes
- Checksum changes (MD5, SHA256, SHA512)
- Inode changes
- Link changes (symlinks, hardlinks)

## Best Practices
1. **Initialize After Clean Install**: Run initial database creation on a known-good system
2. **Regular Checks**: Schedule daily or weekly integrity checks
3. **Update After Changes**: Update database after legitimate system updates
4. **Backup Databases**: Regularly backup AIDE databases
5. **Monitor Critical Paths**: Always monitor /bin, /sbin, /etc, /boot, /usr/bin, /usr/sbin
6. **Exclude Dynamic Paths**: Don't monitor /tmp, /var/tmp, /var/log (too many changes)
7. **Use Appropriate Rules**: Use checksums for executables, simpler rules for config files
8. **Review All Changes**: Investigate any unexpected changes immediately

## Configuration Files
- `/etc/aide.conf` - Main AIDE configuration
- `/var/lib/aide/aide.db` - Current integrity database
- `/var/lib/aide/aide.db.new` - Updated database (before replacement)
- `/var/log/aide/` - AIDE logs and reports

## Notes
- Initial database creation can take significant time on large systems
- Integrity checks can be I/O intensive
- Database updates should only be done after verifying system changes are legitimate
- Store database backups on secure, separate systems
- Consider using `--config-check` to verify configuration before running checks
