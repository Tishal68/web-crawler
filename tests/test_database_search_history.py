"""
Unit tests for SQLite search history persistence in CrawlDatabase.
"""

import os
import tempfile
import pytest
from crawler.database import CrawlDatabase


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = CrawlDatabase(db_path=path)
    yield db
    try:
        os.remove(path)
    except Exception:
        pass


def test_save_and_get_search_history(temp_db):
    h_id = temp_db.save_search_history(
        query="latest developments in quantum computing",
        provider_name="Google API",
        results_count=8,
        direct_answer="Quantum error correction achieved 99.9% physical fidelity. [1]",
        confidence_badge="🟢 Strongly Corroborated",
        confidence_score=0.89,
        has_contradictions=False,
        citations=[
            {"index": 1, "url": "https://nature.com/article", "domain": "nature.com", "title": "Nature QC"}
        ],
        session_data={"intent": "temporal_current"},
    )
    assert h_id is not None
    assert h_id > 0

    history = temp_db.get_search_history(limit=10)
    assert len(history) == 1
    item = history[0]
    assert item["query"] == "latest developments in quantum computing"
    assert item["provider_name"] == "Google API"
    assert item["confidence_score"] == 0.89
    assert item["has_contradictions"] == 0
    assert len(item["citations"]) == 1
    assert item["citations"][0]["domain"] == "nature.com"


def test_delete_and_clear_search_history(temp_db):
    id1 = temp_db.save_search_history(
        query="Query 1",
        provider_name="Engine",
        results_count=5,
        direct_answer="Answer 1",
        confidence_badge="🟡 Moderately Supported",
        confidence_score=0.70,
        has_contradictions=False,
        citations=[],
    )
    id2 = temp_db.save_search_history(
        query="Query 2",
        provider_name="Engine",
        results_count=3,
        direct_answer="Answer 2",
        confidence_badge="🟠 Limited Evidence",
        confidence_score=0.45,
        has_contradictions=False,
        citations=[],
    )
    assert len(temp_db.get_search_history()) == 2

    # Delete 1 record
    assert temp_db.delete_search_history(id1)
    history_after_del = temp_db.get_search_history()
    assert len(history_after_del) == 1
    assert history_after_del[0]["id"] == id2

    # Clear all records
    assert temp_db.clear_search_history()
    assert len(temp_db.get_search_history()) == 0
