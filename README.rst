=====================
django-tsvector-field
=====================

.. _introduction:

**django-tsvector-field** is a drop-in replacement for Django's
``django.contrib.postgres.search.SearchVectorField`` field that manages the
database triggers to keep your search field updated automatically in
the background.


Installation
============

.. _installation:

**Python 3+**, **Django 1.11+** and **psycopg2** are the only requirements.

Install **django-tsvector-field** with your favorite python tool, e.g. ``pip install django-tsvector-field``.

You have two options to integrate it into your project:

1. Simply add ``tsvector_field`` to your ``INSTALLED_APPS`` and start using it. This method
   uses Django's ``pre_migrate`` signal to inject the database operations into
   your migrations. This will work fine for many use cases.

   However, you'll run into issues with this method if you have unmigrated apps
   or you have disabled migrations for your unit tests. The problem is related
   to the fact that Django does not send ``pre_migrate`` signal for apps that
   do not have explicit migrations.

2. Less simple but more reliable method is to create your own database engine module
   referencing ``tsvector_field.DatabaseSchemaEditor``. This will ensure that the
   database triggers are reliably created and dropped for all methods of migration.

   Create a 'db' directory in your Django project with an ``__init__.py`` and a ``base.py``
   with the following contents:


   .. code-block:: python

        from django.db.backends.postgresql import base
        import tsvector_field

        class DatabaseWrapper(base.DatabaseWrapper):
            SchemaEditorClass = tsvector_field.DatabaseSchemaEditor


   Then update the ``'ENGINE'`` configuration in your ``DATABASES`` setting. For example,
   if your project is called ``my_project`` and it has the ``db`` module as described
   above, then change your ``DATABASE`` setting to have the following ``'ENGINE'`` configuration:


   .. code-block:: python

        DATABASES = {
            'default': {
                'ENGINE': 'my_project.db',
            }
        }

Usage
=====

.. _usage:

``tsvector_field.SearchVectorField`` works like any other Django field: add it to your model,
run ``makemigrations``, run ``migrate`` and ``tsvector_field`` will take care to create the
postgres trigger and stored procedure.

To illustrate how this works we'll create a ``TextDocument`` model with a
``tsvector_field.SearchVectorField`` field and two textual fields to be used as
inputs for the full text search.

.. code-block:: python

    from django.db import models
    import tsvector_field

    class TextDocument(models.Model):
        title = models.CharField(max_length=128)
        body = models.TextField()
        search = tsvector_field.SearchVectorField([
            tsvector_field.WeightedColumn('title', 'A'),
            tsvector_field.WeightedColumn('body', 'D'),
        ], 'english')


After you've migrated you can create some ``TextDocument`` records and see that
postgres keeps it synchronized in the background. Specifically, because the
``search`` field is updated at the database level, you'll need to call ``refresh_from_db()``
to see the new value after a ``.save()`` or ``.create()``.


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

Final note about the ``tsvector_field.SearchVectorField`` field is that it takes a
``language_column`` argument instead of or in addition to the ``language`` argument. When
both arguments are provided then the database trigger will first look up the value in the
``language_column`` and if that is null it will use the language in ``language``.

Migrating
=========

.. _migrating:

When adding a ``tsvector_field.SearchVectorField`` field to an existing model you likely
want to update the search vector for all existing records. **django-tsvector-field** includes
the ``tsvector_field.IndexSearchVector`` operation that takes the model name and search vector
column as arguments. If we had previously created the ``TextDocument`` without a ``search`` column
then to add search capability we would use the following migration:

.. code-block:: python

    from django.db import migrations, models
    import tsvector_field

    class Migration(migrations.Migration):

        dependencies = []

        operations = [
            migrations.AddField(
                model_name='textdocument',
                name='search',
                field=tsvector_field.SearchVectorField(columns=[
                    tsvector_field.WeightedColumn('title', 'A'),
                    tsvector_field.WeightedColumn('body', 'D')
                ], language='english'),
            ),
            tsvector_field.IndexSearchVector('textdocument', 'search'),
        ]


For more information on querying, see the Django documentation on Full Text Search:

https://docs.djangoproject.com/en/dev/ref/contrib/postgres/search/

For more information on configuring how the searches work, see PostgreSQL docs:

https://www.postgresql.org/docs/devel/static/textsearch.html
