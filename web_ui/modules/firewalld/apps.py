from django.apps import AppConfig


class FirewalldConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.firewalld'
    label = 'firewalld'
    verbose_name = 'Firewalld Management'
