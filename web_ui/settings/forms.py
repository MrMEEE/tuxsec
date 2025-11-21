"""
Forms for settings app.
"""

from django import forms
from django.contrib.auth.models import User
from modules.models import Module


class ModuleSettingsForm(forms.ModelForm):
    """Form for module global settings."""
    
    class Meta:
        model = Module
        fields = ['enabled_globally', 'auto_enable_new_agents', 'configuration']
        widgets = {
            'configuration': forms.Textarea(attrs={'rows': 10, 'class': 'form-control font-monospace'}),
            'enabled_globally': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'auto_enable_new_agents': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class UserForm(forms.ModelForm):
    """Form for creating/editing users."""
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        help_text='Leave blank to keep current password (when editing)'
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        label='Confirm Password'
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password != password_confirm:
            raise forms.ValidationError('Passwords do not match')
        
        return cleaned_data
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make password required for new users
        if not self.instance.pk:
            self.fields['password'].required = True
            self.fields['password'].help_text = 'Required for new users'
