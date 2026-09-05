"""
Unit tests for conversational follow-up query rewriting.
"""

import pytest
from search.query import rewrite_follow_up_query


class TestConversationalQueryRewriting:
    """Tests conversational query rewriting for multi-turn research sessions."""

    def test_resolves_pronoun_anaphora(self):
        history = [
            {"role": "user", "content": "James Webb Space Telescope recent exoplanet discoveries"},
            {"role": "assistant", "content": "JWST detected atmospheric carbon dioxide on WASP-39 b."},
        ]

        # "it" should be replaced with key entity from previous query
        rewritten = rewrite_follow_up_query("When was it launched?", history)
        assert "it" not in rewritten.lower()
        assert "james webb space telescope" in rewritten.lower()
        assert "launched" in rewritten.lower()

    def test_resolves_possessive_pronoun(self):
        history = [
            {"role": "user", "content": "James Webb Space Telescope exoplanets"},
            {"role": "assistant", "content": "JWST observed several exoplanets."},
        ]

        rewritten = rewrite_follow_up_query("What are its main instruments?", history)
        assert "its" not in rewritten.lower()
        assert "james webb space telescope" in rewritten.lower()

    def test_handles_comparison_and_ellipsis(self):
        history = [
            {"role": "user", "content": "quantum computing fault tolerance"},
            {"role": "assistant", "content": "Quantum systems require error correction."},
        ]

        rewritten = rewrite_follow_up_query("Compare with classical supercomputing", history)
        assert "quantum" in rewritten.lower()
        assert "classical supercomputing" in rewritten.lower()

    def test_preserves_independent_new_topic(self):
        history = [
            {"role": "user", "content": "latest developments in quantum computing"},
            {"role": "assistant", "content": "Progress in topological and neutral atom qubits."},
        ]

        independent_q = "how to bake sourdough bread at home"
        rewritten = rewrite_follow_up_query(independent_q, history)
        assert rewritten == independent_q

    def test_empty_history_returns_original_query(self):
        q = "post-quantum cryptography standards NIST"
        assert rewrite_follow_up_query(q, []) == q
        assert rewrite_follow_up_query(q, None) == q
