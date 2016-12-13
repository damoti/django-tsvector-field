from datetime import datetime

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db import connection, models
from django.db.models.expressions import F
from django.test import TestCase
from django.test.utils import isolate_apps

from tsvector import SearchVectorField, WeightedColumn
from tsvector.schema import TriggerSchemaEditor


@isolate_apps('tests')
class TriggerTests(TestCase):

    def setUp(self):

        class TextDocument(models.Model):
            body = models.TextField()
            other = models.TextField()
            search = SearchVectorField([
                WeightedColumn('body', 'D'),
            ], 'english')

        class TextDocumentLanguageColumn(models.Model):
            body = models.TextField()
            lang = models.TextField(null=True)
            search = SearchVectorField([
                WeightedColumn('body', 'D'),
            ], language_column='lang', language='english')

        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(TextDocument)
            schema_editor.create_model(TextDocumentLanguageColumn)

        with TriggerSchemaEditor(connection) as schema_editor:
            schema_editor.create_model(TextDocument)
            schema_editor.create_model(TextDocumentLanguageColumn)

        self.create = TextDocument.objects.create
        self.lang = TextDocumentLanguageColumn.objects.create

    def test_insert_and_update(self):
        doc = self.create(body="My hovercraft is full of eels.")
        doc.refresh_from_db()
        self.assertEqual(doc.search, "'eel':6 'full':4 'hovercraft':2")

        doc.body = 'No hovercraft for you!'
        doc.save()
        doc.refresh_from_db()
        self.assertEqual(doc.search, "'hovercraft':2")

    def test_performance_improvement_for_guarded_update(self):

        text = HOLY_GRAIL
        text2 = text.replace('king', 'ruler')

        start = datetime.now()
        doc = self.create(body=text)
        create_elapsed = (datetime.now() - start).microseconds
        doc.refresh_from_db()

        doc.body = text2
        start = datetime.now()
        doc.save(update_fields=['body'])
        update_elapsed = (datetime.now() - start).microseconds
        doc.refresh_from_db()

        longest = max(create_elapsed, update_elapsed)

        # check that insert and update times are within 50% of each other
        percent = abs(create_elapsed - update_elapsed) / longest
        self.assertGreater(.5, percent)

        # update not indexed column
        doc.other = text2
        start = datetime.now()
        doc.save(update_fields=['other'])
        noindex_elapsed = (datetime.now() - start).microseconds

        # skipping unnecessary to_tsvector() call is faster
        self.assertGreater(longest, noindex_elapsed)

        # update indexed column with the same value
        doc.body = text2
        start = datetime.now()
        doc.save(update_fields=['body'])
        noindex_elapsed = (datetime.now() - start).microseconds

        # skipping unnecessary to_tsvector() call is faster
        self.assertGreater(longest, noindex_elapsed)

    def test_using_language_column(self):
        # use english config to parse english text, stop words removed
        doc = self.lang(lang='english', body="My hovercraft is full of eels.")
        doc.refresh_from_db()
        self.assertEqual(doc.search, "'eel':6 'full':4 'hovercraft':2")

        # use german config to parse english text, stop words not removed
        doc = self.lang(lang='german', body="My hovercraft is full of eels.")
        doc.refresh_from_db()
        self.assertEqual(doc.search, "'eel':6 'full':4 'hovercraft':2 'is':3 'my':1 'of':5")

        # use english backup config to parse english text, stop words removed
        doc = self.lang(lang=None, body="My hovercraft is full of eels.")
        doc.refresh_from_db()
        self.assertEqual(doc.search, "'eel':6 'full':4 'hovercraft':2")


