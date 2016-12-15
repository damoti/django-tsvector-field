from .fields import SearchVectorField, WeightedColumn
from .schema import DatabaseSchemaEditor
from .query import Headline
from .operations import IndexSearchVector

default_app_config = 'tsvector_field.apps.TextSearchVectorConfig'
