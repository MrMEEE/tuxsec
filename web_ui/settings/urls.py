"""
URL configuration for settings app.
"""

from django.urls import path
from . import views

app_name = 'settings'

urlpatterns = [
    # Settings home
    path('', views.settings_home, name='home'),
    
    # Module management
    path('modules/', views.module_list, name='module_list'),
    path('modules/<str:module_name>/', views.module_detail, name='module_detail'),
    path('modules/<str:module_name>/toggle/', views.module_toggle, name='module_toggle'),
    path('modules/<str:module_name>/agent/<int:agent_id>/toggle/', 
         views.module_agent_toggle, name='module_agent_toggle'),
    path('modules/<str:module_name>/enable-all/', views.module_enable_all, name='module_enable_all'),
    path('modules/<str:module_name>/disable-all/', views.module_disable_all, name='module_disable_all'),
    
    # User management
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:user_id>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:user_id>/delete/', views.user_delete, name='user_delete'),
]
