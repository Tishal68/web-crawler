"""
Unit tests for live crawl progress container telemetry.
Verifies that render_live_progress_container returns an unpackable 6-tuple
compatible with app.py and supports backwards-compatible dictionary key lookups.
"""

from unittest.mock import patch, MagicMock
import pytest
from ui.dashboard import render_live_progress_container, LiveProgressContainer


def test_live_progress_container_unpacking_and_dict_access():
    mock_container = MagicMock()
    mock_progress = MagicMock()
    mock_status = MagicMock()
    mock_pages = MagicMock()
    mock_queue = MagicMock()
    mock_elapsed = MagicMock()

    obj = LiveProgressContainer(
        mock_container,
        mock_progress,
        mock_status,
        mock_pages,
        mock_queue,
        mock_elapsed,
    )

    # 1. Test 6-element tuple unpacking (exact statement in app.py)
    c, p, s, sp, sq, se = obj
    assert c == mock_container
    assert p == mock_progress
    assert s == mock_status
    assert sp == mock_pages
    assert sq == mock_queue
    assert se == mock_elapsed

    # 2. Test length
    assert len(obj) == 6

    # 3. Test dictionary-style access
    assert obj["status_text"] == mock_status
    assert obj["progress_bar"] == mock_progress
    assert obj["metric_crawled"] == mock_pages
    assert obj["progress_container"] == mock_container
    assert obj.get("nonexistent", "default") == "default"


def test_render_live_progress_container_mocked():
    with patch("streamlit.markdown"), \
         patch("streamlit.container") as mock_c, \
         patch("streamlit.empty") as mock_e, \
         patch("streamlit.progress") as mock_p, \
         patch("streamlit.columns") as mock_cols:
        mock_cols.return_value = (MagicMock(), MagicMock(), MagicMock())
        result = render_live_progress_container()
        progress_container, progress_bar, status_text, stat_pages, stat_queue, stat_elapsed = result
        assert progress_container == mock_c.return_value
        assert progress_bar == mock_p.return_value
