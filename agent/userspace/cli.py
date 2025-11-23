#!/usr/bin/env python3
"""
TuxSec CLI - Command-line interface for SSH mode.

This provides a command-line interface that can be invoked via SSH to
execute operations on the agent.

Usage:
    tuxsec-cli system-info
    tuxsec-cli firewall list-zones
    tuxsec-cli firewall add-service --zone public --service http
"""

import sys
import argparse
import json
from typing import Dict, Any

from .rootd_client import RootDaemonClient


class TuxSecCLI:
    """Command-line interface for tuxsec-agent."""
    
    def __init__(self):
        self.rootd = RootDaemonClient()
    
    def system_info(self) -> int:
        """Get system information."""
        try:
            info = self.rootd.get_system_info()
            print(json.dumps(info, indent=2))
            return 0
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
    
    def list_modules(self) -> int:
        """List available modules."""
        try:
            modules = self.rootd.list_modules()
            print("Available modules:")
            for module in modules:
                print(f"  - {module}")
            return 0
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
    
    def installed_modules(self) -> int:
        """List installed module packages."""
        try:
            modules = self.rootd.list_installed_modules()
            print(json.dumps({"modules": modules}))
            return 0
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
    
    def module_info(self, module: str) -> int:
        """Get information about a module."""
        try:
            info = self.rootd.get_module_info(module)
            print(json.dumps(info, indent=2))
            return 0
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
    
    def execute(self, module: str, action: str, parameters: Dict[str, Any]) -> int:
        """Execute a command."""
        try:
            result = self.rootd.execute_command(module, action, parameters)
            print(json.dumps(result, indent=2))
            return 0
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='TuxSec Agent CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  tuxsec-cli system-info
  tuxsec-cli list-modules
  tuxsec-cli module-info firewalld
  tuxsec-cli execute systeminfo get_hostname
  tuxsec-cli execute firewalld list_zones
  tuxsec-cli execute firewalld add_service --param zone=public --param service=http
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # system-info command
    subparsers.add_parser('system-info', help='Get system information')
    
    # list-modules command
    subparsers.add_parser('list-modules', help='List available modules')
    
    # installed-modules command
    subparsers.add_parser('installed-modules', help='List installed module packages')
    
    # module-info command
    module_info_parser = subparsers.add_parser('module-info', help='Get module information')
    module_info_parser.add_argument('module', help='Module name')
    
    # execute command
    execute_parser = subparsers.add_parser('execute', help='Execute a command')
    execute_parser.add_argument('module', help='Module name')
    execute_parser.add_argument('action', help='Action to perform')
    execute_parser.add_argument(
        '--param',
        action='append',
        dest='parameters',
        help='Parameter in format key=value (can be specified multiple times)'
    )
    execute_parser.add_argument(
        '--json',
        action='store_true',
        help='Provide parameters as JSON string'
    )
    execute_parser.add_argument(
        '--json-params',
        help='Parameters as JSON string'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    cli = TuxSecCLI()
    
    try:
        if args.command == 'system-info':
            return cli.system_info()
        
        elif args.command == 'list-modules':
            return cli.list_modules()
        
        elif args.command == 'installed-modules':
            return cli.installed_modules()
        
        elif args.command == 'module-info':
            return cli.module_info(args.module)
        
        elif args.command == 'execute':
            # Parse parameters
            parameters = {}
            
            if args.json_params:
                parameters = json.loads(args.json_params)
            elif args.parameters:
                for param in args.parameters:
                    if '=' not in param:
                        print(f"Invalid parameter format: {param}", file=sys.stderr)
                        return 1
                    key, value = param.split('=', 1)
                    
                    # Try to parse as JSON for complex types
                    try:
                        parameters[key] = json.loads(value)
                    except json.JSONDecodeError:
                        # Use as string if not valid JSON
                        parameters[key] = value
            
            return cli.execute(args.module, args.action, parameters)
        
        else:
            parser.print_help()
            return 1
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
