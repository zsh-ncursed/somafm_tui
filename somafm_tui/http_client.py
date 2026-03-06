"""HTTP client module with retry logic and connection pooling.

Uses a singleton HttpClient class with ThreadPoolExecutor for non-blocking requests.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Any, Dict, Optional, Callable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_TIMEOUT = 10  # seconds
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 0.5


class HttpClient:
    """HTTP client with connection pooling and retry logic.

    Implements lazy initialization and singleton pattern for the session.
    Thread-safe for read operations after initialization.
    Uses ThreadPoolExecutor for async requests.
    """

    _instance: Optional["HttpClient"] = None
    _executor: Optional[ThreadPoolExecutor] = None

    def __init__(
        self,
        retries: int = DEFAULT_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        timeout: int = DEFAULT_TIMEOUT,
        max_workers: int = 4,
    ):
        self.retries = retries
        self.backoff_factor = backoff_factor
        self.timeout = timeout
        self._session: Optional[requests.Session] = None
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
    
    @classmethod
    def get_instance(cls) -> "HttpClient":
        """Get or create the singleton HttpClient instance.
        
        Returns:
            HttpClient instance with configured session
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (useful for testing)."""
        if cls._instance is not None:
            if cls._instance._session is not None:
                cls._instance._session.close()
            cls._instance = None
    
    def get_session(self) -> requests.Session:
        """Get or create the requests session with connection pooling.
        
        Returns:
            Configured requests.Session instance
        """
        if self._session is None:
            self._session = self._create_session()
        return self._session
    
    def _create_session(self) -> requests.Session:
        """Create a new session with retry strategy and adapters.
        
        Returns:
            Configured requests.Session
        """
        session = requests.Session()
        
        retry_strategy = Retry(
            total=self.retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def fetch_json(
        self,
        url: str,
        timeout: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Fetch JSON data from URL.
        
        Args:
            url: URL to fetch from
            timeout: Request timeout (uses default if not specified)
            
        Returns:
            Parsed JSON data or None if request failed
        """
        return self._fetch_with_retry(url, timeout=timeout, parse_json=True)
    
    def fetch_bytes(
        self,
        url: str,
        timeout: Optional[int] = None,
    ) -> Optional[bytes]:
        """Fetch bytes from URL.
        
        Args:
            url: URL to fetch from
            timeout: Request timeout (uses default if not specified)
            
        Returns:
            Response bytes or None if request failed
        """
        return self._fetch_with_retry(url, timeout=timeout, parse_json=False)
    
    def _fetch_with_retry(
        self,
        url: str,
        timeout: Optional[int] = None,
        parse_json: bool = True,
    ) -> Optional[Any]:
        """Internal method for fetching with retry logic.
        
        Args:
            url: URL to fetch from
            timeout: Request timeout
            parse_json: Whether to parse response as JSON
            
        Returns:
            Response data (dict or bytes) or None if all retries failed
        """
        last_error: Optional[Exception] = None
        session = self.get_session()
        effective_timeout = timeout if timeout is not None else self.timeout
        
        for attempt in range(self.retries):
            try:
                response = session.get(url, timeout=effective_timeout)
                response.raise_for_status()
                
                if parse_json:
                    return response.json()
                else:
                    return response.content
                    
            except requests.Timeout as e:
                last_error = e
                logging.warning(
                    f"Timeout fetching {url} (attempt {attempt + 1}/{self.retries})"
                )
            except requests.RequestException as e:
                last_error = e
                logging.warning(
                    f"Error fetching {url} (attempt {attempt + 1}/{self.retries}): {e}"
                )
            
            if attempt < self.retries - 1:
                sleep_time = self.backoff_factor * (2**attempt)
                time.sleep(sleep_time)
        
        logging.error(f"Failed to fetch {url} after {self.retries} attempts: {last_error}")
        return None

    def fetch_json_async(
        self,
        url: str,
        timeout: Optional[int] = None,
        callback: Optional[Callable[[Optional[Dict[str, Any]]], None]] = None,
    ) -> Future:
        """Fetch JSON data asynchronously.
        
        Args:
            url: URL to fetch from
            timeout: Request timeout
            callback: Optional callback function to call with result
            
        Returns:
            Future object that will contain the result
        """
        def _fetch():
            result = self.fetch_json(url, timeout=timeout)
            if callback:
                callback(result)
            return result
        
        return self._executor.submit(_fetch)

    def fetch_bytes_async(
        self,
        url: str,
        timeout: Optional[int] = None,
        callback: Optional[Callable[[Optional[bytes]], None]] = None,
    ) -> Future:
        """Fetch bytes asynchronously.
        
        Args:
            url: URL to fetch from
            timeout: Request timeout
            callback: Optional callback function to call with result
            
        Returns:
            Future object that will contain the result
        """
        def _fetch():
            result = self.fetch_bytes(url, timeout=timeout)
            if callback:
                callback(result)
            return result
        
        return self._executor.submit(_fetch)

    def shutdown(self) -> None:
        """Shutdown the executor. Call before exiting."""
        if self._executor:
            self._executor.shutdown(wait=True)


