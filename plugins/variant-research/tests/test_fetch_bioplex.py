"""Tests for fetch_bioplex.py."""

import os
from unittest.mock import patch, MagicMock
import pytest

from conftest import make_mock_response, BIOPLEX_TSV_DATA
from fetch_bioplex import fetch_bioplex_interactions, _get_cache_path, _download_data


class TestGetCachePath:
    """Tests for cache path resolution."""

    def test_returns_path_in_cache_dir(self):
        path = _get_cache_path()
        assert path.endswith("bioplex_293t.tsv")
        assert ".cache" in path


class TestDownloadData:
    """Tests for the BioPlex data download."""

    def test_skips_if_cached(self, tmp_path):
        cache_file = tmp_path / "bioplex_293t.tsv"
        cache_file.write_text("existing data")
        _download_data(str(cache_file))
        # Should not modify existing file
        assert cache_file.read_text() == "existing data"

    @patch("fetch_bioplex.requests.get")
    def test_downloads_if_missing(self, mock_get, tmp_path):
        cache_file = tmp_path / "bioplex_293t.tsv"
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.iter_content.return_value = [BIOPLEX_TSV_DATA]
        mock_get.return_value = mock_resp

        _download_data(str(cache_file))
        assert cache_file.exists()
        assert "AGT" in cache_file.read_text()


class TestFetchBioplexInteractions:
    """Tests for the main fetch function."""

    @patch("fetch_bioplex._download_data")
    @patch("fetch_bioplex._get_cache_path")
    def test_successful_fetch(self, mock_cache_path, mock_download, tmp_path):
        cache_file = tmp_path / "bioplex_293t.tsv"
        cache_file.write_text(BIOPLEX_TSV_DATA)
        mock_cache_path.return_value = str(cache_file)

        result = fetch_bioplex_interactions("AGT")
        assert result["database"] == "BioPlex"
        assert result["gene_symbol"] == "AGT"
        assert result["total_count"] == 2  # AGT appears in 2 rows
        assert len(result["interactions"]) == 2

        # Check first interaction
        i0 = result["interactions"][0]
        assert i0["symbol_a"] == "AGT"
        assert i0["symbol_b"] == "REN"
        assert i0["p_interaction"] == 0.94
        assert i0["p_wrong"] == 0.01

    @patch("fetch_bioplex._download_data")
    @patch("fetch_bioplex._get_cache_path")
    def test_case_insensitive_match(self, mock_cache_path, mock_download, tmp_path):
        cache_file = tmp_path / "bioplex_293t.tsv"
        cache_file.write_text(BIOPLEX_TSV_DATA)
        mock_cache_path.return_value = str(cache_file)

        result = fetch_bioplex_interactions("agt")
        assert result["total_count"] == 2

    @patch("fetch_bioplex._download_data")
    @patch("fetch_bioplex._get_cache_path")
    def test_gene_not_found(self, mock_cache_path, mock_download, tmp_path):
        cache_file = tmp_path / "bioplex_293t.tsv"
        cache_file.write_text(BIOPLEX_TSV_DATA)
        mock_cache_path.return_value = str(cache_file)

        result = fetch_bioplex_interactions("NONEXISTENT")
        assert result["total_count"] == 0
        assert result["interactions"] == []

    @patch("fetch_bioplex._download_data")
    @patch("fetch_bioplex._get_cache_path")
    def test_max_results_limit(self, mock_cache_path, mock_download, tmp_path):
        cache_file = tmp_path / "bioplex_293t.tsv"
        cache_file.write_text(BIOPLEX_TSV_DATA)
        mock_cache_path.return_value = str(cache_file)

        result = fetch_bioplex_interactions("AGT", max_results=1)
        assert result["total_count"] == 2
        assert len(result["interactions"]) == 1

    @patch("fetch_bioplex._get_cache_path")
    def test_download_failure(self, mock_cache_path, tmp_path):
        mock_cache_path.return_value = str(tmp_path / "missing.tsv")
        with patch("fetch_bioplex._download_data", side_effect=Exception("download failed")):
            result = fetch_bioplex_interactions("AGT")
            assert len(result["errors"]) == 1

    @patch("fetch_bioplex._download_data")
    @patch("fetch_bioplex._get_cache_path")
    def test_invalid_numeric_fields(self, mock_cache_path, mock_download, tmp_path):
        """Non-numeric pW/pNI/pInt values should be handled gracefully."""
        data = (
            "GeneA\tGeneB\tUniprotA\tUniprotB\tSymbolA\tSymbolB\tpW\tpNI\tpInt\n"
            "183\t5972\tP01019\tP00797\tAGT\tREN\tNaN\t\tbad\n"
        )
        cache_file = tmp_path / "bioplex_293t.tsv"
        cache_file.write_text(data)
        mock_cache_path.return_value = str(cache_file)

        result = fetch_bioplex_interactions("AGT")
        i0 = result["interactions"][0]
        # "NaN" parses as float('nan'), empty string raises ValueError -> None,
        # "bad" raises ValueError -> None
        assert i0["p_no_interaction"] is None
        assert i0["p_interaction"] is None
