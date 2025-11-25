from django.contrib import admin
from .models import Agent, FirewallZone, FirewallRule, AgentConnection, AgentCommand, AuditLog


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ['hostname', 'ip_address', 'connection_type', 'status', 'last_seen', 'created_at']
    list_filter = ['connection_type', 'status', 'created_at']
    search_fields = ['hostname', 'ip_address']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(FirewallZone)
class FirewallZoneAdmin(admin.ModelAdmin):
    list_display = ['name', 'agent', 'target', 'masquerade', 'created_at']
    list_filter = ['target', 'masquerade', 'created_at']
    search_fields = ['name', 'agent__hostname']


@admin.register(FirewallRule)
class FirewallRuleAdmin(admin.ModelAdmin):
    list_display = ['rule_type', 'agent', 'zone', 'service', 'port', 'protocol', 'enabled', 'created_at']
    list_filter = ['rule_type', 'protocol', 'enabled', 'permanent', 'created_at']
    search_fields = ['agent__hostname', 'zone__name', 'service', 'port']


@admin.register(AgentConnection)
class AgentConnectionAdmin(admin.ModelAdmin):
    list_display = ['source_agent', 'target_agent', 'source_port', 'target_port', 'protocol', 'created_at']
    list_filter = ['protocol', 'created_at']
    search_fields = ['source_agent__hostname', 'target_agent__hostname', 'service']


@admin.register(AgentCommand)
class AgentCommandAdmin(admin.ModelAdmin):
    list_display = ['agent', 'command_type', 'status', 'created_at', 'completed_at']
    list_filter = ['command_type', 'status', 'created_at']
    search_fields = ['agent__hostname', 'command_type']
    readonly_fields = ['id', 'created_at', 'executed_at', 'completed_at']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'username', 'agent_hostname', 'module', 'action', 'success', 'severity', 'action_category']
    list_filter = ['module', 'action_category', 'success', 'severity', 'timestamp']
    search_fields = ['username', 'agent_hostname', 'module', 'action', 'description']
    readonly_fields = ['id', 'timestamp', 'user', 'username', 'ip_address', 'agent', 'agent_hostname', 
                      'module', 'action', 'action_category', 'params', 'result', 'success', 
                      'error_message', 'description', 'severity', 'command', 'before_state', 
                      'after_state', 'session_id', 'tags']
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        # Audit logs should only be created programmatically
        return False
    
    def has_change_permission(self, request, obj=None):
        # Audit logs are immutable
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Only superusers can delete audit logs
        return request.user.is_superuser