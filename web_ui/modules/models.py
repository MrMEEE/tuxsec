"""
Module models for tracking enabled modules globally and per-agent.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Module(models.Model):
    """
    Stores enable/disable state for modules.
    Module metadata (name, description, capabilities, etc.) comes from the registry.
    """
    name = models.CharField(max_length=100, unique=True, primary_key=True, 
                           help_text="Module identifier - must match module.name from registry")
    
    # Enable/disable state only
    enabled_globally = models.BooleanField(default=False, help_text="Enable this module for all agents")
    auto_enable_new_agents = models.BooleanField(default=False, help_text="Automatically enable for new agents")
    
    # Global configuration overrides
    configuration = models.JSONField(default=dict, blank=True, 
                                    help_text="Global configuration for this module")
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Module"
        verbose_name_plural = "Modules"
    
    def __str__(self):
        return f"{self.name}"
    
    def get_module_instance(self):
        """Get the module instance from the registry."""
        from shared.modules.registry import registry
        return registry.get(self.name)
    
    def get_display_name(self):
        """Get display name from registry."""
        module = self.get_module_instance()
        return module.display_name if module else self.name
    
    def get_description(self):
        """Get description from registry."""
        module = self.get_module_instance()
        return module.description if module else ""
    
    def get_version(self):
        """Get version from registry."""
        module = self.get_module_instance()
        return module.version if module else "unknown"
    
    def get_enabled_agents_count(self):
        """Get count of agents with this module enabled."""
        return self.agentmodule_set.filter(enabled=True).count()
    
    def get_available_agents_count(self):
        """Get count of agents where this module is available."""
        return self.agentmodule_set.filter(available=True).count()


class AgentModule(models.Model):
    """
    Tracks which modules are enabled for specific agents.
    """
    agent = models.ForeignKey('agents.Agent', on_delete=models.CASCADE, related_name='modules')
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    
    # Status
    enabled = models.BooleanField(default=False, help_text="Module is enabled for this agent")
    available = models.BooleanField(default=False, help_text="Module is available on this agent")
    
    # Configuration - agent-specific overrides
    configuration = models.JSONField(default=dict, blank=True, help_text="Agent-specific module configuration")
    
    # Status tracking
    last_check = models.DateTimeField(null=True, blank=True, help_text="Last availability check")
    last_status = models.JSONField(default=dict, blank=True, help_text="Last status from module")
    error_message = models.TextField(blank=True, help_text="Error if module unavailable")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['agent', 'module']
        ordering = ['agent', 'module']
        verbose_name = "Agent Module"
        verbose_name_plural = "Agent Modules"
    
    def __str__(self):
        status = "enabled" if self.enabled else "disabled"
        return f"{self.agent.hostname} - {self.module.display_name} ({status})"
    
    def sync_from_agent(self, available: bool, status: dict = None, error: str = None):
        """
        Update this AgentModule based on agent response.
        
        Args:
            available: Whether the module is available on the agent
            status: Current module status from agent
            error: Error message if unavailable
        """
        from django.utils import timezone
        
        self.available = available
        self.last_check = timezone.now()
        
        if status:
            self.last_status = status
        
        if error:
            self.error_message = error
        elif self.error_message:  # Clear error if now available
            self.error_message = ""
        
        self.save()


class ModuleAction(models.Model):
    """
    Log of module actions executed on agents.
    """
    agent_module = models.ForeignKey(AgentModule, on_delete=models.CASCADE, related_name='actions')
    action = models.CharField(max_length=100, help_text="Action that was executed")
    parameters = models.JSONField(default=dict, help_text="Parameters passed to action")
    
    # Execution details
    initiated_by = models.CharField(max_length=100, blank=True, help_text="User or system that initiated")
    executed_at = models.DateTimeField(auto_now_add=True)
    
    # Results
    success = models.BooleanField(default=False)
    result_data = models.JSONField(default=dict, blank=True, help_text="Result data from action")
    error_message = models.TextField(blank=True)
    
    # Performance
    duration_ms = models.IntegerField(null=True, blank=True, help_text="Execution time in milliseconds")
    
    class Meta:
        ordering = ['-executed_at']
        verbose_name = "Module Action"
        verbose_name_plural = "Module Actions"
        indexes = [
            models.Index(fields=['-executed_at']),
            models.Index(fields=['agent_module', '-executed_at']),
        ]
    
    def __str__(self):
        status = "✓" if self.success else "✗"
        return f"{status} {self.agent_module.agent.hostname} - {self.action} @ {self.executed_at}"

