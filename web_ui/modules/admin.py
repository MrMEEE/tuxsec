"""
Admin configuration for modules.
"""

from django.contrib import admin
from .models import Module, AgentModule, ModuleAction


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_display_name_admin', 'get_version_admin', 'enabled_globally', 'auto_enable_new_agents', 'created_at']
    list_filter = ['enabled_globally', 'auto_enable_new_agents', 'created_at']
    search_fields = ['name']
    readonly_fields = ['name', 'get_display_name_admin', 'get_description_admin', 'get_version_admin', 
                       'get_capabilities_admin', 'get_actions_admin', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Module Information (from registry)', {
            'fields': ('name', 'get_display_name_admin', 'get_description_admin', 'get_version_admin'),
            'description': 'Module metadata is loaded from the registry, not stored in database.'
        }),
        ('Enable/Disable State', {
            'fields': ('enabled_globally', 'auto_enable_new_agents')
        }),
        ('Global Configuration', {
            'fields': ('configuration',),
            'classes': ('collapse',)
        }),
        ('Module Details', {
            'fields': ('get_capabilities_admin', 'get_actions_admin'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_display_name_admin(self, obj):
        """Display name from registry."""
        return obj.get_display_name()
    get_display_name_admin.short_description = 'Display Name'
    
    def get_version_admin(self, obj):
        """Version from registry."""
        return obj.get_version()
    get_version_admin.short_description = 'Version'
    
    def get_description_admin(self, obj):
        """Description from registry."""
        return obj.get_description() or "No description available"
    get_description_admin.short_description = 'Description'
    
    def get_capabilities_admin(self, obj):
        """Capabilities from registry."""
        module = obj.get_module_instance()
        if module:
            return ", ".join([cap.value for cap in module.capabilities])
        return "Module not loaded"
    get_capabilities_admin.short_description = 'Capabilities'
    
    def get_actions_admin(self, obj):
        """Actions from registry."""
        module = obj.get_module_instance()
        if module:
            actions = module.get_available_actions()
            return f"{len(actions)} actions: " + ", ".join(actions[:5]) + ("..." if len(actions) > 5 else "")
        return "Module not loaded"
    get_actions_admin.short_description = 'Available Actions'


@admin.register(AgentModule)
class AgentModuleAdmin(admin.ModelAdmin):
    list_display = ['agent', 'module', 'enabled', 'available', 'last_check', 'updated_at']
    list_filter = ['enabled', 'available', 'module', 'last_check']
    search_fields = ['agent__hostname', 'module__name']
    readonly_fields = ['created_at', 'updated_at', 'last_check']
    
    fieldsets = (
        ('Agent & Module', {
            'fields': ('agent', 'module')
        }),
        ('Status', {
            'fields': ('enabled', 'available', 'last_check', 'error_message')
        }),
        ('Configuration', {
            'fields': ('configuration', 'last_status'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ModuleAction)
class ModuleActionAdmin(admin.ModelAdmin):
    list_display = ['agent_module', 'action', 'success', 'executed_at', 'duration_ms', 'initiated_by']
    list_filter = ['success', 'executed_at', 'action']
    search_fields = ['agent_module__agent__hostname', 'agent_module__module__name', 'action', 'initiated_by']
    readonly_fields = ['executed_at']
    date_hierarchy = 'executed_at'
    
    fieldsets = (
        ('Execution', {
            'fields': ('agent_module', 'action', 'parameters', 'initiated_by', 'executed_at')
        }),
        ('Results', {
            'fields': ('success', 'result_data', 'error_message', 'duration_ms')
        }),
    )
