from django.db.migrations.operations.fields import FieldOperation
from .fields import SearchVectorField


class IndexSearchVector(FieldOperation):

    def state_forwards(self, app_label, state):
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        to_model = to_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, to_model):
            to_field = to_model._meta.get_field(self.name)
            assert isinstance(to_field, SearchVectorField)
            schema_editor.deferred_sql.append(
                'UPDATE {table} SET {column} = NULL'.format(
                    column=to_field.column,
                    table=to_model._meta.db_table
                )
            )

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        pass

    def describe(self):
        return "Runs full text search indexing on '%s' field from %s" % (self.name, self.model_name)
