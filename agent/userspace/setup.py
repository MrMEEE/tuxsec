#!/usr/bin/env python3
"""
TuxSec Agent Setup Tool

Interactive configuration tool for setting up the TuxSec agent.
Helps configure connection mode, server settings, and credentials.
"""

import os
import sys
import yaml
import getpass
import socket
from pathlib import Path


class Colors:
    """ANSI color codes."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text):
    """Print a header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(70)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}\n")


def print_success(text):
    """Print success message."""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_error(text):
    """Print error message."""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_info(text):
    """Print info message."""
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


def print_warning(text):
    """Print warning message."""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def get_input(prompt, default=None):
    """Get user input with optional default."""
    if default:
        prompt = f"{prompt} [{default}]"
    
    value = input(f"{Colors.OKBLUE}{prompt}: {Colors.ENDC}").strip()
    
    if not value and default:
        return default
    
    return value


def get_choice(prompt, choices, default=None):
    """Get user choice from a list."""
    print(f"\n{Colors.OKBLUE}{prompt}{Colors.ENDC}")
    
    for i, choice in enumerate(choices, 1):
        marker = " (default)" if default and choice == default else ""
        print(f"  {i}. {choice}{marker}")
    
    while True:
        value = input(f"\n{Colors.OKBLUE}Enter choice [1-{len(choices)}]: {Colors.ENDC}").strip()
        
        if not value and default:
            return default
        
        try:
            idx = int(value) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        except ValueError:
            pass
        
        print_error(f"Invalid choice. Please enter a number between 1 and {len(choices)}.")


def yes_no(prompt, default=True):
    """Ask a yes/no question."""
    default_str = "Y/n" if default else "y/N"
    value = input(f"{Colors.OKBLUE}{prompt} [{default_str}]: {Colors.ENDC}").strip().lower()
    
    if not value:
        return default
    
    return value in ['y', 'yes']


def check_root():
    """Check if running as root."""
    if os.geteuid() != 0:
        print_error("This setup tool must be run as root.")
        print_info("Please run: sudo tuxsec-setup")
        sys.exit(1)


def check_tuxsec_user():
    """Check if tuxsec user exists."""
    try:
        import pwd
        pwd.getpwnam('tuxsec')
        return True
    except KeyError:
        return False


def create_tuxsec_user():
    """Create tuxsec user if it doesn't exist."""
    if check_tuxsec_user():
        print_success("User 'tuxsec' already exists")
        return
    
    print_info("Creating 'tuxsec' user...")
    
    try:
        os.system("useradd --system --shell /bin/bash --create-home --home-dir /var/lib/tuxsec tuxsec")
        print_success("User 'tuxsec' created successfully")
    except Exception as e:
        print_error(f"Failed to create user: {e}")
        sys.exit(1)


def setup_directories():
    """Create required directories with correct permissions."""
    print_info("Setting up directories...")
    
    directories = [
        ('/etc/tuxsec', 'root', 'root', 0o755),
        ('/etc/tuxsec/certs', 'root', 'tuxsec', 0o750),
        ('/var/run/tuxsec', 'root', 'tuxsec', 0o770),
        ('/var/log/tuxsec', 'tuxsec', 'tuxsec', 0o755),
        ('/var/lib/tuxsec', 'tuxsec', 'tuxsec', 0o755),
    ]
    
    for path, owner, group, mode in directories:
        os.makedirs(path, mode=0o755, exist_ok=True)
        os.chmod(path, mode)
        os.system(f"chown {owner}:{group} {path}")
    
    print_success("Directories created with correct permissions")


def get_hostname():
    """Get system hostname."""
    return socket.gethostname()


