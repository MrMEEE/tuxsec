"""
Firewalld Module Views

All firewall-related view functions for managing firewalld configurations.
Moved from agents.views to separate firewalld module for better organization.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
import json
import httpx
import asyncio
from datetime import datetime

from agents.models import Agent, AgentCommand, AuditLog
from .models import FirewallZone, FirewallRule, CustomService, IPSet, FirewallPolicy, FirewallTemplate, DirectRule
from agents.connection_managers import get_connection_manager


# ============================================================================
# ZONE MANAGEMENT VIEWS
# ============================================================================

@login_required
def agent_zones_data(request, agent_id):
    """Get agent zones and rules data for dynamic updates."""
    agent = get_object_or_404(Agent, id=agent_id)
    
    # Get all zones with proper ordering to ensure consistent results
    zones = agent.zones.all().order_by('name')
    
    zones_data = []
    for zone in zones:
        # Get rules for this zone
        rules = zone.rules.all().order_by('created_at')
        rules_data = []
        
        for rule in rules:
            rules_data.append({
                'id': str(rule.id),
                'rule_type': rule.rule_type,
                'service': rule.service,
                'port': rule.port,
                'protocol': rule.protocol,
                'rich_rule': rule.rich_rule,
                'source': rule.source,
                'enabled': rule.enabled,
                'created_at': rule.created_at.isoformat() if rule.created_at else None,
            })
        
        zones_data.append({
            'id': zone.id,
            'name': zone.name,
            'target': zone.target,
            'interfaces': zone.interfaces or [],
            'sources': zone.sources or [],
            'services': zone.services or [],
            'ports': zone.ports or [],
            'masquerade': zone.masquerade,
            'rules': rules_data,
        })
    
    return JsonResponse({
        'success': True,
        'zones': zones_data
    })


# ============================================================================
# PLACEHOLDER: More zone views will be added here during refactoring
# ============================================================================
# Functions to be moved from agents/views.py:
# - agent_sync_firewall
# - rule_add
# - rule_delete
# - rules_bulk_delete
# - zone_add_service
# - zone_remove_service
# - zone_add_port
# - zone_remove_port
# - zone_list_icmptypes
# - zone_add_icmp_block
# - zone_remove_icmp_block
# - zone_toggle_icmp_inversion
# - zone_create
# - zone_delete
# - agent_firewall_reload
# - agent_firewalld_service_status
# - agent_firewalld_service_control
# - zone_list_helpers
# - zone_add_helper
# - zone_remove_helper
# - set_default_zone
# - zone_detail
# - zone_add_interface
# - zone_remove_interface
# - zone_add_source
# - zone_remove_source
# And many more...
# ============================================================================
