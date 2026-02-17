"""Tests for fetch_biogrid.py."""

import os
from unittest.mock import patch
import pytest

from conftest import make_mock_response, BIOGRID_RESPONSE
from fetch_biogrid import fetch_biogrid_interactions


class TestFetchBiogridInteractions:
    """Tests for BioGRID API calls."""

    @patch.dict(os.environ, {"BIOGRID_API_KEY": "test-key"})
    @patch("fetch_biogrid.requests.get")
    def test_successful_fetch(self, mock_get):
        mock_get.return_value = make_mock_response(json_data=BIOGRID_RESPONSE)
        result = fetch_biogrid_interactions("AGT")

        assert result["database"] == "BioGRID"
        assert result["gene_symbol"] == "AGT"
        assert result["total_count"] == 1
        assert len(result["interactions"]) == 1
        assert result["errors"] == []

        i0 = result["interactions"][0]
        assert i0["biogrid_id"] == "100001"
        assert i0["gene_a"] == "AGT"
        assert i0["gene_b"] == "REN"
        assert i0["experimental_system"] == "Two-hybrid"
        assert i0["pubmed_id"] == "12345678"

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_api_key(self):
        # Remove the key if it exists
        os.environ.pop("BIOGRID_API_KEY", None)
        result = fetch_biogrid_interactions("AGT")
        assert result["interactions"] == []
        assert len(result["errors"]) == 1
        assert "BIOGRID_API_KEY not set" in result["errors"][0]

    @patch.dict(os.environ, {"BIOGRID_API_KEY": "test-key"})
    @patch("fetch_biogrid.requests.get")
    def test_network_failure_with_retry(self, mock_get):
        from requests.exceptions import ConnectionError
        mock_get.side_effect = ConnectionError("fail")
        result = fetch_biogrid_interactions("AGT", max_retries=1)
        assert len(result["errors"]) == 1
        assert mock_get.call_count == 2

    @patch.dict(os.environ, {"BIOGRID_API_KEY": "test-key"})
    @patch("fetch_biogrid.requests.get")
    def test_empty_result(self, mock_get):
        mock_get.return_value = make_mock_response(json_data={})
        result = fetch_biogrid_interactions("NONEXISTENT")
        assert result["total_count"] == 0
        assert result["interactions"] == []

    @patch.dict(os.environ, {"BIOGRID_API_KEY": "test-key"})
    @patch("fetch_biogrid.requests.get")
    def test_api_key_passed_as_param(self, mock_get):
        mock_get.return_value = make_mock_response(json_data={})
        fetch_biogrid_interactions("AGT")
        call_kwargs = mock_get.call_args
        assert call_kwargs.kwargs["params"]["accesskey"] == "test-key"
