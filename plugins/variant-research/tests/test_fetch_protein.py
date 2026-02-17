"""Tests for fetch_protein.py (orchestrator)."""

from unittest.mock import patch
import pytest


class TestFetchAllProtein:
    """Tests for the protein data orchestrator."""

    @patch("fetch_protein.fetch_biogrid_interactions")
    @patch("fetch_protein.fetch_bioplex_interactions")
    @patch("fetch_protein.fetch_intact_interactions")
    @patch("fetch_protein.fetch_hpa_data")
    @patch("fetch_protein.fetch_string_interactions")
    def test_successful_fetch_all(self, mock_string, mock_hpa, mock_intact, mock_bioplex, mock_biogrid):
        from fetch_protein import fetch_all_protein

        mock_string.return_value = {"interactions": [{"protein_a": "AGT", "protein_b": "REN"}], "errors": []}
        mock_hpa.return_value = {"protein_class": "Enzyme", "errors": []}
        mock_intact.return_value = {"interactions": [], "total_count": 0, "errors": []}
        mock_bioplex.return_value = {"interactions": [], "total_count": 0, "errors": []}
        mock_biogrid.return_value = {"interactions": [], "total_count": 0, "errors": []}

        result = fetch_all_protein("rs699", "AGT")
        assert result["rsid"] == "rs699"
        assert result["gene_symbol"] == "AGT"
        assert len(result["string_interactions"]["interactions"]) == 1
        assert result["errors"] == []

    @patch("fetch_protein.fetch_biogrid_interactions")
    @patch("fetch_protein.fetch_bioplex_interactions")
    @patch("fetch_protein.fetch_intact_interactions")
    @patch("fetch_protein.fetch_hpa_data")
    @patch("fetch_protein.fetch_string_interactions")
    def test_one_source_fails(self, mock_string, mock_hpa, mock_intact, mock_bioplex, mock_biogrid):
        from fetch_protein import fetch_all_protein

        mock_string.side_effect = RuntimeError("STRING crashed")
        mock_hpa.return_value = {"protein_class": "Enzyme", "errors": []}
        mock_intact.return_value = {"interactions": [], "errors": []}
        mock_bioplex.return_value = {"interactions": [], "errors": []}
        mock_biogrid.return_value = {"interactions": [], "errors": []}

        result = fetch_all_protein("rs699", "AGT")
        assert result["string_interactions"] == {}
        assert any("STRING-db failed" in e for e in result["errors"])
        # Other sources should still be populated
        assert result["hpa_expression"]["protein_class"] == "Enzyme"

    @patch("fetch_protein.fetch_biogrid_interactions")
    @patch("fetch_protein.fetch_bioplex_interactions")
    @patch("fetch_protein.fetch_intact_interactions")
    @patch("fetch_protein.fetch_hpa_data")
    @patch("fetch_protein.fetch_string_interactions")
    def test_all_sources_fail(self, mock_string, mock_hpa, mock_intact, mock_bioplex, mock_biogrid):
        from fetch_protein import fetch_all_protein

        mock_string.side_effect = RuntimeError("fail")
        mock_hpa.side_effect = RuntimeError("fail")
        mock_intact.side_effect = RuntimeError("fail")
        mock_bioplex.side_effect = RuntimeError("fail")
        mock_biogrid.side_effect = RuntimeError("fail")

        result = fetch_all_protein("rs699", "AGT")
        assert len(result["errors"]) == 5

    @patch("fetch_protein.fetch_biogrid_interactions")
    @patch("fetch_protein.fetch_bioplex_interactions")
    @patch("fetch_protein.fetch_intact_interactions")
    @patch("fetch_protein.fetch_hpa_data")
    @patch("fetch_protein.fetch_string_interactions")
    def test_sub_errors_propagated(self, mock_string, mock_hpa, mock_intact, mock_bioplex, mock_biogrid):
        """Errors within each source's result should bubble up to top-level errors."""
        from fetch_protein import fetch_all_protein

        mock_string.return_value = {"interactions": [], "errors": ["rate limited"]}
        mock_hpa.return_value = {"errors": []}
        mock_intact.return_value = {"interactions": [], "errors": []}
        mock_bioplex.return_value = {"interactions": [], "errors": ["download slow"]}
        mock_biogrid.return_value = {"interactions": [], "errors": []}

        result = fetch_all_protein("rs699", "AGT")
        assert "rate limited" in result["errors"]
        assert "download slow" in result["errors"]
