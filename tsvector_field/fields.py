from django.core import checks
from django.db.models import CharField, TextField
from django.utils.encoding import force_text
from django.utils.itercompat import is_iterable
from django.contrib.postgres.search import SearchVectorField as OriginalSearchVectorField


class WeightedColumn:

    WEIGHTS = ('A', 'B', 'C', 'D')

    def __init__(self, name, weight):
        self.name = name
        self.weight = weight

    def check(self, field, searchable_columns):
        errors = []
        errors.extend(self._check_column_name(field, searchable_columns))
        errors.extend(self._check_weight(field, self.WEIGHTS))
        return errors

    def _check_column_name(self, field, columns):
        if self.name not in columns:
            yield checks.Error(
                '{}.name "{}" is not one of the available columns ({})'.format(
                    self.__class__.__name__, self.name,
                    ', '.join(['"{}"'.format(c) for c in columns])
                ), obj=field, id='postgres.E110',
            )

    def _check_weight(self, field, weights):
        if self.weight not in weights:
            yield checks.Error(
                '{}.weight "{}" is not one of the available weights ({})'.format(
                    self.__class__.__name__, self.weight,
                    ', '.join(['"{}"'.format(w) for w in weights])
                ), obj=field, id='postgres.E111',
            )

    def deconstruct(self):
        path = "tsvector_field.{}".format(self.__class__.__name__)
        return path, [force_text(self.name), force_text(self.weight)], {}


class SearchVectorField(OriginalSearchVectorField):

    def __init__(self, columns=None, language=None, *args, **kwargs):
        self.columns = columns
        self.language = language
        self.language_column = kwargs.pop('language_column', None)
        self.force_update = kwargs.pop('force_update', False)
        kwargs['db_index'] = False  # we create GIN index ourselves
        kwargs['null'] = True
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.columns is not None:
            kwargs['columns'] = self.columns
        if self.language is not None:
            kwargs['language'] = force_text(self.language)
        if self.language_column is not None:
            kwargs['language_column'] = force_text(self.language_column)
        if self.force_update is not False:
            kwargs['force_update'] = self.force_update
        del kwargs['null']
        return name, "tsvector_field.{}".format(self.__class__.__name__), args, kwargs

    def check(self, **kwargs):
        errors = super().check(**kwargs)
        textual_columns = self._find_textual_columns()
        errors.extend(self._check_columns_attribute(textual_columns))
        errors.extend(self._check_language_attributes(textual_columns))
        errors.extend(self._check_force_update_attribute())
        return errors

    def _find_textual_columns(self):
        columns = []
        # PostgreSQL trigger only has access to fields in the table, so we
        # need to make sure to exclude any fields from multi-table inheritance
        for field in self.model._meta.get_fields(include_parents=False):
            # too restrictive?
            if isinstance(field, (CharField, TextField)):
                columns.append(field.column)
        return columns

    def _check_columns_attribute(self, textual_columns):
        if not self.columns:
            return
        if not textual_columns:
            yield checks.Error(
                "No textual columns available in this model for search vector indexing.",
                obj=self, id='postgres.E100',
            )
        elif not is_iterable(self.columns) or \
                not all(isinstance(wc, WeightedColumn) for wc in self.columns):
            yield checks.Error(
                "'columns' must be an iterable containing WeightedColumn instances",
                obj=self, id='postgres.E101',
            )
        else:
            for column in self.columns:
                for error in column.check(self, textual_columns):
                    yield error

    def _check_language_attributes(self, textual_columns):
        if self.columns and not any((self.language, self.language_column)):
            yield checks.Error(
                "'language' or 'language_column' is required when 'columns' is provided",
                obj=self, id='postgres.E102',
            )
            return
        if self.language and not isinstance(self.language, str):
            # can we get list of available langauges?
            yield checks.Error(
                "'language' must be a valid language",
                obj=self, id='postgres.E103',
            )
        if self.language_column and self.language_column not in textual_columns:
            yield checks.Error(
                """'language_column' "{}" is not one of the available columns ({})""".format(
                    self.name, ', '.join(['"{}"'.format(c) for c in textual_columns])
                ), obj=self, id='postgres.E104',
            )

    def _check_force_update_attribute(self):
        if self.force_update not in (None, True, False):
            yield checks.Error(
                "'force_update' must be None, True or False.",
                obj=self, id='postgres.E105',
            )