@isolate_apps('tests')
class QueryTests(TestCase):

    def setUp(self):

        class TextDocument(models.Model):
            title = models.CharField(max_length=128)
            body = models.TextField()
            search = SearchVectorField([
                WeightedColumn('title', 'A'),
                WeightedColumn('body', 'D'),
            ], 'english')

        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(TextDocument)
        with TriggerSchemaEditor(connection) as schema_editor:
            schema_editor.create_model(TextDocument)

        TextDocument.objects.create(
            title="My hovercraft is full of eels.",
            body="Spam! Spam! Spam! Spam! Spam! Spam!",
        )
        TextDocument.objects.create(
            title="Spam! Spam! Spam! Spam! Spam! Spam!",
            body="My hovercraft is full of eels."
        )
        self.objects = TextDocument.objects

    def search(self, terms):
        return list(self.objects.filter(search=terms).values_list('id', flat=True))

    def test_search(self):
        self.assertEqual(self.search('hovercraft'), [1, 2])
        self.assertEqual(self.search('spam'), [1, 2])

    def ranked_search(self, terms):
        return list(self.objects
                    .annotate(rank=SearchRank(F('search'), SearchQuery(terms, config='english')))
                    .order_by('-rank')
                    .values_list('id', flat=True))

    def test_rank_search(self):
        self.assertEqual(self.ranked_search('hovercraft'), [1, 2])
        self.assertEqual(self.ranked_search('spam'), [2, 1])


HOLY_GRAIL = """
King Arthur: Old woman!
Dennis: Man.
King Arthur: Man, sorry. What knight lives in that castle over there?
Dennis: I'm 37.
King Arthur: What?
Dennis: I'm 37. I'm not old.
King Arthur: Well I can't just call you "man".
Dennis: Well you could say "Dennis".
King Arthur: I didn't know you were called Dennis.
Dennis: Well you didn't bother to find out, did you?
King Arthur: I did say sorry about the "old woman", but from behind you looked...
Dennis: What I object to is you automatically treat me like an inferior.
King Arthur: Well, I am king.
Dennis: Oh, king eh? Very nice. And how'd you get that, eh? By exploiting the workers. By hanging on to outdated imperialist dogma which perpetuates the economic and social differences in our society.
...
King Arthur: Please, please, good people, I am in haste. Who lives in that castle?
Peasant Woman: No one lives there.
King Arthur: Then who is your lord?
Peasant Woman: We don't have a lord.
Dennis: I told you, we're an anarcho-syndicalist commune. We take it in turns to be a sort of executive officer for the week...
King Arthur: Yes...
Dennis: ...but all the decisions of that officer have to be ratified at a special bi-weekly meeting...
King Arthur: Yes I see...
Dennis: ...by a simple majority in the case of purely internal affairs...
King Arthur: Be quiet!
Dennis: ...but by a two thirds majority in the case of...
King Arthur: Be quiet! I order you to be quiet!
Peasant Woman: Order, eh? Who does he think he is?
King Arthur: I am your king.
Peasant Woman: Well, I didn't vote for you.
King Arthur: You don't vote for kings.
Peasant Woman: Well, how'd you become king, then?
[Angelic music plays... ]
King Arthur: The Lady of the Lake, her arm clad in the purest shimmering samite, held aloft Excalibur from the bosom of the water, signifying by divine providence that I, Arthur, was to carry Excalibur. That is why I am your king.
Dennis: Listen. Strange women lying in ponds distributing swords is no basis for a system of government. Supreme executive power derives from a mandate from the masses, not from some farcical aquatic ceremony.
Arthur: Be quiet!
Dennis: You can't expect to wield supreme power just 'cause some watery tart threw a sword at you!
Arthur: Shut up
Dennis: I mean, if I went around saying I was an emperor just because some moistened bint had lobbed a scimitar at me, they'd put me away!
Arthur: [grabs Dennis] Shut up! Will you shut up?!
Dennis: Ah, now we see the violence inherent in the system!
Arthur: [shakes Dennis] Shut up!
Dennis: Oh! Come and see the violence inherent in the system! Help, help, I'm being repressed!
Arthur: Bloody Peasant!
Dennis: Ooh, what a giveaway! Did you hear that? Did you hear that, eh? That's what I'm on about! Did you see him repressing me? You saw him, didn't you?
"""