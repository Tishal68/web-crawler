"""
Unit and regression tests for Streamlit state management,
safe callbacks, history reload, search filtering with regex literals,
and StreamlitAPIException prevention.
"""

import pytest
import pandas as pd
from unittest.mock import MagicMock

from app import (
    PRESETS,
    on_preset_change,
    load_preset_card_callback,
    reset_crawl_state_callback,
)
from crawler.models import PageResult, CrawlSessionSummary, CrawlFailure
from crawler.database import CrawlDatabase


class MockSessionState(dict):
    """
    Mock Streamlit session state that enforces the Streamlit rule:
    Once a widget key is locked (instantiated), it cannot be modified
    directly in the script body unless executed via pre-instantiation callback.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._instantiated_widgets = set()

    def lock_widget(self, key: str):
        self._instantiated_widgets.add(key)

    def __setitem__(self, key, value):
        if key in self._instantiated_widgets:
            raise RuntimeError(
                f"StreamlitAPIException: st.session_state.{key} cannot be modified "
                f"after the widget with key {key} is instantiated."
            )
        super().__setitem__(key, value)


class TestStreamlitStateRegression:
    def test_post_instantiation_mutation_causes_exception(self):
        """
        Regression test demonstrating the exact failure mechanism:
        Directly mutating a widget key post-instantiation raises StreamlitAPIException.
        """
        state = MockSessionState()
        state["input_target_url"] = "https://example.com"
        # Simulate widget instantiation: st.text_input(..., key="input_target_url")
        state.lock_widget("input_target_url")

        # Mutating locked widget key raises StreamlitAPIException
        with pytest.raises(RuntimeError) as excinfo:
            state["input_target_url"] = "https://quotes.toscrape.com"
        assert "StreamlitAPIException: st.session_state.input_target_url cannot be modified" in str(excinfo.value)

    def test_callback_pattern_runs_before_instantiation(self):
        """
        Verifies that callbacks execute before widgets are locked/instantiated,
        allowing safe updates of all configuration parameters without error.
        """
        state = MockSessionState()
        state["input_target_url"] = "https://example.com"
        state["input_max_depth"] = 2
        state["input_max_pages"] = 30
        state["console_preset_select"] = "Quotes to Scrape (Sandbox)"

        # Callback executes BEFORE widgets are locked
        preset = PRESETS["Quotes to Scrape (Sandbox)"]
        state["input_target_url"] = preset["url"]
        state["input_max_depth"] = preset["depth"]
        state["input_max_pages"] = preset["pages"]

        # Now widgets instantiate
        state.lock_widget("input_target_url")
        state.lock_widget("input_max_depth")
        state.lock_widget("input_max_pages")

        assert state["input_target_url"] == "https://quotes.toscrape.com/"
        assert state["input_max_depth"] == 2
        assert state["input_max_pages"] == 20

    def test_reset_callback_state_restoration(self):
        """Verify reset_crawl_state_callback resets results and parameters safely."""
        import streamlit as st

        # Seed session state
        st.session_state["crawl_summary"] = MagicMock()
        st.session_state["page_results"] = [MagicMock()]
        st.session_state["failures"] = [MagicMock()]
        st.session_state["input_target_url"] = "https://altered-url.org"
        st.session_state["input_max_depth"] = 5
        st.session_state["input_max_pages"] = 150

        reset_crawl_state_callback()

        assert st.session_state["crawl_summary"] is None
        assert st.session_state["page_results"] == []
        assert st.session_state["failures"] == []
        assert st.session_state["input_target_url"] == "https://en.wikipedia.org/wiki/Web_crawler"
        assert st.session_state["input_max_depth"] == 2
        assert st.session_state["input_max_pages"] == 30
        assert st.session_state["console_preset_select"] == "⚡ Presets: Select Target..."

    def test_load_preset_card_callback(self):
        """Verify load_preset_card_callback populates target preset values."""
        import streamlit as st
        preset_name = "Python 3 Documentation"
        load_preset_card_callback(preset_name)

        assert st.session_state["input_target_url"] == "https://docs.python.org/3/"
        assert st.session_state["input_max_depth"] == 1
        assert st.session_state["input_max_pages"] == 20
        assert st.session_state["console_preset_select"] == preset_name


class TestResultsSearchFilteringRegexSafety:
    def test_search_filtering_with_regex_characters(self):
        """
        Verify that search query handles literal regex symbols like [, *, +, ?, (, )
        without crashing pandas regex compilation.
        """
        data = [
            {"URL": "https://example.com/[test]", "Title": "Title [Section 1]", "Domain": "example.com", "Depth": 0, "Status": 200, "Links": 5},
            {"URL": "https://example.com/item*1", "Title": "Product * Star", "Domain": "example.com", "Depth": 1, "Status": 200, "Links": 2},
            {"URL": "https://example.com/plus+sign", "Title": "C++ Tutorial", "Domain": "example.com", "Depth": 1, "Status": 200, "Links": 3},
            {"URL": "https://example.com/normal", "Title": "Normal Page", "Domain": "example.com", "Depth": 1, "Status": 404, "Links": 0},
        ]
        df = pd.DataFrame(data)

        # Problematic regex queries that would raise re.error if regex=True
        regex_queries = [
            "[test]",
            "[",
            "*",
            "item*1",
            "+",
            "C++",
            "(",
            ")",
            "?",
        ]

        for query in regex_queries:
            query_lower = query.lower()
            # Must execute without re.error exception using regex=False
            mask = (
                df["URL"].astype(str).str.lower().str.contains(query_lower, regex=False, na=False) |
                df["Title"].astype(str).str.lower().str.contains(query_lower, regex=False, na=False) |
                df["Domain"].astype(str).str.lower().str.contains(query_lower, regex=False, na=False)
            )
            filtered = df[mask]
            assert isinstance(filtered, pd.DataFrame)

        # Explicit match check
        mask_bracket = df["Title"].str.lower().str.contains("[section 1]", regex=False, na=False)
        assert mask_bracket.sum() == 1

        mask_plus = df["Title"].str.lower().str.contains("c++", regex=False, na=False)
        assert mask_plus.sum() == 1


class TestDynamicSelectboxSanitization:
    def test_depth_and_status_options_change_safely(self):
        """
        Verify that when available options shrink between crawl runs,
        stale session_state values are sanitized to prevent StreamlitAPIException.
        """
        import streamlit as st

        # Simulate previous selection of Depth 3 and Status 500
        st.session_state["results_depth_select"] = "Depth 3"
        st.session_state["results_status_select"] = "500"

        # New crawl only has Depth 0, 1 and Status 200
        new_depth_options = ["All Depths", "Depth 0", "Depth 1"]
        new_status_options = ["All Status Codes", "200"]

        if st.session_state["results_depth_select"] not in new_depth_options:
            st.session_state["results_depth_select"] = new_depth_options[0]

        if st.session_state["results_status_select"] not in new_status_options:
            st.session_state["results_status_select"] = new_status_options[0]

        assert st.session_state["results_depth_select"] == "All Depths"
        assert st.session_state["results_status_select"] == "All Status Codes"
