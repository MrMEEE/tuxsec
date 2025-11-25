from django import forms
from .models import Agent


class AgentForm(forms.ModelForm):
    """Form for creating and editing agents"""
    
    # Add a password field that isn't required for edits
    ssh_password_input = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Leave blank to keep existing password'
        }),
        label='SSH Password',
        help_text='SSH password (leave blank when editing to keep existing password)'
    )
    
    class Meta:
        model = Agent
        fields = [
            'hostname', 'ip_address', 'connection_type', 'port',
            'ssh_username', 'ssh_private_key',
            'agent_port', 'agent_api_key', 'sync_interval_seconds', 'description'
        ]
        widgets = {
            'hostname': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter hostname'
            }),
            'ip_address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '192.168.1.100'
            }),
            'connection_type': forms.Select(attrs={
                'class': 'form-select',
                'id': 'connection_type'
            }),
            'port': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '22 (SSH) or 8443 (HTTPS)'
            }),
            'ssh_username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'root'
            }),
            'ssh_private_key': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8,
                'placeholder': '-----BEGIN OPENSSH PRIVATE KEY-----\n...\n-----END OPENSSH PRIVATE KEY-----',
                'style': 'font-family: monospace; font-size: 0.875rem;'
            }),
            'agent_port': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '8444'
            }),
            'agent_api_key': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'API key for agent authentication'
            }),
            'sync_interval_seconds': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '60',
                'min': '0',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional description of this agent'
            }),
        }
        help_texts = {
            'sync_interval_seconds': 'Auto-sync interval in seconds (0 to disable)',
            'ssh_private_key': 'Paste your SSH private key here (use key-based auth when possible)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # For editing, populate the password input field if there's an existing password
        if self.instance.pk and self.instance.ssh_password:
            self.fields['ssh_password_input'].initial = self.instance.ssh_password
        
        # Set default ports based on connection type
        if not self.instance.pk:  # New instance
            self.initial['port'] = 22  # Default to SSH port
            self.initial['agent_port'] = 8444
            self.initial['sync_interval_seconds'] = 60  # Default 60 seconds

    def clean(self):
        cleaned_data = super().clean()
        connection_type = cleaned_data.get('connection_type')
        ssh_username = cleaned_data.get('ssh_username')
        ssh_private_key = cleaned_data.get('ssh_private_key')
        ssh_password_input = cleaned_data.get('ssh_password_input')
        agent_api_key = cleaned_data.get('agent_api_key')
        
        # Handle password: use new password if provided, otherwise keep old one
        if ssh_password_input:
            # New password provided
            cleaned_data['ssh_password'] = ssh_password_input
        elif self.instance.pk:
            # Editing and no new password - keep existing
            cleaned_data['ssh_password'] = self.instance.ssh_password
        else:
            # Creating new agent with no password
            cleaned_data['ssh_password'] = ''

        # Validation for SSH connections
        if connection_type == 'ssh':
            if not ssh_username:
                raise forms.ValidationError("SSH username is required for SSH connections.")
            
            if not ssh_private_key and not cleaned_data.get('ssh_password'):
                raise forms.ValidationError(
                    "Either SSH private key or SSH password is required for SSH connections."
                )
            
            # Test SSH connection only if credentials are provided
            if ssh_private_key or ssh_password_input:
                # Only test if key/password provided
                test_result = self._test_ssh_connection(
                    cleaned_data.get('ip_address'),
                    cleaned_data.get('port', 22),
                    ssh_username,
                    ssh_private_key,
                    cleaned_data.get('ssh_password')
                )
                if not test_result['success']:
                    raise forms.ValidationError(
                        f"SSH connection test failed: {test_result.get('error', 'Unknown error')}"
                    )

        # Validation for server-to-agent connections
        if connection_type == 'server_to_agent':
            if not agent_api_key:
                raise forms.ValidationError(
                    "API key is required for server-to-agent connections."
                )

        return cleaned_data
    
    def _test_ssh_connection(self, host, port, username, private_key, password):
        """Test SSH connection with given credentials."""
        try:
            import paramiko
            import io
            
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            connect_kwargs = {
                'hostname': host,
                'port': port,
                'username': username,
                'timeout': 10,
            }
            
            if private_key:
                # Use private key
                try:
                    key_file = io.StringIO(private_key)
                    pkey = paramiko.RSAKey.from_private_key(key_file)
                    connect_kwargs['pkey'] = pkey
                except Exception as e:
                    try:
                        key_file = io.StringIO(private_key)
                        pkey = paramiko.Ed25519Key.from_private_key(key_file)
                        connect_kwargs['pkey'] = pkey
                    except:
                        return {'success': False, 'error': f'Invalid private key format: {str(e)}'}
            elif password:
                connect_kwargs['password'] = password
            else:
                return {'success': False, 'error': 'No authentication method provided'}
            
            client.connect(**connect_kwargs)
            client.close()
            
            return {'success': True}
            
        except paramiko.AuthenticationException:
            return {'success': False, 'error': 'Authentication failed - check username/password/key'}
        except paramiko.SSHException as e:
            return {'success': False, 'error': f'SSH error: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': f'Connection failed: {str(e)}'}
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set the password if it was provided
        if 'ssh_password' in self.cleaned_data:
            instance.ssh_password = self.cleaned_data['ssh_password']
        
        if commit:
            instance.save()
        
        return instance
