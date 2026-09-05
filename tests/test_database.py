"""
Unit and integration tests for SQLite CrawlDatabase storage,
foreign keys cascade, transactional re-save deduplication, and error recovery.
"""

import os
import tempfile
import pytest
from crawler.database import CrawlDatabase
from crawler.models import CrawlSessionSummary, PageResult, CrawlFailure


@pytest.fixture
def temp_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_crawler.db")
        db = CrawlDatabase(db_path=db_path)
        yield db


class TestDatabaseIntegrity:
    def test_save_and_retrieve_session(self, temp_db):
        summary = CrawlSessionSummary(
            session_id="session_101",
            start_url="https://example.com",
            max_depth=2,
            max_pages=10,
            start_time="2026-09-05T12:00:00",
            end_time="2026-09-05T12:00:05",
            elapsed_seconds=5.0,
            pages_crawled=1,
            discovered_urls_count=3,
            failed_urls_count=1,
            total_internal_links=2,
            total_external_links=1,
            stay_on_domain=True,
            max_depth_reached=1,
        )
        page = PageResult(
            url="https://example.com",
            title="Example Domain",
            depth=0,
            status_code=200,
            total_links=3,
            unique_links=3,
            internal_links_count=2,
            external_links_count=1,
            internal_urls=["https://example.com/p1", "https://example.com/p2"],
            external_urls=["https://other.com"],
            response_time=0.15,
            content_type="text/html",
            domain="example.com",
        )
        failure = CrawlFailure(
            url="https://example.com/404",
            depth=1,
            error_type="HTTP 404",
            error_message="Not Found",
        )

        ok = temp_db.save_session(summary, [page], [failure])
        assert ok is True

        # Verify retrieval
        sessions = temp_db.get_all_sessions()
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == "session_101"

        pages = temp_db.get_session_pages("session_101")
        assert len(pages) == 1
        assert pages[0]["url"] == "https://example.com"
        assert len(pages[0]["internal_urls"]) == 2

        failures = temp_db.get_session_failures("session_101")
        assert len(failures) == 1
        assert failures[0]["url"] == "https://example.com/404"

    def test_resave_session_prevents_duplicate_child_records(self, temp_db):
        summary = CrawlSessionSummary(
            session_id="session_dedup_test",
            start_url="https://example.com",
            max_depth=1,
            max_pages=5,
            start_time="2026-09-05T12:00:00",
            end_time="2026-09-05T12:00:02",
            elapsed_seconds=2.0,
            pages_crawled=1,
            discovered_urls_count=1,
            failed_urls_count=0,
            total_internal_links=1,
            total_external_links=0,
            stay_on_domain=True,
            max_depth_reached=0,
        )
        page = PageResult(
            url="https://example.com",
            title="Example",
            depth=0,
            status_code=200,
            total_links=1,
            unique_links=1,
            internal_links_count=1,
            external_links_count=0,
        )

        # Save once
        temp_db.save_session(summary, [page], [])
        assert len(temp_db.get_session_pages("session_dedup_test")) == 1

        # Re-save the same session (e.g. retry or user re-saves)
        temp_db.save_session(summary, [page], [])
        # Must still be exactly 1, NOT 2!
        assert len(temp_db.get_session_pages("session_dedup_test")) == 1

    def test_delete_session_cascades_cleanly(self, temp_db):
        summary = CrawlSessionSummary(
            session_id="session_to_delete",
            start_url="https://example.com",
            max_depth=1,
            max_pages=5,
            start_time="2026-09-05T12:00:00",
            end_time="2026-09-05T12:00:02",
            elapsed_seconds=2.0,
            pages_crawled=1,
            discovered_urls_count=1,
            failed_urls_count=1,
            total_internal_links=1,
            total_external_links=0,
            stay_on_domain=True,
            max_depth_reached=0,
        )
        page = PageResult(url="https://example.com", title="Ex", depth=0, status_code=200, total_links=0, unique_links=0, internal_links_count=0, external_links_count=0)
        fail = CrawlFailure(url="https://example.com/err", depth=1, error_type="HTTP 500", error_message="Internal Error")

        temp_db.save_session(summary, [page], [fail])
        assert len(temp_db.get_all_sessions()) == 1

        # Delete session
        deleted = temp_db.delete_session("session_to_delete")
        assert deleted is True

        assert len(temp_db.get_all_sessions()) == 0
        assert len(temp_db.get_session_pages("session_to_delete")) == 0
        assert len(temp_db.get_session_failures("session_to_delete")) == 0
