=====================
django-tsvector-field
=====================

.. _introduction:

**django-tsvector-field** is a drop-in replacement for Django's
``django.contrib.postgres.search.SearchVectorField`` and manages the
database triggers to keep your search field updated automatically in
the background.


Installation
============

.. _installation:

**Python 3+**, **Django 1.11+** and **psycopg2** are the only requirements.

Install **django-tsvector-field** with your favorite python tool, e.g. ``pip install django-tsvector-field``.

You have two options to integrate **django-tsvector-field** into your project:

1. Simply add ``tsvector`` to your ``INSTALLED_APPS`` and start using it. This method
   uses Django's ``pre_migrate`` signal to inject the database operations into
   your migrations. This will work fine for most people.

   Warning: You'll run into issues with this method if you have unmigrated apps
   or you have disabled migrations for your unit tests. The problem is related
   to the fact that Django does not send ``pre_migrate`` signal for apps that
   do not have explicit migrations.

2. Less simple but more reliable method is to create your own database engine
   and to subclass the **django-tsvector-field** ``tsvector_field.DatabaseSchemaEditor``.

   Create a 'db' directory in your Django project with an `__init__.py` and a `base.py`
   with the following contents:

   .. code-block:: python

        from django.db.backends.postgresql import base
        import postgres_schema

        class DatabaseWrapper(base.DatabaseWrapper):
            SchemaEditorClass = tsvector_schema.DatabaseSchemaEditor

    Then update the ``'ENGINE'`` configuration in your ``DATABASE`` settings. For example,
    if your project is called ``my_project`` and it has the ``db`` directory as described
    above, then change your ``DATABASE`` setting to look like this:

   .. code-block:: python

        DATABASES = {
            'default': {
                'ENGINE': 'your_project.db',
            }
        }

Usage
=====

.. _usage:

``tsvector.SearchVectorField`` works like any other Django field: you add it to your model,
run ``makemigrations`` to add the ``AddField`` operation to your migrations and when you
migrate ``tsvector`` will take care to create the necessary postgres trigger and stored procedure.

Let's create a ``TextDocument`` model with a ``search`` field holding our ``tsvector`` and
having postgres automatically update it with ``title`` and ``body`` as inputs.

.. code-block:: python

    from django.db import models
    import tsvector

    class TextDocument(models.Model):
        title = models.CharField(max_length=128)
        body = models.TextField()
        search = tsvector.SearchVectorField([
            tsvector.WeightedColumn('title', 'A'),
            tsvector.WeightedColumn('body', 'D'),
        ], 'english')


After you've migrated you can create some ``TextDocument`` records and see that
postgres keeps it synchronized in the background. Specifically, because the
``search`` column is set at the database level, you need to call ``refresh_from_db()``
to get the updated search vector.


.. code-block:: python

    >>> doc = TextDocument.objects.create(
    ...     title="My hovercraft is full of spam.",
    ...     body="It's what eels love!"
    ... )
    >>> doc.search
    >>> doc.refresh_from_db()
    >>> doc.search
    "'eel':10 'full':4A 'hovercraft':2A 'love':11 'spam':6A"


Note that ``spam`` is recorded with ``6A``, this will be important later. Let's
continue with the previous session and create another document.


.. code-block:: python

    >>> doc = TextDocument.objects.create(
    ...     title="What do eels eat?",
    ...     body="Spam, spam, spam, they love spam!"
    ... )
    >>> doc.refresh_from_db()
    >>> doc.search
    "'eat':4A 'eel':3A 'love':9 'spam':5,6,7,10"


Now we have two documents: first document has just one ``spam`` with weight ``A`` and
the second document has 4 ``spam`` with lower weight. If we search for ``spam`` and apply
a search rank then the ``A`` weight on the first document will cause that document to
appear higher in the results.


.. code-block:: python

    >>> from django.contrib.postgres.search import SearchQuery, SearchRank
    >>> from django.db.models.expressions import F
    >>> matches = TextDocument.objects\
    ...     .annotate(rank=SearchRank(F('search'), SearchQuery('spam')))\
    ...     .order_by('-rank')\
    ...     .values_list('rank', 'title', 'body')
    >>> for match in matches:
    ...   print(match)
    ...
    (0.607927, 'My hovercraft is full of spam.', "It's what eels love!")
    (0.0865452, 'What do eels eat?', 'Spam, spam, spam, they love spam!')


If you are only interested in getting a list of possible matches without ranking
you can filter directly on the search column like so:

.. code-block:: python

    >>> TextDocument.objects.filter(search='spam')
    <QuerySet [<TextDocument: TextDocument object>, <TextDocument: TextDocument object>]>

For more information on querying, see the Django documentation on Full Text Search:

https://docs.djangoproject.com/en/dev/ref/contrib/postgres/search/

For more information on configuring how the searches work, see PostgreSQL docs:

https://www.postgresql.org/docs/devel/static/textsearch.html
