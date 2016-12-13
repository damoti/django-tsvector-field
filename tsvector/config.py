from django.apps import AppConfig
from django.db.models.signals import pre_migrate


from .migrate import inject_trigger_operations


class TextSearchVectorConfig(AppConfig):
    name = 'tsvector'

    def ready(self):
        pre_migrate.connect(inject_trigger_operations)
