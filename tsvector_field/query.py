from django.db import models
from django.contrib.postgres.search import Value, Func


class Headline(Func):
    function = 'ts_headline'
    _output_field = models.TextField()

    def __init__(self, field, query, config=None, options=None, **extra):
        expressions = [field, query]
        if config:
            expressions.insert(0, Value(config))
        if options:
            expressions.append(Value(options))
        super().__init__(*expressions, **extra)
