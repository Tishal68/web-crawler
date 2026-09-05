"""
Unit tests for URL validation, normalization, and filtering utilities.
"""

import pytest
from crawler.url_utils import (
    is_valid_url,
    is_binary_url,
    get_domain,
    is_same_domain,
    normalize_url,
)


class TestUrlValidation:
    def test_valid_http_and_https(self):
        assert is_valid_url("http://example.com")
        assert is_valid_url("https://example.com/path?query=1")
        assert is_valid_url("https://sub.domain.org/index.html")

    def test_invalid_schemes(self):
        assert not is_valid_url("ftp://example.com")
        assert not is_valid_url("mailto:user@example.com")
        assert not is_valid_url("javascript:alert(1)")
        assert not is_valid_url("tel:+1234567890")
        assert not is_valid_url("file:///etc/passwd")

    def test_empty_and_malformed(self):
        assert not is_valid_url("")
        assert not is_valid_url(None)
        assert not is_valid_url("   ")
        assert not is_valid_url("htp://broken")
        assert not is_valid_url("http://")


class TestBinaryFilter:
    def test_binary_extensions_detected(self):
        assert is_binary_url("https://example.com/image.png")
        assert is_binary_url("https://example.com/photo.jpg")
        assert is_binary_url("https://example.com/doc.pdf")
        assert is_binary_url("https://example.com/archive.zip")
        assert is_binary_url("https://example.com/app.exe")
        assert is_binary_url("https://example.com/video.mp4")

    def test_html_and_text_not_binary(self):
        assert not is_binary_url("https://example.com/index.html")
        assert not is_binary_url("https://example.com/about")
        assert not is_binary_url("https://example.com/")


class TestDomainMatching:
    def test_get_domain(self):
        assert get_domain("https://EXAMPLE.COM/page") == "example.com"
        assert get_domain("http://sub.test.org:8080/foo") == "sub.test.org"

    def test_is_same_domain(self):
        base = "example.com"
        assert is_same_domain("https://example.com/page", base)
        assert is_same_domain("https://blog.example.com/post", base, allow_subdomains=True)
        assert not is_same_domain("https://other.com/page", base)


class TestUrlNormalization:
    def test_strip_fragments(self):
        url = "https://example.com/page#section1"
        assert normalize_url(url) == "https://example.com/page"

    def test_lowercase_scheme_and_domain(self):
        url = "HTTP://ExAmPlE.CoM/Path"
        assert normalize_url(url) == "http://example.com/Path"

    def test_resolve_relative_urls(self):
        base = "https://example.com/blog/article1"
        assert normalize_url("/about", base_url=base) == "https://example.com/about"
        assert normalize_url("page2", base_url="https://example.com/blog/") == "https://example.com/blog/page2"
        assert normalize_url("../contact", base_url="https://example.com/dept/team/") == "https://example.com/dept/contact"

    def test_remove_default_ports(self):
        assert normalize_url("http://example.com:80/home") == "http://example.com/home"
        assert normalize_url("https://example.com:443/home") == "https://example.com/home"
        assert normalize_url("https://example.com:8443/home") == "https://example.com:8443/home"

    def test_sort_query_parameters(self):
        url1 = "https://example.com/search?b=2&a=1"
        url2 = "https://example.com/search?a=1&b=2"
        assert normalize_url(url1) == normalize_url(url2)
        assert normalize_url(url1) == "https://example.com/search?a=1&b=2"

    def test_redundant_slashes_and_trailing_slash(self):
        assert normalize_url("https://example.com//a//b/") == "https://example.com/a/b"
        assert normalize_url("https://example.com/") == "https://example.com"
        assert normalize_url("https://example.com") == "https://example.com"

    def test_reject_javascript_and_mailto(self):
        assert normalize_url("javascript:void(0)", base_url="https://example.com") is None
        assert normalize_url("mailto:info@example.com", base_url="https://example.com") is None
