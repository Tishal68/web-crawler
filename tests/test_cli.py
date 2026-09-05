"""
Unit tests for the CLI interface:
- Argument parsing and defaults
- Input validation and bounds checking
- Y/N prompt parsing
- Export functionality (CSV and JSON)
- Error handling and keyboard interrupt resilience
- End-to-end execution with mocked crawler
"""

import os
import json
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from cli.runner import (
    build_parser,
    prompt_bool,
    export_results,
    main,
)
from cli.terminal import ColorManager, format_progress_bar, truncate
from crawler.models import PageResult, CrawlFailure, CrawlSessionSummary, CrawlProgressEvent


class TestCliArgumentParser:
    def test_default_arguments(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.url is None
        assert args.depth == 2
        assert args.max_pages == 50
        assert args.timeout == 10.0
        assert args.delay == 0.2
        assert args.same_domain is True
        assert args.respect_robots is True
        assert args.output is None
        assert args.no_color is False

    def test_custom_arguments(self):
        parser = build_parser()
        args = parser.parse_args([
            "--url", "https://example.org",
            "--depth", "3",
            "--max-pages", "25",
            "--timeout", "5.5",
            "--delay", "0.5",
            "--allow-external",
            "--ignore-robots",
            "--output", "report.csv",
            "--no-color",
            "--no-tree",
            "--no-table",
            "--no-db",
        ])
        assert args.url == "https://example.org"
        assert args.depth == 3
        assert args.max_pages == 25
        assert args.timeout == 5.5
        assert args.delay == 0.5
        assert args.same_domain is False
        assert args.respect_robots is False
        assert args.output == "report.csv"
        assert args.no_color is True
        assert args.no_tree is True
        assert args.no_table is True
        assert args.no_db is True

    def test_search_and_minimal_arguments(self):
        parser = build_parser()
        args = parser.parse_args([
            "machine learning models",
            "--keyword", "neural",
            "--quiet",
            "--json",
        ])
        assert args.target == "machine learning models"
        assert args.keyword == "neural"
        assert args.quiet is True
        assert args.json is True

    def test_query_flag_and_minimal_alias(self):
        parser = build_parser()
        args = parser.parse_args([
            "--query", "deep learning",
            "-k", "transformer",
            "--minimal",
        ])
        assert args.query == "deep learning"
        assert args.keyword == "transformer"
        assert args.quiet is True


class TestPromptHelpers:
    def test_prompt_bool_parsing(self):
        colors = ColorManager(force_no_color=True)

        with patch("builtins.input", side_effect=["y"]):
            assert prompt_bool("Test?", default=False, colors=colors) is True

        with patch("builtins.input", side_effect=["yes"]):
            assert prompt_bool("Test?", default=False, colors=colors) is True

        with patch("builtins.input", side_effect=["n"]):
            assert prompt_bool("Test?", default=True, colors=colors) is False

        with patch("builtins.input", side_effect=["NO"]):
            assert prompt_bool("Test?", default=True, colors=colors) is False

        with patch("builtins.input", side_effect=["", ""]):
            assert prompt_bool("Test?", default=True, colors=colors) is True
            assert prompt_bool("Test?", default=False, colors=colors) is False


class TestTerminalAndFormatting:
    def test_color_manager_no_color(self):
        colors = ColorManager(force_no_color=True)
        assert colors.enabled is False
        assert colors.green("Test") == "Test"
        assert colors.red("Error") == "Error"

    def test_truncate(self):
        assert truncate("Short", 10) == "Short"
        assert truncate("A very long title that exceeds length", 15) == "A very long ..."

    def test_format_progress_bar(self):
        bar_half = format_progress_bar(25, 50, width=20)
        assert "50%" in bar_half
        assert "25/50" in bar_half

        bar_zero = format_progress_bar(0, 0, width=20)
        assert "0/0" in bar_zero


class TestExportFunctionality:
    def test_export_results_csv(self, tmp_path):
        colors = ColorManager(force_no_color=True)
        csv_path = str(tmp_path / "test_out.csv")

        page = PageResult(
            url="https://example.com/test",
            title="Test Page",
            depth=1,
            status_code=200,
            total_links=3,
            unique_links=3,
            internal_links_count=2,
            external_links_count=1,
            response_time=0.15,
            content_type="text/html",
            domain="example.com",
        )

        ok = export_results([page], [], None, csv_path, colors)
        assert ok is True
        assert os.path.exists(csv_path)

        df = pd.read_csv(csv_path)
        assert len(df) == 1
        assert df.iloc[0]["URL"] == "https://example.com/test"
        assert df.iloc[0]["Title"] == "Test Page"

    def test_export_results_json(self, tmp_path):
        colors = ColorManager(force_no_color=True)
        json_path = str(tmp_path / "test_out.json")

        page = PageResult(
            url="https://example.com/api",
            title="API Page",
            depth=0,
            status_code=200,
            total_links=1,
            unique_links=1,
            internal_links_count=1,
            external_links_count=0,
            internal_urls=["https://example.com/api/v1"],
            external_urls=[],
            response_time=0.08,
            content_type="text/html",
            domain="example.com",
        )

        ok = export_results([page], [], None, json_path, colors)
        assert ok is True
        assert os.path.exists(json_path)

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data["pages"]) == 1
        assert data["pages"][0]["url"] == "https://example.com/api"