# Convenience functions for backward compatibility
# These use the singleton instance internally

def get_session() -> requests.Session:
    """Get the shared session from HttpClient singleton.

    Returns:
        requests.Session instance
    """
    return HttpClient.get_instance().get_session()


def fetch_json(
    url: str,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
) -> Optional[Dict[str, Any]]:
    """Fetch JSON data with retry logic.

    Uses HttpClient singleton for connection pooling.

    Args:
        url: URL to fetch from
        timeout: Request timeout
        retries: Number of retry attempts
        backoff_factor: Backoff factor for retries

    Returns:
        Parsed JSON data or None
    """
    # For custom retries/backoff, create temporary client
    if retries != DEFAULT_RETRIES or backoff_factor != DEFAULT_BACKOFF_FACTOR:
        client = HttpClient(retries=retries, backoff_factor=backoff_factor, timeout=timeout)
        return client.fetch_json(url, timeout=timeout)

    return HttpClient.get_instance().fetch_json(url, timeout=timeout)


def fetch_bytes(
    url: str,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
) -> Optional[bytes]:
    """Fetch bytes with retry logic.

    Uses HttpClient singleton for connection pooling.

    Args:
        url: URL to fetch from
        timeout: Request timeout
        retries: Number of retry attempts
        backoff_factor: Backoff factor for retries

    Returns:
        Response bytes or None
    """
    # For custom retries/backoff, create temporary client
    if retries != DEFAULT_RETRIES or backoff_factor != DEFAULT_BACKOFF_FACTOR:
        client = HttpClient(retries=retries, backoff_factor=backoff_factor, timeout=timeout)
        return client.fetch_bytes(url, timeout=timeout)

    return HttpClient.get_instance().fetch_bytes(url, timeout=timeout)


# Async convenience functions

def fetch_json_async(
    url: str,
    timeout: int = DEFAULT_TIMEOUT,
    callback: Optional[Callable[[Optional[Dict[str, Any]]], None]] = None,
) -> Future:
    """Fetch JSON data asynchronously.

    Uses HttpClient singleton for connection pooling.
    Non-blocking: returns immediately with a Future.

    Args:
        url: URL to fetch from
        timeout: Request timeout
        callback: Optional callback function to call with result

    Returns:
        Future object that will contain the result
    """
    return HttpClient.get_instance().fetch_json_async(url, timeout=timeout, callback=callback)


def fetch_bytes_async(
    url: str,
    timeout: int = DEFAULT_TIMEOUT,
    callback: Optional[Callable[[Optional[bytes]], None]] = None,
) -> Future:
    """Fetch bytes asynchronously.

    Uses HttpClient singleton for connection pooling.
    Non-blocking: returns immediately with a Future.

    Args:
        url: URL to fetch from
        timeout: Request timeout
        callback: Optional callback function to call with result

    Returns:
        Future object that will contain the result
    """
    return HttpClient.get_instance().fetch_bytes_async(url, timeout=timeout, callback=callback)


def shutdown_http() -> None:
    """Shutdown HTTP client executor. Call before exiting."""
    if HttpClient._instance:
        HttpClient._instance.shutdown()
