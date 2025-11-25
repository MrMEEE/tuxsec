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


class FirewallZone(models.Model):
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='zones')
    name = models.CharField(max_length=100)
    target = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    interfaces = models.JSONField(default=list)
    sources = models.JSONField(default=list)
    services = models.JSONField(default=list)
    ports = models.JSONField(default=list)
    masquerade = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['agent', 'name']
    
    def __str__(self):
        return f"{self.agent.hostname} - {self.name}"


class FirewallRule(models.Model):
    RULE_TYPES = [
        ('service', 'Service'),
        ('port', 'Port'),
        ('rich', 'Rich Rule'),
        ('forward', 'Forward Port'),
        ('masquerade', 'Masquerade'),
        ('source_port', 'Source Port'),
        ('icmp_block', 'ICMP Block'),
    ]
    
    PROTOCOLS = [
        ('tcp', 'TCP'),
        ('udp', 'UDP'),
        ('icmp', 'ICMP'),
        ('sctp', 'SCTP'),
        ('dccp', 'DCCP'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='rules')
    zone = models.ForeignKey(FirewallZone, on_delete=models.CASCADE, related_name='rules')
    rule_type = models.CharField(max_length=20, choices=RULE_TYPES)
    
    # Service rule fields
    service = models.CharField(max_length=100, blank=True)
    
    # Port rule fields
    port = models.CharField(max_length=20, blank=True)
    protocol = models.CharField(max_length=10, choices=PROTOCOLS, blank=True)
    
    # Rich rule fields
    rich_rule = models.TextField(blank=True)
    
    # Forward port fields
    to_port = models.CharField(max_length=20, blank=True)
    to_addr = models.GenericIPAddressField(null=True, blank=True)
    
    # Common fields
    source = models.CharField(max_length=100, blank=True)
    destination = models.CharField(max_length=100, blank=True)
    enabled = models.BooleanField(default=True)
    permanent = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.agent.hostname} - {self.zone.name} - {self.rule_type}"


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


