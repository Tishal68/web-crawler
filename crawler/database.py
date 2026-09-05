"""
SQLite database storage for crawl sessions, page results, and failures.
"""

import sqlite3
import json
import os
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from .models import CrawlSessionSummary, PageResult, CrawlFailure


class CrawlDatabase:
    """Manages persistence of crawl sessions and detailed page records in SQLite."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Place in data/crawler.db relative to this file
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(base_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            self.db_path = os.path.join(data_dir, "crawler.db")
        else:
            self.db_path = db_path
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)

        self.init_db()

    @contextmanager
    def _get_connection(self):
        """Yield an active SQLite connection and ensure it is closed on exit."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self) -> None:
        """Create necessary tables if they do not already exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    start_url TEXT NOT NULL,
                    max_depth INTEGER,
                    max_pages INTEGER,
                    start_time TEXT,
                    end_time TEXT,
                    elapsed_seconds REAL,
                    pages_crawled INTEGER,
                    discovered_urls_count INTEGER,
                    failed_urls_count INTEGER,
                    total_internal_links INTEGER,
                    total_external_links INTEGER,
                    stay_on_domain INTEGER,
                    max_depth_reached INTEGER
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS crawled_pages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    url TEXT NOT NULL,
                    title TEXT,
                    depth INTEGER,
                    status_code INTEGER,
                    total_links INTEGER,
                    unique_links INTEGER,
                    internal_links_count INTEGER,
                    external_links_count INTEGER,
                    response_time REAL,
                    content_type TEXT,
                    domain TEXT,
                    timestamp TEXT,
                    parent_url TEXT,
                    internal_urls_json TEXT,
                    external_urls_json TEXT,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS failed_urls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    url TEXT NOT NULL,
                    depth INTEGER,
                    error_type TEXT,
                    error_message TEXT,
                    timestamp TEXT,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                )
            """)
            conn.commit()

    def save_session(
        self,
        summary: CrawlSessionSummary,
        pages: List[PageResult],
        failures: List[CrawlFailure]
    ) -> bool:
        """Save a complete crawl session and all associated records."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO sessions (
                        session_id, start_url, max_depth, max_pages, start_time,
                        end_time, elapsed_seconds, pages_crawled, discovered_urls_count,
                        failed_urls_count, total_internal_links, total_external_links,
                        stay_on_domain, max_depth_reached
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    summary.session_id,
                    summary.start_url,
                    summary.max_depth,
                    summary.max_pages,
                    summary.start_time,
                    summary.end_time,
                    summary.elapsed_seconds,
                    summary.pages_crawled,
                    summary.discovered_urls_count,
                    summary.failed_urls_count,
                    summary.total_internal_links,
                    summary.total_external_links,
                    1 if summary.stay_on_domain else 0,
                    summary.max_depth_reached,
                ))

                for p in pages:
                    cursor.execute("""
                        INSERT INTO crawled_pages (
                            session_id, url, title, depth, status_code, total_links,
                            unique_links, internal_links_count, external_links_count,
                            response_time, content_type, domain, timestamp, parent_url,
                            internal_urls_json, external_urls_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        summary.session_id,
                        p.url,
                        p.title,
                        p.depth,
                        p.status_code,
                        p.total_links,
                        p.unique_links,
                        p.internal_links_count,
                        p.external_links_count,
                        p.response_time,
                        p.content_type,
                        p.domain,
                        p.timestamp,
                        p.parent_url,
                        json.dumps(p.internal_urls),
                        json.dumps(p.external_urls),
                    ))

                for f in failures:
                    cursor.execute("""
                        INSERT INTO failed_urls (
                            session_id, url, depth, error_type, error_message, timestamp
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        summary.session_id,
                        f.url,
                        f.depth,
                        f.error_type,
                        f.error_message,
                        f.timestamp,
                    ))

                conn.commit()
                return True
        except Exception:
            return False

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Retrieve all recorded crawl sessions ordered by start_time descending."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT session_id, start_url, max_depth, max_pages, start_time,
                           end_time, elapsed_seconds, pages_crawled, discovered_urls_count,
                           failed_urls_count, total_internal_links, total_external_links,
                           stay_on_domain, max_depth_reached
                    FROM sessions
                    ORDER BY start_time DESC
                """)
                return [dict(row) for row in cursor.fetchall()]
        except Exception:
            return []

    def get_session_pages(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieve all crawled pages for a specific session."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT url, title, depth, status_code, total_links, unique_links,
                           internal_links_count, external_links_count, response_time,
                           content_type, domain, timestamp, parent_url,
                           internal_urls_json, external_urls_json
                    FROM crawled_pages
                    WHERE session_id = ?
                    ORDER BY depth ASC, id ASC
                """, (session_id,))
                rows = []
                for row in cursor.fetchall():
                    item = dict(row)
                    item["internal_urls"] = json.loads(item.get("internal_urls_json") or "[]")
                    item["external_urls"] = json.loads(item.get("external_urls_json") or "[]")
                    rows.append(item)
                return rows
        except Exception:
            return []

    def get_session_failures(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieve all failed URLs recorded for a session."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT url, depth, error_type, error_message, timestamp
                    FROM failed_urls
                    WHERE session_id = ?
                    ORDER BY id ASC
                """, (session_id,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception:
            return []

    def delete_session(self, session_id: str) -> bool:
        """Delete a crawl session and all related page and failure records."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM failed_urls WHERE session_id = ?", (session_id,))
                cursor.execute("DELETE FROM crawled_pages WHERE session_id = ?", (session_id,))
                cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
                conn.commit()
                return True
        except Exception:
            return False
