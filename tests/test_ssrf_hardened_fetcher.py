"""
Unit tests for SSRF-hardened fetcher, DNS validation, and redirect protection.
"""

import socket
from unittest.mock import patch, MagicMock
import pytest
import requests

from crawler.url_utils import (
    safe_http_get,
    is_safe_target_url,
    SafeFetchResponse,
)


class TestSSRFHardenedFetcher:
    """Test suite ensuring zero SSRF vulnerabilities."""

    @pytest.mark.parametrize("blocked_url", [
        "http://127.0.0.1:8080/admin",
        "http://127.0.0.1/",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/secret",
        "http://localhost:3000/",
        "http://0.0.0.0/",
        "http://metadata.google.internal/computeMetadata/v1/",
    ])
    def test_blocks_prohibited_literal_hosts(self, blocked_url):
        is_safe, err = is_safe_target_url(blocked_url, resolve_dns=False)
        assert is_safe is False
        assert err is not None

        resp, err_msg = safe_http_get(blocked_url)
        assert resp is None
        assert "blocked" in err_msg.lower() or "prohibited" in err_msg.lower()

    @pytest.mark.parametrize("private_ip_url", [
        "http://10.0.0.1/status",
        "http://192.168.1.1/setup",
        "http://172.16.0.5/api",
        "http://172.31.255.255/",
    ])
    def test_blocks_private_rfc1918_addresses(self, private_ip_url):
        is_safe, err = is_safe_target_url(private_ip_url, resolve_dns=False)
        assert is_safe is False
        assert "prohibited" in err.lower() or "private" in err.lower()

        resp, err_msg = safe_http_get(private_ip_url)
        assert resp is None
        assert err_msg is not None

    def test_blocks_dns_resolving_to_private_ip(self):
        fake_addr_info = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))
        ]
        with patch("socket.getaddrinfo", return_value=fake_addr_info):
            is_safe, err = is_safe_target_url("http://evil-domain.com", resolve_dns=True)
            assert is_safe is False
            assert "prohibited ip 127.0.0.1" in err.lower()

    def test_blocks_redirect_to_private_ip(self):
        """A public domain redirects to an internal metadata IP; safe_http_get must block it."""
        mock_public_addr = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80))
        ]

        def fake_getaddrinfo(host, port, *args, **kwargs):
            if "example.com" in host:
                return mock_public_addr
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", port))]

        mock_redirect_resp = MagicMock()
        mock_redirect_resp.is_redirect = True
        mock_redirect_resp.status_code = 302
        mock_redirect_resp.headers = {"Location": "http://169.254.169.254/latest/meta-data/"}

        with patch("socket.getaddrinfo", side_effect=fake_getaddrinfo):
            with patch.object(requests.Session, "get", return_value=mock_redirect_resp):
                resp, err = safe_http_get("http://example.com/redirect")
                assert resp is None
                assert "blocked" in err.lower() or "prohibited" in err.lower()

    def test_exceeds_max_redirects_limit(self):
        """Redirect loops must be terminated when exceeding max_redirects."""
        mock_public_addr = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80))
        ]

        mock_redirect_resp = MagicMock()
        mock_redirect_resp.is_redirect = True
        mock_redirect_resp.status_code = 301
        mock_redirect_resp.headers = {"Location": "http://example.com/loop"}

        with patch("socket.getaddrinfo", return_value=mock_public_addr):
            with patch.object(requests.Session, "get", return_value=mock_redirect_resp):
                resp, err = safe_http_get("http://example.com/start", max_redirects=3)
                assert resp is None
                assert "exceeded maximum redirect limit" in err.lower()

    def test_streams_with_byte_limit_truncation(self):
        """Responses exceeding max_bytes must be rejected with an error to protect memory."""
        mock_public_addr = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80))
        ]

        large_chunks = [b"A" * 1024 for _ in range(50)]  # 50 KB total

        mock_resp = MagicMock()
        mock_resp.is_redirect = False
        mock_resp.status_code = 200
        mock_resp.headers = {"Content-Type": "text/html; charset=utf-8"}
        mock_resp.iter_content.return_value = large_chunks
        mock_resp.encoding = "utf-8"

        with patch("socket.getaddrinfo", return_value=mock_public_addr):
            with patch.object(requests.Session, "get", return_value=mock_resp):
                resp, err = safe_http_get("http://example.com/bigpage", max_bytes=10 * 1024)
                # Safe fetcher must reject oversized responses to prevent memory exhaustion
                assert err is not None
                assert resp is None
                assert "exceeded" in err.lower() or "size" in err.lower()

    def test_successful_public_fetch(self):
        """Standard valid web page returns a SafeFetchResponse."""
        mock_public_addr = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80))
        ]

        mock_resp = MagicMock()
        mock_resp.is_redirect = False
        mock_resp.status_code = 200
        mock_resp.headers = {"Content-Type": "text/html; charset=utf-8"}
        mock_resp.iter_content.return_value = [b"<html><head><title>Test</title></head><body>Hello world</body></html>"]
        mock_resp.encoding = "utf-8"

        with patch("socket.getaddrinfo", return_value=mock_public_addr):
            with patch.object(requests.Session, "get", return_value=mock_resp):
                resp, err = safe_http_get("http://example.com/")
                assert err is None
                assert isinstance(resp, SafeFetchResponse)
                assert resp.status_code == 200
                assert "Hello world" in resp.text
