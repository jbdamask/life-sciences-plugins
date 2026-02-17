"""Tests for ncbi_utils.py — shared NCBI E-utilities helpers."""

from unittest.mock import patch, MagicMock
import pytest

from ncbi_utils import ncbi_get


class TestNcbiGet:
    """Tests for the ncbi_get() function."""

    @patch("ncbi_utils.time.sleep")
    @patch("ncbi_utils.requests.get")
    def test_adds_tool_and_email(self, mock_get, mock_sleep):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        ncbi_get("esearch.fcgi", {"db": "pubmed", "term": "test"})
        call_params = mock_get.call_args[1]["params"]
        assert "tool" in call_params
        assert "email" in call_params

    @patch("ncbi_utils.time.sleep")
    @patch("ncbi_utils.requests.get")
    def test_successful_request(self, mock_get, mock_sleep):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        resp = ncbi_get("esearch.fcgi", {"db": "pubmed"})
        assert resp.status_code == 200

    @patch("ncbi_utils.time.sleep")
    @patch("ncbi_utils.requests.get")
    def test_retries_on_429(self, mock_get, mock_sleep):
        mock_429 = MagicMock()
        mock_429.status_code = 429
        mock_429.headers = {"retry-after": "2"}
        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_get.side_effect = [mock_429, mock_200]
        resp = ncbi_get("esearch.fcgi", {"db": "pubmed"})
        assert resp.status_code == 200
        assert mock_get.call_count == 2

    @patch("ncbi_utils.time.sleep")
    @patch("ncbi_utils.requests.get")
    def test_retries_on_connection_error(self, mock_get, mock_sleep):
        from requests.exceptions import ConnectionError
        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_get.side_effect = [ConnectionError("SSL EOF"), mock_200]
        resp = ncbi_get("esearch.fcgi", {"db": "pubmed"})
        assert resp.status_code == 200
        assert mock_get.call_count == 2

    @patch("ncbi_utils.time.sleep")
    @patch("ncbi_utils.requests.get")
    def test_raises_after_max_retries(self, mock_get, mock_sleep):
        from requests.exceptions import ConnectionError
        mock_get.side_effect = ConnectionError("SSL EOF")
        with pytest.raises(ConnectionError):
            ncbi_get("esearch.fcgi", {"db": "pubmed"}, max_retries=2)

    @patch("ncbi_utils.time.sleep")
    @patch("ncbi_utils.requests.get")
    def test_honors_retry_after_header(self, mock_get, mock_sleep):
        mock_429 = MagicMock()
        mock_429.status_code = 429
        mock_429.headers = {"retry-after": "5"}
        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_get.side_effect = [mock_429, mock_200]
        ncbi_get("esearch.fcgi", {"db": "pubmed"})
        # Should have slept for 5 seconds (from retry-after header)
        sleep_calls = [c[0][0] for c in mock_sleep.call_args_list]
        assert 5 in sleep_calls
