from tsvector import SearchVectorField
from django.db.backends.postgresql.schema import DatabaseSchemaEditor


class TriggerSchemaEditor(DatabaseSchemaEditor):

    def create_model(self, model):
        for field in model._meta.local_fields:
            if isinstance(field, SearchVectorField) and field.columns:
                self.deferred_sql.extend(self._create_tsvector_trigger(model, field))

    def delete_model(self, model):
        for field in model._meta.local_fields:
            if isinstance(field, SearchVectorField):
                self.deferred_sql.extend(self._drop_tsvector_trigger(model, field))

    def add_field(self, model, field):
        if isinstance(field, SearchVectorField) and field.columns:
            self.deferred_sql.extend(self._create_tsvector_trigger(model, field))

    def remove_field(self, model, field):
        if isinstance(field, SearchVectorField):
            self.deferred_sql.extend(self._drop_tsvector_trigger(model, field))

    def alter_field(self, model, old_field, new_field, strict=False):
        self.remove_field(model, old_field)
        self.add_field(model, new_field)

    def _tsvector_setweight(self, field):

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
            "setweight(to_tsvector({language}, COALESCE(NEW.{column}, '')), {weight}) ||"
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

    def _tsvector_update_column_checks(self, field):
        checks = []
        for column in field.columns:
            checks.append(
                "ELSIF (NEW.{column} <> OLD.{column}) THEN do_update = true;".format(
                    column=self.quote_name(column.name)
                )
            )
        checks[0] = checks[0][3:]
        checks.append('END IF;')
        return checks

    sql_tsvector_create_trigger_function = (
        "CREATE FUNCTION {function}() RETURNS trigger AS $$\n"
        "DECLARE\n"
        " do_update bool default false;\n"
        "BEGIN\n"
        " {update_checks}\n"
        " IF do_update THEN\n"
        "  {update_body}\n"
        " END IF;\n"
        " RETURN NEW;\n"
        "END\n"
        "$$ LANGUAGE plpgsql"
    )

    def _create_tsvector_update_function(self, function, field):

        update_checks = ["do_update = true;"]
        if not field.force_update:
            update_checks = [
                                "IF (TG_OP = 'INSERT') THEN do_update = true;",
                                "ELSIF (TG_OP = 'UPDATE') THEN"] + [
                                ' ' + check for check in self._tsvector_update_column_checks(field)] + [
                                "END IF;"
                            ]

        update_body = [
                          "NEW.{} :=".format(self.quote_name(field.column))] + [
                          ' ' + weight for weight in self._tsvector_setweight(field)
                          ]

        return self.sql_tsvector_create_trigger_function.format(
            function=function,
            update_checks='\n '.join(update_checks),
            update_body='\n  '.join(update_body)
        )

    sql_create_insert_or_update_trigger = (
        "CREATE TRIGGER {trigger} BEFORE INSERT OR UPDATE"
        " ON {table} FOR EACH ROW EXECUTE PROCEDURE {function}()"
    )

    def _create_tsvector_trigger(self, model, field):

        assert field.columns, "Cannot create text search trigger without 'columns'."

        tsvector_function = self._create_index_name(model, [field.column], '_func')
        tsvector_trigger = self._create_index_name(model, [field.column], '_trig')

        yield self._create_tsvector_update_function(tsvector_function, field)

        yield self.sql_create_insert_or_update_trigger.format(
            table=self.quote_name(model._meta.db_table),
            trigger=self.quote_name(tsvector_trigger),
            function=tsvector_function,
        )

    sql_drop_trigger = "DROP TRIGGER IF EXISTS {trigger} ON {table}"
    sql_drop_trigger_function = "DROP FUNCTION IF EXISTS {function}()"

    def _drop_tsvector_trigger(self, model, field):

        tsvector_function = self._create_index_name(model, [field.column], '_func')
        tsvector_trigger = self._create_index_name(model, [field.column], '_trig')

        yield self.sql_drop_trigger.format(
            table=self.quote_name(model._meta.db_table),
            trigger=tsvector_trigger,
        )

        yield self.sql_drop_trigger_function.format(
            function=tsvector_function,
        )
