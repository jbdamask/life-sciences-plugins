"""Tests for fetch_patents.py."""

import os
from unittest.mock import patch
import pytest

from conftest import make_mock_response, PATENTSVIEW_RESPONSE
from fetch_patents import search_patents, _classify_patent, fetch_all_patents


class TestClassifyPatent:
    """Tests for patent classification logic."""

    def test_drug_classification(self):
        assert _classify_patent("Novel inhibitor compound", "A pharmaceutical compound for treatment") == "drug"

    def test_diagnostic_classification(self):
        assert _classify_patent("Biomarker detection kit", "An assay for screening patients") == "diagnostic"

    def test_therapeutic_classification(self):
        assert _classify_patent("Method of treating disease", "Therapeutic approach for disorder") == "therapeutic"

    def test_other_classification(self):
        assert _classify_patent("Gene sequence analysis", "A computational method for analysis") == "other"

    def test_tie_drug_wins(self):
        """When drug and diagnostic scores tie, drug wins because drug-related
        patents are more commercially significant for variant research."""
        result = _classify_patent(
            "Pharmaceutical diagnostic compound",
            "An inhibitor antibody compound for assay detection screening"
        )
        # drug keywords: pharmaceutical, compound, inhibitor, antibody = 4
        # diagnostic keywords: diagnostic, assay, detection, screening = 4
        # Tied! Drug wins the tie-break.
        assert result == "drug"

    def test_drug_wins_when_ahead(self):
        """Drug wins only when strictly more drug keywords."""
        result = _classify_patent(
            "Novel inhibitor compound formulation",
            "A pharmaceutical antibody antagonist for disease"
        )
        # drug: inhibitor, compound, formulation, pharmaceutical, antibody, antagonist = 6
        # diagnostic: 0
        # therapeutic: disease = 1
        assert result == "drug"


class TestSearchPatents:
    """Tests for the search_patents() function."""

    @patch("fetch_patents.requests.get")
    def test_successful_search(self, mock_get):
        mock_get.return_value = make_mock_response(json_data=PATENTSVIEW_RESPONSE)
        patents = search_patents("AGT", "test-key")
        assert len(patents) == 2
        assert patents[0]["patent_number"] == "US-11234567-B2"
        assert patents[0]["assignee"] == "Pharma Corp"
        assert patents[0]["classification"] == "drug"
        assert patents[1]["classification"] == "diagnostic"

    @patch("fetch_patents.requests.get")
    def test_empty_result(self, mock_get):
        mock_get.return_value = make_mock_response(json_data={"patents": []})
        patents = search_patents("nonexistent", "test-key")
        assert patents == []

    @patch("fetch_patents.requests.get")
    def test_missing_assignee(self, mock_get):
        response = {"patents": [{
            "patent_id": "US-123",
            "patent_title": "Test patent",
            "patent_abstract": "",
            "patent_date": "2023-01-01",
            "assignees": [],
        }]}
        mock_get.return_value = make_mock_response(json_data=response)
        patents = search_patents("AGT", "test-key")
        assert patents[0]["assignee"] == "Unknown"

    @patch("fetch_patents.requests.get")
    def test_abstract_truncation(self, mock_get):
        long_abstract = "A" * 300
        response = {"patents": [{
            "patent_id": "US-123",
            "patent_title": "Test",
            "patent_abstract": long_abstract,
            "patent_date": "2023-01-01",
            "assignees": [],
        }]}
        mock_get.return_value = make_mock_response(json_data=response)
        patents = search_patents("AGT", "test-key")
        assert patents[0]["abstract_snippet"].endswith("...")
        assert len(patents[0]["abstract_snippet"]) == 253  # 250 + "..."

    @patch("fetch_patents.requests.get")
    def test_api_key_in_header(self, mock_get):
        mock_get.return_value = make_mock_response(json_data={"patents": []})
        search_patents("AGT", "my-secret-key")
        call_kwargs = mock_get.call_args
        assert call_kwargs.kwargs["headers"]["X-Api-Key"] == "my-secret-key"


class TestFetchAllPatents:
    """Tests for the main fetch_all_patents() function."""

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_api_key(self):
        result = fetch_all_patents("rs699", "AGT")
        assert len(result["errors"]) == 1
        assert "PATENTSVIEW_API_KEY not set" in result["errors"][0]
        assert result["patents"] == []

    @patch.dict(os.environ, {"PATENTSVIEW_API_KEY": "test-key"})
    @patch("fetch_patents.search_patents")
    def test_successful_fetch(self, mock_search):
        mock_search.return_value = [
            {"patent_number": "US-123", "title": "Test", "assignee": "Corp", "date": "2023", "abstract_snippet": "...", "classification": "drug"},
        ]
        result = fetch_all_patents("rs699", "AGT", "angiotensinogen")
        assert len(result["patents"]) >= 1
        assert len(result["search_queries_used"]) >= 3

    @patch.dict(os.environ, {"PATENTSVIEW_API_KEY": "test-key"})
    @patch("fetch_patents.search_patents")
    def test_deduplication(self, mock_search):
        """Same patent returned by multiple queries should appear once."""
        mock_search.return_value = [
            {"patent_number": "US-123", "title": "Test", "assignee": "Corp", "date": "2023", "abstract_snippet": "...", "classification": "drug"},
        ]
        result = fetch_all_patents("rs699", "AGT")
        patent_numbers = [p["patent_number"] for p in result["patents"]]
        assert len(patent_numbers) == len(set(patent_numbers))

    @patch.dict(os.environ, {"PATENTSVIEW_API_KEY": "test-key"})
    @patch("fetch_patents.search_patents")
    def test_search_failure_continues(self, mock_search):
        from requests.exceptions import ConnectionError
        call_count = [0]
        def side_effect(query, api_key, per_page=15):
            call_count[0] += 1
            if call_count[0] == 1:
                raise ConnectionError("fail")
            return [{"patent_number": f"US-{call_count[0]}", "title": "T", "assignee": "C", "date": "2023", "abstract_snippet": "...", "classification": "other"}]
        mock_search.side_effect = side_effect
        result = fetch_all_patents("rs699", "AGT")
        assert len(result["patents"]) >= 1
        assert any("PatentsView search failed" in e for e in result["errors"])

    @patch.dict(os.environ, {"PATENTSVIEW_API_KEY": "test-key"})
    @patch("fetch_patents.search_patents")
    def test_extra_query_for_multi_word_gene_name(self, mock_search):
        """Gene names with multiple words should trigger an extra query."""
        mock_search.return_value = []
        result = fetch_all_patents("rs699", "AGT", "angiotensinogen precursor protein")
        assert len(result["search_queries_used"]) == 4  # base 3 + 1 extra
