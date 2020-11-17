from datetime import (
    datetime,
    timedelta,
)
from unittest import skip

from djangae.contrib.search import (
    Document,
    Index,
    fields,
)
from djangae.contrib.search.query import _tokenize_query_string
from djangae.test import TestCase


class CompanyDocument(Document):
    company_name = fields.TextField()
    company_type = fields.TextField()


class FuzzyDocument(Document):
    company_name = fields.FuzzyTextField()


class QueryTests(TestCase):
    def test_tokenization_breaks_at_punctuation(self):
        q = "hi, there is a 100% chance this works [honest]"

        tokens = _tokenize_query_string(q)
        kinds = set(x[0] for x in tokens[0])
        tokens = [x[-1] for x in tokens[0]]

        self.assertEqual(kinds, {"word"})  # All tokens should be recognised as "word" tokens
        self.assertCountEqual(tokens, ["hi", ",", "100", "%", "chance", "works", "[", "honest", "]"])

    @skip("Implement stemming and fix this test")
    def test_fuzzy_matching(self):
        index = Index(name="test")

        doc1 = FuzzyDocument(company_name="Google")
        doc2 = FuzzyDocument(company_name="Potato")
        doc3 = FuzzyDocument(company_name="Facebook")
        doc4 = FuzzyDocument(company_name="Potential Company")

        index.add(doc1)
        index.add(doc2)
        index.add(doc3)
        index.add(doc4)

        results = [x.company_name for x in index.search("goo", document_class=FuzzyDocument)]
        self.assertCountEqual(results, ["Google"])

        results = [x.company_name for x in index.search("pot", document_class=FuzzyDocument)]
        self.assertCountEqual(results, ["Potato", "Potential Company"])

        results = [x.company_name for x in index.search("pota", document_class=FuzzyDocument)]
        self.assertCountEqual(results, ["Potato"])

    def test_startswith_matching(self):
        index = Index(name="test")

        doc1 = CompanyDocument(company_name="Google")
        doc2 = CompanyDocument(company_name="Potato")
        doc3 = CompanyDocument(company_name="Facebook")
        doc4 = CompanyDocument(company_name="Potential Company")

        index.add(doc1)
        index.add(doc2)
        index.add(doc3)
        index.add(doc4)

        results = [x.company_name for x in index.search("goo", document_class=CompanyDocument, use_startswith=True)]
        self.assertCountEqual(results, ["Google"])

        results = [x.company_name for x in index.search("pot", document_class=CompanyDocument, use_startswith=True)]
        self.assertCountEqual(results, ["Potato", "Potential Company"])

        results = [x.company_name for x in index.search("pota", document_class=CompanyDocument, use_startswith=True)]
        self.assertCountEqual(results, ["Potato"])

    def test_startswith_with_multiple_results_per_token(self):
        """
            The problem here is that doing startswith matches can return multiple
            matching tokens from the database, for a single input token. e.g.
            in this example searching for "test" will return matches for "testing" and "test.

            This caused a bug when document matching would use token counts to determine
            if a document matched a search string.
        """

        index = Index(name="test")

        doc1 = CompanyDocument(company_name="Internal testing test", company_type="LLC")
        doc2 = CompanyDocument(company_name="My test", company_type="Ltd")

        index.add(doc1)
        index.add(doc2)

        results = [
            x.company_name
            for x in index.search("test ltd", CompanyDocument, use_startswith=True)
        ]

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], "My test")

    def test_startswith_multiple_tokens(self):
        index = Index(name="test")

        doc1 = CompanyDocument(company_name="Google", company_type="LLC")
        doc2 = CompanyDocument(company_name="Potato", company_type="Ltd.")
        doc3 = CompanyDocument(company_name="Facebook", company_type="Inc.")
        doc4 = CompanyDocument(company_name="Awesome", company_type="LLC")
        doc5 = CompanyDocument(company_name="Google", company_type="Ltd.")

        index.add(doc1)
        index.add(doc2)
        index.add(doc3)
        index.add(doc4)
        index.add(doc5)

        results = [
            (x.company_name, x.company_type)
            for x in index.search("goo llc", document_class=CompanyDocument, use_startswith=True)
        ]

        self.assertCountEqual(results, [("Google", "LLC")])

        results = [
            (x.company_name, x.company_type)
            for x in index.search("pot ltd", document_class=CompanyDocument, use_startswith=True)
        ]

        self.assertCountEqual(results, [("Potato", "Ltd.")])

    def test_number_field_querying(self):
        class Doc(Document):
            number = fields.NumberField()

        index = Index(name="test")

        doc1 = index.add(Doc(number=1))
        doc2 = index.add(Doc(number=2341920))

        results = [x for x in index.search("number:1", document_class=Doc)]

        # Should only return the exact match
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, doc1)

        results = [x for x in index.search("1", document_class=Doc)]

        # Should only return the exact match
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, doc1)

        results = [x for x in index.search("2341920", document_class=Doc)]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, doc2)

    def test_datefield_querying(self):
        class Doc(Document):
            datefield = fields.DateField()

        date = datetime(year=2020, month=1, day=1, hour=6, minute=15)
        tomorrow = date + timedelta(days=1)

        index = Index(name="test")
        index.add(Doc(datefield=date))
        index.add(Doc(datefield=tomorrow))

        results = [x for x in index.search("2020-01-01", document_class=Doc)]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].datefield, date)

    def test_match_all_flag(self):

        class Doc(Document):
            text = fields.TextField()

        index = Index(name="test")
        doc1 = index.add(Doc(text="test string one"))
        doc2 = index.add(Doc(text="test string two"))

        results = list(index.search("test string", Doc, match_all=True))
        self.assertEqual(len(results), 2)

        results = list(index.search("string one", Doc, match_all=True))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, doc1)

        results = list(index.search("test two", Doc, match_all=True))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, doc2)

        # Should return both as we're defaulting to OR behaviour
        results = list(index.search("string one", Doc, match_all=False))
        self.assertEqual(len(results), 2)

    def test_or_queries(self):
        class Doc(Document):
            text = fields.TextField()

        index = Index(name="test")
        index.add(Doc(text="test string one"))
        index.add(Doc(text="test string two"))

        results = list(index.search("one OR two", Doc, match_all=True))
        self.assertEqual(len(results), 2)

    def test_trailing_period(self):
        class Doc(Document):
            text = fields.TextField()

        index = Index(name="test")
        index.add(Doc(text="My company ltd."))
        index.add(Doc(text="Company co."))

        results = list(index.search("co", Doc))
        self.assertEqual(len(results), 1)

        results = list(index.search("co.", Doc))
        self.assertEqual(len(results), 1)

        results = list(index.search("ltd", Doc))
        self.assertEqual(len(results), 1)

        results = list(index.search("ltd.", Doc))
        self.assertEqual(len(results), 1)

    def test_acronyms(self):
        class Doc(Document):
            text = fields.TextField()

        index = Index(name="test")
        doc1 = index.add(Doc(text="a.b.c"))
        doc2 = index.add(Doc(text="1-2-3"))
        index.add(Doc(text="do-re-mi"))

        results = list(index.search("a.b.c", Doc))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, doc1)

        results = list(index.search("abc", Doc))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, doc1)

        results = list(index.search("a-b-c", Doc))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, doc1)

        results = list(index.search("1-2-3", Doc))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, doc2)
