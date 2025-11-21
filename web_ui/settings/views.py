"""
Views for the settings app.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User
from shared.modules.registry import registry
from modules.models import Module, AgentModule
from agents.models import Agent
from .forms import ModuleSettingsForm, UserForm


def is_staff(user):
    """Check if user is staff."""
    return user.is_staff


@login_required
@user_passes_test(is_staff)
def settings_home(request):
    """Settings home page."""
    return render(request, 'settings/home.html')


# ===== Module Management =====

@login_required
@user_passes_test(is_staff)
def module_list(request):
    """List all available modules with enable/disable options."""
    modules_data = []
    
    for module_name in registry.list_module_names():
        module = registry.get(module_name)
        
        # Get or create state record
        state, created = Module.objects.get_or_create(
            name=module_name,
            defaults={'enabled_globally': False}
        )
        
        # Count agents
        enabled_count = AgentModule.objects.filter(module=state, enabled=True).count()
        available_count = AgentModule.objects.filter(module=state, available=True).count()
        total_agents = Agent.objects.count()
        
        modules_data.append({
            'name': module_name,
            'display_name': module.display_name,
            'description': module.description,
            'version': module.version,
            'enabled_globally': state.enabled_globally,
            'auto_enable_new_agents': state.auto_enable_new_agents,
            'enabled_count': enabled_count,
            'available_count': available_count,
            'total_agents': total_agents,
            'capabilities': [cap.value for cap in module.capabilities],
            'required_packages': module.get_required_packages(),
        })
    
    return render(request, 'settings/modules/list.html', {
        'modules': modules_data
    })


@login_required
@user_passes_test(is_staff)
def module_toggle(request, module_name):
    """Toggle module enabled status."""
    if request.method == 'POST':
        # Verify module exists in registry
        module = registry.get(module_name)
        if not module:
            messages.error(request, f'Module "{module_name}" not found in registry')
            return redirect('settings:module_list')
        
        # Get or create state
        state, created = Module.objects.get_or_create(
            name=module_name,
            defaults={'enabled_globally': False}
        )
        
        # Toggle status
        state.enabled_globally = not state.enabled_globally
        state.save()
        
        status = "enabled" if state.enabled_globally else "disabled"
        messages.success(request, f'Module "{module.display_name}" {status} globally')
    
    return redirect('settings:module_list')


@login_required
@user_passes_test(is_staff)
def module_detail(request, module_name):
    """Detail view for a module with per-agent settings."""
    module = registry.get(module_name)
    if not module:
        messages.error(request, f'Module "{module_name}" not found')
        return redirect('settings:module_list')
    
    # Get state
    state, created = Module.objects.get_or_create(
        name=module_name,
        defaults={'enabled_globally': False}
    )
    
    # Handle form submission
    if request.method == 'POST':
        form = ModuleSettingsForm(request.POST, instance=state)
        if form.is_valid():
            form.save()
            messages.success(request, f'Settings updated for {module.display_name}')
            return redirect('settings:module_detail', module_name=module_name)
    else:
        form = ModuleSettingsForm(instance=state)
    
    # Get per-agent status
    agent_modules = AgentModule.objects.filter(module=state).select_related('agent')
    
    return render(request, 'settings/modules/detail.html', {
        'module': module,
        'state': state,
        'form': form,
        'agent_modules': agent_modules,
        'actions': module.get_available_actions(),
    })


@login_required
@user_passes_test(is_staff)
def module_agent_toggle(request, module_name, agent_id):
    """Toggle module for specific agent."""
    if request.method == 'POST':
        agent = get_object_or_404(Agent, id=agent_id)
        state = get_object_or_404(Module, name=module_name)
        
        agent_module, created = AgentModule.objects.get_or_create(
            agent=agent,
            module=state,
            defaults={'enabled': False, 'available': False}
        )
        
        agent_module.enabled = not agent_module.enabled
        agent_module.save()
        
        module = registry.get(module_name)
        status = "enabled" if agent_module.enabled else "disabled"
        messages.success(request, f'Module "{module.display_name}" {status} for {agent.hostname}')
    
    return redirect('settings:module_detail', module_name=module_name)


@login_required
@user_passes_test(is_staff)
def module_enable_all(request, module_name):
    """Enable module for all agents."""
    if request.method == 'POST':
        module = registry.get(module_name)
        if not module:
            messages.error(request, f'Module "{module_name}" not found in registry')
            return redirect('settings:module_list')
        
        state = get_object_or_404(Module, name=module_name)
        
        # Enable for all agents
        all_agents = Agent.objects.all()
        enabled_count = 0
        
        for agent in all_agents:
            agent_module, created = AgentModule.objects.get_or_create(
                agent=agent,
                module=state,
                defaults={'enabled': True, 'available': False}
            )
            if not agent_module.enabled:
                agent_module.enabled = True
                agent_module.save()
                enabled_count += 1
        
        if enabled_count > 0:
            messages.success(request, f'Module "{module.display_name}" enabled for {enabled_count} agent(s)')
        else:
            messages.info(request, f'Module "{module.display_name}" was already enabled for all agents')
    
    return redirect('settings:module_list')


@login_required
@user_passes_test(is_staff)
def module_disable_all(request, module_name):
    """Disable module for all agents."""
    if request.method == 'POST':
        module = registry.get(module_name)
        if not module:
            messages.error(request, f'Module "{module_name}" not found in registry')
            return redirect('settings:module_list')
        
        state = get_object_or_404(Module, name=module_name)
        
        # Disable for all agents
        disabled_count = AgentModule.objects.filter(
            module=state,
            enabled=True
        ).update(enabled=False)
        
        if disabled_count > 0:
            messages.success(request, f'Module "{module.display_name}" disabled for {disabled_count} agent(s)')
        else:
            messages.info(request, f'Module "{module.display_name}" was already disabled for all agents')
    
    return redirect('settings:module_list')


# ===== User Management =====

@login_required
@user_passes_test(is_staff)
def user_list(request):
    """List all users."""
    users = User.objects.all().order_by('username')
    return render(request, 'settings/users/list.html', {'users': users})


@login_required
@user_passes_test(is_staff)
def user_create(request):
    """Create a new user."""
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # Set password properly
            password = form.cleaned_data.get('password')
            if password:
                user.set_password(password)
            user.save()
            messages.success(request, f'User "{user.username}" created successfully')
            return redirect('settings:user_list')
    else:
        form = UserForm()
    
    return render(request, 'settings/users/form.html', {
        'form': form,
        'title': 'Create User'
    })


@login_required
@user_passes_test(is_staff)
def user_edit(request, user_id):
    """Edit an existing user."""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save(commit=False)
            password = form.cleaned_data.get('password')
            if password:  # Only update password if provided
                user.set_password(password)
            user.save()
            messages.success(request, f'User "{user.username}" updated successfully')
            return redirect('settings:user_list')
    else:
        form = UserForm(instance=user)
    
    return render(request, 'settings/users/form.html', {
        'form': form,
        'user': user,
        'title': f'Edit User: {user.username}'
    })


@login_required
@user_passes_test(is_staff)
def user_delete(request, user_id):
    """Delete a user."""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        if user == request.user:
            messages.error(request, 'You cannot delete your own account')
        else:
            username = user.username
            user.delete()
            messages.success(request, f'User "{username}" deleted successfully')
        return redirect('settings:user_list')
    
    return render(request, 'settings/users/delete.html', {'user_to_delete': user})
