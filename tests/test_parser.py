"""
Unit tests for HTML parsing and hyperlink extraction.
"""

import pytest
from crawler.parser import parse_page_html


class TestHtmlParser:
    def test_extract_title(self):
        html = """
        <html>
            <head><title>  My Test Webpage  </title></head>
            <body><h1>Heading 1</h1></body>
        </html>
        """
        res = parse_page_html(html, base_url="https://example.com", base_domain="example.com")
        assert res["title"] == "My Test Webpage"

    def test_title_fallback_to_h1(self):
        html = """
        <html>
            <head></head>
            <body><h1>Alternative Title Heading</h1></body>
        </html>
        """
        res = parse_page_html(html, base_url="https://example.com", base_domain="example.com")
        assert res["title"] == "Alternative Title Heading"

    def test_title_fallback_when_empty(self):
        html = "<html><body><p>Just text</p></body></html>"
        res = parse_page_html(html, base_url="https://example.com", base_domain="example.com")
        assert res["title"] == "Untitled Page"

    def test_link_categorization_and_deduplication(self):
        html = """
        <html>
            <head><title>Portal</title></head>
            <body>
                <a href="/about">About Us</a>
                <a href="/about#team">About Team (Fragment)</a>
                <a href="https://example.com/contact">Contact</a>
                <a href="https://github.com/google">External GitHub</a>
                <a href="https://twitter.com/news">External Twitter</a>
                <a href="mailto:contact@example.com">Email</a>
                <a href="/doc.pdf">PDF Manual</a>
                <a href="/image.png">Logo</a>
            </body>
        </html>
        """
        res = parse_page_html(html, base_url="https://example.com", base_domain="example.com")

        # /about and /about#team normalize to https://example.com/about, deduplicated!
        assert "https://example.com/about" in res["internal_urls"]
        assert "https://example.com/contact" in res["internal_urls"]
        assert res["internal_count"] == 2

        # External links
        assert "https://github.com/google" in res["external_urls"]
        assert "https://twitter.com/news" in res["external_urls"]
        assert res["external_count"] == 2

        # Binary links and mailto should not be present
        for link in res["internal_urls"] + res["external_urls"]:
            assert not link.endswith(".pdf")
            assert not link.endswith(".png")
            assert not link.startswith("mailto:")

        assert res["unique_links_count"] == 4
        assert res["total_links_found"] == 8
