"""
Firewalld Module Admin Configuration

Django admin registration for firewall models.
"""
from django.contrib import admin
from .models import (
    FirewallZone,
    FirewallRule,
    CustomService,
    IPSet,
    FirewallPolicy,
    FirewallTemplate,
    DirectRule,
)


@admin.register(FirewallZone)
class FirewallZoneAdmin(admin.ModelAdmin):
    """Admin interface for FirewallZone model."""
    list_display = ['name', 'agent', 'target', 'masquerade', 'created_at']
    list_filter = ['agent', 'masquerade', 'created_at']
    search_fields = ['name', 'agent__hostname', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(FirewallRule)
class FirewallRuleAdmin(admin.ModelAdmin):
    """Admin interface for FirewallRule model."""
    list_display = ['agent', 'zone', 'rule_type', 'service', 'port', 'protocol', 'enabled', 'created_at']
    list_filter = ['rule_type', 'protocol', 'enabled', 'permanent', 'created_at']
    search_fields = ['agent__hostname', 'zone__name', 'service', 'rich_rule']
    readonly_fields = ['id', 'created_at']


@admin.register(CustomService)
class CustomServiceAdmin(admin.ModelAdmin):
    """Admin interface for CustomService model."""
    list_display = ['name', 'agent', 'is_system', 'created_at']
    list_filter = ['is_system', 'created_at', 'agent']
    search_fields = ['name', 'description', 'agent__hostname']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(IPSet)
class IPSetAdmin(admin.ModelAdmin):
    """Admin interface for IPSet model."""
    list_display = ['name', 'agent', 'ipset_type', 'created_at']
    list_filter = ['ipset_type', 'created_at', 'agent']
    search_fields = ['name', 'description', 'agent__hostname']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(FirewallPolicy)
class FirewallPolicyAdmin(admin.ModelAdmin):
    """Admin interface for FirewallPolicy model."""
    list_display = ['name', 'agent', 'target', 'priority', 'is_active', 'created_at']
    list_filter = ['target', 'is_active', 'created_at', 'agent']
    search_fields = ['name', 'description', 'agent__hostname']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['priority', 'name']


@admin.register(FirewallTemplate)
class FirewallTemplateAdmin(admin.ModelAdmin):
    """Admin interface for FirewallTemplate model."""
    list_display = ['name', 'category', 'is_global', 'is_active', 'usage_count', 'created_by', 'updated_at']
    list_filter = ['category', 'is_global', 'is_active', 'created_at', 'updated_at']
    search_fields = ['name', 'description', 'tags']
    readonly_fields = ['id', 'usage_count', 'created_at', 'updated_at']
    filter_horizontal = []
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'category')
        }),
        ('Configuration', {
            'fields': ('configuration',)
        }),
        ('Settings', {
            'fields': ('is_global', 'is_active', 'tags')
        }),
        ('Metadata', {
            'fields': ('created_by', 'usage_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DirectRule)
class DirectRuleAdmin(admin.ModelAdmin):
    """Admin interface for DirectRule model."""
    list_display = ['agent', 'ipv', 'table', 'chain', 'priority', 'is_active', 'created_at']
    list_filter = ['ipv', 'table', 'is_active', 'created_at', 'agent']
    search_fields = ['agent__hostname', 'chain', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['ipv', 'table', 'chain', 'priority']
