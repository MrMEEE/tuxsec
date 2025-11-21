"""
AIDE (Advanced Intrusion Detection Environment) Module

Provides file integrity monitoring and intrusion detection capabilities.
"""

from typing import Dict, List, Any
from shared.modules.base import BaseModule, ModuleCapability, ModuleCommand, ModuleResult


class AIDEModule(BaseModule):
    """AIDE file integrity monitoring and intrusion detection module."""
    
    @property
    def name(self) -> str:
        return "aide"
    
    @property
    def display_name(self) -> str:
        return "AIDE File Integrity"
    
    @property
    def description(self) -> str:
        return "File integrity monitoring and intrusion detection using AIDE"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def capabilities(self) -> List[ModuleCapability]:
        return [
            ModuleCapability.FILE_INTEGRITY,
            ModuleCapability.INTRUSION_DETECTION,
        ]
    
    def get_required_packages(self) -> List[str]:
        """Return list of required system packages."""
        return ["aide"]
    
    def check_availability(self, agent_id: str) -> bool:
        """
        Check if AIDE is available on the agent.
        
        Args:
            agent_id: The ID of the agent to check
            
        Returns:
            True if AIDE is installed and available
        """
        # This would be implemented by the agent to check if aide is available
        return True
    
    def get_available_actions(self) -> List[str]:
        """Return list of available actions for this module."""
        return [
            # Database management
            "initialize_database",
            "update_database",
            "get_database_info",
            
            # Scanning and checking
            "check_integrity",
            "compare_databases",
            "quick_check",
            
            # Configuration
            "get_config",
            "set_config",
            "add_watch_path",
            "remove_watch_path",
            "list_watch_paths",
            "set_check_rules",
            
            # Reporting
            "get_last_check_report",
            "get_check_history",
            "get_changes_summary",
            "export_report",
            
            # Database backup/restore
            "backup_database",
            "restore_database",
            "list_backups",
            
            # Advanced operations
            "verify_config",
            "get_statistics",
            "reset_baseline",
        ]
    
    def execute_action(self, action: str, parameters: Dict[str, Any]) -> ModuleResult:
        """
        Execute an AIDE action.
        
        Args:
            action: The action to execute
            parameters: Action-specific parameters
            
        Returns:
            ModuleResult with execution outcome
        """
        command = ModuleCommand(
            module_name=self.name,
            action=action,
            parameters=parameters
        )
        
        # Actions would be executed by the agent
        # This is the interface definition
        
        return ModuleResult(
            success=True,
            message=f"AIDE action '{action}' queued for execution",
            data={"command": command.dict()}
        )
    
    def get_status(self, agent_id: str) -> Dict[str, Any]:
        """
        Get current AIDE status on an agent.
        
        Args:
            agent_id: The ID of the agent
            
        Returns:
            Dictionary containing status information
        """
        return {
            "database_initialized": None,  # Would be populated by agent
            "last_check": None,
            "last_update": None,
            "database_version": None,
            "watched_paths_count": None,
            "changes_detected": None,
            "last_check_duration": None,
        }
    
    def validate_parameters(self, action: str, parameters: Dict[str, Any]) -> bool:
        """
        Validate parameters for a specific action.
        
        Args:
            action: The action to validate parameters for
            parameters: The parameters to validate
            
        Returns:
            True if parameters are valid
        """
        if action in ["add_watch_path", "remove_watch_path"]:
            return "path" in parameters
        elif action == "set_config":
            return "key" in parameters and "value" in parameters
        elif action == "set_check_rules":
            return "path" in parameters and "rules" in parameters
        elif action in ["restore_database", "export_report"]:
            return "backup_id" in parameters or "filename" in parameters
        
        # Most actions don't require specific parameters
        return True
    
    def get_action_description(self, action: str) -> str:
        """Get human-readable description of an action."""
        descriptions = {
            "initialize_database": "Initialize AIDE database (first-time setup)",
            "update_database": "Update AIDE database with current system state",
            "get_database_info": "Get information about current database",
            "check_integrity": "Run full integrity check against database",
            "compare_databases": "Compare two database versions",
            "quick_check": "Quick check of critical system paths",
            "get_config": "Get current AIDE configuration",
            "set_config": "Update AIDE configuration settings",
            "add_watch_path": "Add a path to monitor for changes",
            "remove_watch_path": "Remove a path from monitoring",
            "list_watch_paths": "List all monitored paths",
            "set_check_rules": "Set integrity check rules for a path",
            "get_last_check_report": "Get report from last integrity check",
            "get_check_history": "Get history of integrity checks",
            "get_changes_summary": "Get summary of detected changes",
            "export_report": "Export integrity report to file",
            "backup_database": "Create backup of current database",
            "restore_database": "Restore database from backup",
            "list_backups": "List available database backups",
            "verify_config": "Verify AIDE configuration syntax",
            "get_statistics": "Get statistics about monitored files",
            "reset_baseline": "Reset baseline (reinitialize database)",
        }
        return descriptions.get(action, f"Execute {action}")
    
    def get_change_types(self) -> List[str]:
        """Get types of changes AIDE can detect."""
        return [
            "Added files",
            "Removed files",
            "Modified files",
            "Permission changes",
            "Ownership changes",
            "Timestamp changes",
            "Size changes",
            "Checksum changes",
            "Inode changes",
            "Link changes",
        ]
    
    def get_default_rules(self) -> Dict[str, str]:
        """Get default check rules for common paths."""
        return {
            "/bin": "p+i+n+u+g+s+b+m+c+md5+sha256",
            "/sbin": "p+i+n+u+g+s+b+m+c+md5+sha256",
            "/usr/bin": "p+i+n+u+g+s+b+m+c+md5+sha256",
            "/usr/sbin": "p+i+n+u+g+s+b+m+c+md5+sha256",
            "/lib": "p+i+n+u+g+s+b+m+c+md5+sha256",
            "/lib64": "p+i+n+u+g+s+b+m+c+md5+sha256",
            "/etc": "p+i+n+u+g+s+b+m+c+md5+sha256",
            "/boot": "p+i+n+u+g+s+b+m+c+md5+sha256",
        }
