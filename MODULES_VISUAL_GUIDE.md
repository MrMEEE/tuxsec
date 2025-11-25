# TuxSec Module Architecture - Visual Guide

## Current Architecture (Before Refactoring)

```
┌─────────────────────────────────────────────────────────────────┐
│                         Core System                              │
│  (Knows about firewalld specifics - BAD!)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  agents/models.py                                               │
│  ├── Agent                                                      │
│  │   ├── firewalld_version      ← Firewalld-specific!          │
│  │   └── available_services     ← Firewalld-specific!          │
│  ├── FirewallZone                ← Should be in module!         │
│  └── FirewallRule                ← Should be in module!         │
│                                                                  │
│  agents/views.py                                                │
│  ├── FirewallZoneViewSet         ← Should be in module!         │
│  ├── FirewallRuleViewSet         ← Should be in module!         │
│  ├── sync_firewall_config()      ← Should be in module!         │
│  ├── zone_services()             ← Should be in module!         │
│  └── ... 20+ firewalld views    ← Should be in module!         │
│                                                                  │
│  agents/connection_managers.py                                  │
│  ├── get_zones()                 ← Hardcoded firewalld!         │
│  ├── get_services()              ← Hardcoded firewalld!         │
│  └── get_status()                ← Hardcoded firewalld!         │
│                                                                  │
│  dashboard/views.py                                             │
│  └── if module == 'firewalld':   ← Hardcoded check!            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
        ↓                                ↓
┌──────────────┐              ┌──────────────────┐
│   modules/   │              │  Adding new      │
│   firewalld/ │              │  module requires │
│              │              │  modifying core! │
│ (partial)    │              └──────────────────┘
└──────────────┘

PROBLEMS:
❌ Firewalld code scattered across core system
❌ Hard to add new modules (aide, selinux, clamav)
❌ Core system tightly coupled to firewalld
❌ Poor separation of concerns
❌ Difficult to test modules independently
```

## Proposed Architecture (After Refactoring)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Generic Core System                           │
│  (No module-specific code - GOOD!)                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  agents/models.py                                               │
│  └── Agent                                                      │
│      ├── module_metadata         ← Generic JSONField            │
│      ├── available_modules       ← Generic list                 │
│      └── installed_modules       ← Generic list                 │
│                                                                  │
│  modules/base/                                                  │
│  ├── module.py                   ← BaseModule interface         │
│  ├── registry.py                 ← Module registry              │
│  └── models.py                   ← ModuleData (generic)         │
│                                                                  │
│  agents/connection_managers.py                                  │
│  └── execute_module_action()     ← Generic method!              │
│                                                                  │
│  tuxsec/urls.py                                                 │
│  └── Dynamic URL registration    ← Modules register themselves  │
│                                                                  │
│  agents/management/commands/sync_agents.py                      │
│  └── for module in modules:      ← Generic sync!               │
│          module.on_sync(agent)                                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
        ↓                ↓               ↓               ↓
┌──────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  firewalld   │  │    aide     │  │  selinux    │  │   clamav    │
│   Module     │  │   Module    │  │   Module    │  │   Module    │
├──────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤
│ • models.py  │  │ • models.py │  │ • models.py │  │ • models.py │
│ • views.py   │  │ • views.py  │  │ • views.py  │  │ • views.py  │
│ • urls.py    │  │ • urls.py   │  │ • urls.py   │  │ • urls.py   │
│ • module.py  │  │ • module.py │  │ • module.py │  │ • module.py │
│              │  │             │  │             │  │             │
│ self-        │  │ self-       │  │ self-       │  │ self-       │
│ contained    │  │ contained   │  │ contained   │  │ contained   │
└──────────────┘  └─────────────┘  └─────────────┘  └─────────────┘

