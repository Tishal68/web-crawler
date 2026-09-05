"""
Unit tests for Robots.txt manager conforming to RFC 9309.
Tests HTTP 200/203 rule evaluation, 4xx allowance, 5xx server error rejection,
timeout and SSL failure handling, and caching.
"""

import pytest
from unittest.mock import patch, MagicMock
import requests

from crawler.robots import RobotsManager, RobotsCheckResult


class TestRobotsManager:
    def test_robots_200_ok_allow_and_disallow(self):
        manager = RobotsManager(user_agent="MyCrawlerBot")
        robots_content = """User-agent: *
Disallow: /admin/
Disallow: /private/
Allow: /public/
"""
        with patch("requests.get") as mock_get:
            mock_resp = requests.Response()
            mock_resp.status_code = 200
            mock_resp._content = robots_content.encode("utf-8")
            mock_get.return_value = mock_resp

            # Check allowed page
            res_pub = manager.check_allowed("https://example.com/public/index.html", user_agent="MyCrawlerBot")
            assert res_pub.allowed is True
            assert res_pub.status == "ALLOWED"

            # Check disallowed page
            res_priv = manager.check_allowed("https://example.com/admin/settings", user_agent="MyCrawlerBot")
            assert res_priv.allowed is False
            assert res_priv.status == "DISALLOWED"

            # Verify caching: requests.get called only once for example.com
            manager.is_allowed("https://example.com/other-page")
            assert mock_get.call_count == 1

    def test_robots_404_not_found_allows_all(self):
        manager = RobotsManager()
        with patch("requests.get") as mock_get:
            mock_resp = requests.Response()
            mock_resp.status_code = 404
            mock_get.return_value = mock_resp

            res = manager.check_allowed("https://example.com/anything")
            assert res.allowed is True
            assert res.status == "ALLOWED_NO_POLICY"
            assert manager.is_allowed("https://example.com/anything") is True

    def test_robots_500_server_error_fails_closed(self):
        manager = RobotsManager()
        with patch("requests.get") as mock_get:
            mock_resp = requests.Response()
            mock_resp.status_code = 500
            mock_get.return_value = mock_resp

            res = manager.check_allowed("https://example.com/page")
            assert res.allowed is False
            assert res.status == "SERVER_ERROR_DISALLOWED"
            assert manager.is_allowed("https://example.com/page") is False

    def test_robots_timeout_fails_closed(self):
        manager = RobotsManager(timeout=1.0)
        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectTimeout("Timeout connecting to server")

            res = manager.check_allowed("https://example.com/page")
            assert res.allowed is False
            assert res.status == "TIMEOUT"
            assert manager.is_allowed("https://example.com/page") is False

    def test_robots_ssl_error_fails_closed(self):
        manager = RobotsManager()
        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.SSLError("Certificate verify failed")

            res = manager.check_allowed("https://example.com/page")
            assert res.allowed is False
            assert res.status == "SSL_ERROR"
            assert manager.is_allowed("https://example.com/page") is False

    def test_robots_connection_error_fails_closed(self):
        manager = RobotsManager()
        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("DNS lookup failed")

            res = manager.check_allowed("https://example.com/page")
            assert res.allowed is False
            assert res.status == "CONNECTION_ERROR"
            assert manager.is_allowed("https://example.com/page") is False

    def test_robots_malformed_text_permissive_fallback(self):
        manager = RobotsManager()
        with patch("requests.get") as mock_get:
            mock_resp = requests.Response()
            mock_resp.status_code = 200
            mock_resp._content = b"\x00\x01\x02Non-text binary garbage"
            mock_get.return_value = mock_resp

            res = manager.check_allowed("https://example.com/page")
            # Should not crash, returns boolean
            assert isinstance(res.allowed, bool)
