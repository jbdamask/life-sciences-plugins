"""Tests for fetch_intact.py."""

from unittest.mock import patch
import pytest

from conftest import make_mock_response, INTACT_MITAB_RESPONSE
from fetch_intact import (
    fetch_intact_interactions,
    _extract_name,
    _extract_id,
    _extract_psi_value,
)


class TestExtractName:
    """Tests for MITAB alias name extraction."""

    def test_display_short(self):
        alias = 'uniprotkb:AGT(display_short)|uniprotkb:ANGT(gene name)'
        assert _extract_name(alias) == "AGT"

    def test_gene_name_fallback(self):
        alias = 'uniprotkb:P01019(uniprot)|uniprotkb:AGT(gene name)'
        assert _extract_name(alias) == "AGT"

    def test_no_match(self):
        assert _extract_name("uniprotkb:P01019(uniprot)") == ""

    def test_empty(self):
        assert _extract_name("-") == ""


class TestExtractId:
    """Tests for MITAB ID extraction."""

    def test_standard_id(self):
        assert _extract_id("uniprotkb:P01019") == "P01019"

    def test_pipe_separated(self):
        assert _extract_id("uniprotkb:P01019|intact:EBI-123") == "P01019"

    def test_no_colon(self):
        assert _extract_id("P01019") == "P01019"


class TestExtractPsiValue:
    """Tests for PSI-MI formatted value extraction."""

    def test_standard_format(self):
        assert _extract_psi_value('psi-mi:"MI:0006"(anti bait coimmunoprecipitation)') == "anti bait coimmunoprecipitation"

    def test_simple_format(self):
        assert _extract_psi_value('psi-mi:"MI:0915"(physical association)') == "physical association"

    def test_no_parens(self):
        assert _extract_psi_value("raw-value") == "raw-value"


class TestFetchIntactInteractions:
    """Tests for the main fetch function."""

    @patch("fetch_intact.requests.get")
    def test_successful_fetch(self, mock_get):
        mock_get.return_value = make_mock_response(text=INTACT_MITAB_RESPONSE)
        result = fetch_intact_interactions("AGT")

        assert result["database"] == "IntAct"
        assert result["gene_symbol"] == "AGT"
        assert len(result["interactions"]) == 2
        assert result["errors"] == []

        # Check first interaction
        i0 = result["interactions"][0]
        assert i0["interactors"] == ["AGT", "REN"]
        assert i0["interaction_type"] == "physical association"
        assert i0["detection_method"] == "anti bait coimmunoprecipitation"
        assert i0["publication"] == "12345678"
        assert i0["confidence_score"] == 0.65

    @patch("fetch_intact.requests.get")
    def test_empty_response(self, mock_get):
        mock_get.return_value = make_mock_response(text="")
        result = fetch_intact_interactions("NONEXISTENT")
        assert result["interactions"] == []

    @patch("fetch_intact.requests.get")
    def test_network_failure_with_retry(self, mock_get):
        from requests.exceptions import ConnectionError
        mock_get.side_effect = ConnectionError("fail")
        result = fetch_intact_interactions("AGT", max_retries=1)
        assert len(result["errors"]) == 1
        assert mock_get.call_count == 2

    @patch("fetch_intact.requests.get")
    def test_short_lines_skipped(self, mock_get):
        """Lines with fewer than 15 fields should be skipped."""
        bad_line = "col1\tcol2\tcol3\n"
        mock_get.return_value = make_mock_response(text=bad_line)
        result = fetch_intact_interactions("AGT")
        assert result["interactions"] == []

    @patch("fetch_intact.requests.get")
    def test_total_count_matches_parsed_interactions(self, mock_get):
        """total_count should only count successfully parsed interactions, not unparseable lines."""
        text = "short_line\n" + INTACT_MITAB_RESPONSE
        mock_get.return_value = make_mock_response(text=text)
        result = fetch_intact_interactions("AGT")
        # total_count should match the number of successfully parsed interactions
        assert result["total_count"] == 2
        assert len(result["interactions"]) == 2

    @patch("fetch_intact.requests.get")
    def test_missing_confidence_score(self, mock_get):
        """Lines without intact-miscore should have None confidence."""
        # Modify the fixture to remove confidence
        line = (
            "uniprotkb:P01019\tuniprotkb:P00797\t-\t-\t"
            "uniprotkb:AGT(display_short)\tuniprotkb:REN(display_short)\t"
            'psi-mi:"MI:0006"(method)\t'
            "author1\t"
            "pubmed:12345678\t"
            "taxid:9606\ttaxid:9606\t"
            'psi-mi:"MI:0915"(physical association)\t'
            "psi-mi:\"MI:0469\"(IntAct)\t"
            "intact:EBI-12345\t"
            "other-score:0.5\n"
        )
        mock_get.return_value = make_mock_response(text=line)
        result = fetch_intact_interactions("AGT")
        assert result["interactions"][0]["confidence_score"] is None
