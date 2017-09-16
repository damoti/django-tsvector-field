from django.db import models
from django.test import TestCase
from django.test.utils import isolate_apps

from tsvector_field import SearchVectorField, WeightedColumn


@isolate_apps('tsvector_test_app')
class CheckTests(TestCase):

    def test_without_arguments(self):

        class TextDocument(models.Model):
            search = SearchVectorField()

        errors = TextDocument.check()
        self.assertEqual(len(errors), 0)

    def test_good_arguments(self):

        class TextDocument(models.Model):
            title = models.CharField(max_length=128)
            title2 = models.CharField(max_length=128, db_column='body')
            search = SearchVectorField([
                WeightedColumn('title', 'A'),
                WeightedColumn('body', 'D')
            ], language='english')

        errors = TextDocument.check()
        self.assertEqual(len(errors), 0)

    def test_columns_E100(self):

        class TextDocument(models.Model):
            search = SearchVectorField([
                WeightedColumn('title', 'A')
            ], language='english')

        errors = TextDocument.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'postgres.E100')
        self.assertIn('No textual columns', errors[0].msg)

    def test_columns_E101(self):

        class TextDocument(models.Model):
            title = models.CharField(max_length=128)
            search = SearchVectorField([
                ('title', 'A')
            ], language='english')

        errors = TextDocument.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'postgres.E101')
        self.assertIn('columns', errors[0].msg)
        self.assertIn('iterable', errors[0].msg)
        self.assertIn('WeightedColumn', errors[0].msg)

    def test_languages_required_E102(self):

        class TextDocument(models.Model):
            title = models.CharField(max_length=128)
            search = SearchVectorField([
                WeightedColumn('title', 'A')
            ])

        errors = TextDocument.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'postgres.E102')
        self.assertIn('required', errors[0].msg)
        self.assertIn('language', errors[0].msg)
        self.assertIn('language_column', errors[0].msg)

    def test_language_E103(self):

        class TextDocument(models.Model):
            search = SearchVectorField(language=1)

        errors = TextDocument.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'postgres.E103')
        self.assertIn('language', errors[0].msg)

    def test_language_column_E104(self):

        class TextDocument(models.Model):
            title = models.CharField(max_length=128)
            search = SearchVectorField(language_column='body')

        errors = TextDocument.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'postgres.E104')
        self.assertIn('language_column', errors[0].msg)
        self.assertIn('title', errors[0].msg)

    def test_force_update_E105(self):

        class TextDocument(models.Model):
            search = SearchVectorField(force_update='invalid')

        errors = TextDocument.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'postgres.E105')
        self.assertIn('force_update', errors[0].msg)
        self.assertIn('True or False', errors[0].msg)

    def test_WeightedColumn_name_E110(self):

        class TextDocument(models.Model):
            title = models.CharField(max_length=128)
            search = SearchVectorField([
                WeightedColumn('body', 'A')
            ], language='english')

        errors = TextDocument.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'postgres.E110')
        self.assertIn('body', errors[0].msg)
        self.assertIn('available columns', errors[0].msg)
        self.assertIn('title', errors[0].msg)

    def test_WeightedColumn_weight_E111(self):

        class TextDocument(models.Model):
            title = models.CharField(max_length=128)
            search = SearchVectorField([
                WeightedColumn('title', 'X')
            ], language='english')

        errors = TextDocument.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'postgres.E111')
        self.assertIn('weight', errors[0].msg)
        self.assertIn('"A", "B", "C"', errors[0].msg)

    def test_several_errors(self):

        class TextDocument(models.Model):
            title = models.CharField(max_length=128)
            search = SearchVectorField([
                WeightedColumn('body', 'A'),
                WeightedColumn('name', 'X')
            ], language=9, force_update=False)

        errors = TextDocument.check()
        self.assertEqual(len(errors), 4)
