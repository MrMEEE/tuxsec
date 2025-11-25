# TuxSec Module System - Summary

## Overview

This document provides a high-level overview of the TuxSec module system refactoring. For detailed information, see:

- **[MODULES_REFACTORING.md](MODULES_REFACTORING.md)** - Complete architecture plan and rationale
- **[MODULES_IMPLEMENTATION_GUIDE.md](MODULES_IMPLEMENTATION_GUIDE.md)** - Step-by-step implementation
- **[MODULES_QUICK_REFERENCE.md](MODULES_QUICK_REFERENCE.md)** - Quick start guide for developers

## Current State (Before Refactoring)

### Problems
1. **Firewalld-specific code scattered throughout core system**
   - Models in `agents/models.py` instead of firewalld module
   - Views in `agents/views.py` instead of firewalld module
   - Agent model has firewalld-specific fields
   - Connection managers have hardcoded firewalld methods

2. **Difficult to add new modules**
   - No clear pattern to follow
   - Must modify core system files
   - High risk of conflicts

3. **Poor separation of concerns**
   - Core system knows about firewalld specifics
   - Module logic mixed with core logic

## Proposed Architecture

### Core Principles

1. **Self-Contained Modules**
   ```
   modules/mymodule/
   ├── __init__.py        # Registration
   ├── module.py          # Module class
   ├── models.py          # Database models
   ├── views.py           # REST API views
   ├── urls.py            # URL patterns
   ├── serializers.py     # DRF serializers
   └── admin.py           # Django admin
   ```

2. **Generic Core System**
   - No hardcoded module logic
   - Dynamic URL registration
   - Generic module execution
   - Lifecycle hooks for modules

3. **Standard Patterns**
   - BaseModule interface
   - Module registry
   - Lifecycle hooks (on_enable, on_disable, on_sync)
   - Generic data storage

## Implementation Phases

### Phase 1: Infrastructure (Week 1)
- [ ] Create ModuleData generic storage model
- [ ] Update Agent model with module_metadata field
- [ ] Enhanced BaseModule with full interface
- [ ] Module registry system

### Phase 2: Firewalld Refactor (Week 2-3)
- [ ] Move models to modules/firewalld/models.py
- [ ] Move views to modules/firewalld/views.py
- [ ] Create URL patterns in modules/firewalld/urls.py
- [ ] Data migration from old to new tables
- [ ] Update all imports and references

### Phase 3: Connection Managers (Week 3)
- [ ] Add generic execute_module_action() method
- [ ] Remove hardcoded firewalld methods
- [ ] Update firewalld module to use generic methods
- [ ] Test all three connection modes

### Phase 4: Core System Updates (Week 4)
- [ ] Dynamic module URL registration
- [ ] Update sync_agents to call module hooks
- [ ] Remove module-specific logic from core
- [ ] Generic module enable/disable

### Phase 5: Testing & Documentation (Week 5-6)
- [ ] Complete testing of all functionality
- [ ] Performance benchmarking
- [ ] Documentation for module developers
- [ ] Example module creation
- [ ] Migration of old data

## Module Development Patterns

### Pattern 1: Simple Status Module
```python
class StatusModule(BaseModule):
    def get_name(self):
        return "status"
    
    def on_sync(self, agent):
        # Pull status from agent
        # Store in agent.module_metadata
        return {'message': 'Status updated'}
```

### Pattern 2: Module with Database
```python
class MyModule(BaseModule):
    def get_models(self):
        from .models import MyData
        return [MyData]
    
    def on_enable(self, agent):
        # Initialize database
        return self.sync_data(agent)
```

### Pattern 3: Module with REST API
```python
class MyModule(BaseModule):
    def get_url_patterns(self):
        from . import urls
        return urls.urlpatterns
    
    def get_viewsets(self):
        from .views import MyViewSet
        return [MyViewSet]
```

## API Structure

### Old (Module-Specific)
```
/api/agents/<id>/zones/              # Hardcoded firewalld
/api/agents/<id>/rules/              # Hardcoded firewalld
```

### New (Generic)
```
/api/agents/<id>/firewalld/zones/   # Dynamic module URLs
/api/agents/<id>/firewalld/rules/
/api/agents/<id>/aide/alerts/       # Future modules
/api/agents/<id>/selinux/policies/
```

## Data Storage

