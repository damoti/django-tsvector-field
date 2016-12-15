from django.apps import AppConfig


class TextSearchVectorConfig(AppConfig):
    name = 'tsvector_field'

    def ready(self):
        """

        This supports two use cases for using tsvector_field:

        1. Configure your Django project to use tsvecotr_field's DatabaseSchemaEditor
           directly by creating your own DatabaseWrapper and referencing
           tsvector_field.DatabaseSchemaEditor in the SchemaEditorClass attribute.
           See: tsvector_field/schema.py for more info.

        2. Just add `tsvector_field` to your project's INSTALLED_APPS setting and this
           will use the `pre_migrate` mechanism. Note: `pre_migrate` is not fired for
           ./manage.py migrate --run-syncdb. So if you are building apps without migrations
           you will have to use the more reliable approach in option #1.

        """
        from django.db import connection
        from . import DatabaseSchemaEditor
        if not isinstance(connection.schema_editor(), DatabaseSchemaEditor):
            # only register for pre_migrate if we're not already configured
            # with the DatabaseSchemaEditor, see option #1 in doc above
            from django.db.models.signals import pre_migrate
            from .receivers import inject_trigger_operations
            pre_migrate.connect(inject_trigger_operations)
