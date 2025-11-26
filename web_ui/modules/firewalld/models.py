"""
Firewalld Module Models

All firewall-related database models for managing firewalld configurations.
Moved from agents.models to separate firewalld module for better organization.
"""
from django.db import models
from django.contrib.auth.models import User
import uuid


class FirewallZone(models.Model):
    """Firewalld zone configuration model."""
    agent = models.ForeignKey('agents.Agent', on_delete=models.CASCADE, related_name='zones')
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
        app_label = 'firewalld'
        unique_together = ['agent', 'name']
        db_table = 'agents_firewallzone'  # Keep same table name for migration compatibility
    
    def __str__(self):
        return f"{self.agent.hostname} - {self.name}"


class FirewallRule(models.Model):
    """Firewalld rule model."""
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
    agent = models.ForeignKey('agents.Agent', on_delete=models.CASCADE, related_name='rules')
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
        app_label = 'firewalld'
        ordering = ['created_at']
        db_table = 'agents_firewallrule'  # Keep same table name for migration compatibility
    
    def __str__(self):
        return f"{self.agent.hostname} - {self.zone.name} - {self.rule_type}"


class CustomService(models.Model):
    """Custom firewalld service definitions."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey('agents.Agent', on_delete=models.CASCADE, related_name='custom_services')
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
        app_label = 'firewalld'
        unique_together = ['agent', 'name']
        ordering = ['name']
        db_table = 'agents_customservice'  # Keep same table name for migration compatibility
    
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
    agent = models.ForeignKey('agents.Agent', on_delete=models.CASCADE, related_name='ipsets')
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
        app_label = 'firewalld'
        unique_together = ['agent', 'name']
        ordering = ['name']
        db_table = 'agents_ipset'  # Keep same table name for migration compatibility
    
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
    agent = models.ForeignKey('agents.Agent', on_delete=models.CASCADE, related_name='firewall_policies')
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
        app_label = 'firewalld'
        unique_together = ['agent', 'name']
        ordering = ['priority', 'name']
        verbose_name_plural = 'Firewall Policies'
        db_table = 'agents_firewallpolicy'  # Keep same table name for migration compatibility
    
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
        app_label = 'firewalld'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['-updated_at']),
        ]
        db_table = 'agents_firewalltemplate'  # Keep same table name for migration compatibility
    
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
    agent = models.ForeignKey('agents.Agent', on_delete=models.CASCADE, related_name='direct_rules')
    
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
        app_label = 'firewalld'
        ordering = ['ipv', 'table', 'chain', 'priority']
        indexes = [
            models.Index(fields=['agent', 'is_active']),
            models.Index(fields=['ipv', 'table', 'chain']),
        ]
        unique_together = [['agent', 'ipv', 'table', 'chain', 'priority']]
        db_table = 'agents_directrule'  # Keep same table name for migration compatibility
    
    def __str__(self):
        return f"{self.agent.hostname} - {self.ipv}/{self.table}/{self.chain}:{self.priority}"
    
    def get_args_str(self):
        """Get rule arguments as space-separated string."""
        if isinstance(self.args, list):
            return ' '.join(str(arg) for arg in self.args)
        return str(self.args)