class TestCliExecution:
    def test_invalid_url_returns_code_1(self):
        exit_code = main(["--url", "invalid-scheme://bad", "--no-color"])
        assert exit_code == 1

    @patch("cli.runner.WebCrawler")
    def test_mocked_cli_crawl_execution(self, mock_crawler_class, tmp_path):
        mock_crawler = MagicMock()
        mock_crawler_class.return_value = mock_crawler

        page = PageResult(
            url="https://example.com",
            title="Mock Home",
            depth=0,
            status_code=200,
            total_links=2,
            unique_links=2,
            internal_links_count=2,
            external_links_count=0,
            response_time=0.1,
            content_type="text/html",
            domain="example.com",
        )
        mock_crawler.page_results = [page]
        mock_crawler.failures = []
        mock_crawler.discovered_urls = {"https://example.com", "https://example.com/about"}

        summary = CrawlSessionSummary(
            session_id="mock_session",
            start_url="https://example.com",
            max_depth=1,
            max_pages=10,
            start_time="2026-09-05T10:00:00",
            end_time="2026-09-05T10:00:01",
            elapsed_seconds=1.0,
            pages_crawled=1,
            discovered_urls_count=2,
            failed_urls_count=0,
            total_internal_links=2,
            total_external_links=0,
            stay_on_domain=True,
            max_depth_reached=0,
        )

        def mock_stream(cfg):
            yield CrawlProgressEvent(
                event_type="success",
                current_url="https://example.com",
                current_depth=0,
                pages_crawled=1,
                discovered_count=2,
                failed_count=0,
                message="Crawled mock",
                page_result=page,
            )
            return summary

        mock_crawler.crawl_stream.side_effect = mock_stream

        out_file = str(tmp_path / "mock_output.json")
        exit_code = main([
            "--url", "https://example.com",
            "--depth", "1",
            "--max-pages", "5",
            "--output", out_file,
            "--no-color",
            "--no-db",
        ])

        assert exit_code == 0
        assert os.path.exists(out_file)
        with open(out_file, "r", encoding="utf-8") as f:
            saved = json.load(f)
        assert len(saved["pages"]) == 1
        assert saved["pages"][0]["title"] == "Mock Home"

    @patch("cli.runner.WebCrawler")
    def test_keyboard_interrupt_handling(self, mock_crawler_class):
        mock_crawler = MagicMock()
        mock_crawler_class.return_value = mock_crawler
        mock_crawler.page_results = []
        mock_crawler.failures = []
        mock_crawler.discovered_urls = set()

        def mock_interrupt_stream(cfg):
            raise KeyboardInterrupt()
            yield

        mock_crawler.crawl_stream.side_effect = mock_interrupt_stream

        exit_code = main(["--url", "https://example.com", "--no-color", "--no-db"])
        assert exit_code == 130

    def test_invalid_cli_arguments_return_code_1(self):
        # Negative depth
        assert main(["--url", "https://example.com", "--depth", "-1"]) == 1

        # Zero or negative max pages
        assert main(["--url", "https://example.com", "--max-pages", "0"]) == 1
        assert main(["--url", "https://example.com", "--max-pages", "-5"]) == 1

        # Zero or negative timeout
        assert main(["--url", "https://example.com", "--timeout", "0"]) == 1
        assert main(["--url", "https://example.com", "--timeout", "-2.0"]) == 1

        # Negative delay
        assert main(["--url", "https://example.com", "--delay", "-0.5"]) == 1

        # Invalid export extension
        assert main(["--url", "https://example.com", "--output", "bad_file.txt"]) == 1
        assert main(["--url", "https://example.com", "--output", "binary.exe"]) == 1

    @patch("cli.runner.WebCrawler")
    def test_cli_quiet_minimal_mode(self, mock_crawler_class, capsys):
        mock_crawler = MagicMock()
        mock_crawler_class.return_value = mock_crawler
        page = PageResult(
            url="https://example.com",
            title="Mock Home",
            depth=0,
            status_code=200,
            word_count=150,
            match_count=2,
            total_links=5,
            unique_links=5,
            internal_links_count=5,
            external_links_count=0,
            response_time=0.1,
            domain="example.com",
            text_snippet="A mock page",
            content_type="text/html",
            timestamp="2026-09-05T10:00:00",
        )
        mock_crawler.page_results = [page]
        mock_crawler.failures = []
        mock_crawler.discovered_urls = {"https://example.com"}

        summary = CrawlSessionSummary(
            session_id="mock_session",
            start_url="https://example.com",
            max_depth=1,
            max_pages=1,
            start_time="2026-09-05T10:00:00",
            end_time="2026-09-05T10:00:01",
            elapsed_seconds=0.5,
            pages_crawled=1,
            discovered_urls_count=5,
            failed_urls_count=0,
            total_internal_links=5,
            total_external_links=0,
            stay_on_domain=True,
            max_depth_reached=0,
        )

        def mock_stream(cfg):
            yield CrawlProgressEvent(
                event_type="success",
                current_url="https://example.com",
                current_depth=0,
                pages_crawled=1,
                discovered_count=5,
                failed_count=0,
                message="Crawled mock",
                page_result=page,
            )
            return summary

        mock_crawler.crawl_stream.side_effect = mock_stream

        exit_code = main(["https://example.com", "--quiet", "--no-db", "--no-color"])
        assert exit_code == 0
        captured = capsys.readouterr().out
        assert "[200] D0 https://example.com" in captured
        assert "[DONE] Finished in" in captured
        # Ensure ASCII visualization blocks are omitted
        assert "+---" not in captured
        assert "WEB CRAWLER ANALYTICS" not in captured

    @patch("cli.runner.WebCrawler")
    def test_cli_json_mode(self, mock_crawler_class, capsys):
        mock_crawler = MagicMock()
        mock_crawler_class.return_value = mock_crawler
        page = PageResult(
            url="https://example.com",
            title="Mock Home",
            depth=0,
            status_code=200,
            word_count=50,
            match_count=1,
            total_links=2,
            unique_links=2,
            internal_links_count=2,
            external_links_count=0,
            response_time=0.1,
            domain="example.com",
            text_snippet="A mock page",
            content_type="text/html",
            timestamp="2026-09-05T10:00:00",
        )
        mock_crawler.page_results = [page]
        mock_crawler.failures = []
        mock_crawler.discovered_urls = {"https://example.com"}

        summary = CrawlSessionSummary(
            session_id="mock_json_session",
            start_url="https://example.com",
            max_depth=1,
            max_pages=1,
            start_time="2026-09-05T10:00:00",
            end_time="2026-09-05T10:00:01",
            elapsed_seconds=0.2,
            pages_crawled=1,
            discovered_urls_count=2,
            failed_urls_count=0,
            total_internal_links=2,
            total_external_links=0,
            stay_on_domain=True,
            max_depth_reached=0,
        )

        def mock_stream(cfg):
            yield CrawlProgressEvent(
                event_type="success",
                current_url="https://example.com",
                current_depth=0,
                pages_crawled=1,
                discovered_count=2,
                failed_count=0,
                message="Crawled mock",
                page_result=page,
            )
            return summary

        mock_crawler.crawl_stream.side_effect = mock_stream

        exit_code = main(["https://example.com", "--json", "--no-db"])
        assert exit_code == 0
        captured = capsys.readouterr().out.strip()
        data = json.loads(captured)
        assert "summary" in data
        assert "pages" in data
        assert len(data["pages"]) == 1
        assert data["pages"][0]["URL"] == "https://example.com"

    @patch("cli.runner.WebCrawler")
    def test_cli_search_query_positional(self, mock_crawler_class):
        mock_crawler = MagicMock()
        mock_crawler_class.return_value = mock_crawler
        mock_crawler.page_results = []
        mock_crawler.failures = []
        mock_crawler.discovered_urls = set()

        def mock_stream(cfg):
            assert cfg.search_query == "artificial intelligence neural networks"
            assert cfg.stay_on_domain is False
            yield CrawlProgressEvent(
                event_type="searching",
                current_url="artificial intelligence neural networks",
                current_depth=0,
                pages_crawled=0,
                discovered_count=0,
                failed_count=0,
                message="Searching",
            )
            return CrawlSessionSummary(
                session_id="mock_s",
                start_url="artificial intelligence neural networks",
                max_depth=1,
                max_pages=1,
                start_time="",
                end_time="",
                elapsed_seconds=0.1,
                pages_crawled=0,
                discovered_urls_count=0,
                failed_urls_count=0,
                total_internal_links=0,
                total_external_links=0,
                stay_on_domain=False,
                max_depth_reached=0,
                search_query="artificial intelligence neural networks",
            )

        mock_crawler.crawl_stream.side_effect = mock_stream

        exit_code = main(["artificial intelligence neural networks", "--quiet", "--no-db"])
        assert exit_code == 0