BENEFITS:
✅ Each module is self-contained
✅ Easy to add new modules
✅ Core system stays generic
✅ Clear separation of concerns
✅ Modules can be tested independently
```

## Module Lifecycle Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Action                              │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│  Enable Module in Web UI                                        │
│  http://localhost:8001/dashboard/agents/1/                      │
│  [Toggle: firewalld ○ → ●]                                      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│  agents/views.py: agent_module_toggle()                         │
│  ├── Get module from registry                                   │
│  ├── Check if hasattr(module, 'on_enable')                      │
│  └── Call module.on_enable(agent)                               │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│  modules/firewalld/module.py: on_enable()                       │
│  ├── Get connection manager                                     │
│  ├── Execute: manager.execute_module_action('firewalld',        │
│  │                                          'list_zones')       │
│  ├── Parse zones and details                                    │
│  ├── Create FirewallZone objects                                │
│  ├── Create FirewallRule objects                                │
│  └── Return: {'message': 'Synced 5 zones, 42 rules'}           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│  Connection Manager (SSH/Pull/Push)                             │
│  ├── execute_module_action('firewalld', 'list_zones')           │
│  ├── SSH: sudo -u tuxsec tuxsec-cli execute firewalld          │
│  │        list_zones                                            │
│  ├── Pull: Queue command, wait for agent                        │
│  └── Push: POST https://agent/execute                           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│  Agent (tuxsec-agent + tuxsec-rootd)                            │
│  ├── tuxsec-cli receives command                                │
│  ├── Sends to tuxsec-rootd via Unix socket                      │
│  ├── rootd loads firewalld module                               │
│  ├── module.execute('list_zones')                               │
│  └── Returns: {'success': true, 'result': ['public', 'dmz']}   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│  Database Updated                                                │
│  ├── FirewallZone objects created                               │
│  ├── FirewallRule objects created                               │
│  └── Agent.module_metadata updated                              │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│  UI Updated                                                      │
│  ├── Success message: "Module enabled and synced"               │
│  ├── Zones now visible in UI                                    │
│  └── Rules now visible in UI                                    │
└─────────────────────────────────────────────────────────────────┘
```

## API Structure Comparison

### Old API (Module-Specific)
```
/api/
├── agents/
│   ├── {agent_id}/
│   │   ├── zones/              ← Firewalld hardcoded
│   │   │   ├── GET (list)
│   │   │   ├── POST (create)
│   │   │   └── {zone_id}/
│   │   │       ├── GET
│   │   │       ├── PUT
│   │   │       └── DELETE
│   │   │
│   │   └── rules/              ← Firewalld hardcoded
│   │       ├── GET (list)
│   │       ├── POST (create)
│   │       └── {rule_id}/
│   │           ├── GET
│   │           ├── PUT
│   │           └── DELETE

PROBLEM: Adding new module requires editing core URLs!
```

### New API (Generic)
```
/api/
├── agents/
│   └── {agent_id}/
│       ├── firewalld/          ← Dynamic module URLs
│       │   ├── zones/
│       │   │   ├── GET (list)
│       │   │   ├── POST (create)
│       │   │   └── {zone_id}/
│       │   │       ├── GET
│       │   │       ├── PUT
│       │   │       └── DELETE
│       │   │
│       │   └── rules/
│       │       ├── GET (list)
│       │       ├── POST (create)
│       │       └── {rule_id}/
│       │           ├── GET
│       │           ├── PUT
│       │           └── DELETE
│       │
│       ├── aide/               ← New module - no core changes!
│       │   ├── databases/
│       │   └── alerts/
│       │
│       ├── selinux/            ← New module - no core changes!
│       │   ├── policies/
│       │   └── booleans/
│       │
│       └── clamav/             ← New module - no core changes!
│           ├── scans/
│           └── quarantine/

BENEFIT: New modules add their own URLs automatically!
```

## Data Storage Patterns

### Pattern 1: Simple Metadata (Agent.module_metadata)
```
Agent
├── module_metadata (JSONField)
    ├── firewalld: {
    │   version: "1.2.0",
    │   zones_count: 5,
    │   last_sync: "2025-11-25T10:00:00Z"
    │   }
    ├── aide: {
    │   database_version: 3,
    │   files_monitored: 1523
    │   }
    └── selinux: {
        mode: "enforcing",
        policy: "targeted"
        }

USE WHEN: Simple key-value data, no relationships
```

### Pattern 2: Generic Storage (ModuleData)
```
ModuleData
├── agent_id: 1
├── module_name: "clamav"
├── data_type: "scan_result"
└── data: {
    scan_time: "2025-11-25T10:00:00Z",
    files_scanned: 1234,
    threats_found: 2
    }

ModuleData
├── agent_id: 1
├── module_name: "clamav"
├── data_type: "threat"
└── data: {
    file: "/tmp/virus.exe",
    threat: "Win32.Trojan",
    quarantined: true
    }

USE WHEN: Simple data without complex relationships
```

### Pattern 3: Custom Models (Module-Specific)
```
FirewallZone                    FirewallRule
├── id                          ├── id
├── agent_id                    ├── agent_id
├── name: "public"              ├── zone_id (FK)
├── target: "default"           ├── rule_type: "service"
├── services: ["ssh","http"]    ├── service: "ssh"
├── ports: ["8080/tcp"]         ├── enabled: true
├── masquerade: false           └── description: "..."
└── ...                         

USE WHEN: Complex data with relationships, queries needed
```

