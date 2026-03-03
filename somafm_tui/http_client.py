"""HTTP client module with retry logic and connection pooling"""

import logging
import time
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_TIMEOUT = 10  # seconds
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 0.5

# Global session for connection pooling
_session: Optional[requests.Session] = None


def get_session() -> requests.Session:
    """Get or create a shared session with connection pooling."""
    global _session

    if _session is None:
        _session = requests.Session()

        retry_strategy = Retry(
            total=DEFAULT_RETRIES,
            backoff_factor=DEFAULT_BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        _session.mount("http://", adapter)
        _session.mount("https://", adapter)
        _session.timeout = DEFAULT_TIMEOUT

    return _session


def fetch_json(
    url: str,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
) -> Optional[Dict[str, Any]]:
    """Fetch JSON data with retry logic using shared session."""
    return _fetch_with_retry(
        url,
        timeout=timeout,
        retries=retries,
        backoff_factor=backoff_factor,
        parse_json=True,
    )


def fetch_bytes(
    url: str,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
) -> Optional[bytes]:
    """Fetch bytes with retry logic using shared session."""
    return _fetch_with_retry(
        url,
        timeout=timeout,
        retries=retries,
        backoff_factor=backoff_factor,
        parse_json=False,
    )


def _fetch_with_retry(
    url: str,
    timeout: int,
    retries: int,
    backoff_factor: float,
    parse_json: bool,
) -> Optional[Any]:
    """Internal function for fetching with retry logic."""
    last_error: Optional[Exception] = None
    session = get_session()

    for attempt in range(retries):
        try:
            response = session.get(url, timeout=timeout)
            response.raise_for_status()

            if parse_json:
                return response.json()
            else:
                return response.content

        except requests.Timeout as e:
            last_error = e
            logging.warning(f"Timeout fetching {url} (attempt {attempt + 1}/{retries})")
        except requests.RequestException as e:
            last_error = e
            logging.warning(f"Error fetching {url} (attempt {attempt + 1}/{retries}): {e}")

        if attempt < retries - 1:
            sleep_time = backoff_factor * (2**attempt)
            time.sleep(sleep_time)

    logging.error(f"Failed to fetch {url} after {retries} attempts: {last_error}")
    return None
