from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import api_views

router = DefaultRouter()
router.register(r'', views.AgentViewSet)
router.register(r'(?P<agent_id>[^/.]+)/zones', views.FirewallZoneViewSet, basename='agent-zones')
router.register(r'(?P<agent_id>[^/.]+)/rules', views.FirewallRuleViewSet, basename='agent-rules')
router.register(r'(?P<agent_id>[^/.]+)/commands', views.AgentCommandViewSet, basename='agent-commands')

urlpatterns = [
    # API routes
    path('api/', include(router.urls)),
    path('api/<uuid:agent_id>/status/', views.agent_status, name='agent-status'),
    path('api/<uuid:agent_id>/approve/', views.approve_agent, name='approve-agent'),
    path('api/<uuid:agent_id>/reject/', views.reject_agent, name='reject-agent'),
    path('api/connections/', views.ConnectionListCreateView.as_view(), name='connections'),
    path('api/connections/<uuid:connection_id>/', views.ConnectionDetailView.as_view(), name='connection-detail'),
    
    # Agent communication API endpoints
    path('api/checkin/', api_views.agent_checkin, name='api-agent-checkin'),
    path('api/register/', api_views.agent_register, name='api-agent-register'),
    path('api/<uuid:agent_id>/execute/', api_views.AgentCommandAPI.as_view(), name='api-agent-execute'),
    
    # Web interface routes
    # NOTE: agent_list and agent_detail removed - use /dashboard/agents/ and /dashboard/agents/<id>/ instead
    path('create/', views.agent_create, name='agent-create'),
    path('quick-add/', views.agent_quick_add, name='agent-quick-add'),
    # NOTE: agent_detail removed - use /dashboard/agents/<id>/ instead (dashboard.views.agent_detail)
    path('<uuid:agent_id>/edit/', views.agent_edit, name='agent-edit'),
    path('<uuid:agent_id>/services-page/', views.agent_services_page, name='agent-services-page'),
    path('<uuid:agent_id>/test-connection/', views.agent_test_connection, name='agent-test-connection'),
    path('<uuid:agent_id>/sync-firewall/', views.agent_sync_firewall, name='agent-sync-firewall'),
    path('<uuid:agent_id>/zones-data/', views.agent_zones_data, name='agent-zones-data'),
    path('<uuid:agent_id>/status-data/', views.agent_status_data, name='agent-status-data'),
    path('<uuid:agent_id>/available-services/', views.agent_available_services, name='agent-available-services'),
    path('<uuid:agent_id>/module/<str:module_name>/toggle/', views.agent_module_toggle, name='agent-module-toggle'),
    
    # Rule management routes
    path('<uuid:agent_id>/rule/add/', views.rule_add, name='rule-add'),
    path('<uuid:agent_id>/rule/<uuid:rule_id>/delete/', views.rule_delete, name='rule-delete'),
    path('<uuid:agent_id>/rules/bulk-delete/', views.rules_bulk_delete, name='rules-bulk-delete'),
    
    # Zone management routes
    path('<uuid:agent_id>/zone/create/', views.zone_create, name='zone-create'),
    path('<uuid:agent_id>/zone/<int:zone_id>/', views.zone_detail, name='zone-detail'),
    path('<uuid:agent_id>/zone/<int:zone_id>/delete/', views.zone_delete, name='zone-delete'),
    path('<uuid:agent_id>/zone/set-default/', views.set_default_zone, name='set-default-zone'),
    path('<uuid:agent_id>/zone/<int:zone_id>/service/add/', views.zone_add_service, name='zone-add-service'),
    path('<uuid:agent_id>/zone/<int:zone_id>/service/<str:service>/remove/', views.zone_remove_service, name='zone-remove-service'),
    path('<uuid:agent_id>/zone/<int:zone_id>/port/add/', views.zone_add_port, name='zone-add-port'),
    path('<uuid:agent_id>/zone/<int:zone_id>/port/remove/', views.zone_remove_port, name='zone-remove-port'),
    path('<uuid:agent_id>/zone/<int:zone_id>/interface/add/', views.zone_add_interface, name='zone-add-interface'),
    path('<uuid:agent_id>/zone/<int:zone_id>/interface/<str:interface>/remove/', views.zone_remove_interface, name='zone-remove-interface'),
    path('<uuid:agent_id>/zone/<int:zone_id>/source/add/', views.zone_add_source, name='zone-add-source'),
    path('<uuid:agent_id>/zone/<int:zone_id>/source/<path:source>/remove/', views.zone_remove_source, name='zone-remove-source'),
    
    # ICMP block management routes
    path('<uuid:agent_id>/icmptypes/', views.zone_list_icmptypes, name='zone-list-icmptypes'),
    path('<uuid:agent_id>/zone/<int:zone_id>/icmp-block/add/', views.zone_add_icmp_block, name='zone-add-icmp-block'),
    path('<uuid:agent_id>/zone/<int:zone_id>/icmp-block/<str:icmp_type>/remove/', views.zone_remove_icmp_block, name='zone-remove-icmp-block'),
    path('<uuid:agent_id>/zone/<int:zone_id>/icmp-inversion/toggle/', views.zone_toggle_icmp_inversion, name='zone-toggle-icmp-inversion'),
    
    # Audit log routes
    path('audit/', views.audit_log_list, name='audit-log-list'),
    path('audit/<uuid:audit_id>/', views.audit_log_detail, name='audit-log-detail'),
    path('<uuid:agent_id>/audit/', views.agent_audit_logs, name='agent-audit-logs'),
    
    # Firewall reload routes
    path('<uuid:agent_id>/firewall/reload/', views.agent_firewall_reload, name='agent-firewall-reload'),
    path('<uuid:agent_id>/firewall/check-config/', views.agent_check_config, name='agent-check-config'),
    
    # Firewalld service control routes
    path('<uuid:agent_id>/firewalld/service/status/', views.agent_firewalld_service_status, name='agent-firewalld-service-status'),
    path('<uuid:agent_id>/firewalld/service/control/', views.agent_firewalld_service_control, name='agent-firewalld-service-control'),
    
    # Panic mode routes
    path('<uuid:agent_id>/panic/status/', views.agent_panic_status, name='agent-panic-status'),
    path('<uuid:agent_id>/panic/control/', views.agent_panic_control, name='agent-panic-control'),
    
    # Log denied packets routes
    path('<uuid:agent_id>/log-denied/status/', views.agent_log_denied_status, name='agent-log-denied-status'),
    path('<uuid:agent_id>/log-denied/control/', views.agent_log_denied_control, name='agent-log-denied-control'),
    
    # Custom service management routes
    path('<uuid:agent_id>/services/', views.agent_list_services, name='agent-list-services'),
    path('<uuid:agent_id>/services/<str:service_name>/', views.agent_service_detail, name='agent-service-detail'),
    path('<uuid:agent_id>/services/create/', views.agent_service_create, name='agent-service-create'),
    path('<uuid:agent_id>/services/<str:service_name>/delete/', views.agent_service_delete, name='agent-service-delete'),
    path('<uuid:agent_id>/services/<str:service_name>/port/add/', views.agent_service_add_port, name='agent-service-add-port'),
    path('<uuid:agent_id>/services/<str:service_name>/port/remove/', views.agent_service_remove_port, name='agent-service-remove-port'),
    
    # IPSet management routes
    path('<uuid:agent_id>/ipsets-page/', views.agent_ipsets_page, name='agent-ipsets-page'),
    path('<uuid:agent_id>/ipsets/', views.agent_list_ipsets, name='agent-list-ipsets'),
    path('<uuid:agent_id>/ipsets/<str:ipset_name>/', views.agent_ipset_detail, name='agent-ipset-detail'),
    path('<uuid:agent_id>/ipsets/create/', views.agent_ipset_create, name='agent-ipset-create'),
    path('<uuid:agent_id>/ipsets/<str:ipset_name>/delete/', views.agent_ipset_delete, name='agent-ipset-delete'),
    path('<uuid:agent_id>/ipsets/<str:ipset_name>/entry/add/', views.agent_ipset_add_entry, name='agent-ipset-add-entry'),
    path('<uuid:agent_id>/ipsets/<str:ipset_name>/entry/remove/', views.agent_ipset_remove_entry, name='agent-ipset-remove-entry'),
    
    # Helper module management routes
    path('<uuid:agent_id>/helpers/', views.agent_list_helpers, name='agent-list-helpers'),
    path('<uuid:agent_id>/zone/<int:zone_id>/helpers/', views.zone_list_helpers, name='zone-list-helpers'),
    path('<uuid:agent_id>/zone/<int:zone_id>/helper/add/', views.zone_add_helper, name='zone-add-helper'),
    path('<uuid:agent_id>/zone/<int:zone_id>/helper/<str:helper>/remove/', views.zone_remove_helper, name='zone-remove-helper'),
    
    # Policy management routes
    path('<uuid:agent_id>/policies-page/', views.agent_policies_page, name='agent-policies-page'),
    path('<uuid:agent_id>/policies/', views.agent_list_policies, name='agent-list-policies'),
    path('<uuid:agent_id>/policies/<str:policy_name>/', views.agent_policy_detail, name='agent-policy-detail'),
    path('<uuid:agent_id>/policies/create/', views.agent_policy_create, name='agent-policy-create'),
    path('<uuid:agent_id>/policies/<str:policy_name>/delete/', views.agent_policy_delete, name='agent-policy-delete'),
    
    # Template management routes
    path('templates/', views.templates_page, name='templates-page'),
    path('api/templates/', views.template_list, name='template-list'),
    path('api/templates/<uuid:template_id>/', views.template_detail, name='template-detail'),
    path('api/templates/create/', views.template_create, name='template-create'),
    path('api/templates/<uuid:template_id>/update/', views.template_update, name='template-update'),
    path('api/templates/<uuid:template_id>/delete/', views.template_delete, name='template-delete'),
    path('api/templates/<uuid:template_id>/duplicate/', views.template_duplicate, name='template-duplicate'),
    path('api/templates/<uuid:template_id>/preview/', views.template_preview, name='template-preview'),
    path('api/templates/<uuid:template_id>/apply/', views.template_apply, name='template-apply'),
    
    # Direct rules management routes
    path('<uuid:agent_id>/direct-rules-page/', views.agent_direct_rules_page, name='agent-direct-rules-page'),
    path('<uuid:agent_id>/direct-rules/', views.agent_list_direct_rules, name='agent-list-direct-rules'),
    path('<uuid:agent_id>/direct-rules/create/', views.agent_direct_rule_create, name='agent-direct-rule-create'),
    path('<uuid:agent_id>/direct-rules/<uuid:rule_id>/delete/', views.agent_direct_rule_delete, name='agent-direct-rule-delete'),
    path('<uuid:agent_id>/chains/', views.agent_list_chains, name='agent-list-chains'),
    
    # Lockdown whitelist management routes
    path('<uuid:agent_id>/lockdown/status/', views.agent_lockdown_status, name='agent-lockdown-status'),
    path('<uuid:agent_id>/lockdown/control/', views.agent_lockdown_control, name='agent-lockdown-control'),
    path('<uuid:agent_id>/lockdown/commands/', views.agent_lockdown_list_commands, name='agent-lockdown-list-commands'),
    path('<uuid:agent_id>/lockdown/commands/add/', views.agent_lockdown_add_command, name='agent-lockdown-add-command'),
    path('<uuid:agent_id>/lockdown/commands/remove/', views.agent_lockdown_remove_command, name='agent-lockdown-remove-command'),
    path('<uuid:agent_id>/lockdown/users/', views.agent_lockdown_list_users, name='agent-lockdown-list-users'),
    path('<uuid:agent_id>/lockdown/users/add/', views.agent_lockdown_add_user, name='agent-lockdown-add-user'),
    path('<uuid:agent_id>/lockdown/users/remove/', views.agent_lockdown_remove_user, name='agent-lockdown-remove-user'),
]