## Module Registration Flow

```
1. Module Created
   └── modules/mymodule/
       ├── __init__.py
       ├── module.py      (class MyModule(BaseModule))
       ├── models.py
       ├── views.py
       └── urls.py

2. Module Imported
   └── modules/__init__.py
       from .mymodule import MyModule

3. Module Registered
   └── modules/__init__.py
       module_registry.register(MyModule())

4. Django Startup
   ├── Apps discover models from module.get_models()
   ├── URLs register from module.get_url_patterns()
   └── Admin registers from models

5. Module Available
   ├── Web UI shows module in list
   ├── API endpoints accessible
   ├── Can be enabled per agent
   └── Sync calls module.on_sync()
```

## Connection Manager Flow

### Old (Hardcoded)
```
┌──────────────────────┐
│  Firewalld Module    │
│  wants zones         │
└──────────┬───────────┘
           │
           ↓
┌──────────────────────┐
│  Connection Manager  │
│  has get_zones()     │ ← Hardcoded method!
│  method              │
└──────────┬───────────┘
           │
           ↓
┌──────────────────────┐
│  Agent               │
│  executes command    │
└──────────────────────┘

PROBLEM: Adding new module means adding new methods!
```

### New (Generic)
```
┌──────────────────────┐
│  Any Module          │
│  wants data          │
└──────────┬───────────┘
           │
           ↓
┌──────────────────────────────────┐
│  Connection Manager              │
│  execute_module_action(          │ ← Generic method!
│    module='firewalld',           │
│    action='list_zones'           │
│  )                               │
└──────────┬───────────────────────┘
           │
           ↓
┌──────────────────────────────────┐
│  Agent                           │
│  tuxsec-cli execute firewalld    │
│             list_zones           │
└──────────────────────────────────┘

BENEFIT: Same method works for all modules!
```

## Migration Path

```
Phase 1: Infrastructure      Phase 2: Firewalld         Phase 3: Connection
┌──────────────────┐         ┌───────────────────┐      ┌──────────────────┐
│ • ModuleData     │    →    │ • New models      │  →   │ • Generic        │
│ • BaseModule     │         │ • Move views      │      │   execute_       │
│ • Registry       │         │ • URLs            │      │   module_action()│
│ • Agent.metadata │         │ • Data migration  │      │ • Test all modes │
└──────────────────┘         └───────────────────┘      └──────────────────┘
        ↓                            ↓                           ↓
Phase 4: Core Updates        Phase 5: Testing           Phase 6: Cleanup
┌──────────────────┐         ┌───────────────────┐      ┌──────────────────┐
│ • Dynamic URLs   │    →    │ • All features    │  →   │ • Drop old       │
│ • Generic sync   │         │ • Performance     │      │   tables         │
│ • Module hooks   │         │ • Documentation   │      │ • Remove old code│
└──────────────────┘         └───────────────────┘      └──────────────────┘
```

## File Structure Comparison

### Before
```
web_ui/
├── agents/
│   ├── models.py         ← Firewalld models here (BAD)
│   ├── views.py          ← Firewalld views here (BAD)
│   ├── urls.py           ← Firewalld URLs here (BAD)
│   └── ...
├── modules/
│   └── firewalld/
│       ├── module.py     ← Only module class
│       └── ...           ← Missing models/views/urls
```

### After
```
web_ui/
├── agents/
│   ├── models.py         ← Only Agent model (GOOD)
│   ├── views.py          ← Only agent mgmt views (GOOD)
│   ├── urls.py           ← Only agent URLs (GOOD)
│   └── ...
├── modules/
│   ├── base/
│   │   ├── module.py     ← BaseModule interface
│   │   ├── registry.py   ← Module registry
│   │   └── models.py     ← ModuleData generic
│   │
│   ├── firewalld/
│   │   ├── module.py     ← Firewalld module class
│   │   ├── models.py     ← Firewalld models (GOOD)
│   │   ├── views.py      ← Firewalld views (GOOD)
│   │   ├── urls.py       ← Firewalld URLs (GOOD)
│   │   └── ...
│   │
│   ├── aide/             ← New module
│   ├── selinux/          ← New module
│   └── clamav/           ← New module
```

---

**Visual Guide Created:** 25 November 2025  
**Status:** Ready for Implementation
