"""
Unit tests for webpage visible text extraction, word counts, snippet generation,
and sentence mining.
"""

import pytest
from crawler.parser import parse_page_html


class TestContentMining:
    """Test text parsing, word counting, and sentence mining."""

    def test_text_and_word_count_extraction(self):
        html = """
        <!DOCTYPE html>
        <html>
            <head>
                <title>AI Crawler Research</title>
                <style>body { font-size: 14px; }</style>
                <script>console.log("secret script");</script>
            </head>
            <body>
                <header><p>Header brand</p></header>
                <nav><a href="/">Home</a></nav>
                <main>
                    <h1>Distributed Web Crawlers</h1>
                    <p>Web crawlers systematically traverse the World Wide Web for indexing.</p>
                    <p>They collect documents to build modern search engine inverted indexes.</p>
                </main>
                <footer>Footer notice &copy; 2026</footer>
            </body>
        </html>
        """
        res = parse_page_html(
            html_content=html,
            base_url="https://crawler-research.org/article",
            base_domain="crawler-research.org",
        )

        assert res["title"] == "AI Crawler Research"
        # Script and style contents should be completely excluded from visible text and snippet
        assert "console.log" not in res["text_snippet"]
        assert "font-size" not in res["text_snippet"]

        # Word count should accurately count visible body words
        assert res["word_count"] > 10
        assert "Distributed Web Crawlers" in res["text_snippet"]

    def test_sentence_mining_with_search_terms(self):
        html = """
        <html>
            <body>
                <p>Quantum computing harnesses quantum mechanics to solve complex problems.</p>
                <p>Classical supercomputers take thousands of years for such calculations.</p>
                <p>Qubits exist in multidimensional states of superposition and entanglement.</p>
                <p>Weather forecasts and logistics will be transformed by quantum algorithms.</p>
            </body>
        </html>
        """
        # User provided target search query / filter: "quantum algorithms"
        res = parse_page_html(
            html_content=html,
            base_url="https://quantum.edu/intro",
            base_domain="quantum.edu",
            target_terms="quantum algorithms",
        )

        assert res["match_count"] >= 2
        assert len(res["matching_sentences"]) == 2
        # Should match sentence 1 containing "quantum"
        assert any("mechanics" in s for s in res["matching_sentences"])
        # Should match sentence 4 containing "quantum algorithms"
        assert any("transformed by quantum algorithms" in s for s in res["matching_sentences"])
        # Should not match sentence 2 which has neither "quantum" nor "algorithms"
        assert not any("Classical supercomputers" in s for s in res["matching_sentences"])

    def test_snippet_truncation(self):
        long_text = "<p>" + ("Streamlit provides interactive dashboards. " * 30) + "</p>"
        html = f"<html><body>{long_text}</body></html>"

        res = parse_page_html(
            html_content=html,
            base_url="https://test.io",
            base_domain="test.io",
        )

        assert len(res["text_snippet"]) <= 320
        assert res["word_count"] >= 80

    def test_empty_or_malformed_content(self):
        res = parse_page_html(
            html_content="",
            base_url="https://empty.org",
            base_domain="empty.org",
            target_terms="search",
        )

        assert res["word_count"] == 0
        assert res["text_snippet"] == ""
        assert res["matching_sentences"] == []
        assert res["match_count"] == 0
