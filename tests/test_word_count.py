"""
Unit and acceptance tests for Answer Depth and Exact Word Count Control.

Covers:
- Deterministic whitespace/token word counting rule
- Word count constraint extraction (exact vs approximate)
- Output-length instruction removal from queries
- Semantic repetition detection
- Programmatic exact word count enforcement (150, 300, 500 words)
- Citation integrity and valid source reference mapping
- Adaptive answer depth scaling by query complexity
"""

import pytest
from answer.word_count import (
    count_words,
    parse_word_count_constraint,
    extract_requested_word_count,
    remove_word_count_instruction,
    is_semantically_repetitive,
    fit_exact_word_count,
    WordCountConstraint,
)
from evidence.models import EvidencePassage, ConfidenceReport
from search.query import QueryAnalysis, QueryComplexity
from answer.citations import CitationRegistry
from answer.generator import AnswerGenerator
from ai.fallback import DeterministicResearchSynthesizer


class TestDeterministicWordCounting:
    """Tests deterministic whitespace/token-based counting."""

    def test_basic_word_count(self):
        text = "Artificial intelligence refers to machines simulating human cognition."
        assert count_words(text) == 8

    def test_punctuation_and_citations(self):
        # [1] is counted as part of the visible text token
        text = "Artificial intelligence is powerful [1]."
        # Tokens: ['Artificial', 'intelligence', 'is', 'powerful', '[1].']
        assert count_words(text) == 5

    def test_markdown_bold_and_italics(self):
        text = "**Artificial intelligence** is *transformative* across industries [2]."
        assert count_words(text) == 7

    def test_whitespace_collapsing(self):
        text = "   Quantum   computing    leverages   superposition.   "
        assert count_words(text) == 4

    def test_empty_and_none(self):
        assert count_words("") == 0
        assert count_words(None) == 0


class TestConstraintParsing:
    """Tests exact vs approximate constraint extraction."""

    def test_exact_in_n_words(self):
        c = extract_requested_word_count("Explain artificial intelligence in 300 words.")
        assert c == 300
        assert c.is_exact is True

    def test_exact_500_word_explanation(self):
        c = extract_requested_word_count("Give me a 500-word explanation of Python.")
        assert c == 500
        assert c.is_exact is True

    def test_exact_in_150_words(self):
        c = extract_requested_word_count("Explain this in 150 words.")
        assert c == 150
        assert c.is_exact is True

    def test_exact_explicit_keyword(self):
        c = extract_requested_word_count("Explain artificial intelligence in exactly 300 words.")
        assert c == 300
        assert c.is_exact is True

    def test_approximate_around(self):
        c = extract_requested_word_count("explain this in around 300 words")
        assert c == 300
        assert c.is_exact is False

    def test_approximate_about(self):
        c = extract_requested_word_count("about 500 words on quantum computing")
        assert c == 500
        assert c.is_exact is False

    def test_no_constraint_in_normal_query(self):
        c = extract_requested_word_count("What is quantum computing?")
        assert c is None


class TestQueryCleaning:
    """Tests stripping length instructions before search retrieval."""

    def test_clean_in_300_words(self):
        cleaned = remove_word_count_instruction("Explain artificial intelligence in 300 words.")
        assert "300" not in cleaned
        assert "words" not in cleaned
        assert "artificial intelligence" in cleaned.lower()

    def test_clean_500_word_explanation(self):
        cleaned = remove_word_count_instruction("Give me a 500-word explanation of Python.")
        assert "500" not in cleaned
        assert "Python" in cleaned

    def test_clean_around_words(self):
        cleaned = remove_word_count_instruction("explain quantum computing in around 250 words")
        assert "250" not in cleaned
        assert "quantum computing" in cleaned.lower()


class TestRepetitionDetection:
    """Tests semantic and near-duplicate sentence repetition filtering."""

    def test_detects_semantic_repetition(self):
        existing = ["AI is used in healthcare."]
        duplicate = "AI is also increasingly used in the healthcare industry."
        assert is_semantically_repetitive(duplicate, existing) is True

    def test_detects_reworded_repetition(self):
        existing = ["Healthcare is one area where AI is becoming common."]
        duplicate = "AI is frequently deployed in healthcare environments."
        assert is_semantically_repetitive(duplicate, existing) is True

    def test_allows_distinct_factual_points(self):
        existing = ["Python was created by Guido van Rossum in the late 1980s [1]."]
        distinct = "Python features dynamic typing and automated memory management [2]."
        assert is_semantically_repetitive(distinct, existing) is False