### Simple Data (ModuleData)
Use generic JSONField for simple key-value storage:
```python
ModuleData.objects.create(
    agent=agent,
    module_name='selinux',
    data_type='status',
    data={'mode': 'enforcing', 'policy': 'targeted'}
)
```

### Complex Data (Custom Models)
Create module-specific models for complex relationships:
```python
# modules/firewalld/models.py
class FirewallZone(models.Model):
    agent = ForeignKey(Agent, related_name='firewalld_zones')
    name = CharField(max_length=100)
    # ... complex fields and relationships
```

### Metadata (Agent.module_metadata)
Store module-specific metadata on Agent model:
```python
agent.module_metadata = {
    'firewalld': {
        'version': '1.2.0',
        'zones_count': 5,
        'rules_count': 42
    },
    'aide': {
        'database_version': 3,
        'files_monitored': 1523
    }
}
```

## Migration Strategy

### Database Migration
1. Create new tables (firewalld_zone, firewalld_rule)
2. Copy data from old tables (agents_firewallzone, agents_firewallrule)
3. Update all foreign keys
4. Keep old tables for rollback
5. After verification, drop old tables

### Code Migration
1. Create module structure
2. Move models
3. Move views
4. Update imports throughout codebase
5. Test thoroughly
6. Remove deprecated code

### Zero-Downtime Migration
- Gradual rollout per module
- Maintain API compatibility during transition
- Feature flags for new/old code paths
- Comprehensive testing before production

## Benefits

### For TuxSec Project
- **Modularity**: Each module is independent
- **Maintainability**: Module code stays with module
- **Scalability**: Easy to add new modules
- **Testing**: Modules tested independently
- **Documentation**: Each module self-documenting

### For Module Developers
- **Clear Structure**: Standard pattern to follow
- **Minimal Boilerplate**: BaseModule provides defaults
- **Flexibility**: Choose complexity level (simple JSON vs custom models)
- **Documentation**: Clear examples and guides

### For Users
- **Consistency**: All modules follow same UI/API patterns
- **Organization**: Module-specific endpoints clearly separated
- **Flexibility**: Enable/disable modules per agent
- **Extensibility**: Custom modules for specific needs

## Timeline

| Week | Phase | Deliverables |
|------|-------|-------------|
| 1 | Infrastructure | ModuleData model, BaseModule interface, Registry |
| 2 | Firewalld Models | New models, data migration |
| 3 | Firewalld Views | Views, URLs, connection managers |
| 4 | Core Updates | Dynamic URLs, sync_agents, module hooks |
| 5 | Testing | All functionality tested, performance validated |
| 6 | Documentation | Complete guides, example module, cleanup |

## Success Criteria

- [ ] All firewalld functionality works with new architecture
- [ ] No firewalld-specific code in core system
- [ ] Example module created following the pattern
- [ ] Documentation complete for module developers
- [ ] Performance equal or better than before
- [ ] Data migration completed without loss
- [ ] Rollback plan tested and verified

## Getting Started

1. **Review Documentation**
   - Read MODULES_REFACTORING.md for architecture details
   - Read MODULES_IMPLEMENTATION_GUIDE.md for implementation steps
   - Check MODULES_QUICK_REFERENCE.md for examples

2. **Set Up Development Environment**
   ```bash
   git checkout -b refactor-module-framework
   cd web_ui
   python manage.py dumpdata > backup_before_refactor.json
   ```

3. **Start with Phase 1**
   - Create base infrastructure
   - Test thoroughly before proceeding
   - Commit each completed step

4. **Proceed Methodically**
   - Follow implementation guide step-by-step
   - Test after each phase
   - Document any deviations from plan

5. **Create Example Module**
   - Once infrastructure complete, create simple example
   - Validate pattern works end-to-end
   - Update documentation with lessons learned

## Questions?

- Architecture questions → See MODULES_REFACTORING.md
- Implementation questions → See MODULES_IMPLEMENTATION_GUIDE.md
- Quick how-to → See MODULES_QUICK_REFERENCE.md
- Example code → See modules/firewalld/ (after refactoring)

## Status

**Current Status:** Documentation complete, ready for implementation

**Next Steps:**
1. Review documentation with team
2. Get approval for refactoring plan
3. Begin Phase 1 implementation
4. Schedule regular review checkpoints

---

**Last Updated:** 25 November 2025  
**Authors:** TuxSec Development Team  
**Status:** Planning Complete - Ready for Implementation