def get_local_ip():
    """Get local IP address."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def configure_pull_mode():
    """Configure pull mode settings."""
    print_header("Pull Mode Configuration")
    print_info("In pull mode, the agent polls the TuxSec server for jobs.")
    print_info("This is ideal for agents behind firewalls or NAT.\n")
    
    config = {}
    config['mode'] = 'pull'
    
    # Server URL
    config['server_url'] = get_input(
        "TuxSec Server URL",
        "https://tuxsec.example.com"
    )
    
    # Agent ID (optional, can be set during registration)
    if yes_no("Do you have an agent ID already?", False):
        config['agent_id'] = get_input("Agent ID")
    else:
        config['agent_id'] = None
        print_info("Agent ID will be assigned during registration")
    
    # API Key (optional, can be set during registration)
    if yes_no("Do you have an API key already?", False):
        config['api_key'] = getpass.getpass("API Key: ")
    else:
        config['api_key'] = None
        print_info("API key will be assigned during registration")
    
    # Poll interval
    poll_interval = get_input("Poll interval (seconds)", "30")
    config['poll_interval'] = int(poll_interval)
    
    return config


def configure_push_mode():
    """Configure push mode settings."""
    print_header("Push Mode Configuration")
    print_info("In push mode, the TuxSec server connects to the agent.")
    print_info("The agent listens on a port for incoming connections.\n")
    
    config = {}
    config['mode'] = 'push'
    
    # Server URL (for registration/heartbeat)
    config['server_url'] = get_input(
        "TuxSec Server URL",
        "https://tuxsec.example.com"
    )
    
    # Listen settings
    config['listen_host'] = get_input("Listen address", "0.0.0.0")
    
    listen_port = get_input("Listen port", "8443")
    config['listen_port'] = int(listen_port)
    
    # Agent ID and API Key
    if yes_no("Do you have an agent ID and API key?", False):
        config['agent_id'] = get_input("Agent ID")
        config['api_key'] = getpass.getpass("API Key: ")
    else:
        config['agent_id'] = None
        config['api_key'] = None
        print_info("Agent ID and API key will be assigned during registration")
    
    return config


def configure_ssh_mode():
    """Configure SSH mode settings."""
    print_header("SSH Mode Configuration")
    print_info("In SSH mode, the TuxSec server connects via SSH.")
    print_info("Commands are executed through the tuxsec-cli tool.\n")
    
    config = {}
    config['mode'] = 'ssh'
    
    print_info("For SSH mode, you need to:")
    print_info("1. Add the TuxSec server's SSH public key to ~tuxsec/.ssh/authorized_keys")
    print_info("2. Ensure the tuxsec user can execute tuxsec-cli")
    print_info("3. Configure the server to use SSH connection type for this agent\n")
    
    # SSH doesn't need much config, but we still track the server URL
    config['server_url'] = get_input(
        "TuxSec Server URL (for reference)",
        "https://tuxsec.example.com"
    )
    
    config['agent_id'] = None
    config['api_key'] = None
    
    return config


def configure_ssl_certs(config):
    """Configure SSL certificate paths."""
    print_header("SSL/TLS Configuration")
    
    if config['mode'] == 'ssh':
        print_info("SSH mode doesn't require SSL certificates for the agent.")
        config['ssl_cert'] = None
        config['ssl_key'] = None
        config['ca_cert'] = None
        return
    
    print_info("SSL/TLS certificates are needed for secure communication.\n")
    
    if yes_no("Do you have SSL certificates?", False):
        config['ssl_cert'] = get_input("Certificate file path", "/etc/tuxsec/certs/agent.crt")
        config['ssl_key'] = get_input("Private key file path", "/etc/tuxsec/certs/agent.key")
        config['ca_cert'] = get_input("CA certificate path", "/etc/tuxsec/certs/ca.crt")
    else:
        print_warning("You'll need to generate SSL certificates before starting the agent.")
        print_info("Default paths will be used:")
        config['ssl_cert'] = "/etc/tuxsec/certs/agent.crt"
        config['ssl_key'] = "/etc/tuxsec/certs/agent.key"
        config['ca_cert'] = "/etc/tuxsec/certs/ca.crt"


def configure_logging(config):
    """Configure logging settings."""
    print_header("Logging Configuration")
    
    log_level = get_choice(
        "Log level",
        ["DEBUG", "INFO", "WARNING", "ERROR"],
        "INFO"
    )
    config['log_level'] = log_level
    
    config['log_file'] = get_input("Log file path", "/var/log/tuxsec/agent.log")


def save_config(config):
    """Save configuration to file."""
    config_file = "/etc/tuxsec/agent.yaml"
    
    print_header("Saving Configuration")
    print_info(f"Configuration will be saved to: {config_file}")
    
    # Add default rootd socket path
    config['rootd_socket'] = '/var/run/tuxsec/rootd.sock'
    
    try:
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        # Set correct permissions
        os.chmod(config_file, 0o640)
        os.system(f"chown root:tuxsec {config_file}")
        
        print_success(f"Configuration saved to {config_file}")
        return True
    except Exception as e:
        print_error(f"Failed to save configuration: {e}")
        return False


def enable_services():
    """Enable and start systemd services."""
    print_header("Systemd Services")
    
    if not yes_no("Enable and start services now?", True):
        print_info("You can start services later with:")
        print_info("  systemctl start tuxsec-rootd tuxsec-agent")
        return
    
    print_info("Enabling services...")
    os.system("systemctl daemon-reload")
    os.system("systemctl enable tuxsec-rootd tuxsec-agent")
    
    print_info("Starting tuxsec-rootd...")
    ret = os.system("systemctl start tuxsec-rootd")
    if ret == 0:
        print_success("tuxsec-rootd started successfully")
    else:
        print_error("Failed to start tuxsec-rootd")
        print_info("Check logs with: journalctl -u tuxsec-rootd -e")
        return
    
    print_info("Starting tuxsec-agent...")
    ret = os.system("systemctl start tuxsec-agent")
    if ret == 0:
        print_success("tuxsec-agent started successfully")
    else:
        print_error("Failed to start tuxsec-agent")
        print_info("Check logs with: journalctl -u tuxsec-agent -e")


def show_summary(config):
    """Show configuration summary."""
    print_header("Configuration Summary")
    
    print(f"{Colors.BOLD}Connection Mode:{Colors.ENDC} {config['mode']}")
    print(f"{Colors.BOLD}Server URL:{Colors.ENDC} {config.get('server_url', 'N/A')}")
    
    if config.get('agent_id'):
        print(f"{Colors.BOLD}Agent ID:{Colors.ENDC} {config['agent_id']}")
    
    if config['mode'] == 'pull':
        print(f"{Colors.BOLD}Poll Interval:{Colors.ENDC} {config['poll_interval']} seconds")
    elif config['mode'] == 'push':
        print(f"{Colors.BOLD}Listen Address:{Colors.ENDC} {config['listen_host']}:{config['listen_port']}")
    
    print(f"{Colors.BOLD}Log Level:{Colors.ENDC} {config['log_level']}")
    print(f"{Colors.BOLD}Log File:{Colors.ENDC} {config['log_file']}")


def show_next_steps(config):
    """Show next steps after setup."""
    print_header("Next Steps")
    
    if config['mode'] == 'pull':
        if not config.get('agent_id'):
            print_info("1. Register the agent with your TuxSec server")
            print_info("   The agent will receive an ID and API key")
    
    elif config['mode'] == 'push':
        print_info("1. Ensure firewall allows incoming connections on port " + str(config['listen_port']))
        print_info(f"   Example: firewall-cmd --add-port={config['listen_port']}/tcp --permanent")
        if not config.get('agent_id'):
            print_info("2. Register the agent with your TuxSec server")
    
    elif config['mode'] == 'ssh':
        print_info("1. Add TuxSec server's SSH public key to ~tuxsec/.ssh/authorized_keys")
        print_info("2. Configure the agent in TuxSec server web UI with SSH connection type")
        print_info("3. Test SSH connection: ssh tuxsec@" + get_hostname())
    
    print_info("\nCheck service status:")
    print_info("  systemctl status tuxsec-rootd")
    print_info("  systemctl status tuxsec-agent")
    
    print_info("\nView logs:")
    print_info("  journalctl -u tuxsec-rootd -f")
    print_info("  journalctl -u tuxsec-agent -f")
    
    print_info("\nTest the agent:")
    print_info("  sudo -u tuxsec tuxsec-cli system-info")


def main():
    """Main setup flow."""
    print_header("TuxSec Agent Setup")
    print_info(f"Hostname: {get_hostname()}")
    print_info(f"IP Address: {get_local_ip()}\n")
    
    # Check root
    check_root()
    
    # Create user and directories
    create_tuxsec_user()
    setup_directories()
    
    # Choose connection mode
    print_header("Connection Mode")
    mode = get_choice(
        "Select connection mode",
        ["pull", "push", "ssh"],
        "pull"
    )
    
    # Configure based on mode
    if mode == "pull":
        config = configure_pull_mode()
    elif mode == "push":
        config = configure_push_mode()
    else:
        config = configure_ssh_mode()
    
    # SSL/TLS configuration
    configure_ssl_certs(config)
    
    # Logging configuration
    configure_logging(config)
    
    # Show summary
    show_summary(config)
    
    # Confirm and save
    if not yes_no("\nSave this configuration?", True):
        print_warning("Setup cancelled.")
        sys.exit(0)
    
    if not save_config(config):
        sys.exit(1)
    
    # Enable services
    enable_services()
    
    # Show next steps
    show_next_steps(config)
    
    print_success("\n✓ Setup complete!")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print_warning("\n\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print_error(f"\nUnexpected error: {e}")
        sys.exit(1)
