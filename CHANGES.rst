0.9.5
-----

* Use IS DISTINCT FROM instead of <> as comparing anything to NULL returns NULL.

0.9.4
-----

* Initial support django 2.0 alpha

0.9.3
-----

* Automatically create GIN index on tsvector column

0.9.2
-----

* IndexSearchVector migration operation added
* documentation fixes
* Added support for both pre_migrate signal based integration and extending DatabaseSchemaEditor

0.9.1
-----

* Fixed bug with AlterField migrations.

0.9.0
-----

* Initial release.