class TestExactWordCountRefinement:
    """Tests programmatic exact-count fitting across various targets."""

    @pytest.fixture
    def mock_passages(self):
        return [
            EvidencePassage(
                text="Artificial intelligence represents computational systems that simulate human reasoning and perception [1]. It encompasses machine learning algorithms and deep neural networks [1]. Computer vision enables automated systems to process and interpret visual inputs [1]. Convolutional networks extract hierarchical spatial representations from raw pixel data [1].",
                source_url="https://example.com/ai",
                source_domain="example.com",
                source_title="AI Overview",
            ),
            EvidencePassage(
                text="Natural language processing allows computers to comprehend and manipulate human text [2]. Transformer architectures have revolutionized semantic modeling and language translation [2]. Self-attention mechanisms calculate dynamic relevance between tokens across long sequences [2]. Large language models acquire broad general knowledge through unsupervised pretraining [2].",
                source_url="https://example.edu/nlp",
                source_domain="example.edu",
                source_title="NLP Research",
            ),
            EvidencePassage(
                text="Modern artificial intelligence relies on specialized computational hardware for neural training [3]. Tensor processing units optimize parallel tensor mathematics and matrix operations [3]. Distributed computing clusters coordinate gradient synchronization across thousands of processor nodes [3]. Quantization methods compress neural weights to run efficiently on mobile microcontrollers [3].",
                source_url="https://example.org/hardware",
                source_domain="example.org",
                source_title="AI Hardware",
            ),
            EvidencePassage(
                text="Healthcare diagnostics increasingly leverage deep learning for radiological analysis [4]. Automated algorithms identify malignant anomalies in computed tomography scans with high accuracy [4]. Genomic sequencing platforms utilize predictive modeling to isolate hereditary disease markers [4]. Clinical decision support systems integrate real-time patient telemetry to assist physicians [4].",
                source_url="https://example.gov/health",
                source_domain="example.gov",
                source_title="Healthcare AI",
            ),
            EvidencePassage(
                text="Autonomous vehicle platforms combine multimodal sensor fusion with predictive trajectory planning [5]. Lidar sensors generate dense three-dimensional point clouds to detect surrounding obstacles [5]. Radar systems provide robust velocity measurements through adverse weather conditions [5]. Real-time control software executes closed-loop steering and braking maneuvers to ensure safety [5].",
                source_url="https://example.com/auto",
                source_domain="example.com",
                source_title="Autonomous Systems",
            ),
            EvidencePassage(
                text="Industrial robotics integrates mechanical actuators with intelligent sensory perception loops [6]. Collaborative robots work safely alongside human operators in manufacturing environments [6]. Predictive maintenance platforms analyze vibration patterns from industrial machinery to prevent downtime [6]. Autonomous mobile robots navigate warehouse floors using simultaneous localization algorithms [6].",
                source_url="https://example.org/robotics",
                source_domain="example.org",
                source_title="Industrial Robotics",
            ),
            EvidencePassage(
                text="Financial institutions deploy machine learning models to identify fraudulent transactions in real time [7]. Graph convolutional neural networks trace transaction paths across interconnected banking databases [7]. Algorithmic risk models evaluate creditworthiness by synthesizing historical repayment behavior and market metrics [7]. High-frequency trading algorithms execute automated orders based on quantitative predictive signals [7].",
                source_url="https://example.com/fintech",
                source_domain="example.com",
                source_title="Financial AI",
            ),
            EvidencePassage(
                text="Cybersecurity defense systems employ anomaly detection to neutralize incoming network intrusions [8]. Deep neural classifiers flag malicious payloads hidden inside encrypted application traffic [8]. Automated endpoint response agents isolate compromised virtual machines before lateral movement occurs [8]. Continuous threat intelligence engines aggregate global attack telemetry to fortify perimeter defenses [8].",
                source_url="https://example.org/security",
                source_domain="example.org",
                source_title="Cyber Defense AI",
            ),
            EvidencePassage(
                text="Scientific discovery increasingly benefits from computational structural biology models [9]. Deep learning architectures predict three-dimensional protein fold geometries directly from amino acid sequences [9]. Virtual chemical screening pipelines simulate molecular docking against pathogenic viral receptors [9]. Material informatics algorithms discover novel superconducting crystal lattices using generative modeling [9].",
                source_url="https://example.edu/science",
                source_domain="example.edu",
                source_title="AI Science Discovery",
            ),
            EvidencePassage(
                text="Reinforcement learning agents master complex strategic games through trial and error simulations [10]. Policy networks compute probability distributions over possible action spaces while value networks estimate expected game outcomes [10]. Monte Carlo tree search guides decision exploration in vast discrete state spaces [10]. Multi-agent competitive environments foster emergent tactical reasoning without human intervention [10].",
                source_url="https://example.org/rl",
                source_domain="example.org",
                source_title="Reinforcement Learning",
            ),
        ]

    def test_exact_150_words(self, mock_passages):
        draft = "Artificial intelligence enables computational systems to simulate human cognitive functions and automate complex analytical tasks [1]."
        fitted = fit_exact_word_count(
            draft,
            150,
            passages=mock_passages,
            source_lookup={"https://example.com/ai": 1, "https://example.edu/nlp": 2, "https://example.org/hardware": 3, "https://example.gov/health": 4, "https://example.com/auto": 5, "https://example.org/robotics": 6, "https://example.com/fintech": 7, "https://example.org/security": 8, "https://example.edu/science": 9, "https://example.org/rl": 10}
        )
        assert fitted is not None
        assert count_words(fitted) == 150

    def test_exact_300_words(self, mock_passages):
        draft = "Artificial intelligence enables computational systems to simulate human cognitive functions and automate complex analytical tasks [1]."
        fitted = fit_exact_word_count(
            draft,
            300,
            passages=mock_passages,
            source_lookup={"https://example.com/ai": 1, "https://example.edu/nlp": 2, "https://example.org/hardware": 3, "https://example.gov/health": 4, "https://example.com/auto": 5, "https://example.org/robotics": 6, "https://example.com/fintech": 7, "https://example.org/security": 8, "https://example.edu/science": 9, "https://example.org/rl": 10}
        )
        assert fitted is not None
        assert count_words(fitted) == 300

    def test_no_fabrication_preserves_citations(self, mock_passages):
        draft = "Artificial intelligence simulates human reasoning [1]."
        fitted = fit_exact_word_count(
            draft,
            50,
            passages=mock_passages,
            source_lookup={"https://example.com/ai": 1, "https://example.edu/nlp": 2}
        )
        assert fitted is not None
        assert count_words(fitted) == 50
        # Verify citation markers like [1], [2] are present
        assert "[1]" in fitted or "[2]" in fitted


