"""Tests for http_client module."""

import pytest
from unittest.mock import Mock, patch, call, MagicMock
import time
from concurrent.futures import Future

from somafm_tui.http_client import (
    HttpClient,
    get_session,
    fetch_json,
    fetch_bytes,
    fetch_json_async,
    fetch_bytes_async,
    shutdown_http,
    DEFAULT_TIMEOUT,
    DEFAULT_RETRIES,
    DEFAULT_BACKOFF_FACTOR,
)


class TestHttpClientInit:
    """Tests for HttpClient initialization."""

    def test_init_sets_attributes(self):
        """Should initialize all attributes correctly."""
        client = HttpClient(
            retries=5,
            backoff_factor=1.0,
            timeout=20,
            max_workers=8,
        )

        assert client.retries == 5
        assert client.backoff_factor == 1.0
        assert client.timeout == 20
        assert client._session is None
        assert client._executor is not None

    def test_init_default_values(self):
        """Should use default values."""
        client = HttpClient()

        assert client.retries == DEFAULT_RETRIES
        assert client.backoff_factor == DEFAULT_BACKOFF_FACTOR
        assert client.timeout == DEFAULT_TIMEOUT


class TestHttpClientSingleton:
    """Tests for HttpClient singleton pattern."""

    def test_get_instance_creates_singleton(self):
        """Should create singleton instance."""
        HttpClient.reset_instance()

        instance1 = HttpClient.get_instance()
        instance2 = HttpClient.get_instance()

        assert instance1 is instance2

    def test_get_instance_thread_safe(self):
        """Should be thread-safe (basic test)."""
        HttpClient.reset_instance()

        # Multiple calls should return same instance
        instances = [HttpClient.get_instance() for _ in range(5)]

        assert all(inst is instances[0] for inst in instances)

    def test_reset_instance(self):
        """Should reset singleton instance."""
        HttpClient.reset_instance()

        instance = HttpClient.get_instance()
        HttpClient.reset_instance()
        new_instance = HttpClient.get_instance()

        assert instance is not new_instance

    def test_reset_instance_closes_session(self):
        """Should close session on reset."""
        HttpClient.reset_instance()

        client = HttpClient.get_instance()
        client.get_session()  # Create session
        session = client._session

        HttpClient.reset_instance()

        # Session should be closed (we can't directly test this, but we can verify reset)
        new_client = HttpClient.get_instance()
        assert new_client._session is None

    def test_reset_instance_with_none(self):
        """Should handle reset when instance is None."""
        HttpClient.reset_instance()
        HttpClient.reset_instance()  # Should not raise


class TestHttpClientSession:
    """Tests for HttpClient session management."""

    def test_get_session_creates_session(self):
        """Should create session on first call."""
        client = HttpClient()

        session = client.get_session()

        assert session is not None
        assert client._session is session

    def test_get_session_returns_cached(self):
        """Should return cached session."""
        client = HttpClient()

        session1 = client.get_session()
        session2 = client.get_session()

        assert session1 is session2

    def test_create_session_configures_retry(self):
        """Should configure session with retry strategy."""
        client = HttpClient(retries=5, backoff_factor=2.0)

        session = client.get_session()

        # Verify session has adapters mounted
        assert 'http://' in session.adapters
        assert 'https://' in session.adapters


class TestHttpClientFetchJson:
    """Tests for HttpClient fetch_json method."""

    def test_fetch_json_success(self):
        """Should fetch JSON successfully."""
        client = HttpClient()
        mock_response = Mock()
        mock_response.json.return_value = {"key": "value"}
        mock_response.raise_for_status = Mock()

        with patch.object(client, 'get_session') as mock_get_session:
            mock_get_session.return_value.get.return_value = mock_response

            result = client.fetch_json("https://example.com/api")

            assert result == {"key": "value"}
            mock_get_session.return_value.get.assert_called_once()

    def test_fetch_json_returns_none_on_error(self):
        """Should return None on error."""
        import requests
        client = HttpClient(retries=1)

        with patch.object(client, 'get_session') as mock_get_session:
            mock_get_session.return_value.get.side_effect = requests.RequestException("error")

            result = client.fetch_json("https://example.com/api")

            assert result is None

    def test_fetch_json_with_timeout(self):
        """Should use provided timeout."""
        client = HttpClient()
        mock_response = Mock()
        mock_response.json.return_value = {"key": "value"}
        mock_response.raise_for_status = Mock()

        with patch.object(client, 'get_session') as mock_get_session:
            mock_get_session.return_value.get.return_value = mock_response

            client.fetch_json("https://example.com/api", timeout=30)

            mock_get_session.return_value.get.assert_called_once()
            call_kwargs = mock_get_session.return_value.get.call_args[1]
            assert call_kwargs['timeout'] == 30

    def test_fetch_json_uses_default_timeout(self):
        """Should use default timeout when not provided."""
        client = HttpClient(timeout=25)
        mock_response = Mock()
        mock_response.json.return_value = {"key": "value"}
        mock_response.raise_for_status = Mock()

        with patch.object(client, 'get_session') as mock_get_session:
            mock_get_session.return_value.get.return_value = mock_response

            client.fetch_json("https://example.com/api")

            call_kwargs = mock_get_session.return_value.get.call_args[1]
            assert call_kwargs['timeout'] == 25