class CustomService(models.Model):
    """Custom firewalld service definitions."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='custom_services')
    name = models.CharField(max_length=100, help_text="Service name")
    description = models.TextField(blank=True, help_text="Service description")
    
    # Service configuration
    ports = models.JSONField(default=list, blank=True, help_text="List of ports (e.g., ['80/tcp', '443/tcp'])")
    protocols = models.JSONField(default=list, blank=True, help_text="List of protocols")
    modules = models.JSONField(default=list, blank=True, help_text="List of netfilter helper modules")
    destinations = models.JSONField(default=dict, blank=True, help_text="Destination addresses (IPv4/IPv6)")
    
    # Metadata
    is_system = models.BooleanField(default=False, help_text="Is this a system service (read-only)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_services')
    
    class Meta:
        unique_together = ['agent', 'name']
        ordering = ['name']
    
    def __str__(self):
        return f"{self.agent.hostname} - {self.name}"




class IPSet(models.Model):
    """Firewalld IPSet definitions."""
    IPSET_TYPES = [
        ('hash:ip', 'Hash: IP Address'),
        ('hash:net', 'Hash: Network'),
        ('hash:mac', 'Hash: MAC Address'),
        ('hash:ip,port', 'Hash: IP and Port'),
        ('hash:net,port', 'Hash: Network and Port'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='ipsets')
    name = models.CharField(max_length=100, help_text="IPSet name")
    ipset_type = models.CharField(max_length=20, choices=IPSET_TYPES, help_text="IPSet type")
    description = models.TextField(blank=True, help_text="IPSet description")
    
    # Entries stored as JSON array
    entries = models.JSONField(default=list, blank=True, help_text="List of entries (IPs, networks, MACs)")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_ipsets')
    
    class Meta:
        unique_together = ['agent', 'name']
        ordering = ['name']
    
    def __str__(self):
        return f"{self.agent.hostname} - {self.name} ({self.ipset_type})"


class FirewallPolicy(models.Model):
    """Firewalld Policy definitions for zone-to-zone traffic control."""
    TARGET_CHOICES = [
        ('ACCEPT', 'Accept'),
        ('REJECT', 'Reject'),
        ('DROP', 'Drop'),
        ('CONTINUE', 'Continue'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='firewall_policies')
    name = models.CharField(max_length=100, help_text="Policy name")
    description = models.TextField(blank=True, help_text="Policy description")
    
    # Policy zones
    ingress_zones = models.JSONField(default=list, blank=True, help_text="List of ingress zone names")
    egress_zones = models.JSONField(default=list, blank=True, help_text="List of egress zone names")
    
    # Policy target
    target = models.CharField(max_length=10, choices=TARGET_CHOICES, default='CONTINUE', help_text="Policy target action")
    
    # Metadata
    priority = models.IntegerField(default=0, help_text="Policy priority (lower is higher priority)")
    is_active = models.BooleanField(default=True, help_text="Is policy active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_policies')
    
    class Meta:
        unique_together = ['agent', 'name']
        ordering = ['priority', 'name']
        verbose_name_plural = 'Firewall Policies'
    
    def __str__(self):
        return f"{self.agent.hostname} - {self.name} ({self.target})"


class FirewallTemplate(models.Model):
    """Firewall configuration templates for quick deployment."""
    
    CATEGORY_CHOICES = [
        ('server', 'Server'),
        ('workstation', 'Workstation'),
        ('dmz', 'DMZ'),
        ('network', 'Network'),
        ('custom', 'Custom'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, help_text="Template name")
    description = models.TextField(help_text="Template description")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='custom', help_text="Template category")
    
    # Template configuration stored as JSON
    # Structure: {
    #   "zones": {
    #     "public": {
    #       "services": ["ssh", "http", "https"],
    #       "ports": [{"port": "8080", "protocol": "tcp"}],
    #       "interfaces": ["eth0"],
    #       "sources": ["192.168.1.0/24"],
    #       "icmp_blocks": ["echo-request"],
    #       "helpers": ["ftp"],
    #       "target": "default",
    #       "masquerade": false,
    #       "forward_ports": [{"port": "80", "protocol": "tcp", "to_port": "8080"}]
    #     }
    #   },
    #   "policies": [
    #     {"name": "dmz-to-internal", "ingress_zone": "dmz", "egress_zone": "internal", "target": "REJECT"}
    #   ],
    #   "custom_services": [
    #     {"name": "myapp", "ports": ["8080/tcp", "8443/tcp"], "description": "My Application"}
    #   ],
    #   "ipsets": [
    #     {"name": "whitelist", "type": "hash:ip", "entries": ["10.0.0.1", "10.0.0.2"]}
    #   ]
    # }
    configuration = models.JSONField(default=dict, help_text="Template configuration (zones, policies, services, ipsets)")
    
    # Template metadata
    is_global = models.BooleanField(default=False, help_text="Available to all users")
    is_active = models.BooleanField(default=True, help_text="Template is active")
    usage_count = models.IntegerField(default=0, help_text="Number of times template has been applied")
    
    # Ownership and timestamps
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_templates')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Tags for organization
    tags = models.JSONField(default=list, blank=True, help_text="Template tags for filtering")
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['-updated_at']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.category})"
    
    def increment_usage(self):
        """Increment the usage counter."""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])
    
    def get_zones(self):
        """Get list of zones defined in template."""
        return list(self.configuration.get('zones', {}).keys())
    
    def get_policies_count(self):
        """Get count of policies in template."""
        return len(self.configuration.get('policies', []))
    
    def get_services_count(self):
        """Get count of custom services in template."""
        return len(self.configuration.get('custom_services', []))
    
    def validate_configuration(self):
        """Validate template configuration structure."""
        errors = []
        
        # Check zones structure
        zones = self.configuration.get('zones', {})
        if not isinstance(zones, dict):
            errors.append("zones must be a dictionary")
        else:
            for zone_name, zone_config in zones.items():
                if not isinstance(zone_config, dict):
                    errors.append(f"Zone '{zone_name}' configuration must be a dictionary")
                    continue
                
                # Validate zone fields
                valid_fields = ['services', 'ports', 'interfaces', 'sources', 'icmp_blocks', 
                               'helpers', 'target', 'masquerade', 'forward_ports']
                for field in zone_config:
                    if field not in valid_fields:
                        errors.append(f"Unknown field '{field}' in zone '{zone_name}'")
        
        # Check policies structure
        policies = self.configuration.get('policies', [])
        if not isinstance(policies, list):
            errors.append("policies must be a list")
        else:
            for i, policy in enumerate(policies):
                if not isinstance(policy, dict):
                    errors.append(f"Policy {i} must be a dictionary")
                    continue
                required = ['name', 'ingress_zone', 'egress_zone', 'target']
                for field in required:
                    if field not in policy:
                        errors.append(f"Policy {i} missing required field: {field}")
        
        # Check custom_services structure
        services = self.configuration.get('custom_services', [])
        if not isinstance(services, list):
            errors.append("custom_services must be a list")
        else:
            for i, service in enumerate(services):
                if not isinstance(service, dict):
                    errors.append(f"Service {i} must be a dictionary")
                    continue
                if 'name' not in service:
                    errors.append(f"Service {i} missing required field: name")
        
        # Check ipsets structure
        ipsets = self.configuration.get('ipsets', [])
        if not isinstance(ipsets, list):
            errors.append("ipsets must be a list")
        else:
            for i, ipset in enumerate(ipsets):
                if not isinstance(ipset, dict):
                    errors.append(f"IPSet {i} must be a dictionary")
                    continue
                required = ['name', 'type']
                for field in required:
                    if field not in ipset:
                        errors.append(f"IPSet {i} missing required field: {field}")
        
        return errors


class DirectRule(models.Model):
    """Model to store firewalld direct rules."""
    IPV_CHOICES = [
        ('ipv4', 'IPv4'),
        ('ipv6', 'IPv6'),
    ]
    
    TABLE_CHOICES = [
        ('filter', 'Filter'),
        ('nat', 'NAT'),
        ('mangle', 'Mangle'),
        ('raw', 'Raw'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='direct_rules')
    
    # Rule identification
    ipv = models.CharField(max_length=4, choices=IPV_CHOICES, help_text="IP version (ipv4 or ipv6)")
    table = models.CharField(max_length=10, choices=TABLE_CHOICES, help_text="iptables table")
    chain = models.CharField(max_length=100, help_text="Chain name")
    priority = models.IntegerField(help_text="Rule priority (0-999)")
    
    # Rule definition
    args = models.JSONField(help_text="Rule arguments as list")
    description = models.TextField(blank=True, help_text="Rule description")
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_direct_rules')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['ipv', 'table', 'chain', 'priority']
        indexes = [
            models.Index(fields=['agent', 'is_active']),
            models.Index(fields=['ipv', 'table', 'chain']),
        ]
        unique_together = [['agent', 'ipv', 'table', 'chain', 'priority']]
    
    def __str__(self):
        return f"{self.agent.hostname} - {self.ipv}/{self.table}/{self.chain}:{self.priority}"
    
    def get_args_str(self):
        """Get rule arguments as space-separated string."""
        if isinstance(self.args, list):
            return ' '.join(str(arg) for arg in self.args)
        return str(self.args)


