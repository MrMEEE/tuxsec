from django.db import models
from django.contrib.auth.models import User
import uuid


class Agent(models.Model):
    CONNECTION_TYPES = [
        ('agent_to_server', 'Agent connects to Server'),
        ('server_to_agent', 'Server connects to Agent'),
        ('ssh', 'SSH Connection'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('offline', 'Offline'),
        ('online', 'Online'),
        ('error', 'Error'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hostname = models.CharField(max_length=255, unique=True)
    ip_address = models.GenericIPAddressField()
    port = models.IntegerField(default=8443)
    connection_type = models.CharField(max_length=20, choices=CONNECTION_TYPES, default='agent_to_server')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    last_seen = models.DateTimeField(null=True, blank=True)
    certificate = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # SSH connection fields
    ssh_username = models.CharField(max_length=100, blank=True, help_text="Username for SSH connections")
    ssh_private_key = models.TextField(blank=True, help_text="SSH private key content (PEM format)")
    ssh_password = models.CharField(max_length=255, blank=True, help_text="SSH password (use key-based auth when possible)")
    
    # Agent endpoint fields (for server_to_agent connections)
    agent_port = models.IntegerField(default=8444, help_text="Port where agent listens for connections")
    agent_api_key = models.CharField(max_length=255, blank=True, help_text="API key for agent authentication")
    
    # Position for whiteboard interface
    position_x = models.FloatField(default=0)
    position_y = models.FloatField(default=0)
    
    # Agent metadata
    version = models.CharField(max_length=50, blank=True)
    operating_system = models.CharField(max_length=100, blank=True)
    firewalld_version = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    
    # Auto-sync configuration
    sync_interval_seconds = models.IntegerField(
        default=60,
        help_text="Interval in seconds for automatic firewall configuration sync (0 to disable)"
    )
    last_sync = models.DateTimeField(null=True, blank=True, help_text="Last time firewall config was synced")
    
    # Available firewalld services on this agent
    available_services = models.JSONField(
        default=list,
        blank=True,
        help_text="List of available firewalld services on this agent"
    )
    
    # Available modules on this agent (v0.1.0+)
    available_modules = models.JSONField(
        default=list,
        blank=True,
        help_text="List of available modules (systeminfo, firewalld, selinux, aide, etc)"
    )
    
    # Installed module packages on this agent (v0.1.9+)
    installed_modules = models.JSONField(
        default=list,
        blank=True,
        help_text="List of installed TuxSec module packages (RPMs)"
    )
    
    # Firewall reload tracking
    firewall_reload_required = models.BooleanField(
        default=False,
        help_text="Whether firewall configuration changes need reload"
    )
    last_firewall_reload = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time firewall was reloaded"
    )
    
    class Meta:
        ordering = ['hostname']
    
    def __str__(self):
        return f"{self.hostname} ({self.ip_address})"
    
    @property
    def os_info(self):
        """Return formatted OS information"""
        if self.operating_system:
            return self.operating_system
        return "Unknown"
    
    def get_connection_endpoint(self):
        """Get the connection endpoint based on connection type"""
        if self.connection_type == 'server_to_agent':
            return f"{self.ip_address}:{self.agent_port}"
        elif self.connection_type == 'ssh':
            return f"{self.ssh_username}@{self.ip_address}:{self.port}"
        else:  # agent_to_server
            return f"Server listens for {self.hostname}"


# ============================================================================
# FIREWALL MODELS MOVED TO modules.firewalld
# ============================================================================
# All firewall-related models have been moved to the modules.firewalld Django app.
# Import them with: from modules.firewalld.models import FirewallZone, FirewallRule, etc.
# Models moved: FirewallZone, FirewallRule, CustomService, IPSet, FirewallPolicy,
#               FirewallTemplate, DirectRule
# ============================================================================


class AgentConnection(models.Model):
    """Represents a connection between two agents for network visualization."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='outgoing_connections')
    target_agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='incoming_connections')
    
    # Connection details
    source_port = models.CharField(max_length=20, blank=True)
    target_port = models.CharField(max_length=20, blank=True)
    protocol = models.CharField(max_length=10, blank=True)
    service = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    
    # Visual properties
    color = models.CharField(max_length=7, default='#007bff')  # Hex color
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        unique_together = ['source_agent', 'target_agent', 'source_port', 'target_port']
    
    def __str__(self):
        return f"{self.source_agent.hostname} -> {self.target_agent.hostname}"


class AgentCommand(models.Model):
    """Track commands sent to agents with module-based structure (v0.1.0+)."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('timeout', 'Timeout'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='commands')
    
    # New module-based structure (v0.1.0+)
    module = models.CharField(max_length=50, default='firewalld', blank=True, help_text="Module to execute (systeminfo, firewalld, etc)")
    action = models.CharField(max_length=50, blank=True, help_text="Action to perform (get_status, add_service, etc)")
    params = models.JSONField(default=dict, blank=True, help_text="Parameters for the action")
    
    # Legacy field for backward compatibility - stores "module.action"
    command_type = models.CharField(max_length=100, blank=True, help_text="Legacy: stores module.action")
    
    # Legacy field for backward compatibility
    parameters = models.JSONField(default=dict, blank=True, help_text="Legacy: use params instead")
    
    # Command execution tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    result = models.JSONField(null=True, blank=True, help_text="Command result from agent")
    error_message = models.TextField(blank=True)
    timeout = models.IntegerField(default=30, help_text="Timeout in seconds")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['agent', 'status']),
            models.Index(fields=['module', 'action']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.agent.hostname} - {self.module}.{self.action} - {self.status}"
    
    def save(self, *args, **kwargs):
        # Auto-populate command_type for backward compatibility
        if not self.command_type and self.module and self.action:
            self.command_type = f"{self.module}.{self.action}"
        
        # Auto-populate parameters for backward compatibility
        if not self.parameters and self.params:
            self.parameters = self.params
        
        super().save(*args, **kwargs)


class AuditLog(models.Model):
    """Generic audit log for all module operations across the system."""
    
    ACTION_CATEGORIES = [
        ('read', 'Read/Query'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('execute', 'Execute'),
        ('configure', 'Configure'),
    ]
    
    SEVERITY_LEVELS = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Who
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                            help_text="User who performed the action")
    username = models.CharField(max_length=150, help_text="Username (preserved if user deleted)")
    ip_address = models.GenericIPAddressField(null=True, blank=True, 
                                             help_text="IP address of the user")
    
    # Where
    agent = models.ForeignKey(Agent, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name='audit_logs',
                             help_text="Agent where action was performed (null for system-wide actions)")
    agent_hostname = models.CharField(max_length=255, blank=True,
                                     help_text="Agent hostname (preserved if agent deleted)")
    
    # What
    module = models.CharField(max_length=50, help_text="Module name (firewalld, selinux, aide, systeminfo, etc)")
    action = models.CharField(max_length=100, help_text="Action performed (add_service, create_zone, etc)")
    action_category = models.CharField(max_length=20, choices=ACTION_CATEGORIES, default='execute',
                                      help_text="Category of action for filtering")
    
    # Details
    params = models.JSONField(default=dict, help_text="Parameters used in the action")
    result = models.JSONField(null=True, blank=True, help_text="Result of the action")
    success = models.BooleanField(help_text="Whether the action succeeded")
    error_message = models.TextField(blank=True, help_text="Error message if action failed")
    
    # Context
    description = models.TextField(blank=True, help_text="Human-readable description of the action")
    severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS, default='info',
                               help_text="Severity level of the action")
    
    # Associated command (if executed via AgentCommand)
    command = models.ForeignKey(AgentCommand, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='audit_logs')
    
    # Changes tracking (for update/delete operations)
    before_state = models.JSONField(null=True, blank=True, 
                                   help_text="State before the action (for updates/deletes)")
    after_state = models.JSONField(null=True, blank=True,
                                  help_text="State after the action (for creates/updates)")
    
    # When
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Metadata
    session_id = models.CharField(max_length=100, blank=True, 
                                 help_text="Session ID for grouping related actions")
    tags = models.JSONField(default=list, blank=True,
                          help_text="Custom tags for categorization")
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['agent', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['module', 'action', '-timestamp']),
            models.Index(fields=['action_category', '-timestamp']),
            models.Index(fields=['success', '-timestamp']),
            models.Index(fields=['severity', '-timestamp']),
            models.Index(fields=['-timestamp']),  # For general browsing
        ]
        verbose_name = "Audit Log Entry"
        verbose_name_plural = "Audit Logs"
    
    def __str__(self):
        agent_str = self.agent_hostname or "System"
        status = "✓" if self.success else "✗"
        return f"{status} {self.timestamp.strftime('%Y-%m-%d %H:%M')} | {self.username} | {agent_str} | {self.module}.{self.action}"
    
    def save(self, *args, **kwargs):
        # Auto-populate hostname from agent if available
        if self.agent and not self.agent_hostname:
            self.agent_hostname = self.agent.hostname
        
        # Auto-populate username from user if available
        if self.user and not self.username:
            self.username = self.user.username
        
        # Generate description if not provided
        if not self.description:
            self.description = self._generate_description()
        
        super().save(*args, **kwargs)
    
    def _generate_description(self) -> str:
        """Generate a human-readable description of the action."""
        action_verb = {
            'read': 'queried',
            'create': 'created',
            'update': 'updated',
            'delete': 'deleted',
            'execute': 'executed',
            'configure': 'configured',
        }.get(self.action_category, 'performed')
        
        # Build parameter summary
        param_summary = []
        if self.params:
            for key, value in list(self.params.items())[:3]:  # Show first 3 params
                if isinstance(value, (str, int, bool)):
                    param_summary.append(f"{key}={value}")
        
        param_str = f" with {', '.join(param_summary)}" if param_summary else ""
        agent_str = f" on {self.agent_hostname}" if self.agent_hostname else ""
        
        return f"{self.username} {action_verb} {self.module}.{self.action}{param_str}{agent_str}"
    
    @classmethod
    def log(cls, user, module, action, agent=None, params=None, result=None, 
            success=True, error_message='', action_category='execute', 
            severity='info', before_state=None, after_state=None, 
            command=None, ip_address=None, description='', tags=None, session_id=''):
        """
        Convenience method to create audit log entries.
        
        Usage:
            AuditLog.log(
                user=request.user,
                module='firewalld',
                action='add_service',
                agent=agent_obj,
                params={'zone': 'public', 'service': 'http'},
                success=True,
                action_category='create'
            )
        """
        return cls.objects.create(
            user=user,
            username=user.username if user else 'system',
            module=module,
            action=action,
            agent=agent,
            agent_hostname=agent.hostname if agent else '',
            params=params or {},
            result=result,
            success=success,
            error_message=error_message,
            action_category=action_category,
            severity=severity,
            before_state=before_state,
            after_state=after_state,
            command=command,
            ip_address=ip_address,
            description=description,
            tags=tags or [],
            session_id=session_id,
        )