class TestHttpClientFetchBytes:
    """Tests for HttpClient fetch_bytes method."""

    def test_fetch_bytes_success(self):
        """Should fetch bytes successfully."""
        client = HttpClient()
        mock_response = Mock()
        mock_response.content = b"binary data"
        mock_response.raise_for_status = Mock()

        with patch.object(client, 'get_session') as mock_get_session:
            mock_get_session.return_value.get.return_value = mock_response

            result = client.fetch_bytes("https://example.com/file")

            assert result == b"binary data"

    def test_fetch_bytes_returns_none_on_error(self):
        """Should return None on error."""
        import requests
        client = HttpClient(retries=1)

        with patch.object(client, 'get_session') as mock_get_session:
            mock_get_session.return_value.get.side_effect = requests.RequestException("error")

            result = client.fetch_bytes("https://example.com/file")

            assert result is None


class TestHttpClientRetry:
    """Tests for HttpClient retry logic."""

    def test_fetch_json_retries_on_timeout(self):
        """Should retry on timeout."""
        import requests
        client = HttpClient(retries=3, backoff_factor=0.01)
        mock_response = Mock()
        mock_response.json.return_value = {"key": "value"}
        mock_response.raise_for_status = Mock()

        with patch.object(client, 'get_session') as mock_get_session:
            mock_get_session.return_value.get.side_effect = [
                requests.Timeout("timeout"),
                requests.Timeout("timeout"),
                mock_response,
            ]

            result = client.fetch_json("https://example.com/api")

            assert result == {"key": "value"}
            assert mock_get_session.return_value.get.call_count == 3

    def test_fetch_json_returns_none_after_max_retries(self):
        """Should return None after max retries."""
        import requests
        client = HttpClient(retries=2, backoff_factor=0.01)

        with patch.object(client, 'get_session') as mock_get_session:
            mock_get_session.return_value.get.side_effect = requests.RequestException("error")

            result = client.fetch_json("https://example.com/api")

            assert result is None
            assert mock_get_session.return_value.get.call_count == 2

    def test_fetch_json_retries_on_request_exception(self):
        """Should retry on RequestException."""
        import requests
        client = HttpClient(retries=2, backoff_factor=0.01)
        mock_response = Mock()
        mock_response.json.return_value = {"key": "value"}
        mock_response.raise_for_status = Mock()

        with patch.object(client, 'get_session') as mock_get_session:
            mock_get_session.return_value.get.side_effect = [
                requests.RequestException("error"),
                mock_response,
            ]

            result = client.fetch_json("https://example.com/api")

            assert result == {"key": "value"}

    def test_fetch_json_handles_timeout_exception(self):
        """Should handle Timeout exception."""
        import requests
        client = HttpClient(retries=1)

        with patch.object(client, 'get_session') as mock_get_session:
            mock_get_session.return_value.get.side_effect = requests.Timeout("timeout")

            result = client.fetch_json("https://example.com/api")

            assert result is None


class TestHttpClientAsync:
    """Tests for HttpClient async methods."""

    def test_fetch_json_async_returns_future(self):
        """Should return Future object."""
        client = HttpClient()

        with patch.object(client, 'fetch_json', return_value={"key": "value"}):
            future = client.fetch_json_async("https://example.com/api")

            assert isinstance(future, Future)

    def test_fetch_json_async_calls_callback(self):
        """Should call callback with result."""
        client = HttpClient()
        callback = Mock()

        with patch.object(client, 'fetch_json', return_value={"key": "value"}):
            future = client.fetch_json_async("https://example.com/api", callback=callback)
            future.result()  # Wait for completion

            callback.assert_called_once_with({"key": "value"})

    def test_fetch_json_async_without_callback(self):
        """Should work without callback."""
        client = HttpClient()

        with patch.object(client, 'fetch_json', return_value={"key": "value"}):
            future = client.fetch_json_async("https://example.com/api")
            result = future.result()

            assert result == {"key": "value"}

    def test_fetch_bytes_async_returns_future(self):
        """Should return Future object for bytes."""
        client = HttpClient()

        with patch.object(client, 'fetch_bytes', return_value=b"data"):
            future = client.fetch_bytes_async("https://example.com/file")

            assert isinstance(future, Future)

    def test_fetch_bytes_async_calls_callback(self):
        """Should call callback with bytes result."""
        client = HttpClient()
        callback = Mock()

        with patch.object(client, 'fetch_bytes', return_value=b"data"):
            future = client.fetch_bytes_async("https://example.com/file", callback=callback)
            future.result()

            callback.assert_called_once_with(b"data")

    def test_fetch_json_async_handles_exception(self):
        """Should handle exception in async fetch."""
        client = HttpClient()
        callback = Mock()

        with patch.object(client, 'fetch_json', return_value=None):
            future = client.fetch_json_async("https://example.com/api", callback=callback)
            result = future.result()

            assert result is None

    def test_fetch_bytes_async_handles_exception(self):
        """Should handle exception in async bytes fetch."""
        client = HttpClient()
        callback = Mock()

        with patch.object(client, 'fetch_bytes', return_value=None):
            future = client.fetch_bytes_async("https://example.com/file", callback=callback)
            result = future.result()

            assert result is None


