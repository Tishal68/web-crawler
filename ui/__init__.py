"""
UI presentation layer for Web Crawler and Web Search Engine.
"""

from .search_view import render_search_view, render_search_history_view
from .source_inspector import render_source_inspector

__all__ = [
    "render_search_view",
    "render_search_history_view",
    "render_source_inspector",
]
