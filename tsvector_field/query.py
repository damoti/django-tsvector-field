from django.db import models
from django.contrib.postgres.search import Value, Func


class Headline(Func):
    function = 'ts_headline'

    def __init__(self, field, query, config=None, options=None, **extra):
        expressions = [field, query]
        if config:
            expressions.insert(0, Value(config))
        if options:
            expressions.append(Value(options))
        extra.setdefault('output_field', models.TextField())
        super().__init__(*expressions, **extra)