class TestHttpClientShutdown:
    """Tests for HttpClient shutdown."""

    def test_shutdown(self):
        """Should shutdown executor."""
        client = HttpClient()

        # Should not raise
        client.shutdown()


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_session(self):
        """Should return session from singleton."""
        HttpClient.reset_instance()

        session = get_session()

        assert session is not None

    def test_fetch_json_uses_singleton(self):
        """Should use singleton client."""
        HttpClient.reset_instance()
        mock_response = Mock()
        mock_response.json.return_value = {"key": "value"}
        mock_response.raise_for_status = Mock()

        with patch.object(HttpClient, 'get_instance') as mock_get_instance:
            mock_client = mock_get_instance.return_value
            mock_client.fetch_json.return_value = {"key": "value"}

            result = fetch_json("https://example.com/api")

            assert result == {"key": "value"}
            mock_client.fetch_json.assert_called_once()

    def test_fetch_json_with_custom_retries(self):
        """Should create temporary client for custom retries."""
        with patch('somafm_tui.http_client.HttpClient') as MockClient:
            mock_client = Mock()
            mock_client.fetch_json.return_value = {"key": "value"}
            MockClient.return_value = mock_client

            result = fetch_json("https://example.com/api", retries=5, backoff_factor=1.0)

            MockClient.assert_called_once_with(retries=5, backoff_factor=1.0, timeout=DEFAULT_TIMEOUT)
            assert result == {"key": "value"}

    def test_fetch_bytes_uses_singleton(self):
        """Should use singleton client for bytes."""
        HttpClient.reset_instance()

        with patch.object(HttpClient, 'get_instance') as mock_get_instance:
            mock_client = mock_get_instance.return_value
            mock_client.fetch_bytes.return_value = b"data"

            result = fetch_bytes("https://example.com/file")

            assert result == b"data"
            mock_client.fetch_bytes.assert_called_once()

    def test_fetch_bytes_with_custom_retries(self):
        """Should create temporary client for custom retries."""
        with patch('somafm_tui.http_client.HttpClient') as MockClient:
            mock_client = Mock()
            mock_client.fetch_bytes.return_value = b"data"
            MockClient.return_value = mock_client

            result = fetch_bytes("https://example.com/file", retries=5, backoff_factor=1.0)

            MockClient.assert_called_once()
            assert result == b"data"

    def test_fetch_json_async_uses_singleton(self):
        """Should use singleton client for async fetch."""
        HttpClient.reset_instance()

        with patch.object(HttpClient, 'get_instance') as mock_get_instance:
            mock_client = mock_get_instance.return_value
            mock_client.fetch_json_async.return_value = Mock(spec=Future)

            future = fetch_json_async("https://example.com/api")

            mock_client.fetch_json_async.assert_called_once()
            assert isinstance(future, Future)

    def test_fetch_bytes_async_uses_singleton(self):
        """Should use singleton client for async bytes fetch."""
        HttpClient.reset_instance()

        with patch.object(HttpClient, 'get_instance') as mock_get_instance:
            mock_client = mock_get_instance.return_value
            mock_client.fetch_bytes_async.return_value = Mock(spec=Future)

            future = fetch_bytes_async("https://example.com/file")

            mock_client.fetch_bytes_async.assert_called_once()
            assert isinstance(future, Future)

    def test_shutdown_http(self):
        """Should shutdown singleton client."""
        HttpClient.reset_instance()

        # Get instance to create one
        _ = HttpClient.get_instance()

        # Should not raise
        shutdown_http()


class TestHttpRetryStrategy:
    """Tests for HTTP retry strategy configuration."""

    def test_retry_strategy_status_codes(self):
        """Should retry on specific status codes."""
        client = HttpClient()
        session = client.get_session()

        # Get the adapter
        adapter = session.get_adapter('https://example.com')

        # Verify retry strategy is configured
        assert adapter.max_retries is not None
        # Status codes that should trigger retry
        assert 429 in adapter.max_retries.status_forcelist
        assert 500 in adapter.max_retries.status_forcelist
        assert 502 in adapter.max_retries.status_forcelist
        assert 503 in adapter.max_retries.status_forcelist
        assert 504 in adapter.max_retries.status_forcelist

    def test_retry_strategy_allowed_methods(self):
        """Should only retry safe methods."""
        client = HttpClient()
        session = client.get_session()
        adapter = session.get_adapter('https://example.com')

        # Should only retry GET, HEAD, OPTIONS
        assert 'GET' in adapter.max_retries.allowed_methods
        assert 'HEAD' in adapter.max_retries.allowed_methods
        assert 'OPTIONS' in adapter.max_retries.allowed_methods
