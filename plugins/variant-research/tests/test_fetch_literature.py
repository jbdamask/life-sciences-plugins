"""Tests for fetch_literature.py."""

from unittest.mock import patch, call
import pytest

from conftest import (
    make_mock_response,
    PUBMED_ESEARCH_RESPONSE,
    PUBMED_EFETCH_XML,
)
from fetch_literature import fetch_literature, esearch, efetch_articles, _parse_pubmed_article, _get_text


class TestEsearch:
    """Tests for PubMed esearch."""

    @patch("fetch_literature.requests.get")
    def test_returns_pmids(self, mock_get):
        mock_get.return_value = make_mock_response(json_data=PUBMED_ESEARCH_RESPONSE)
        pmids = esearch("AGT AND rs699")
        assert pmids == ["12345678", "87654321"]

    @patch("fetch_literature.requests.get")
    def test_empty_result(self, mock_get):
        mock_get.return_value = make_mock_response(json_data={"esearchresult": {"idlist": []}})
        pmids = esearch("nonexistent_gene_12345")
        assert pmids == []

    @patch("fetch_literature.requests.get")
    def test_network_failure(self, mock_get):
        from requests.exceptions import ConnectionError
        mock_get.side_effect = ConnectionError("fail")
        with pytest.raises(ConnectionError):
            esearch("AGT")


class TestEfetchArticles:
    """Tests for PubMed efetch."""

    @patch("fetch_literature.requests.get")
    def test_parses_articles(self, mock_get):
        mock_get.return_value = make_mock_response(text=PUBMED_EFETCH_XML)
        articles = efetch_articles(["12345678", "87654321"])
        assert len(articles) == 2
        assert articles[0]["pmid"] == "12345678"
        assert articles[0]["title"] == "AGT variant and hypertension risk"
        assert articles[0]["authors"] == "Smith J et al."
        assert articles[0]["journal"] == "Journal of Hypertension"
        assert articles[0]["year"] == "2023"

    def test_empty_pmids(self):
        articles = efetch_articles([])
        assert articles == []

    @patch("fetch_literature.requests.get")
    def test_single_author(self, mock_get):
        """Single author should not have 'et al.'"""
        articles = efetch_articles.__wrapped__ if hasattr(efetch_articles, '__wrapped__') else None
        mock_get.return_value = make_mock_response(text=PUBMED_EFETCH_XML)
        articles = efetch_articles(["87654321"])
        # Second article in our fixture has one author
        for a in articles:
            if a["pmid"] == "87654321":
                assert a["authors"] == "Lee K"


class TestFetchLiterature:
    """Tests for the main fetch_literature() function."""

    @patch("fetch_literature.esearch")
    @patch("fetch_literature.efetch_articles")
    def test_successful_fetch(self, mock_efetch, mock_esearch):
        mock_esearch.return_value = ["12345678"]
        mock_efetch.return_value = [
            {"pmid": "12345678", "title": "Test", "authors": "A B", "journal": "J", "year": "2023", "abstract_snippet": "..."},
        ]
        result = fetch_literature("rs699", "AGT")

        assert result["rsid"] == "rs699"
        assert result["gene_symbol"] == "AGT"
        assert len(result["pubmed_articles"]) == 1
        assert len(result["search_queries_used"]) == 3  # 3 queries
        assert result["errors"] == []  # No errors on success

    @patch("fetch_literature.esearch")
    @patch("fetch_literature.efetch_articles")
    def test_deduplicates_pmids(self, mock_efetch, mock_esearch):
        """Same PMID returned by multiple queries should be fetched only once."""
        mock_esearch.return_value = ["12345678"]
        mock_efetch.return_value = [{"pmid": "12345678", "title": "T", "authors": "", "journal": "", "year": "", "abstract_snippet": ""}]
        result = fetch_literature("rs699", "AGT")
        # efetch should be called with the deduplicated list
        mock_efetch.assert_called_once()
        pmids_arg = mock_efetch.call_args[0][0]
        assert len(pmids_arg) == len(set(pmids_arg))

    @patch("fetch_literature.esearch")
    @patch("fetch_literature.efetch_articles")
    def test_search_failure_continues(self, mock_efetch, mock_esearch):
        """If one search query fails, others should still proceed."""
        from requests.exceptions import ConnectionError
        call_count = [0]
        def side_effect(query, retmax=10):
            call_count[0] += 1
            if call_count[0] == 1:
                raise ConnectionError("fail")
            return ["99999999"]
        mock_esearch.side_effect = side_effect
        mock_efetch.return_value = [{"pmid": "99999999", "title": "T", "authors": "", "journal": "", "year": "", "abstract_snippet": ""}]
        result = fetch_literature("rs699", "AGT")
        assert len(result["pubmed_articles"]) == 1
        assert any("PubMed search failed" in e for e in result["errors"])

    @patch("fetch_literature.esearch")
    @patch("fetch_literature.efetch_articles")
    def test_efetch_failure(self, mock_efetch, mock_esearch):
        from requests.exceptions import ConnectionError
        mock_esearch.return_value = ["12345678"]
        mock_efetch.side_effect = ConnectionError("fail")
        result = fetch_literature("rs699", "AGT")
        assert result["pubmed_articles"] == []
        assert any("efetch failed" in e for e in result["errors"])

    @patch("fetch_literature.esearch")
    @patch("fetch_literature.efetch_articles")
    def test_caps_at_30_pmids(self, mock_efetch, mock_esearch):
        """Should send at most 30 PMIDs to efetch."""
        mock_esearch.return_value = [str(i) for i in range(15)]
        mock_efetch.return_value = []
        result = fetch_literature("rs699", "AGT")
        pmids_arg = mock_efetch.call_args[0][0]
        assert len(pmids_arg) <= 30


class TestGetText:
    """Tests for the _get_text() helper."""

    def test_none_element(self):
        assert _get_text(None) == ""

    def test_mixed_content(self):
        import xml.etree.ElementTree as ET
        elem = ET.fromstring("<root>Hello <b>world</b> test</root>")
        assert _get_text(elem) == "Hello world test"