class TestAdaptiveAnswerDepth:
    """Tests answer depth when no word count is requested."""

    def test_normal_moderate_query_depth(self):
        synthesizer = DeterministicResearchSynthesizer()
        passages = [
            EvidencePassage(
                text="Quantum computing utilizes quantum mechanics principles including superposition and entanglement [1]. Unlike classical bits which represent zero or one, quantum qubits can exist in linear combinations of both states [1].",
                source_url="https://example.com/qc1",
                source_domain="example.com",
                source_title="Quantum Physics",
            ),
            EvidencePassage(
                text="Superconducting circuits and trapped ion architectures represent the leading experimental qubit modalities [2]. Cryogenic dilution refrigerators maintain sub-kelvin temperatures to preserve quantum coherence [2].",
                source_url="https://example.edu/qc2",
                source_domain="example.edu",
                source_title="Quantum Architectures",
            ),
            EvidencePassage(
                text="Quantum algorithms like Shor's algorithm threaten classical asymmetric cryptography like RSA [3]. Post-quantum cryptography standards developed by NIST aim to secure digital networks against future quantum decryption [3].",
                source_url="https://example.org/qc3",
                source_domain="example.org",
                source_title="Quantum Cryptography",
            ),
        ]
        registry = CitationRegistry()
        for p in passages:
            registry.register(p.source_url, p.source_title, p.source_domain)
        citations = registry.all_citations()

        analysis = QueryAnalysis(
            original_query="What is quantum computing?",
            clean_query="What is quantum computing?",
            complexity=QueryComplexity.MODERATE,
        )

        resp = synthesizer.synthesize(
            query="What is quantum computing?",
            sources=citations,
            passages=passages,
            analysis=analysis,
        )

        words = count_words(resp.direct_answer)
        # Verify it does NOT stop after only 1-3 sentences
        assert words >= 80, f"Expected normal query depth >= 80 words, got {words}"
        assert "[1]" in resp.direct_answer
        assert "[2]" in resp.direct_answer
