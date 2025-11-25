"""Management command to seed firewall templates."""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from agents.models import FirewallTemplate

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed the database with predefined firewall templates'

    def handle(self, *args, **kwargs):
        # Get or create a system user for templates
        system_user, _ = User.objects.get_or_create(
            username='system',
            defaults={
                'email': 'system@tuxsec.local',
                'is_active': True,
            }
        )

        templates = [
            {
                'name': 'Basic Web Server',
                'description': 'Basic configuration for a web server with HTTP/HTTPS',
                'category': 'server',
                'is_global': True,
                'configuration': {
                    'zones': {
                        'public': {
                            'services': ['ssh', 'http', 'https'],
                            'ports': [],
                            'interfaces': [],
                            'sources': [],
                            'icmp_blocks': [],
                            'helpers': [],
                            'target': 'default',
                            'masquerade': False,
                            'forward_ports': []
                        }
                    },
                    'policies': [],
                    'custom_services': [],
                    'ipsets': []
                },
                'tags': ['web', 'server', 'http', 'https']
            },
            {
                'name': 'Database Server',
                'description': 'Configuration for database servers (MySQL/PostgreSQL)',
                'category': 'server',
                'is_global': True,
                'configuration': {
                    'zones': {
                        'internal': {
                            'services': ['ssh', 'mysql', 'postgresql'],
                            'ports': [],
                            'interfaces': [],
                            'sources': [],
                            'icmp_blocks': ['echo-request'],
                            'helpers': [],
                            'target': 'default',
                            'masquerade': False,
                            'forward_ports': []
                        }
                    },
                    'policies': [],
                    'custom_services': [],
                    'ipsets': []
                },
                'tags': ['database', 'server', 'mysql', 'postgresql']
            },
            {
                'name': 'DMZ Web Server',
                'description': 'DMZ configuration with strict rules and limited ICMP',
                'category': 'dmz',
                'is_global': True,
                'configuration': {
                    'zones': {
                        'dmz': {
                            'services': ['ssh', 'http', 'https'],
                            'ports': [],
                            'interfaces': [],
                            'sources': [],
                            'icmp_blocks': ['echo-request', 'timestamp-request'],
                            'helpers': [],
                            'target': 'default',
                            'masquerade': False,
                            'forward_ports': []
                        }
                    },
                    'policies': [
                        {
                            'name': 'dmz-to-internal-deny',
                            'ingress_zone': 'dmz',
                            'egress_zone': 'internal',
                            'target': 'REJECT'
                        }
                    ],
                    'custom_services': [],
                    'ipsets': []
                },
                'tags': ['dmz', 'web', 'restricted', 'security']
            },
            {
                'name': 'Office Workstation',
                'description': 'Standard configuration for office workstations',
                'category': 'workstation',
                'is_global': True,
                'configuration': {
                    'zones': {
                        'work': {
                            'services': ['ssh', 'dhcpv6-client', 'mdns', 'samba-client'],
                            'ports': [],
                            'interfaces': [],
                            'sources': [],
                            'icmp_blocks': [],
                            'helpers': [],
                            'target': 'default',
                            'masquerade': False,
                            'forward_ports': []
                        }
                    },
                    'policies': [],
                    'custom_services': [],
                    'ipsets': []
                },
                'tags': ['workstation', 'office', 'desktop']
            },
            {
                'name': 'Home Network',
                'description': 'Configuration for home network with media sharing',
                'category': 'network',
                'is_global': True,
                'configuration': {
                    'zones': {
                        'home': {
                            'services': ['ssh', 'mdns', 'samba-client', 'dhcpv6-client'],
                            'ports': [],
                            'interfaces': [],
                            'sources': [],
                            'icmp_blocks': [],
                            'helpers': [],
                            'target': 'default',
                            'masquerade': False,
                            'forward_ports': []
                        }
                    },
                    'policies': [],
                    'custom_services': [],
                    'ipsets': []
                },
                'tags': ['home', 'network', 'personal']
            },
            {
                'name': 'NAT Gateway',
                'description': 'NAT gateway configuration with masquerading',
                'category': 'network',
                'is_global': True,
                'configuration': {
                    'zones': {
                        'external': {
                            'services': ['ssh'],
                            'ports': [],
                            'interfaces': [],
                            'sources': [],
                            'icmp_blocks': ['echo-request'],
                            'helpers': [],
                            'target': 'default',
                            'masquerade': True,
                            'forward_ports': []
                        },
                        'internal': {
                            'services': ['ssh', 'dhcpv6-client'],
                            'ports': [],
                            'interfaces': [],
                            'sources': [],
                            'icmp_blocks': [],
                            'helpers': [],
                            'target': 'default',
                            'masquerade': False,
                            'forward_ports': []
                        }
                    },
                    'policies': [],
                    'custom_services': [],
                    'ipsets': []
                },
                'tags': ['nat', 'gateway', 'router', 'masquerade']
            },
            {
                'name': 'High Security Server',
                'description': 'Locked down server with minimal services',
                'category': 'server',
                'is_global': True,
                'configuration': {
                    'zones': {
                        'public': {
                            'services': ['ssh'],
                            'ports': [],
                            'interfaces': [],
                            'sources': [],
                            'icmp_blocks': ['echo-request', 'timestamp-request', 'timestamp-reply'],
                            'helpers': [],
                            'target': 'DROP',
                            'masquerade': False,
                            'forward_ports': []
                        }
                    },
                    'policies': [],
                    'custom_services': [],
                    'ipsets': [
                        {
                            'name': 'admin-whitelist',
                            'type': 'hash:ip',
                            'entries': [],
                            'description': 'Administrator IP whitelist'
                        }
                    ]
                },
                'tags': ['security', 'locked-down', 'minimal', 'restricted']
            },
            {
                'name': 'Container Host',
                'description': 'Configuration for Docker/container hosts',
                'category': 'server',
                'is_global': True,
                'configuration': {
                    'zones': {
                        'public': {
                            'services': ['ssh', 'http', 'https'],
                            'ports': [],
                            'interfaces': [],
                            'sources': [],
                            'icmp_blocks': [],
                            'helpers': [],
                            'target': 'default',
                            'masquerade': False,
                            'forward_ports': []
                        },
                        'trusted': {
                            'services': [],
                            'ports': [],
                            'interfaces': ['docker0'],
                            'sources': ['172.17.0.0/16'],
                            'icmp_blocks': [],
                            'helpers': [],
                            'target': 'ACCEPT',
                            'masquerade': False,
                            'forward_ports': []
                        }
                    },
                    'policies': [],
                    'custom_services': [],
                    'ipsets': []
                },
                'tags': ['docker', 'container', 'kubernetes', 'server']
            }
        ]

        created_count = 0
        updated_count = 0

        for template_data in templates:
            template, created = FirewallTemplate.objects.update_or_create(
                name=template_data['name'],
                defaults={
                    'description': template_data['description'],
                    'category': template_data['category'],
                    'is_global': template_data['is_global'],
                    'configuration': template_data['configuration'],
                    'tags': template_data['tags'],
                    'created_by': system_user,
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Created template: {template.name}'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'↻ Updated template: {template.name}'))

        self.stdout.write(self.style.SUCCESS(f'\n{created_count} templates created, {updated_count} templates updated'))
