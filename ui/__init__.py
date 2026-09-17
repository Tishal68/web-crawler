"""
UI presentation layer for Web Crawler and Web Search Engine.
"""


def __getattr__(name: str):
    """Lazy-load UI views to prevent circular imports during module bootstrapping."""
    if name in ("render_search_view", "render_search_history_view"):
        from .search_view import render_search_view, render_search_history_view
        mapping = {
            "render_search_view": render_search_view,
            "render_search_history_view": render_search_history_view,
        }
        return mapping[name]
    if name == "render_source_inspector":
        from .source_inspector import render_source_inspector
        return render_source_inspector
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "render_search_view",
    "render_search_history_view",
    "render_source_inspector",
]
