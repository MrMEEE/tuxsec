#!/usr/bin/env python3
"""
Firewalld Module - Manages firewall configuration.

This module provides firewalld management capabilities including:
- Zone management
- Service management  
- Port management
- Rich rules
- Query operations
"""

from typing import List, Optional, Dict, Any
import subprocess
from ..base_module import BaseModule
from ..protocol import ModuleCapability, CommandRequest, CommandResponse


class FirewalldModule(BaseModule):
    """Manages firewalld configuration."""
    
    @property
    def name(self) -> str:
        return "firewalld"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "Manages firewalld zones, services, ports, and rules"
    
    def get_capabilities(self) -> List[ModuleCapability]:
        return [
            # Query operations
            ModuleCapability(
                name="get_status",
                description="Get firewalld running status",
                parameters=[]
            ),
            ModuleCapability(
                name="get_version",
                description="Get firewalld version",
                parameters=[]
            ),
            ModuleCapability(
                name="list_zones",
                description="List all zones",
                parameters=[]
            ),
            ModuleCapability(
                name="get_zone",
                description="Get zone configuration",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"}
                ]
            ),
            ModuleCapability(
                name="get_default_zone",
                description="Get default zone",
                parameters=[]
            ),
            ModuleCapability(
                name="list_services",
                description="List available services",
                parameters=[]
            ),
            ModuleCapability(
                name="list_icmptypes",
                description="List available ICMP types",
                parameters=[]
            ),
            
            # Zone operations
            ModuleCapability(
                name="new_zone",
                description="Create a new zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Create permanent zone", "required": "false"}
                ]
            ),
            ModuleCapability(
                name="delete_zone",
                description="Delete a zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Delete permanent zone", "required": "false"}
                ]
            ),
            ModuleCapability(
                name="get_zone_of_interface",
                description="Get the zone an interface belongs to",
                parameters=[
                    {"name": "interface", "type": "string", "description": "Interface name", "required": "true"}
                ]
            ),
            ModuleCapability(
                name="get_zone_of_source",
                description="Get the zone a source belongs to",
                parameters=[
                    {"name": "source", "type": "string", "description": "Source (IP/CIDR)", "required": "true"}
                ]
            ),
            ModuleCapability(
                name="set_default_zone",
                description="Set default zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"}
                ]
            ),
            ModuleCapability(
                name="get_active_zones",
                description="Get all active zones with their interfaces and sources",
                parameters=[]
            ),
            
            # Service operations
            ModuleCapability(
                name="add_service",
                description="Add service to zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "service", "type": "string", "description": "Service name", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make permanent", "required": "false"}
                ]
            ),
            ModuleCapability(
                name="remove_service",
                description="Remove service from zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "service", "type": "string", "description": "Service name", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make permanent", "required": "false"}
                ]
            ),
            
            # Interface operations
            ModuleCapability(
                name="add_interface",
                description="Add interface to zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "interface", "type": "string", "description": "Interface name (e.g., eth0)", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make permanent", "required": "false"}
                ]
            ),
            ModuleCapability(
                name="remove_interface",
                description="Remove interface from zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "interface", "type": "string", "description": "Interface name", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make permanent", "required": "false"}
                ]
            ),
            ModuleCapability(
                name="change_interface",
                description="Change interface to different zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Target zone name", "required": "true"},
                    {"name": "interface", "type": "string", "description": "Interface name", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make permanent", "required": "false"}
                ]
            ),
            ModuleCapability(
                name="list_interfaces",
                description="List interfaces in a zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"}
                ]
            ),
            
            # Source operations
            ModuleCapability(
                name="add_source",
                description="Add source to zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "source", "type": "string", "description": "Source (IP/CIDR, MAC, ipset)", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make permanent", "required": "false"}
                ]
            ),
            ModuleCapability(
                name="remove_source",
                description="Remove source from zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "source", "type": "string", "description": "Source", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make permanent", "required": "false"}
                ]
            ),
            ModuleCapability(
                name="change_source",
                description="Change source to different zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Target zone name", "required": "true"},
                    {"name": "source", "type": "string", "description": "Source", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make permanent", "required": "false"}
                ]
            ),
            ModuleCapability(
                name="list_sources",
                description="List sources in a zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"}
                ]
            ),
            
            # Port operations
            ModuleCapability(
                name="add_port",
                description="Add port to zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "port", "type": "string", "description": "Port/protocol (e.g., 8080/tcp)", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make permanent", "required": "false"}
                ]
            ),
            ModuleCapability(
                name="remove_port",
                description="Remove port from zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "port", "type": "string", "description": "Port/protocol (e.g., 8080/tcp)", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make permanent", "required": "false"}
                ]
            ),
            
            # Rich rule operations
            ModuleCapability(
                name="add_rich_rule",
                description="Add rich rule to zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "rule", "type": "string", "description": "Rich rule", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make permanent", "required": "false"}
                ]
            ),
            ModuleCapability(
                name="remove_rich_rule",
                description="Remove rich rule from zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "rule", "type": "string", "description": "Rich rule", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make permanent", "required": "false"}
                ]
            ),
            
            # Protocol operations
            ModuleCapability(
                name="add_protocol",
                description="Add protocol to zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "protocol", "type": "string", "description": "Protocol (e.g., icmp, igmp)", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make permanent", "required": "false"}
                ]
            ),
            ModuleCapability(
                name="remove_protocol",
                description="Remove protocol from zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "protocol", "type": "string", "description": "Protocol", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make permanent", "required": "false"}
                ]
            ),
            
            # Source port operations
            ModuleCapability(
                name="add_source_port",
                description="Add source port to zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "port", "type": "string", "description": "Source port/protocol (e.g., 8080/tcp)", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make permanent", "required": "false"}
                ]
            ),
            ModuleCapability(
                name="remove_source_port",
                description="Remove source port from zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "port", "type": "string", "description": "Source port/protocol", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make permanent", "required": "false"}
                ]
            ),
            
            # ICMP block operations
            ModuleCapability(
                name="add_icmp_block",
                description="Add ICMP block to zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "icmp_type", "type": "string", "description": "ICMP type", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make permanent", "required": "false"}
                ]
            ),
            ModuleCapability(
                name="remove_icmp_block",
                description="Remove ICMP block from zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "icmp_type", "type": "string", "description": "ICMP type", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make permanent", "required": "false"}
                ]
            ),
            ModuleCapability(
                name="add_icmp_block_inversion",
                description="Enable ICMP block inversion for zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make permanent", "required": "false"}
                ]
            ),
            ModuleCapability(
                name="remove_icmp_block_inversion",
                description="Disable ICMP block inversion for zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make permanent", "required": "false"}
                ]
            ),
            
            # Masquerade operations
            ModuleCapability(
                name="add_masquerade",
                description="Enable masquerading for zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make permanent", "required": "false"}
                ]
            ),
            ModuleCapability(
                name="remove_masquerade",
                description="Disable masquerading for zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make permanent", "required": "false"}
                ]
            ),
            
            # Forward port operations
            ModuleCapability(
                name="add_forward_port",
                description="Add port forwarding rule to zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "port", "type": "string", "description": "Port/protocol (e.g., 80/tcp)", "required": "true"},
                    {"name": "to_port", "type": "string", "description": "Destination port", "required": "false"},
                    {"name": "to_addr", "type": "string", "description": "Destination address", "required": "false"},
                    {"name": "permanent", "type": "boolean", "description": "Make permanent", "required": "false"}
                ]
            ),
            ModuleCapability(
                name="remove_forward_port",
                description="Remove port forwarding rule from zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "port", "type": "string", "description": "Port/protocol", "required": "true"},
                    {"name": "to_port", "type": "string", "description": "Destination port", "required": "false"},
                    {"name": "to_addr", "type": "string", "description": "Destination address", "required": "false"},
                    {"name": "permanent", "type": "boolean", "description": "Make permanent", "required": "false"}
                ]
            ),
            
            # Control operations
            ModuleCapability(
                name="reload",
                description="Reload firewalld configuration",
                parameters=[]
            ),
            ModuleCapability(
                name="complete_reload",
                description="Complete reload - recreates all zones, interfaces, and rules",
                parameters=[]
            ),
            ModuleCapability(
                name="runtime_to_permanent",
                description="Save runtime configuration to permanent",
                parameters=[]
            ),
            ModuleCapability(
                name="check_config",
                description="Check firewalld configuration for errors",
                parameters=[]
            ),
            
            # Service control operations
            ModuleCapability(
                name="service_status",
                description="Get firewalld service status",
                parameters=[]
            ),
            ModuleCapability(
                name="start_service",
                description="Start firewalld service",
                parameters=[]
            ),
            ModuleCapability(
                name="stop_service",
                description="Stop firewalld service",
                parameters=[]
            ),
            ModuleCapability(
                name="restart_service",
                description="Restart firewalld service",
                parameters=[]
            ),
            
            # Panic mode operations
            ModuleCapability(
                name="query_panic",
                description="Check if panic mode is enabled",
                parameters=[]
            ),
            ModuleCapability(
                name="panic_on",
                description="Enable panic mode (drop all incoming and outgoing packets)",
                parameters=[]
            ),
            ModuleCapability(
                name="panic_off",
                description="Disable panic mode",
                parameters=[]
            ),
            
            # Log denied packets operations
            ModuleCapability(
                name="get_log_denied",
                description="Get log denied packets setting",
                parameters=[]
            ),
            ModuleCapability(
                name="set_log_denied",
                description="Set log denied packets (all, unicast, broadcast, multicast, off)",
                parameters=[
                    {"name": "value", "type": "string", "description": "Log level: all, unicast, broadcast, multicast, off", "required": "true"}
                ]
            ),
            
            # Custom service management operations
            ModuleCapability(
                name="list_services",
                description="List all available firewalld services",
                parameters=[]
            ),
            ModuleCapability(
                name="get_service_info",
                description="Get detailed information about a service",
                parameters=[
                    {"name": "service", "type": "string", "description": "Service name", "required": "true"}
                ]
            ),
            ModuleCapability(
                name="new_service",
                description="Create a new custom service",
                parameters=[
                    {"name": "service", "type": "string", "description": "Service name", "required": "true"}
                ]
            ),
            ModuleCapability(
                name="delete_service",
                description="Delete a custom service",
                parameters=[
                    {"name": "service", "type": "string", "description": "Service name", "required": "true"}
                ]
            ),
            ModuleCapability(
                name="service_add_port",
                description="Add port to a service definition",
                parameters=[
                    {"name": "service", "type": "string", "description": "Service name", "required": "true"},
                    {"name": "port", "type": "string", "description": "Port number or range", "required": "true"},
                    {"name": "protocol", "type": "string", "description": "Protocol (tcp/udp)", "required": "true"}
                ]
            ),
            ModuleCapability(
                name="service_remove_port",
                description="Remove port from a service definition",
                parameters=[
                    {"name": "service", "type": "string", "description": "Service name", "required": "true"},
                    {"name": "port", "type": "string", "description": "Port number or range", "required": "true"},
                    {"name": "protocol", "type": "string", "description": "Protocol (tcp/udp)", "required": "true"}
                ]
            ),
            ModuleCapability(
                name="service_add_protocol",
                description="Add protocol to a service definition",
                parameters=[
                    {"name": "service", "type": "string", "description": "Service name", "required": "true"},
                    {"name": "protocol", "type": "string", "description": "Protocol name", "required": "true"}
                ]
            ),
            ModuleCapability(
                name="service_remove_protocol",
                description="Remove protocol from a service definition",
                parameters=[
                    {"name": "service", "type": "string", "description": "Service name", "required": "true"},
                    {"name": "protocol", "type": "string", "description": "Protocol name", "required": "true"}
                ]
            ),
            
            # IPSet management operations
            ModuleCapability(
                name="list_ipsets",
                description="List all IPSets",
                parameters=[]
            ),
            ModuleCapability(
                name="get_ipset_info",
                description="Get detailed information about an IPSet",
                parameters=[
                    {"name": "ipset", "type": "string", "description": "IPSet name", "required": "true"}
                ]
            ),
            ModuleCapability(
                name="new_ipset",
                description="Create a new IPSet",
                parameters=[
                    {"name": "ipset", "type": "string", "description": "IPSet name", "required": "true"},
                    {"name": "type", "type": "string", "description": "IPSet type (hash:ip, hash:net, hash:mac, etc)", "required": "true"}
                ]
            ),
            ModuleCapability(
                name="delete_ipset",
                description="Delete an IPSet",
                parameters=[
                    {"name": "ipset", "type": "string", "description": "IPSet name", "required": "true"}
                ]
            ),
            ModuleCapability(
                name="ipset_add_entry",
                description="Add entry to an IPSet",
                parameters=[
                    {"name": "ipset", "type": "string", "description": "IPSet name", "required": "true"},
                    {"name": "entry", "type": "string", "description": "Entry to add (IP, network, MAC)", "required": "true"}
                ]
            ),
            ModuleCapability(
                name="ipset_remove_entry",
                description="Remove entry from an IPSet",
                parameters=[
                    {"name": "ipset", "type": "string", "description": "IPSet name", "required": "true"},
                    {"name": "entry", "type": "string", "description": "Entry to remove", "required": "true"}
                ]
            ),
            ModuleCapability(
                name="zone_add_source_ipset",
                description="Add IPSet as source to zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "ipset", "type": "string", "description": "IPSet name", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make change permanent", "required": "false"}
                ]
            ),
            ModuleCapability(
                name="zone_remove_source_ipset",
                description="Remove IPSet source from zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "ipset", "type": "string", "description": "IPSet name", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make change permanent", "required": "false"}
                ]
            ),
            
            # Helper module management operations
            ModuleCapability(
                name="list_helpers",
                description="List all available helper modules",
                parameters=[]
            ),
            ModuleCapability(
                name="zone_list_helpers",
                description="List helpers enabled in a zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"}
                ]
            ),
            ModuleCapability(
                name="zone_add_helper",
                description="Add helper module to zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "helper", "type": "string", "description": "Helper module name", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make change permanent", "required": "false"}
                ]
            ),
            ModuleCapability(
                name="zone_remove_helper",
                description="Remove helper module from zone",
                parameters=[
                    {"name": "zone", "type": "string", "description": "Zone name", "required": "true"},
                    {"name": "helper", "type": "string", "description": "Helper module name", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make change permanent", "required": "false"}
                ]
            ),
            
            # Policy management operations
            Capability(
                name="list_policies",
                description="List all firewall policies",
                parameters=[]
            ),
            Capability(
                name="policy_add",
                description="Add a new firewall policy",
                parameters=[
                    {"name": "policy", "type": "string", "description": "Policy name", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make change permanent", "required": "false"}
                ]
            ),
            Capability(
                name="policy_delete",
                description="Delete a firewall policy",
                parameters=[
                    {"name": "policy", "type": "string", "description": "Policy name", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make change permanent", "required": "false"}
                ]
            ),
            Capability(
                name="policy_get_info",
                description="Get detailed information about a policy",
                parameters=[
                    {"name": "policy", "type": "string", "description": "Policy name", "required": "true"}
                ]
            ),
            Capability(
                name="policy_set_ingress_zone",
                description="Set ingress zone for policy",
                parameters=[
                    {"name": "policy", "type": "string", "description": "Policy name", "required": "true"},
                    {"name": "zone", "type": "string", "description": "Ingress zone name", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make change permanent", "required": "false"}
                ]
            ),
            Capability(
                name="policy_set_egress_zone",
                description="Set egress zone for policy",
                parameters=[
                    {"name": "policy", "type": "string", "description": "Policy name", "required": "true"},
                    {"name": "zone", "type": "string", "description": "Egress zone name", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make change permanent", "required": "false"}
                ]
            ),
            Capability(
                name="policy_set_target",
                description="Set target action for policy",
                parameters=[
                    {"name": "policy", "type": "string", "description": "Policy name", "required": "true"},
                    {"name": "target", "type": "string", "description": "Target action (ACCEPT, REJECT, DROP, CONTINUE)", "required": "true"},
                    {"name": "permanent", "type": "boolean", "description": "Make change permanent", "required": "false"}
                ]
            ),
            
            # Direct rules management operations
            Capability(
                name="direct_get_all_chains",
                description="Get all direct chains",
                parameters=[
                    {"name": "ipv", "type": "string", "description": "IP version (ipv4 or ipv6)", "required": "true"},
                    {"name": "table", "type": "string", "description": "Table name (filter, nat, mangle, raw)", "required": "true"}
                ]
            ),
            Capability(
                name="direct_add_chain",
                description="Add a new direct chain",
                parameters=[
                    {"name": "ipv", "type": "string", "description": "IP version (ipv4 or ipv6)", "required": "true"},
                    {"name": "table", "type": "string", "description": "Table name (filter, nat, mangle, raw)", "required": "true"},
                    {"name": "chain", "type": "string", "description": "Chain name", "required": "true"}
                ]
            ),
            Capability(
                name="direct_remove_chain",
                description="Remove a direct chain",
                parameters=[
                    {"name": "ipv", "type": "string", "description": "IP version (ipv4 or ipv6)", "required": "true"},
                    {"name": "table", "type": "string", "description": "Table name (filter, nat, mangle, raw)", "required": "true"},
                    {"name": "chain", "type": "string", "description": "Chain name", "required": "true"}
                ]
            ),
            Capability(
                name="direct_get_all_rules",
                description="Get all direct rules",
                parameters=[]
            ),
            Capability(
                name="direct_add_rule",
                description="Add a direct rule",
                parameters=[
                    {"name": "ipv", "type": "string", "description": "IP version (ipv4 or ipv6)", "required": "true"},
                    {"name": "table", "type": "string", "description": "Table name (filter, nat, mangle, raw)", "required": "true"},
                    {"name": "chain", "type": "string", "description": "Chain name", "required": "true"},
                    {"name": "priority", "type": "integer", "description": "Rule priority (0-999)", "required": "true"},
                    {"name": "args", "type": "array", "description": "Rule arguments", "required": "true"}
                ]
            ),
            Capability(
                name="direct_remove_rule",
                description="Remove a direct rule",
                parameters=[
                    {"name": "ipv", "type": "string", "description": "IP version (ipv4 or ipv6)", "required": "true"},
                    {"name": "table", "type": "string", "description": "Table name (filter, nat, mangle, raw)", "required": "true"},
                    {"name": "chain", "type": "string", "description": "Chain name", "required": "true"},
                    {"name": "priority", "type": "integer", "description": "Rule priority (0-999)", "required": "true"},
                    {"name": "args", "type": "array", "description": "Rule arguments", "required": "true"}
                ]
            ),
            Capability(
                name="direct_get_passthrough",
                description="Get all passthrough rules",
                parameters=[
                    {"name": "ipv", "type": "string", "description": "IP version (ipv4 or ipv6)", "required": "true"}
                ]
            ),
            Capability(
                name="direct_add_passthrough",
                description="Add a passthrough rule",
                parameters=[
                    {"name": "ipv", "type": "string", "description": "IP version (ipv4 or ipv6)", "required": "true"},
                    {"name": "args", "type": "array", "description": "Passthrough arguments", "required": "true"}
                ]
            ),
            
            # Lockdown whitelist operations
            Capability(
                name="lockdown_get_status",
                description="Get lockdown mode status",
                parameters=[]
            ),
            Capability(
                name="lockdown_enable",
                description="Enable lockdown mode",
                parameters=[]
            ),
            Capability(
                name="lockdown_disable",
                description="Disable lockdown mode",
                parameters=[]
            ),
            Capability(
                name="lockdown_list_commands",
                description="List whitelisted commands",
                parameters=[]
            ),
            Capability(
                name="lockdown_add_command",
                description="Add command to whitelist",
                parameters=[
                    {"name": "command", "type": "string", "description": "Command path", "required": "true"}
                ]
            ),
            Capability(
                name="lockdown_remove_command",
                description="Remove command from whitelist",
                parameters=[
                    {"name": "command", "type": "string", "description": "Command path", "required": "true"}
                ]
            ),
            Capability(
                name="lockdown_list_contexts",
                description="List whitelisted SELinux contexts",
                parameters=[]
            ),
            Capability(
                name="lockdown_add_context",
                description="Add SELinux context to whitelist",
                parameters=[
                    {"name": "context", "type": "string", "description": "SELinux context", "required": "true"}
                ]
            ),
            Capability(
                name="lockdown_remove_context",
                description="Remove SELinux context from whitelist",
                parameters=[
                    {"name": "context", "type": "string", "description": "SELinux context", "required": "true"}
                ]
            ),
            Capability(
                name="lockdown_list_users",
                description="List whitelisted users",
                parameters=[]
            ),
            Capability(
                name="lockdown_add_user",
                description="Add user to whitelist",
                parameters=[
                    {"name": "user", "type": "string", "description": "Username", "required": "true"}
                ]
            ),
            Capability(
                name="lockdown_remove_user",
                description="Remove user from whitelist",
                parameters=[
                    {"name": "user", "type": "string", "description": "Username", "required": "true"}
                ]
            ),
            Capability(
                name="lockdown_list_uids",
                description="List whitelisted UIDs",
                parameters=[]
            ),
            Capability(
                name="lockdown_add_uid",
                description="Add UID to whitelist",
                parameters=[
                    {"name": "uid", "type": "integer", "description": "User ID", "required": "true"}
                ]
            ),
            Capability(
                name="lockdown_remove_uid",
                description="Remove UID from whitelist",
                parameters=[
                    {"name": "uid", "type": "integer", "description": "User ID", "required": "true"}
                ]
            ),
        ]
    
    def initialize(self) -> tuple[bool, Optional[str]]:
        """Initialize the firewalld module."""
        # Check if firewalld is available
        success, stdout, stderr = self._run_command(['which', 'firewall-cmd'], timeout=5)
        if not success:
            return False, "firewall-cmd not found. Is firewalld installed?"
        
        # Check if firewalld service is running
        success, stdout, stderr = self._run_command(['systemctl', 'is-active', 'firewalld'], timeout=5)
        if not success:
            self.logger.warning("firewalld service is not active")
        
        self.logger.info("Firewalld module initialized")
        return True, None
    
    def shutdown(self):
        """Cleanup on shutdown."""
        self.logger.info("Firewalld module shutting down")
    
    def execute_command(self, command: CommandRequest) -> CommandResponse:
        """Execute a firewalld command."""
        # Validate command
        is_valid, error = self.validate_command(command)
        if not is_valid:
            return CommandResponse(success=False, error=error)
        
        try:
            action = command.action
            params = command.parameters
            
            # Query operations
            if action == "get_status":
                return self._get_status()
            elif action == "get_version":
                return self._get_version()
            elif action == "list_zones":
                return self._list_zones()
            elif action == "get_zone":
                return self._get_zone(params.get('zone'))
            elif action == "get_default_zone":
                return self._get_default_zone()
            elif action == "list_services":
                return self._list_services()
            elif action == "list_icmptypes":
                return self._list_icmptypes()
            
            # Zone operations
            elif action == "new_zone":
                return self._new_zone(params.get('zone'), params.get('permanent', True))
            elif action == "delete_zone":
                return self._delete_zone(params.get('zone'), params.get('permanent', True))
            elif action == "get_zone_of_interface":
                return self._get_zone_of_interface(params.get('interface'))
            elif action == "get_zone_of_source":
                return self._get_zone_of_source(params.get('source'))
            elif action == "set_default_zone":
                return self._set_default_zone(params.get('zone'))
            elif action == "get_active_zones":
                return self._get_active_zones()

            
            # Service operations
            elif action == "add_service":
                return self._add_service(
                    params.get('zone'),
                    params.get('service'),
                    params.get('permanent', False)
                )
            elif action == "remove_service":
                return self._remove_service(
                    params.get('zone'),
                    params.get('service'),
                    params.get('permanent', False)
                )
            
            # Interface operations
            elif action == "add_interface":
                return self._add_interface(
                    params.get('zone'),
                    params.get('interface'),
                    params.get('permanent', False)
                )
            elif action == "remove_interface":
                return self._remove_interface(
                    params.get('zone'),
                    params.get('interface'),
                    params.get('permanent', False)
                )
            elif action == "change_interface":
                return self._change_interface(
                    params.get('zone'),
                    params.get('interface'),
                    params.get('permanent', False)
                )
            elif action == "list_interfaces":
                return self._list_interfaces(params.get('zone'))
            
            # Source operations
            elif action == "add_source":
                return self._add_source(
                    params.get('zone'),
                    params.get('source'),
                    params.get('permanent', False)
                )
            elif action == "remove_source":
                return self._remove_source(
                    params.get('zone'),
                    params.get('source'),
                    params.get('permanent', False)
                )
            elif action == "change_source":
                return self._change_source(
                    params.get('zone'),
                    params.get('source'),
                    params.get('permanent', False)
                )
            elif action == "list_sources":
                return self._list_sources(params.get('zone'))
            
            # Port operations
            elif action == "add_port":
                return self._add_port(
                    params.get('zone'),
                    params.get('port'),
                    params.get('permanent', False)
                )
            elif action == "remove_port":
                return self._remove_port(
                    params.get('zone'),
                    params.get('port'),
                    params.get('permanent', False)
                )
            
            # Rich rule operations
            elif action == "add_rich_rule":
                return self._add_rich_rule(
                    params.get('zone'),
                    params.get('rule'),
                    params.get('permanent', False)
                )
            elif action == "remove_rich_rule":
                return self._remove_rich_rule(
                    params.get('zone'),
                    params.get('rule'),
                    params.get('permanent', False)
                )
            
            # Protocol operations
            elif action == "add_protocol":
                return self._add_protocol(
                    params.get('zone'),
                    params.get('protocol'),
                    params.get('permanent', False)
                )
            elif action == "remove_protocol":
                return self._remove_protocol(
                    params.get('zone'),
                    params.get('protocol'),
                    params.get('permanent', False)
                )
            
            # Source port operations
            elif action == "add_source_port":
                return self._add_source_port(
                    params.get('zone'),
                    params.get('port'),
                    params.get('permanent', False)
                )
            elif action == "remove_source_port":
                return self._remove_source_port(
                    params.get('zone'),
                    params.get('port'),
                    params.get('permanent', False)
                )
            
            # ICMP block operations
            elif action == "add_icmp_block":
                return self._add_icmp_block(
                    params.get('zone'),
                    params.get('icmp_type'),
                    params.get('permanent', False)
                )
            elif action == "remove_icmp_block":
                return self._remove_icmp_block(
                    params.get('zone'),
                    params.get('icmp_type'),
                    params.get('permanent', False)
                )
            elif action == "add_icmp_block_inversion":
                return self._add_icmp_block_inversion(
                    params.get('zone'),
                    params.get('permanent', False)
                )
            elif action == "remove_icmp_block_inversion":
                return self._remove_icmp_block_inversion(
                    params.get('zone'),
                    params.get('permanent', False)
                )
            
            # Masquerade operations
            elif action == "add_masquerade":
                return self._add_masquerade(
                    params.get('zone'),
                    params.get('permanent', False)
                )
            elif action == "remove_masquerade":
                return self._remove_masquerade(
                    params.get('zone'),
                    params.get('permanent', False)
                )
            
            # Forward port operations
            elif action == "add_forward_port":
                return self._add_forward_port(
                    params.get('zone'),
                    params.get('port'),
                    params.get('to_port'),
                    params.get('to_addr'),
                    params.get('permanent', False)
                )
            elif action == "remove_forward_port":
                return self._remove_forward_port(
                    params.get('zone'),
                    params.get('port'),
                    params.get('to_port'),
                    params.get('to_addr'),
                    params.get('permanent', False)
                )
            
            # Control operations
            elif action == "reload":
                return self._reload()
            elif action == "complete_reload":
                return self._complete_reload()
            elif action == "runtime_to_permanent":
                return self._runtime_to_permanent()
            elif action == "check_config":
                return self._check_config()
            
            # Service control operations
            elif action == "service_status":
                return self._service_status()
            elif action == "start_service":
                return self._start_service()
            elif action == "stop_service":
                return self._stop_service()
            elif action == "restart_service":
                return self._restart_service()
            
            # Panic mode operations
            elif action == "query_panic":
                return self._query_panic()
            elif action == "panic_on":
                return self._panic_on()
            elif action == "panic_off":
                return self._panic_off()
            
            # Log denied packets operations
            elif action == "get_log_denied":
                return self._get_log_denied()
            elif action == "set_log_denied":
                return self._set_log_denied(command.parameters)
            
            # Custom service management operations
            elif action == "list_services":
                return self._list_services()
            elif action == "get_service_info":
                return self._get_service_info(params.get('service'))
            elif action == "new_service":
                return self._new_service(params.get('service'))
            elif action == "delete_service":
                return self._delete_service(params.get('service'))
            elif action == "service_add_port":
                return self._service_add_port(params.get('service'), params.get('port'), params.get('protocol'))
            elif action == "service_remove_port":
                return self._service_remove_port(params.get('service'), params.get('port'), params.get('protocol'))
            elif action == "service_add_protocol":
                return self._service_add_protocol(params.get('service'), params.get('protocol'))
            elif action == "service_remove_protocol":
                return self._service_remove_protocol(params.get('service'), params.get('protocol'))
            
            # IPSet management operations
            elif action == "list_ipsets":
                return self._list_ipsets()
            elif action == "get_ipset_info":
                return self._get_ipset_info(params.get('ipset'))
            elif action == "new_ipset":
                return self._new_ipset(params.get('ipset'), params.get('type'))
            elif action == "delete_ipset":
                return self._delete_ipset(params.get('ipset'))
            elif action == "ipset_add_entry":
                return self._ipset_add_entry(params.get('ipset'), params.get('entry'))
            elif action == "ipset_remove_entry":
                return self._ipset_remove_entry(params.get('ipset'), params.get('entry'))
            elif action == "zone_add_source_ipset":
                return self._zone_add_source_ipset(params.get('zone'), params.get('ipset'), params.get('permanent', False))
            elif action == "zone_remove_source_ipset":
                return self._zone_remove_source_ipset(params.get('zone'), params.get('ipset'), params.get('permanent', False))
            
            # Helper module management operations
            elif action == "list_helpers":
                return self._list_helpers()
            elif action == "zone_list_helpers":
                return self._zone_list_helpers(params.get('zone'))
            elif action == "zone_add_helper":
                return self._zone_add_helper(params.get('zone'), params.get('helper'), params.get('permanent', False))
            elif action == "zone_remove_helper":
                return self._zone_remove_helper(params.get('zone'), params.get('helper'), params.get('permanent', False))
            
            # Policy management operations
            elif action == "list_policies":
                return self._list_policies()
            elif action == "policy_add":
                return self._policy_add(params.get('policy'), params.get('permanent', False))
            elif action == "policy_delete":
                return self._policy_delete(params.get('policy'), params.get('permanent', False))
            elif action == "policy_get_info":
                return self._policy_get_info(params.get('policy'))
            elif action == "policy_set_ingress_zone":
                return self._policy_set_ingress_zone(params.get('policy'), params.get('zone'), params.get('permanent', False))
            elif action == "policy_set_egress_zone":
                return self._policy_set_egress_zone(params.get('policy'), params.get('zone'), params.get('permanent', False))
            elif action == "policy_set_target":
                return self._policy_set_target(params.get('policy'), params.get('target'), params.get('permanent', False))
            
            # Direct rules operations
            elif action == "direct_get_all_chains":
                return self._direct_get_all_chains(params.get('ipv'), params.get('table'))
            elif action == "direct_add_chain":
                return self._direct_add_chain(params.get('ipv'), params.get('table'), params.get('chain'))
            elif action == "direct_remove_chain":
                return self._direct_remove_chain(params.get('ipv'), params.get('table'), params.get('chain'))
            elif action == "direct_get_all_rules":
                return self._direct_get_all_rules()
            elif action == "direct_add_rule":
                return self._direct_add_rule(params.get('ipv'), params.get('table'), params.get('chain'), 
                                            params.get('priority'), params.get('args'))
            elif action == "direct_remove_rule":
                return self._direct_remove_rule(params.get('ipv'), params.get('table'), params.get('chain'), 
                                               params.get('priority'), params.get('args'))
            elif action == "direct_get_passthrough":
                return self._direct_get_passthrough(params.get('ipv'))
            elif action == "direct_add_passthrough":
                return self._direct_add_passthrough(params.get('ipv'), params.get('args'))
            
            # Lockdown operations
            elif action == "lockdown_get_status":
                return self._lockdown_get_status()
            elif action == "lockdown_enable":
                return self._lockdown_enable()
            elif action == "lockdown_disable":
                return self._lockdown_disable()
            elif action == "lockdown_list_commands":
                return self._lockdown_list_commands()
            elif action == "lockdown_add_command":
                return self._lockdown_add_command(params.get('command'))
            elif action == "lockdown_remove_command":
                return self._lockdown_remove_command(params.get('command'))
            elif action == "lockdown_list_contexts":
                return self._lockdown_list_contexts()
            elif action == "lockdown_add_context":
                return self._lockdown_add_context(params.get('context'))
            elif action == "lockdown_remove_context":
                return self._lockdown_remove_context(params.get('context'))
            elif action == "lockdown_list_users":
                return self._lockdown_list_users()
            elif action == "lockdown_add_user":
                return self._lockdown_add_user(params.get('user'))
            elif action == "lockdown_remove_user":
                return self._lockdown_remove_user(params.get('user'))
            elif action == "lockdown_list_uids":
                return self._lockdown_list_uids()
            elif action == "lockdown_add_uid":
                return self._lockdown_add_uid(params.get('uid'))
            elif action == "lockdown_remove_uid":
                return self._lockdown_remove_uid(params.get('uid'))
            
            else:
                return CommandResponse(success=False, error=f"Unknown action: {action}")
                
        except Exception as e:
            self.logger.error(f"Error executing command {command.action}: {e}")
            return CommandResponse(success=False, error=str(e))
    
    def _get_status(self) -> CommandResponse:
        """Get firewalld status."""
        success, stdout, stderr = self._run_command(['systemctl', 'is-active', 'firewalld'])
        is_active = stdout.strip() == 'active'
        
        return CommandResponse(
            success=True,
            data={'active': is_active, 'status': stdout.strip()}
        )
    
    def _get_version(self) -> CommandResponse:
        """Get firewalld version."""
        success, stdout, stderr = self._run_command(['firewall-cmd', '--version'])
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(success=True, data={'version': stdout.strip()})
    
    def _list_zones(self) -> CommandResponse:
        """List all zones."""
        success, stdout, stderr = self._run_command(['firewall-cmd', '--get-zones'])
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        zones = stdout.strip().split()
        return CommandResponse(success=True, data={'zones': zones})
    
    def _get_zone(self, zone: str) -> CommandResponse:
        """Get zone configuration."""
        if not zone:
            return CommandResponse(success=False, error="Zone name is required")
        
        # Get zone info
        success, stdout, stderr = self._run_command(['firewall-cmd', '--zone', zone, '--list-all'])
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(success=True, data={'zone': zone, 'config': stdout})
    
    def _get_default_zone(self) -> CommandResponse:
        """Get default zone."""
        success, stdout, stderr = self._run_command(['firewall-cmd', '--get-default-zone'])
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(success=True, data={'default_zone': stdout.strip()})
    
    def _list_services(self) -> CommandResponse:
        """List available services."""
        success, stdout, stderr = self._run_command(['firewall-cmd', '--get-services'])
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        services = stdout.strip().split()
        return CommandResponse(success=True, data={'services': services})
    
    def _list_icmptypes(self) -> CommandResponse:
        """List available ICMP types."""
        success, stdout, stderr = self._run_command(['firewall-cmd', '--get-icmptypes'])
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        icmptypes = stdout.strip().split()
        return CommandResponse(success=True, data={'icmptypes': icmptypes})
    
    def _new_zone(self, zone: str, permanent: bool) -> CommandResponse:
        """Create a new zone."""
        if not zone:
            return CommandResponse(success=False, error="Zone name is required")
        
        cmd = ['firewall-cmd', f'--new-zone={zone}']
        if permanent:
            cmd.append('--permanent')
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(
            success=True,
            data={'zone': zone, 'permanent': permanent, 'message': 'Zone created successfully'}
        )
    
    def _delete_zone(self, zone: str, permanent: bool) -> CommandResponse:
        """Delete a zone."""
        if not zone:
            return CommandResponse(success=False, error="Zone name is required")
        
        cmd = ['firewall-cmd', f'--delete-zone={zone}']
        if permanent:
            cmd.append('--permanent')
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(
            success=True,
            data={'zone': zone, 'permanent': permanent, 'message': 'Zone deleted successfully'}
        )
    
    def _get_zone_of_interface(self, interface: str) -> CommandResponse:
        """Get the zone an interface belongs to."""
        if not interface:
            return CommandResponse(success=False, error="Interface name is required")
        
        success, stdout, stderr = self._run_command(['firewall-cmd', f'--get-zone-of-interface={interface}'])
        if not success:
            # Interface might not be assigned to any zone
            if "no zone" in stderr.lower():
                return CommandResponse(success=True, data={'interface': interface, 'zone': None})
            return CommandResponse(success=False, error=stderr)
        
        zone = stdout.strip()
        return CommandResponse(success=True, data={'interface': interface, 'zone': zone})
    
    def _get_zone_of_source(self, source: str) -> CommandResponse:
        """Get the zone a source belongs to."""
        if not source:
            return CommandResponse(success=False, error="Source is required")
        
        success, stdout, stderr = self._run_command(['firewall-cmd', f'--get-zone-of-source={source}'])
        if not success:
            # Source might not be assigned to any zone
            if "no zone" in stderr.lower():
                return CommandResponse(success=True, data={'source': source, 'zone': None})
            return CommandResponse(success=False, error=stderr)
        
        zone = stdout.strip()
        return CommandResponse(success=True, data={'source': source, 'zone': zone})
    
    def _get_active_zones(self) -> CommandResponse:
        """Get all active zones with their interfaces and sources."""
        success, stdout, stderr = self._run_command(['firewall-cmd', '--get-active-zones'])
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(success=True, data={'active_zones': stdout})
    
    def _set_default_zone(self, zone: str) -> CommandResponse:
        """Set default zone."""
        if not zone:
            return CommandResponse(success=False, error="Zone name is required")
        
        success, stdout, stderr = self._run_command(['firewall-cmd', '--set-default-zone', zone])
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(success=True, data={'default_zone': zone})
    
    def _add_service(self, zone: str, service: str, permanent: bool) -> CommandResponse:
        """Add service to zone."""
        if not zone or not service:
            return CommandResponse(success=False, error="Zone and service are required")
        
        cmd = ['firewall-cmd', f'--zone={zone}', f'--add-service={service}']
        if permanent:
            cmd.append('--permanent')
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(
            success=True,
            data={'zone': zone, 'service': service, 'permanent': permanent}
        )
    
    def _remove_service(self, zone: str, service: str, permanent: bool) -> CommandResponse:
        """Remove service from zone."""
        if not zone or not service:
            return CommandResponse(success=False, error="Zone and service are required")
        
        cmd = ['firewall-cmd', f'--zone={zone}', f'--remove-service={service}']
        if permanent:
            cmd.append('--permanent')
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(
            success=True,
            data={'zone': zone, 'service': service, 'permanent': permanent}
        )
    
    def _add_interface(self, zone: str, interface: str, permanent: bool) -> CommandResponse:
        """Add interface to zone."""
        if not zone or not interface:
            return CommandResponse(success=False, error="Zone and interface are required")
        
        cmd = ['firewall-cmd', f'--zone={zone}', f'--add-interface={interface}']
        if permanent:
            cmd.append('--permanent')
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(
            success=True,
            data={'zone': zone, 'interface': interface, 'permanent': permanent}
        )
    
    def _remove_interface(self, zone: str, interface: str, permanent: bool) -> CommandResponse:
        """Remove interface from zone."""
        if not zone or not interface:
            return CommandResponse(success=False, error="Zone and interface are required")
        
        cmd = ['firewall-cmd', f'--zone={zone}', f'--remove-interface={interface}']
        if permanent:
            cmd.append('--permanent')
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(
            success=True,
            data={'zone': zone, 'interface': interface, 'permanent': permanent}
        )
    
    def _change_interface(self, zone: str, interface: str, permanent: bool) -> CommandResponse:
        """Change interface to different zone."""
        if not zone or not interface:
            return CommandResponse(success=False, error="Zone and interface are required")
        
        cmd = ['firewall-cmd', f'--zone={zone}', f'--change-interface={interface}']
        if permanent:
            cmd.append('--permanent')
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(
            success=True,
            data={'zone': zone, 'interface': interface, 'permanent': permanent}
        )
    
    def _list_interfaces(self, zone: str) -> CommandResponse:
        """List interfaces in a zone."""
        if not zone:
            return CommandResponse(success=False, error="Zone is required")
        
        success, stdout, stderr = self._run_command(['firewall-cmd', f'--zone={zone}', '--list-interfaces'])
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        interfaces = stdout.strip().split() if stdout.strip() else []
        return CommandResponse(success=True, data={'zone': zone, 'interfaces': interfaces})
    
    def _add_source(self, zone: str, source: str, permanent: bool) -> CommandResponse:
        """Add source to zone."""
        if not zone or not source:
            return CommandResponse(success=False, error="Zone and source are required")
        
        cmd = ['firewall-cmd', f'--zone={zone}', f'--add-source={source}']
        if permanent:
            cmd.append('--permanent')
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(
            success=True,
            data={'zone': zone, 'source': source, 'permanent': permanent}
        )
    
    def _remove_source(self, zone: str, source: str, permanent: bool) -> CommandResponse:
        """Remove source from zone."""
        if not zone or not source:
            return CommandResponse(success=False, error="Zone and source are required")
        
        cmd = ['firewall-cmd', f'--zone={zone}', f'--remove-source={source}']
        if permanent:
            cmd.append('--permanent')
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(
            success=True,
            data={'zone': zone, 'source': source, 'permanent': permanent}
        )
    
    def _change_source(self, zone: str, source: str, permanent: bool) -> CommandResponse:
        """Change source to different zone."""
        if not zone or not source:
            return CommandResponse(success=False, error="Zone and source are required")
        
        cmd = ['firewall-cmd', f'--zone={zone}', f'--change-source={source}']
        if permanent:
            cmd.append('--permanent')
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(
            success=True,
            data={'zone': zone, 'source': source, 'permanent': permanent}
        )
    
    def _list_sources(self, zone: str) -> CommandResponse:
        """List sources in a zone."""
        if not zone:
            return CommandResponse(success=False, error="Zone is required")
        
        success, stdout, stderr = self._run_command(['firewall-cmd', f'--zone={zone}', '--list-sources'])
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        sources = stdout.strip().split() if stdout.strip() else []
        return CommandResponse(success=True, data={'zone': zone, 'sources': sources})
    
    def _add_port(self, zone: str, port: str, permanent: bool) -> CommandResponse:
        """Add port to zone."""
        if not zone or not port:
            return CommandResponse(success=False, error="Zone and port are required")
        
        cmd = ['firewall-cmd', f'--zone={zone}', f'--add-port={port}']
        if permanent:
            cmd.append('--permanent')
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(
            success=True,
            data={'zone': zone, 'port': port, 'permanent': permanent}
        )
    
    def _remove_port(self, zone: str, port: str, permanent: bool) -> CommandResponse:
        """Remove port from zone."""
        if not zone or not port:
            return CommandResponse(success=False, error="Zone and port are required")
        
        cmd = ['firewall-cmd', f'--zone={zone}', f'--remove-port={port}']
        if permanent:
            cmd.append('--permanent')
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(
            success=True,
            data={'zone': zone, 'port': port, 'permanent': permanent}
        )
    
    def _add_rich_rule(self, zone: str, rule: str, permanent: bool) -> CommandResponse:
        """Add rich rule to zone."""
        if not zone or not rule:
            return CommandResponse(success=False, error="Zone and rule are required")
        
        cmd = ['firewall-cmd', f'--zone={zone}', f'--add-rich-rule={rule}']
        if permanent:
            cmd.append('--permanent')
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(
            success=True,
            data={'zone': zone, 'rule': rule, 'permanent': permanent}
        )
    
    def _remove_rich_rule(self, zone: str, rule: str, permanent: bool) -> CommandResponse:
        """Remove rich rule from zone."""
        if not zone or not rule:
            return CommandResponse(success=False, error="Zone and rule are required")
        
        cmd = ['firewall-cmd', f'--zone={zone}', f'--remove-rich-rule={rule}']
        if permanent:
            cmd.append('--permanent')
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(
            success=True,
            data={'zone': zone, 'rule': rule, 'permanent': permanent}
        )
    
    def _add_protocol(self, zone: str, protocol: str, permanent: bool) -> CommandResponse:
        """Add protocol to zone."""
        if not zone or not protocol:
            return CommandResponse(success=False, error="Zone and protocol are required")
        
        cmd = ['firewall-cmd', f'--zone={zone}', f'--add-protocol={protocol}']
        if permanent:
            cmd.append('--permanent')
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(
            success=True,
            data={'zone': zone, 'protocol': protocol, 'permanent': permanent}
        )
    
    def _remove_protocol(self, zone: str, protocol: str, permanent: bool) -> CommandResponse:
        """Remove protocol from zone."""
        if not zone or not protocol:
            return CommandResponse(success=False, error="Zone and protocol are required")
        
        cmd = ['firewall-cmd', f'--zone={zone}', f'--remove-protocol={protocol}']
        if permanent:
            cmd.append('--permanent')
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(
            success=True,
            data={'zone': zone, 'protocol': protocol, 'permanent': permanent}
        )
    
    def _add_source_port(self, zone: str, port: str, permanent: bool) -> CommandResponse:
        """Add source port to zone."""
        if not zone or not port:
            return CommandResponse(success=False, error="Zone and source port are required")
        
        cmd = ['firewall-cmd', f'--zone={zone}', f'--add-source-port={port}']
        if permanent:
            cmd.append('--permanent')
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(
            success=True,
            data={'zone': zone, 'source_port': port, 'permanent': permanent}
        )
    
    def _remove_source_port(self, zone: str, port: str, permanent: bool) -> CommandResponse:
        """Remove source port from zone."""
        if not zone or not port:
            return CommandResponse(success=False, error="Zone and source port are required")
        
        cmd = ['firewall-cmd', f'--zone={zone}', f'--remove-source-port={port}']
        if permanent:
            cmd.append('--permanent')
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(
            success=True,
            data={'zone': zone, 'source_port': port, 'permanent': permanent}
        )
    
    def _add_icmp_block(self, zone: str, icmp_type: str, permanent: bool) -> CommandResponse:
        """Add ICMP block to zone."""
        if not zone or not icmp_type:
            return CommandResponse(success=False, error="Zone and ICMP type are required")
        
        cmd = ['firewall-cmd', f'--zone={zone}', f'--add-icmp-block={icmp_type}']
        if permanent:
            cmd.append('--permanent')
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(
            success=True,
            data={'zone': zone, 'icmp_type': icmp_type, 'permanent': permanent}
        )
    
    def _remove_icmp_block(self, zone: str, icmp_type: str, permanent: bool) -> CommandResponse:
        """Remove ICMP block from zone."""
        if not zone or not icmp_type:
            return CommandResponse(success=False, error="Zone and ICMP type are required")
        
        cmd = ['firewall-cmd', f'--zone={zone}', f'--remove-icmp-block={icmp_type}']
        if permanent:
            cmd.append('--permanent')
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(
            success=True,
            data={'zone': zone, 'icmp_type': icmp_type, 'permanent': permanent}
        )
    
    def _add_icmp_block_inversion(self, zone: str, permanent: bool) -> CommandResponse:
        """Enable ICMP block inversion for zone."""
        if not zone:
            return CommandResponse(success=False, error="Zone is required")
        
        cmd = ['firewall-cmd', f'--zone={zone}', '--add-icmp-block-inversion']
        if permanent:
            cmd.append('--permanent')
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(
            success=True,
            data={'zone': zone, 'permanent': permanent}
        )
    
    def _remove_icmp_block_inversion(self, zone: str, permanent: bool) -> CommandResponse:
        """Disable ICMP block inversion for zone."""
        if not zone:
            return CommandResponse(success=False, error="Zone is required")
        
        cmd = ['firewall-cmd', f'--zone={zone}', '--remove-icmp-block-inversion']
        if permanent:
            cmd.append('--permanent')
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(
            success=True,
            data={'zone': zone, 'permanent': permanent}
        )
    
    def _add_masquerade(self, zone: str, permanent: bool) -> CommandResponse:
        """Enable masquerading for zone."""
        if not zone:
            return CommandResponse(success=False, error="Zone is required")
        
        cmd = ['firewall-cmd', f'--zone={zone}', '--add-masquerade']
        if permanent:
            cmd.append('--permanent')
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(
            success=True,
            data={'zone': zone, 'permanent': permanent}
        )
    
    def _remove_masquerade(self, zone: str, permanent: bool) -> CommandResponse:
        """Disable masquerading for zone."""
        if not zone:
            return CommandResponse(success=False, error="Zone is required")
        
        cmd = ['firewall-cmd', f'--zone={zone}', '--remove-masquerade']
        if permanent:
            cmd.append('--permanent')
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(
            success=True,
            data={'zone': zone, 'permanent': permanent}
        )
    
    def _add_forward_port(self, zone: str, port: str, to_port: Optional[str], to_addr: Optional[str], permanent: bool) -> CommandResponse:
        """Add port forwarding rule to zone."""
        if not zone or not port:
            return CommandResponse(success=False, error="Zone and port are required")
        
        cmd = ['firewall-cmd', f'--zone={zone}', f'--add-forward-port=port={port}']
        if to_port:
            # Append to the same parameter
            cmd[-1] += f':toport={to_port}'
        if to_addr:
            cmd[-1] += f':toaddr={to_addr}'
        
        if permanent:
            cmd.append('--permanent')
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(
            success=True,
            data={'zone': zone, 'port': port, 'to_port': to_port, 'to_addr': to_addr, 'permanent': permanent}
        )
    
    def _remove_forward_port(self, zone: str, port: str, to_port: Optional[str], to_addr: Optional[str], permanent: bool) -> CommandResponse:
        """Remove port forwarding rule from zone."""
        if not zone or not port:
            return CommandResponse(success=False, error="Zone and port are required")
        
        cmd = ['firewall-cmd', f'--zone={zone}', f'--remove-forward-port=port={port}']
        if to_port:
            cmd[-1] += f':toport={to_port}'
        if to_addr:
            cmd[-1] += f':toaddr={to_addr}'
        
        if permanent:
            cmd.append('--permanent')
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(
            success=True,
            data={'zone': zone, 'port': port, 'to_port': to_port, 'to_addr': to_addr, 'permanent': permanent}
        )
    
    def _reload(self) -> CommandResponse:
        """Reload firewalld."""
        success, stdout, stderr = self._run_command(['firewall-cmd', '--reload'])
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(success=True, data={'reloaded': True})
    
    def _complete_reload(self) -> CommandResponse:
        """Complete reload of firewalld - recreates all zones, interfaces, and rules."""
        success, stdout, stderr = self._run_command(['firewall-cmd', '--complete-reload'])
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(success=True, data={'reloaded': True, 'complete': True})
    
    def _runtime_to_permanent(self) -> CommandResponse:
        """Save runtime configuration to permanent."""
        success, stdout, stderr = self._run_command(['firewall-cmd', '--runtime-to-permanent'])
        if not success:
            return CommandResponse(success=False, error=stderr)
        
        return CommandResponse(success=True, data={'saved': True})
    
    def _check_config(self) -> CommandResponse:
        """Check firewalld configuration for errors."""
        success, stdout, stderr = self._run_command(['firewall-cmd', '--check-config'])
        if not success:
            return CommandResponse(success=False, error=stderr, data={'valid': False})
        
        return CommandResponse(success=True, data={'valid': True, 'message': stdout.strip()})
    
    def _service_status(self) -> CommandResponse:
        """Get detailed firewalld service status."""
        # Get basic status
        success, stdout, stderr = self._run_command(['systemctl', 'is-active', 'firewalld'])
        is_active = stdout.strip() == 'active'
        
        # Get detailed status
        success2, stdout2, stderr2 = self._run_command(['systemctl', 'status', 'firewalld'])
        
        # Get enabled status
        success3, stdout3, stderr3 = self._run_command(['systemctl', 'is-enabled', 'firewalld'])
        is_enabled = stdout3.strip() == 'enabled'
        
        return CommandResponse(
            success=True,
            data={
                'active': is_active,
                'enabled': is_enabled,
                'status': stdout.strip(),
                'detailed_status': stdout2 if success2 else stderr2
            }
        )
    
    def _start_service(self) -> CommandResponse:
        """Start firewalld service."""
        success, stdout, stderr = self._run_command(['systemctl', 'start', 'firewalld'], timeout=30)
        if not success:
            return CommandResponse(success=False, error=f"Failed to start firewalld: {stderr}")
        
        # Verify it started
        success2, stdout2, stderr2 = self._run_command(['systemctl', 'is-active', 'firewalld'])
        is_active = stdout2.strip() == 'active'
        
        if not is_active:
            return CommandResponse(success=False, error="Service command executed but firewalld is not active")
        
        return CommandResponse(
            success=True,
            data={
                'action': 'start',
                'active': True,
                'message': 'Firewalld service started successfully'
            }
        )
    
    def _stop_service(self) -> CommandResponse:
        """Stop firewalld service."""
        success, stdout, stderr = self._run_command(['systemctl', 'stop', 'firewalld'], timeout=30)
        if not success:
            return CommandResponse(success=False, error=f"Failed to stop firewalld: {stderr}")
        
        # Verify it stopped
        success2, stdout2, stderr2 = self._run_command(['systemctl', 'is-active', 'firewalld'])
        is_active = stdout2.strip() == 'active'
        
        if is_active:
            return CommandResponse(success=False, error="Service command executed but firewalld is still active")
        
        return CommandResponse(
            success=True,
            data={
                'action': 'stop',
                'active': False,
                'message': 'Firewalld service stopped successfully'
            }
        )
    
    def _restart_service(self) -> CommandResponse:
        """Restart firewalld service."""
        success, stdout, stderr = self._run_command(['systemctl', 'restart', 'firewalld'], timeout=30)
        if not success:
            return CommandResponse(success=False, error=f"Failed to restart firewalld: {stderr}")
        
        # Verify it's active
        success2, stdout2, stderr2 = self._run_command(['systemctl', 'is-active', 'firewalld'])
        is_active = stdout2.strip() == 'active'
        
        if not is_active:
            return CommandResponse(success=False, error="Service command executed but firewalld is not active")
        
        return CommandResponse(
            success=True,
            data={
                'action': 'restart',
                'active': True,
                'message': 'Firewalld service restarted successfully'
            }
        )
    
    def _query_panic(self) -> CommandResponse:
        """Check if panic mode is enabled."""
        success, stdout, stderr = self._run_command(['firewall-cmd', '--query-panic'])
        
        # firewall-cmd returns 0 if panic mode is enabled, 1 if disabled
        panic_enabled = success
        
        return CommandResponse(
            success=True,
            data={
                'panic_mode': panic_enabled,
                'status': 'enabled' if panic_enabled else 'disabled'
            }
        )
    
    def _panic_on(self) -> CommandResponse:
        """Enable panic mode - drops all incoming and outgoing packets."""
        success, stdout, stderr = self._run_command(['firewall-cmd', '--panic-on'])
        if not success:
            return CommandResponse(success=False, error=f"Failed to enable panic mode: {stderr}")
        
        # Verify panic mode is enabled
        success2, stdout2, stderr2 = self._run_command(['firewall-cmd', '--query-panic'])
        if not success2:
            return CommandResponse(success=False, error="Panic mode command executed but verification failed")
        
        return CommandResponse(
            success=True,
            data={
                'panic_mode': True,
                'message': 'Panic mode enabled - all traffic is now blocked'
            }
        )
    
    def _panic_off(self) -> CommandResponse:
        """Disable panic mode."""
        success, stdout, stderr = self._run_command(['firewall-cmd', '--panic-off'])
        if not success:
            return CommandResponse(success=False, error=f"Failed to disable panic mode: {stderr}")
        
        # Verify panic mode is disabled
        success2, stdout2, stderr2 = self._run_command(['firewall-cmd', '--query-panic'])
        # query-panic returns 1 (failure) when disabled, which is what we want
        if success2:
            return CommandResponse(success=False, error="Panic mode command executed but verification failed")
        
        return CommandResponse(
            success=True,
            data={
                'panic_mode': False,
                'message': 'Panic mode disabled - normal firewall rules restored'
            }
        )
    
    def _get_log_denied(self) -> CommandResponse:
        """Get the log denied packets setting."""
        success, stdout, stderr = self._run_command(['firewall-cmd', '--get-log-denied'])
        if not success:
            return CommandResponse(success=False, error=f"Failed to get log denied setting: {stderr}")
        
        setting = stdout.strip()
        return CommandResponse(
            success=True,
            data={
                'log_denied': setting,
                'description': f"Logging denied packets: {setting}"
            }
        )
    
    def _set_log_denied(self, parameters: Dict[str, Any]) -> CommandResponse:
        """Set the log denied packets setting.
        
        Args:
            parameters: Dictionary containing:
                - value: The log level (all, unicast, broadcast, multicast, off)
        """
        value = parameters.get('value', '').strip().lower()
        valid_values = ['all', 'unicast', 'broadcast', 'multicast', 'off']
        
        if value not in valid_values:
            return CommandResponse(
                success=False,
                error=f"Invalid log denied value: {value}. Must be one of: {', '.join(valid_values)}"
            )
        
        success, stdout, stderr = self._run_command(['firewall-cmd', f'--set-log-denied={value}'])
        if not success:
            return CommandResponse(success=False, error=f"Failed to set log denied: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'log_denied': value,
                'message': f"Log denied packets set to: {value}"
            }
        )
    
    def _list_services(self) -> CommandResponse:
        """List all available firewalld services."""
        success, stdout, stderr = self._run_command(['firewall-cmd', '--get-services'])
        if not success:
            return CommandResponse(success=False, error=f"Failed to list services: {stderr}")
        
        services = stdout.strip().split()
        return CommandResponse(
            success=True,
            data={
                'services': services,
                'count': len(services)
            }
        )
    
    def _get_service_info(self, service: str) -> CommandResponse:
        """Get detailed information about a specific service."""
        if not service:
            return CommandResponse(success=False, error="Service name is required")
        
        # Get service info using --info-service
        success, stdout, stderr = self._run_command(['firewall-cmd', '--info-service', service, '--permanent'])
        if not success:
            return CommandResponse(success=False, error=f"Failed to get service info: {stderr}")
        
        # Parse the service info
        service_info = {'name': service, 'ports': [], 'protocols': [], 'modules': [], 'destinations': {}}
        
        for line in stdout.strip().split('\n'):
            line = line.strip()
            if line.startswith('ports:'):
                ports_str = line.replace('ports:', '').strip()
                if ports_str:
                    service_info['ports'] = ports_str.split()
            elif line.startswith('protocols:'):
                protocols_str = line.replace('protocols:', '').strip()
                if protocols_str:
                    service_info['protocols'] = protocols_str.split()
            elif line.startswith('modules:'):
                modules_str = line.replace('modules:', '').strip()
                if modules_str:
                    service_info['modules'] = modules_str.split()
            elif line.startswith('destination:'):
                dest_str = line.replace('destination:', '').strip()
                if dest_str:
                    service_info['destinations'] = dest_str
        
        return CommandResponse(success=True, data=service_info)
    
    def _new_service(self, service: str) -> CommandResponse:
        """Create a new custom service."""
        if not service:
            return CommandResponse(success=False, error="Service name is required")
        
        success, stdout, stderr = self._run_command(['firewall-cmd', '--permanent', '--new-service', service])
        if not success:
            return CommandResponse(success=False, error=f"Failed to create service: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'service': service,
                'message': f"Service '{service}' created successfully"
            }
        )
    
    def _delete_service(self, service: str) -> CommandResponse:
        """Delete a custom service."""
        if not service:
            return CommandResponse(success=False, error="Service name is required")
        
        success, stdout, stderr = self._run_command(['firewall-cmd', '--permanent', '--delete-service', service])
        if not success:
            return CommandResponse(success=False, error=f"Failed to delete service: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'service': service,
                'message': f"Service '{service}' deleted successfully"
            }
        )
    
    def _service_add_port(self, service: str, port: str, protocol: str) -> CommandResponse:
        """Add a port to a service definition."""
        if not all([service, port, protocol]):
            return CommandResponse(success=False, error="Service, port, and protocol are required")
        
        if protocol not in ['tcp', 'udp']:
            return CommandResponse(success=False, error="Protocol must be tcp or udp")
        
        port_spec = f"{port}/{protocol}"
        success, stdout, stderr = self._run_command([
            'firewall-cmd', '--permanent', '--service', service, '--add-port', port_spec
        ])
        
        if not success:
            return CommandResponse(success=False, error=f"Failed to add port: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'service': service,
                'port': port,
                'protocol': protocol,
                'message': f"Port {port_spec} added to service '{service}'"
            }
        )
    
    def _service_remove_port(self, service: str, port: str, protocol: str) -> CommandResponse:
        """Remove a port from a service definition."""
        if not all([service, port, protocol]):
            return CommandResponse(success=False, error="Service, port, and protocol are required")
        
        if protocol not in ['tcp', 'udp']:
            return CommandResponse(success=False, error="Protocol must be tcp or udp")
        
        port_spec = f"{port}/{protocol}"
        success, stdout, stderr = self._run_command([
            'firewall-cmd', '--permanent', '--service', service, '--remove-port', port_spec
        ])
        
        if not success:
            return CommandResponse(success=False, error=f"Failed to remove port: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'service': service,
                'port': port,
                'protocol': protocol,
                'message': f"Port {port_spec} removed from service '{service}'"
            }
        )
    
    def _service_add_protocol(self, service: str, protocol: str) -> CommandResponse:
        """Add a protocol to a service definition."""
        if not all([service, protocol]):
            return CommandResponse(success=False, error="Service and protocol are required")
        
        success, stdout, stderr = self._run_command([
            'firewall-cmd', '--permanent', '--service', service, '--add-protocol', protocol
        ])
        
        if not success:
            return CommandResponse(success=False, error=f"Failed to add protocol: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'service': service,
                'protocol': protocol,
                'message': f"Protocol {protocol} added to service '{service}'"
            }
        )
    
    def _service_remove_protocol(self, service: str, protocol: str) -> CommandResponse:
        """Remove a protocol from a service definition."""
        if not all([service, protocol]):
            return CommandResponse(success=False, error="Service and protocol are required")
        
        success, stdout, stderr = self._run_command([
            'firewall-cmd', '--permanent', '--service', service, '--remove-protocol', protocol
        ])
        
        if not success:
            return CommandResponse(success=False, error=f"Failed to remove protocol: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'service': service,
                'protocol': protocol,
                'message': f"Protocol {protocol} removed from service '{service}'"
            }
        )


    
    def _list_ipsets(self) -> CommandResponse:
        """List all IPSets."""
        success, stdout, stderr = self._run_command(['firewall-cmd', '--permanent', '--get-ipsets'])
        if not success:
            return CommandResponse(success=False, error=f"Failed to list IPSets: {stderr}")
        
        ipsets = stdout.strip().split() if stdout.strip() else []
        return CommandResponse(
            success=True,
            data={
                'ipsets': ipsets,
                'count': len(ipsets)
            }
        )
    
    def _get_ipset_info(self, ipset: str) -> CommandResponse:
        """Get detailed information about an IPSet."""
        if not ipset:
            return CommandResponse(success=False, error="IPSet name is required")
        
        # Get IPSet info
        success, stdout, stderr = self._run_command(['firewall-cmd', '--permanent', '--info-ipset', ipset])
        if not success:
            return CommandResponse(success=False, error=f"Failed to get IPSet info: {stderr}")
        
        # Parse the IPSet info
        ipset_info = {'name': ipset, 'type': '', 'entries': []}
        
        for line in stdout.strip().split('\n'):
            line = line.strip()
            if line.startswith('type:'):
                ipset_info['type'] = line.replace('type:', '').strip()
            elif line.startswith('entries:'):
                entries_str = line.replace('entries:', '').strip()
                if entries_str:
                    ipset_info['entries'] = entries_str.split()
        
        return CommandResponse(success=True, data=ipset_info)
    
    def _new_ipset(self, ipset: str, ipset_type: str) -> CommandResponse:
        """Create a new IPSet."""
        if not ipset or not ipset_type:
            return CommandResponse(success=False, error="IPSet name and type are required")
        
        # Valid IPSet types
        valid_types = ['hash:ip', 'hash:net', 'hash:mac', 'hash:ip,port', 'hash:net,port']
        if ipset_type not in valid_types:
            return CommandResponse(
                success=False,
                error=f"Invalid IPSet type. Must be one of: {', '.join(valid_types)}"
            )
        
        success, stdout, stderr = self._run_command([
            'firewall-cmd', '--permanent', '--new-ipset', ipset, '--type', ipset_type
        ])
        
        if not success:
            return CommandResponse(success=False, error=f"Failed to create IPSet: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'ipset': ipset,
                'type': ipset_type,
                'message': f"IPSet '{ipset}' created with type {ipset_type}"
            }
        )
    
    def _delete_ipset(self, ipset: str) -> CommandResponse:
        """Delete an IPSet."""
        if not ipset:
            return CommandResponse(success=False, error="IPSet name is required")
        
        success, stdout, stderr = self._run_command(['firewall-cmd', '--permanent', '--delete-ipset', ipset])
        if not success:
            return CommandResponse(success=False, error=f"Failed to delete IPSet: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'ipset': ipset,
                'message': f"IPSet '{ipset}' deleted successfully"
            }
        )
    
    def _ipset_add_entry(self, ipset: str, entry: str) -> CommandResponse:
        """Add entry to an IPSet."""
        if not ipset or not entry:
            return CommandResponse(success=False, error="IPSet name and entry are required")
        
        success, stdout, stderr = self._run_command([
            'firewall-cmd', '--permanent', '--ipset', ipset, '--add-entry', entry
        ])
        
        if not success:
            return CommandResponse(success=False, error=f"Failed to add entry: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'ipset': ipset,
                'entry': entry,
                'message': f"Entry '{entry}' added to IPSet '{ipset}'"
            }
        )
    
    def _ipset_remove_entry(self, ipset: str, entry: str) -> CommandResponse:
        """Remove entry from an IPSet."""
        if not ipset or not entry:
            return CommandResponse(success=False, error="IPSet name and entry are required")
        
        success, stdout, stderr = self._run_command([
            'firewall-cmd', '--permanent', '--ipset', ipset, '--remove-entry', entry
        ])
        
        if not success:
            return CommandResponse(success=False, error=f"Failed to remove entry: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'ipset': ipset,
                'entry': entry,
                'message': f"Entry '{entry}' removed from IPSet '{ipset}'"
            }
        )
    
    def _zone_add_source_ipset(self, zone: str, ipset: str, permanent: bool) -> CommandResponse:
        """Add IPSet as source to zone."""
        if not zone or not ipset:
            return CommandResponse(success=False, error="Zone and IPSet name are required")
        
        cmd = ['firewall-cmd']
        if permanent:
            cmd.append('--permanent')
        cmd.extend(['--zone', zone, '--add-source', f'ipset:{ipset}'])
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to add IPSet source: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'zone': zone,
                'ipset': ipset,
                'permanent': permanent,
                'message': f"IPSet '{ipset}' added as source to zone '{zone}'"
            }
        )
    
    def _zone_remove_source_ipset(self, zone: str, ipset: str, permanent: bool) -> CommandResponse:
        """Remove IPSet source from zone."""
        if not zone or not ipset:
            return CommandResponse(success=False, error="Zone and IPSet name are required")
        
        cmd = ['firewall-cmd']
        if permanent:
            cmd.append('--permanent')
        cmd.extend(['--zone', zone, '--remove-source', f'ipset:{ipset}'])
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to remove IPSet source: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'zone': zone,
                'ipset': ipset,
                'permanent': permanent,
                'message': f"IPSet '{ipset}' removed from zone '{zone}'"
            }
        )
    
    def _list_helpers(self) -> CommandResponse:
        """List all available helper modules."""
        cmd = ['firewall-cmd', '--get-helpers']
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to list helpers: {stderr}")
        
        # Parse helpers - typically space-separated list
        helpers = [h.strip() for h in stdout.strip().split() if h.strip()]
        
        return CommandResponse(
            success=True,
            data={
                'helpers': helpers,
                'count': len(helpers)
            }
        )
    
    def _zone_list_helpers(self, zone: str) -> CommandResponse:
        """List helper modules enabled in a specific zone."""
        if not zone:
            return CommandResponse(success=False, error="Zone name is required")
        
        cmd = ['firewall-cmd', '--zone', zone, '--list-helpers']
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to list helpers for zone: {stderr}")
        
        # Parse helpers - typically space-separated list
        helpers = [h.strip() for h in stdout.strip().split() if h.strip()]
        
        return CommandResponse(
            success=True,
            data={
                'zone': zone,
                'helpers': helpers,
                'count': len(helpers)
            }
        )
    
    def _zone_add_helper(self, zone: str, helper: str, permanent: bool) -> CommandResponse:
        """Add helper module to zone."""
        if not zone or not helper:
            return CommandResponse(success=False, error="Zone and helper name are required")
        
        cmd = ['firewall-cmd']
        if permanent:
            cmd.append('--permanent')
        cmd.extend(['--zone', zone, '--add-helper', helper])
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to add helper: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'zone': zone,
                'helper': helper,
                'permanent': permanent,
                'message': f"Helper '{helper}' added to zone '{zone}'"
            }
        )
    
    def _zone_remove_helper(self, zone: str, helper: str, permanent: bool) -> CommandResponse:
        """Remove helper module from zone."""
        if not zone or not helper:
            return CommandResponse(success=False, error="Zone and helper name are required")
        
        cmd = ['firewall-cmd']
        if permanent:
            cmd.append('--permanent')
        cmd.extend(['--zone', zone, '--remove-helper', helper])
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to remove helper: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'zone': zone,
                'helper': helper,
                'permanent': permanent,
                'message': f"Helper '{helper}' removed from zone '{zone}'"
            }
        )
    
    def _list_policies(self) -> CommandResponse:
        """List all firewall policies."""
        cmd = ['firewall-cmd', '--get-policies']
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to list policies: {stderr}")
        
        # Parse policies - typically space-separated list
        policies = [p.strip() for p in stdout.strip().split() if p.strip()]
        
        return CommandResponse(
            success=True,
            data={
                'policies': policies,
                'count': len(policies)
            }
        )
    
    def _policy_add(self, policy: str, permanent: bool) -> CommandResponse:
        """Add a new firewall policy."""
        if not policy:
            return CommandResponse(success=False, error="Policy name is required")
        
        cmd = ['firewall-cmd']
        if permanent:
            cmd.append('--permanent')
        cmd.extend(['--new-policy', policy])
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to add policy: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'policy': policy,
                'permanent': permanent,
                'message': f"Policy '{policy}' created"
            }
        )
    
    def _policy_delete(self, policy: str, permanent: bool) -> CommandResponse:
        """Delete a firewall policy."""
        if not policy:
            return CommandResponse(success=False, error="Policy name is required")
        
        cmd = ['firewall-cmd']
        if permanent:
            cmd.append('--permanent')
        cmd.extend(['--delete-policy', policy])
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to delete policy: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'policy': policy,
                'permanent': permanent,
                'message': f"Policy '{policy}' deleted"
            }
        )
    
    def _policy_get_info(self, policy: str) -> CommandResponse:
        """Get detailed information about a policy."""
        if not policy:
            return CommandResponse(success=False, error="Policy name is required")
        
        cmd = ['firewall-cmd', '--info-policy', policy]
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to get policy info: {stderr}")
        
        # Parse the output
        info = {'name': policy}
        for line in stdout.strip().split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                
                # Parse lists
                if value:
                    info[key] = value.split() if ' ' in value else value
                else:
                    info[key] = []
        
        return CommandResponse(
            success=True,
            data={'policy': info}
        )
    
    def _policy_set_ingress_zone(self, policy: str, zone: str, permanent: bool) -> CommandResponse:
        """Set ingress zone for policy."""
        if not policy or not zone:
            return CommandResponse(success=False, error="Policy name and zone are required")
        
        cmd = ['firewall-cmd']
        if permanent:
            cmd.append('--permanent')
        cmd.extend(['--policy', policy, '--add-ingress-zone', zone])
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to set ingress zone: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'policy': policy,
                'zone': zone,
                'permanent': permanent,
                'message': f"Ingress zone '{zone}' set for policy '{policy}'"
            }
        )
    
    def _policy_set_egress_zone(self, policy: str, zone: str, permanent: bool) -> CommandResponse:
        """Set egress zone for policy."""
        if not policy or not zone:
            return CommandResponse(success=False, error="Policy name and zone are required")
        
        cmd = ['firewall-cmd']
        if permanent:
            cmd.append('--permanent')
        cmd.extend(['--policy', policy, '--add-egress-zone', zone])
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to set egress zone: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'policy': policy,
                'zone': zone,
                'permanent': permanent,
                'message': f"Egress zone '{zone}' set for policy '{policy}'"
            }
        )
    
    def _policy_set_target(self, policy: str, target: str, permanent: bool) -> CommandResponse:
        """Set target action for policy."""
        if not policy or not target:
            return CommandResponse(success=False, error="Policy name and target are required")
        
        # Validate target
        valid_targets = ['ACCEPT', 'REJECT', 'DROP', 'CONTINUE']
        if target not in valid_targets:
            return CommandResponse(success=False, error=f"Invalid target. Must be one of: {', '.join(valid_targets)}")
        
        cmd = ['firewall-cmd']
        if permanent:
            cmd.append('--permanent')
        cmd.extend(['--policy', policy, '--set-target', target])
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to set target: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'policy': policy,
                'target': target,
                'permanent': permanent,
                'message': f"Target '{target}' set for policy '{policy}'"
            }
        )
    
    # Direct rules methods
    
    def _direct_get_all_chains(self, ipv: str, table: str) -> CommandResponse:
        """Get all direct chains for a specific table."""
        if not ipv or not table:
            return CommandResponse(success=False, error="IP version and table are required")
        
        # Validate ipv
        if ipv not in ['ipv4', 'ipv6']:
            return CommandResponse(success=False, error="IP version must be 'ipv4' or 'ipv6'")
        
        # Validate table
        valid_tables = ['filter', 'nat', 'mangle', 'raw']
        if table not in valid_tables:
            return CommandResponse(success=False, error=f"Invalid table. Must be one of: {', '.join(valid_tables)}")
        
        cmd = ['firewall-cmd', '--permanent', '--direct', '--get-all-chains']
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to get chains: {stderr}")
        
        # Parse output - format is "ipv table chain" per line
        all_chains = []
        if stdout.strip():
            for line in stdout.strip().split('\n'):
                parts = line.split()
                if len(parts) >= 3 and parts[0] == ipv and parts[1] == table:
                    all_chains.append(parts[2])
        
        return CommandResponse(
            success=True,
            data={
                'ipv': ipv,
                'table': table,
                'chains': all_chains
            }
        )
    
    def _direct_add_chain(self, ipv: str, table: str, chain: str) -> CommandResponse:
        """Add a new direct chain."""
        if not ipv or not table or not chain:
            return CommandResponse(success=False, error="IP version, table, and chain name are required")
        
        # Validate ipv
        if ipv not in ['ipv4', 'ipv6']:
            return CommandResponse(success=False, error="IP version must be 'ipv4' or 'ipv6'")
        
        # Validate table
        valid_tables = ['filter', 'nat', 'mangle', 'raw']
        if table not in valid_tables:
            return CommandResponse(success=False, error=f"Invalid table. Must be one of: {', '.join(valid_tables)}")
        
        cmd = ['firewall-cmd', '--permanent', '--direct', '--add-chain', ipv, table, chain]
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to add chain: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'ipv': ipv,
                'table': table,
                'chain': chain,
                'message': f"Chain '{chain}' added to {ipv}/{table}"
            }
        )
    
    def _direct_remove_chain(self, ipv: str, table: str, chain: str) -> CommandResponse:
        """Remove a direct chain."""
        if not ipv or not table or not chain:
            return CommandResponse(success=False, error="IP version, table, and chain name are required")
        
        # Validate ipv
        if ipv not in ['ipv4', 'ipv6']:
            return CommandResponse(success=False, error="IP version must be 'ipv4' or 'ipv6'")
        
        # Validate table
        valid_tables = ['filter', 'nat', 'mangle', 'raw']
        if table not in valid_tables:
            return CommandResponse(success=False, error=f"Invalid table. Must be one of: {', '.join(valid_tables)}")
        
        cmd = ['firewall-cmd', '--permanent', '--direct', '--remove-chain', ipv, table, chain]
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to remove chain: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'ipv': ipv,
                'table': table,
                'chain': chain,
                'message': f"Chain '{chain}' removed from {ipv}/{table}"
            }
        )
    
    def _direct_get_all_rules(self) -> CommandResponse:
        """Get all direct rules."""
        cmd = ['firewall-cmd', '--permanent', '--direct', '--get-all-rules']
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to get rules: {stderr}")
        
        # Parse output - format is "ipv table chain priority args..." per line
        rules = []
        if stdout.strip():
            for line in stdout.strip().split('\n'):
                parts = line.split(None, 4)  # Split on first 4 spaces
                if len(parts) >= 5:
                    rules.append({
                        'ipv': parts[0],
                        'table': parts[1],
                        'chain': parts[2],
                        'priority': int(parts[3]),
                        'args': parts[4]
                    })
        
        return CommandResponse(
            success=True,
            data={'rules': rules}
        )
    
    def _direct_add_rule(self, ipv: str, table: str, chain: str, priority: int, args: list) -> CommandResponse:
        """Add a direct rule."""
        if not ipv or not table or not chain or priority is None or not args:
            return CommandResponse(success=False, error="All parameters are required: ipv, table, chain, priority, args")
        
        # Validate ipv
        if ipv not in ['ipv4', 'ipv6']:
            return CommandResponse(success=False, error="IP version must be 'ipv4' or 'ipv6'")
        
        # Validate table
        valid_tables = ['filter', 'nat', 'mangle', 'raw']
        if table not in valid_tables:
            return CommandResponse(success=False, error=f"Invalid table. Must be one of: {', '.join(valid_tables)}")
        
        # Validate priority
        if not (0 <= priority <= 999):
            return CommandResponse(success=False, error="Priority must be between 0 and 999")
        
        cmd = ['firewall-cmd', '--permanent', '--direct', '--add-rule', ipv, table, chain, str(priority)]
        cmd.extend(args if isinstance(args, list) else [args])
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to add rule: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'ipv': ipv,
                'table': table,
                'chain': chain,
                'priority': priority,
                'args': args,
                'message': f"Rule added to {ipv}/{table}/{chain} at priority {priority}"
            }
        )
    
    def _direct_remove_rule(self, ipv: str, table: str, chain: str, priority: int, args: list) -> CommandResponse:
        """Remove a direct rule."""
        if not ipv or not table or not chain or priority is None or not args:
            return CommandResponse(success=False, error="All parameters are required: ipv, table, chain, priority, args")
        
        # Validate ipv
        if ipv not in ['ipv4', 'ipv6']:
            return CommandResponse(success=False, error="IP version must be 'ipv4' or 'ipv6'")
        
        # Validate table
        valid_tables = ['filter', 'nat', 'mangle', 'raw']
        if table not in valid_tables:
            return CommandResponse(success=False, error=f"Invalid table. Must be one of: {', '.join(valid_tables)}")
        
        cmd = ['firewall-cmd', '--permanent', '--direct', '--remove-rule', ipv, table, chain, str(priority)]
        cmd.extend(args if isinstance(args, list) else [args])
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to remove rule: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'ipv': ipv,
                'table': table,
                'chain': chain,
                'priority': priority,
                'args': args,
                'message': f"Rule removed from {ipv}/{table}/{chain} at priority {priority}"
            }
        )
    
    def _direct_get_passthrough(self, ipv: str) -> CommandResponse:
        """Get all passthrough rules."""
        if not ipv:
            return CommandResponse(success=False, error="IP version is required")
        
        # Validate ipv
        if ipv not in ['ipv4', 'ipv6']:
            return CommandResponse(success=False, error="IP version must be 'ipv4' or 'ipv6'")
        
        cmd = ['firewall-cmd', '--permanent', '--direct', '--get-passthroughs', ipv]
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to get passthroughs: {stderr}")
        
        passthroughs = []
        if stdout.strip():
            passthroughs = stdout.strip().split('\n')
        
        return CommandResponse(
            success=True,
            data={
                'ipv': ipv,
                'passthroughs': passthroughs
            }
        )
    
    def _direct_add_passthrough(self, ipv: str, args: list) -> CommandResponse:
        """Add a passthrough rule."""
        if not ipv or not args:
            return CommandResponse(success=False, error="IP version and args are required")
        
        # Validate ipv
        if ipv not in ['ipv4', 'ipv6']:
            return CommandResponse(success=False, error="IP version must be 'ipv4' or 'ipv6'")
        
        cmd = ['firewall-cmd', '--permanent', '--direct', '--add-passthrough', ipv]
        cmd.extend(args if isinstance(args, list) else [args])
        
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to add passthrough: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'ipv': ipv,
                'args': args,
                'message': f"Passthrough rule added for {ipv}"
            }
        )
    
    # Lockdown whitelist methods
    
    def _lockdown_get_status(self) -> CommandResponse:
        """Get lockdown mode status."""
        cmd = ['firewall-cmd', '--query-lockdown']
        success, stdout, stderr = self._run_command(cmd)
        
        # firewall-cmd --query-lockdown returns exit code 0 if enabled, 1 if disabled
        is_enabled = success
        
        return CommandResponse(
            success=True,
            data={
                'enabled': is_enabled,
                'status': 'enabled' if is_enabled else 'disabled'
            }
        )
    
    def _lockdown_enable(self) -> CommandResponse:
        """Enable lockdown mode."""
        cmd = ['firewall-cmd', '--lockdown-on']
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to enable lockdown: {stderr}")
        
        return CommandResponse(
            success=True,
            data={'message': 'Lockdown mode enabled'}
        )
    
    def _lockdown_disable(self) -> CommandResponse:
        """Disable lockdown mode."""
        cmd = ['firewall-cmd', '--lockdown-off']
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to disable lockdown: {stderr}")
        
        return CommandResponse(
            success=True,
            data={'message': 'Lockdown mode disabled'}
        )
    
    def _lockdown_list_commands(self) -> CommandResponse:
        """List whitelisted commands."""
        cmd = ['firewall-cmd', '--permanent', '--list-lockdown-whitelist-commands']
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to list commands: {stderr}")
        
        commands = []
        if stdout.strip():
            commands = stdout.strip().split('\n')
        
        return CommandResponse(
            success=True,
            data={'commands': commands}
        )
    
    def _lockdown_add_command(self, command: str) -> CommandResponse:
        """Add command to whitelist."""
        if not command:
            return CommandResponse(success=False, error="Command is required")
        
        cmd = ['firewall-cmd', '--permanent', '--add-lockdown-whitelist-command', command]
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to add command: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'command': command,
                'message': f"Command '{command}' added to whitelist"
            }
        )
    
    def _lockdown_remove_command(self, command: str) -> CommandResponse:
        """Remove command from whitelist."""
        if not command:
            return CommandResponse(success=False, error="Command is required")
        
        cmd = ['firewall-cmd', '--permanent', '--remove-lockdown-whitelist-command', command]
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to remove command: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'command': command,
                'message': f"Command '{command}' removed from whitelist"
            }
        )
    
    def _lockdown_list_contexts(self) -> CommandResponse:
        """List whitelisted SELinux contexts."""
        cmd = ['firewall-cmd', '--permanent', '--list-lockdown-whitelist-contexts']
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to list contexts: {stderr}")
        
        contexts = []
        if stdout.strip():
            contexts = stdout.strip().split('\n')
        
        return CommandResponse(
            success=True,
            data={'contexts': contexts}
        )
    
    def _lockdown_add_context(self, context: str) -> CommandResponse:
        """Add SELinux context to whitelist."""
        if not context:
            return CommandResponse(success=False, error="Context is required")
        
        cmd = ['firewall-cmd', '--permanent', '--add-lockdown-whitelist-context', context]
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to add context: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'context': context,
                'message': f"Context '{context}' added to whitelist"
            }
        )
    
    def _lockdown_remove_context(self, context: str) -> CommandResponse:
        """Remove SELinux context from whitelist."""
        if not context:
            return CommandResponse(success=False, error="Context is required")
        
        cmd = ['firewall-cmd', '--permanent', '--remove-lockdown-whitelist-context', context]
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to remove context: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'context': context,
                'message': f"Context '{context}' removed from whitelist"
            }
        )
    
    def _lockdown_list_users(self) -> CommandResponse:
        """List whitelisted users."""
        cmd = ['firewall-cmd', '--permanent', '--list-lockdown-whitelist-users']
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to list users: {stderr}")
        
        users = []
        if stdout.strip():
            users = stdout.strip().split('\n')
        
        return CommandResponse(
            success=True,
            data={'users': users}
        )
    
    def _lockdown_add_user(self, user: str) -> CommandResponse:
        """Add user to whitelist."""
        if not user:
            return CommandResponse(success=False, error="User is required")
        
        cmd = ['firewall-cmd', '--permanent', '--add-lockdown-whitelist-user', user]
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to add user: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'user': user,
                'message': f"User '{user}' added to whitelist"
            }
        )
    
    def _lockdown_remove_user(self, user: str) -> CommandResponse:
        """Remove user from whitelist."""
        if not user:
            return CommandResponse(success=False, error="User is required")
        
        cmd = ['firewall-cmd', '--permanent', '--remove-lockdown-whitelist-user', user]
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to remove user: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'user': user,
                'message': f"User '{user}' removed from whitelist"
            }
        )
    
    def _lockdown_list_uids(self) -> CommandResponse:
        """List whitelisted UIDs."""
        cmd = ['firewall-cmd', '--permanent', '--list-lockdown-whitelist-uids']
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to list UIDs: {stderr}")
        
        uids = []
        if stdout.strip():
            uids = [int(uid) for uid in stdout.strip().split('\n')]
        
        return CommandResponse(
            success=True,
            data={'uids': uids}
        )
    
    def _lockdown_add_uid(self, uid: int) -> CommandResponse:
        """Add UID to whitelist."""
        if uid is None:
            return CommandResponse(success=False, error="UID is required")
        
        cmd = ['firewall-cmd', '--permanent', '--add-lockdown-whitelist-uid', str(uid)]
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to add UID: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'uid': uid,
                'message': f"UID {uid} added to whitelist"
            }
        )
    
    def _lockdown_remove_uid(self, uid: int) -> CommandResponse:
        """Remove UID from whitelist."""
        if uid is None:
            return CommandResponse(success=False, error="UID is required")
        
        cmd = ['firewall-cmd', '--permanent', '--remove-lockdown-whitelist-uid', str(uid)]
        success, stdout, stderr = self._run_command(cmd)
        if not success:
            return CommandResponse(success=False, error=f"Failed to remove UID: {stderr}")
        
        return CommandResponse(
            success=True,
            data={
                'uid': uid,
                'message': f"UID {uid} removed from whitelist"
            }
        )


