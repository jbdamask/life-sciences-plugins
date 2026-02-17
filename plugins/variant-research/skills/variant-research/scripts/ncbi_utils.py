"""Shared NCBI E-utilities helpers: rate limiting, retries, and required params."""

import os
import time

import requests

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# NCBI requires tool and email on every request.
# See: https://www.ncbi.nlm.nih.gov/books/NBK25497/
NCBI_TOOL = os.environ.get("NCBI_TOOL", "variant_research")
NCBI_EMAIL = os.environ.get("NCBI_EMAIL", "variant_research@example.com")
NCBI_API_KEY = os.environ.get("NCBI_API_KEY")

# Rate: 3 req/s without key, 10 req/s with key
NCBI_MIN_INTERVAL = 0.11 if NCBI_API_KEY else 0.35
_last_request_time = 0.0


def ncbi_get(endpoint: str, params: dict, timeout: int = 30, max_retries: int = 3) -> requests.Response:
    """Make a GET request to an NCBI E-utilities endpoint with rate limiting and retries.

    Adds required tool/email/api_key params, enforces rate limiting,
    and retries on 429 (honoring retry-after header) and connection errors.
    """
    global _last_request_time

    # Add required NCBI params
    params["tool"] = NCBI_TOOL
    params["email"] = NCBI_EMAIL
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY

    url = f"{EUTILS_BASE}/{endpoint}"

    for attempt in range(max_retries):
        # Proactive rate limiting
        elapsed = time.time() - _last_request_time
        if elapsed < NCBI_MIN_INTERVAL:
            time.sleep(NCBI_MIN_INTERVAL - elapsed)

        try:
            _last_request_time = time.time()
            resp = requests.get(url, params=params, timeout=timeout)

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("retry-after", 2))
                time.sleep(retry_after)
                continue

            resp.raise_for_status()
            return resp

        except (requests.ConnectionError, requests.Timeout) as e:
            if attempt < max_retries - 1:
                backoff = 2 ** attempt  # 1s, 2s, 4s
                time.sleep(backoff)
                continue
            raise

    # Final attempt — let exceptions propagate
    _last_request_time = time.time()
    resp = requests.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp
