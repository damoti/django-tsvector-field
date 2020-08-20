from tsvector_field import SearchVectorField
from django.db.backends.postgresql.schema import DatabaseSchemaEditor as PostgreSQLSchemaEditor
from django import VERSION as DJANGO_VERSION


class DatabaseSchemaEditor(PostgreSQLSchemaEditor):
    """

    A nice trick to managing multiple schema editors in your project is to
    merge them using the type() function like so (as long as all the editors
    properly call super() in the overloaded methods):

        import tsvector_field
        from . import schema as your_app_schema

        class DatabaseWrapper(base.DatabaseWrapper):
            SchemaEditorClass = type('DatabaseSchemaEditor', (
                tsvector_field.DatabaseSchemaEditor,
                your_app_schema.DatabaseSchemaEditor,
            ), {})

    """

    def create_model(self, model):
        super().create_model(model)
        DatabaseTriggerEditor(self).create_model(model)

    def delete_model(self, model):
        super().delete_model(model)
        DatabaseTriggerEditor(self).delete_model(model)

    def add_field(self, model, field):
        super().add_field(model, field)
        DatabaseTriggerEditor(self).add_field(model, field)

    def remove_field(self, model, field):
        super().remove_field(model, field)
        DatabaseTriggerEditor(self).remove_field(model, field)

    def alter_field(self, model, old_field, new_field, strict=False):
        super().alter_field(model, old_field, new_field)
        DatabaseTriggerEditor(self).alter_field(model, old_field, new_field)


class DatabaseTriggerEditor:

    def __init__(self, schema_editor):
        self.schema_editor = schema_editor
        self.deferred_sql = schema_editor.deferred_sql

    # Instead of directly inheriting from the DatabaseSchemaEditor
    # we piecemeal expose the necessary functionality in case something
    # changes in the base class that has unintended consequences.

    def quote_name(self, name):
        return self.schema_editor.quote_name(name)

    def quote_value(self, value):
        return self.schema_editor.quote_value(value)

    @property
    def connection(self):
        return self.schema_editor.connection

    def _create_index_name(self, model, column_names, suffix=""):
        if DJANGO_VERSION >= (2,):
            return self.schema_editor._create_index_name(model._meta.db_table, column_names, suffix)
        else:
            return self.schema_editor._create_index_name(model, column_names, suffix)

    def create_model(self, model):
        for field in model._meta.local_fields:
            if isinstance(field, SearchVectorField):
                self.deferred_sql.extend(self._create_tsvector(model, field))

    def delete_model(self, model):
        for field in model._meta.local_fields:
            if isinstance(field, SearchVectorField):
                self.deferred_sql.extend(self._drop_tsvector(model, field))

    def add_field(self, model, field):
        if isinstance(field, SearchVectorField):
            self.deferred_sql.extend(self._create_tsvector(model, field))

    def remove_field(self, model, field):
        if isinstance(field, SearchVectorField):
            self.deferred_sql.extend(self._drop_tsvector(model, field))

    def alter_field(self, model, old_field, new_field, strict=False):
        self.remove_field(model, old_field)
        self.add_field(model, new_field)

    def get_names(self, model, field):
        return (
            self._create_index_name(model, [field.column], '_tsvector'),
            self._create_index_name(model, [field.column], '_function')+'()',
            self._create_index_name(model, [field.column], '_trigger')
        )

    def _to_tsvector_weights(self, field):

        if field.language_column and field.language:
            language = 'COALESCE(NEW.{}::regconfig, {})'.format(
                self.quote_name(field.language_column),
                self.quote_value(field.language)
            )

        elif field.language_column:
            language = 'NEW.{}::regconfig'.format(
                self.quote_name(field.language_column)
            )

        else:
            language = self.quote_value(field.language or 'english')

        sql_setweight = (
            " setweight(to_tsvector({language}, COALESCE(NEW.{column}, '')), {weight}) ||"
        )

        weights = []
        for column in field.columns:
            weights.append(sql_setweight.format(
                language=language,
                column=self.quote_name(column.name),
                weight=self.quote_value(column.weight)
            ))
        weights[-1] = weights[-1][:-3] + ';'

        return weights

    def _to_tsvector(self, field):
        yield "NEW.{} :=".format(self.quote_name(field.column))
        yield from self._to_tsvector_weights(field)

    def _to_tsvector_preconditions(self, field):
        yield "IF (TG_OP = 'INSERT') THEN do_update = true;"
        yield "ELSIF (TG_OP = 'UPDATE') THEN"
        yield " IF (NEW.{column} IS NULL) THEN do_update = true;".format(
            column=self.quote_name(field.column)
        )

        for column in field.columns:
            yield " ELSIF (NEW.{column} IS DISTINCT FROM OLD.{column}) THEN do_update = true;".format(
                column=self.quote_name(column.name)
            )

        yield " END IF;"
        yield "END IF;"

    sql_create_function = (
        "CREATE FUNCTION {function} RETURNS trigger AS $$\n"
        "DECLARE\n"
        " do_update bool default false;\n"
        "BEGIN\n"
        " {preconditions}\n"
        " IF do_update THEN\n"
        "  {to_tsvector}\n"
        " END IF;\n"
        " RETURN NEW;\n"
        "END\n"
        "$$ LANGUAGE plpgsql"
    )

    def _create_function(self, function, field):
        preconditions = ["do_update = true;"]
        if not field.force_update:
            preconditions = self._to_tsvector_preconditions(field)
        return self.sql_create_function.format(
            function=function,
            preconditions='\n '.join(preconditions),
            to_tsvector='\n  '.join(self._to_tsvector(field))
        )

    sql_create_index = (
        "CREATE INDEX {index} ON {table} USING {index_type} ({column})"
    )

    sql_create_trigger = (
        "CREATE TRIGGER {trigger} BEFORE INSERT OR UPDATE"
        " ON {table} FOR EACH ROW EXECUTE PROCEDURE {function}"
    )

    def _create_tsvector(self, model, field):

        index, function, trigger = self.get_names(model, field)
        table = self.quote_name(model._meta.db_table)

        yield self.sql_create_index.format(
            index=self.quote_name(index),
            table=table,
            index_type='GIN',
            column=self.quote_name(field.column)
        )

        if not field.columns:
            return

        yield self._create_function(function, field)

        yield self.sql_create_trigger.format(
            trigger=self.quote_name(trigger),
            table=table,
            function=function,
        )

    def _drop_tsvector(self, model, field):

        index, function, trigger = self.get_names(model, field)
        table = self.quote_name(model._meta.db_table)

        yield "DROP TRIGGER IF EXISTS {trigger} ON {table}".format(
            trigger=trigger, table=table,
        )

        yield "DROP FUNCTION IF EXISTS {function}".format(
            function=function,
        )

        yield "DROP INDEX IF EXISTS {index}".format(
            index=index
        )
