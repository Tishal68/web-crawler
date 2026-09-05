"""
Query understanding, intent analysis, and question decomposition module.
Extracts keywords, entities, user intent, complexity tier, and decomposes
complex research questions into distinct information requirements (facets).
"""

from enum import Enum
import re
from dataclasses import dataclass, field
from typing import List, Optional, Set, Dict, Any


class QueryComplexity(str, Enum):
    SIMPLE = "simple"          # Factual lookup, direct definition, single-sentence answer
    MODERATE = "moderate"      # Focused topic
    COMPARISON = "comparison"  # Side-by-side comparative analysis
    COMPLEX = "complex"        # Deep multi-facet technical or scientific research topic


@dataclass
class QueryFacet:
    """An individual information requirement or sub-topic for comprehensive research."""
    facet_id: str
    title: str
    description: str
    keywords: List[str] = field(default_factory=list)
    search_query: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "facet_id": self.facet_id,
            "title": self.title,
            "description": self.description,
            "keywords": self.keywords,
            "search_query": self.search_query,
        }


@dataclass
class QueryAnalysis:
    """Structured understanding of user search intent, complexity, and information requirements."""
    original_query: str
    clean_query: str
    keywords: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    intent: str = "exploratory"  # "factual", "exploratory", "comparison", "temporal_current"
    complexity: QueryComplexity = QueryComplexity.MODERATE
    is_time_sensitive: bool = False
    is_comparison: bool = False
    target_year: Optional[int] = None
    search_variations: List[str] = field(default_factory=list)
    facets: List[QueryFacet] = field(default_factory=list)
    follow_up_suggestions: List[str] = field(default_factory=list)

    @property
    def follow_up_questions(self) -> List[str]:
        """Alias for follow_up_suggestions."""
        return self.follow_up_suggestions

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clean_query": self.clean_query,
            "keywords": self.keywords,
            "entities": self.entities,
            "intent": self.intent,
            "complexity": self.complexity.value if hasattr(self.complexity, "value") else str(self.complexity),
            "is_time_sensitive": self.is_time_sensitive,
            "is_comparison": self.is_comparison,
            "target_year": self.target_year,
            "search_variations": self.search_variations,
            "facets": [f.to_dict() for f in self.facets],
            "follow_up_suggestions": self.follow_up_suggestions,
        }


class QueryAnalyzer:
    """Analyzes raw queries and decomposes them into information requirements."""

    TEMPORAL_TRIGGERS: Set[str] = {
        "latest", "today", "current", "recent", "recently", "price", "prices",
        "ranking", "rankings", "schedule", "schedules", "winner", "winners",
        "2026", "2025", "2024", "this week", "this month", "new features",
        "updates", "news", "release", "released", "roadmap", "now"
    }

    STOPWORDS: Set[str] = {
        "a", "an", "the", "in", "on", "at", "for", "of", "with", "by", "to",
        "and", "or", "is", "are", "was", "were", "what", "which", "who", "whom",
        "how", "why", "where", "when", "can", "could", "should", "would", "do",
        "does", "did", "tell", "me", "about", "show", "find", "give", "explain",
        "describe", "elaborate"
    }

    def analyze(self, query: str) -> QueryAnalysis:
        """Analyze search query, classify complexity, and generate information facets."""
        clean = (query or "").strip()
        lower = clean.lower()

        # 1. Temporal Sensitivity
        is_time_sensitive = any(trigger in lower for trigger in self.TEMPORAL_TRIGGERS)
        year_match = re.search(r"\b(202[0-9]|19[0-9]{2})\b", clean)
        target_year = int(year_match.group(1)) if year_match else (2026 if "latest" in lower or "current" in lower else None)

        # 2. Comparison Check
        is_comparison = bool(
            re.search(r"\b(vs\.?|versus|compare|comparison|difference between)\b", lower)
            or (" or " in lower and len(clean.split()) <= 6)
        )

        # 3. Intent Classification
        if is_comparison:
            intent = "comparison"
        elif is_time_sensitive:
            intent = "temporal_current"
        elif any(lower.startswith(prefix) for prefix in ("who ", "when ", "where ", "what is ", "current price")):
            intent = "factual"
        else:
            intent = "exploratory"

        # 4. Keyword & Entity Extraction
        tokens = re.findall(r"\b[A-Za-z0-9+#.-]+\b", clean)
        keywords = [t.lower() for t in tokens if t.lower() not in self.STOPWORDS and len(t) > 1]

        entities = []
        for word in clean.split():
            clean_word = re.sub(r"[^\w+#.-]", "", word)
            if not clean_word:
                continue
            if clean_word.isupper() and len(clean_word) >= 2:
                entities.append(clean_word)
            elif clean_word[0].isupper() and clean_word.lower() not in self.STOPWORDS:
                entities.append(clean_word)

        unique_entities = []
        for e in entities:
            if e not in unique_entities:
                unique_entities.append(e)

        # 5. Complexity Classification
        complexity = self._classify_complexity(clean, lower, is_comparison, is_time_sensitive, keywords)

        # 6. Question Decomposition (Facets Generation)
        facets = self._decompose_query(clean, lower, complexity, is_comparison, is_time_sensitive, unique_entities, keywords)

        # 7. Search Variations Generation
        variations = [clean]
        for f in facets:
            if f.search_query and f.search_query not in variations:
                variations.append(f.search_query)

        # 8. Follow-up Research Suggestions
        follow_ups = self._generate_follow_ups(clean, unique_entities, keywords, is_comparison)

        return QueryAnalysis(
            original_query=query,
            clean_query=clean,
            keywords=keywords,
            entities=unique_entities,
            intent=intent,
            complexity=complexity,
            is_time_sensitive=is_time_sensitive,
            is_comparison=is_comparison,
            target_year=target_year,
            search_variations=variations,
            facets=facets,
            follow_up_suggestions=follow_ups,
        )

    def _classify_complexity(
        self,
        clean: str,
        lower: str,
        is_comparison: bool,
        is_time_sensitive: bool,
        keywords: List[str],
    ) -> QueryComplexity:
        """Determine whether the query demands a concise summary or a deep research breakdown."""
        words = clean.split()

        if is_comparison:
            return QueryComplexity.COMPARISON


        # Complex triggers: scientific observatories, architectures, "how does X work", "explain X"
        complex_triggers = [
            "how does", "how do", "explain", "major discoveries", "developments in",
            "james webb", "jwst", "quantum computing", "post-quantum", "hubble",
            "nuclear fusion", "crispr", "architecture", "mechanism"
        ]
        if any(trig in lower for trig in complex_triggers):
            return QueryComplexity.COMPLEX

        # Simple definitions: "What is Python?", "Who created Linux?", "When was X released?"
        if len(words) <= 4 and (lower.startswith("what is") or lower.startswith("who is") or lower.startswith("who created") or lower.startswith("when was")):
            return QueryComplexity.SIMPLE

        if len(keywords) >= 4 or is_time_sensitive:
            return QueryComplexity.COMPLEX

        return QueryComplexity.MODERATE

    def _decompose_query(
        self,
        clean: str,
        lower: str,
        complexity: QueryComplexity,
        is_comparison: bool,
        is_time_sensitive: bool,
        entities: List[str],
        keywords: List[str],
    ) -> List[QueryFacet]:
        """Decompose a query into distinct information requirements."""
        facets: List[QueryFacet] = []

        # Case A: Astronomical / Scientific Telescopes (JWST, Hubble, etc.)
        if any(term in lower for term in ("james webb", "jwst", "webb telescope")):
            facets.extend([
                QueryFacet(
                    facet_id="jwst_overview",
                    title="Overview & Mission",
                    description="Mission objectives, international partnership (NASA/ESA/CSA), launch date, and Sun-Earth L2 halo orbit.",
                    keywords=["nasa", "esa", "csa", "launch", "l2", "lagrange", "mission", "orbit", "observatory"],
                    search_query="James Webb Space Telescope NASA ESA mission L2 orbit overview",
                ),
                QueryFacet(
                    facet_id="jwst_optics",
                    title="Optics & How It Works",
                    description="6.5-meter gold-coated beryllium primary mirror, infrared astronomy wavelengths, and five-layer sunshield cooling.",
                    keywords=["primary mirror", "beryllium", "gold", "infrared", "sunshield", "cooling", "kelvin", "wavelength"],
                    search_query="JWST 6.5 meter primary mirror infrared sunshield how it works",
                ),
                QueryFacet(
                    facet_id="jwst_instruments",
                    title="Scientific Instruments",
                    description="Core scientific payload: NIRCam, NIRSpec, MIRI, and FGS/NIRISS instruments and their capabilities.",
                    keywords=["nircam", "nirspec", "miri", "niriss", "spectrograph", "camera", "instruments"],
                    search_query="JWST instruments NIRCam NIRSpec MIRI NIRISS capabilities",
                ),
                QueryFacet(
                    facet_id="jwst_discoveries",
                    title="Major Scientific Discoveries",
                    description="Discoveries of early cosmic dawn galaxies, exoplanet atmospheres (carbon dioxide, water vapor), and star nurseries.",
                    keywords=["discoveries", "early galaxies", "exoplanet", "atmosphere", "cosmic dawn", "jades", "wasp", "trappist"],
                    search_query="James Webb Space Telescope major scientific discoveries early galaxies exoplanets",
                ),
                QueryFacet(
                    facet_id="jwst_recent",
                    title="Recent Operational Developments",
                    description="Latest findings, ongoing Cycle observations, and newest published astronomical data.",
                    keywords=["recent", "latest", "new", "2024", "2025", "2026", "observations", "cycle"],
                    search_query="JWST latest discoveries new images recent observations",
                ),
            ])
            return facets

        # Case B: Comparison Queries (X vs Y)
        if is_comparison:
            comp_match = re.search(r"(?:compare\s+)?([A-Za-z0-9_+#.-]+)\s+(?:vs\.?|versus|and|or)\s+([A-Za-z0-9_+#.-]+)", clean, re.IGNORECASE)
            item_a = comp_match.group(1) if comp_match else "Item A"
            item_b = comp_match.group(2) if comp_match else "Item B"

            facets.extend([
                QueryFacet(
                    facet_id="comp_architecture",
                    title="Architecture & Design Philosophy",
                    description=f"Core structural design, data model, and internal philosophy of {item_a} versus {item_b}.",

                    keywords=[item_a.lower(), item_b.lower(), "architecture", "design", "engine", "structure"],
                    search_query=f"{item_a} vs {item_b} architecture design differences",
                ),
                QueryFacet(
                    facet_id="comp_features",
                    title="Key Features & Technical Capabilities",
                    description=f"Supported standards, feature sets, SQL/language compliance, and tooling for {item_a} and {item_b}.",
                    keywords=["features", "support", "capabilities", "syntax", "json", "extensions"],
                    search_query=f"{item_a} vs {item_b} feature comparison specifications",
                ),
                QueryFacet(
                    facet_id="comp_performance",
                    title="Performance, Concurrency & Scalability",
                    description=f"Read/write performance, concurrency control, clustering, and scaling behavior of {item_a} compared to {item_b}.",
                    keywords=["performance", "speed", "concurrency", "scaling", "benchmarks", "mvcc"],
                    search_query=f"{item_a} vs {item_b} performance benchmarks concurrency scaling",
                ),
                QueryFacet(
                    facet_id="comp_selection",
                    title="Ideal Use Cases & Trade-offs",
                    description=f"When to choose {item_a} over {item_b}, operational strengths, and trade-offs.",
                    keywords=["use cases", "when to use", "tradeoffs", "pros and cons", "recommendation"],
                    search_query=f"when to choose {item_a} over {item_b} pros cons use cases",
                ),
            ])
            return facets

        # Case C: Quantum Computing
        if any(term in lower for term in ("quantum computing", "quantum computer", "qubits")):
            facets.extend([
                QueryFacet(
                    facet_id="qc_principles",
                    title="Fundamental Principles & Qubits",
                    description="Quantum mechanics principles: superposition, entanglement, interference, and physical qubits.",
                    keywords=["qubits", "superposition", "entanglement", "quantum mechanics", "principles"],
                    search_query="quantum computing fundamental principles superposition entanglement qubits",
                ),
                QueryFacet(
                    facet_id="qc_hardware",
                    title="Hardware Architectures & Modalities",
                    description="Superconducting circuits, trapped ions, neutral atoms, photonics, and cryogenics.",
                    keywords=["superconducting", "trapped ion", "neutral atoms", "photonic", "hardware", "ibm", "google"],
                    search_query="quantum computing hardware modalities superconducting trapped ion",
                ),
                QueryFacet(
                    facet_id="qc_error_correction",
                    title="Fault Tolerance & Quantum Error Correction",
                    description="Logical qubits, surface codes, error mitigation, and roadmaps to fault-tolerant computation.",
                    keywords=["error correction", "logical qubits", "fault-tolerant", "threshold", "surface code"],
                    search_query="quantum error correction fault tolerant logical qubits progress",
                ),
                QueryFacet(
                    facet_id="qc_developments",
                    title="Recent Milestones & Commercial Horizon",
                    description="Latest processor releases, post-quantum standards, and practical industry milestones.",
                    keywords=["latest", "2024", "2025", "2026", "breakthroughs", "post-quantum", "commercial"],
                    search_query="quantum computing latest breakthroughs recent developments 2025 2026",
                ),
            ])
            return facets

        # Case D: Artificial Intelligence / LLMs / Agents
        if any(term in lower for term in ("ai", "artificial intelligence", "large language model", "llm", "agents")):
            facets.extend([
                QueryFacet(
                    facet_id="ai_models",
                    title="Frontier Model Architectures & Reasoning",
                    description="Reasoning models, test-time compute scaling, chain-of-thought, and frontier architectures.",
                    keywords=["reasoning", "models", "architecture", "test-time compute", "frontier"],
                    search_query="frontier AI models reasoning architectures test-time compute",
                ),
                QueryFacet(
                    facet_id="ai_agents",
                    title="Autonomous Multi-Agent Systems & Tool Use",
                    description="Autonomous agent frameworks, workflow orchestration, multi-agent pair programming, and tool calling.",
                    keywords=["autonomous agents", "multi-agent", "orchestration", "tools", "workflows"],
                    search_query="autonomous AI agents multi-agent architectures tool use",
                ),
                QueryFacet(
                    facet_id="ai_multimodal",
                    title="Multimodal Perception & World Models",
                    description="Native multimodal processing across vision, audio, spatial video, and embodied robotics.",
                    keywords=["multimodal", "vision", "video", "world models", "robotics"],
                    search_query="multimodal AI models vision audio robotics world models",
                ),
                QueryFacet(
                    facet_id="ai_efficiency",
                    title="Hardware Efficiency & Open Weights",
                    description="Inference optimization, quantization, custom silicon, and open-weights community ecosystems.",
                    keywords=["efficiency", "quantization", "silicon", "open weights", "inference"],
                    search_query="AI efficiency quantization custom silicon open weights models",
                ),
            ])
            return facets

        # Case E: Generic Simple Queries ("What is Python?", etc.)
        if complexity == QueryComplexity.SIMPLE:
            topic = " ".join([k for k in keywords if k not in ("what", "is", "explain")]) or clean
            facets.append(
                QueryFacet(
                    facet_id="core_definition",
                    title="Definition & Core Overview",
                    description=f"Clear concise definition, primary purpose, and core characteristics of {topic}.",
                    keywords=keywords,
                    search_query=f"{topic} overview definition documentation",
                )
            )
            return facets

        # Case F: Generic Complex / Explanatory Queries
        core_topic = " ".join(keywords[:4]) if keywords else clean
        facets.extend([
            QueryFacet(
                facet_id="topic_overview",
                title="Overview & Fundamental Concepts",
                description=f"Core definition, foundational background, and purpose of {core_topic}.",
                keywords=keywords[:3],
                search_query=f"{core_topic} overview guide documentation",
            ),
            QueryFacet(
                facet_id="topic_mechanism",
                title="How It Works & Core Architecture",
                description=f"Operational mechanisms, technical architecture, and key principles of {core_topic}.",
                keywords=keywords[1:5] if len(keywords) > 2 else keywords,
                search_query=f"{core_topic} how it works architecture mechanism",
            ),
            QueryFacet(
                facet_id="topic_applications",
                title="Key Applications & Practical Capabilities",
                description=f"Practical use cases, capabilities, and significance of {core_topic}.",
                keywords=keywords,
                search_query=f"{core_topic} capabilities applications use cases",
            ),
        ])

        if is_time_sensitive:
            facets.append(
                QueryFacet(
                    facet_id="topic_recent",
                    title="Recent Updates & Developments",
                    description=f"Current announcements, recent milestones, and ongoing updates regarding {core_topic}.",
                    keywords=["recent", "latest", "updates", "news"] + keywords[:2],
                    search_query=f"{core_topic} latest updates recent news developments",
                )
            )

        return facets

    def _generate_follow_ups(
        self,
        clean: str,
        entities: List[str],
        keywords: List[str],
        is_comparison: bool,
    ) -> List[str]:
        """Generate intelligent, clickable follow-up research questions."""
        lower = clean.lower()

        if "james webb" in lower or "jwst" in lower:
            return [
                "What are the biggest exoplanet discoveries made by JWST?",
                "How does the James Webb Space Telescope compare to the Hubble Space Telescope?",
                "What has JWST revealed about the earliest cosmic dawn galaxies?",
                "What are the latest JWST observations published this year?",
            ]

        if "quantum" in lower:
            return [
                "How does quantum error correction enable fault-tolerant computing?",
                "What are the main differences between superconducting and trapped-ion qubits?",
                "What is the status of NIST post-quantum cryptography standards?",
                "When will quantum computers achieve practical commercial advantage?",
            ]

        if is_comparison:
            comp_match = re.search(r"(?:compare\s+)?([A-Za-z0-9_+#.-]+)\s+(?:vs\.?|versus|and|or)\s+([A-Za-z0-9_+#.-]+)", clean, re.IGNORECASE)
            item_a = comp_match.group(1) if comp_match else "Item A"
            item_b = comp_match.group(2) if comp_match else "Item B"
            return [
                f"What are the key performance benchmarks comparing {item_a} and {item_b}?",
                f"When is it better to choose {item_a} over {item_b}?",
                f"How do {item_a} and {item_b} handle high concurrency and scaling?",
                f"What are the primary architectural trade-offs between {item_a} and {item_b}?",
            ]

        if "python" in lower:
            return [
                "What are the major performance improvements in recent Python releases?",
                "How does Python's memory management and garbage collection work?",
                "What is the GIL in Python and how is free-threading being implemented?",
                "How does Python compare with Go and Rust for backend services?",
            ]

        # Generic intelligent follow-ups
        main_subject = entities[0] if entities else (" ".join(keywords[:2]) if keywords else clean)
        return [
            f"What are the primary technical advantages and limitations of {main_subject}?",
            f"How does {main_subject} work under the hood?",
            f"What are the latest developments and future roadmap for {main_subject}?",
            f"What are the most common real-world use cases for {main_subject}?",
        ]


def extract_core_subject(text: str) -> str:
    """Extract the primary subject or entity from a previous query."""
    if not text:
        return ""
    clean = text.strip().rstrip("?.! ")
    lower = clean.lower()

    # Known entity shortcuts
    if "james webb" in lower or "jwst" in lower:
        return "James Webb Space Telescope"
    if "quantum computing" in lower or "quantum computer" in lower:
        return "quantum computing"
    if "postgresql" in lower and "mysql" in lower:
        return "PostgreSQL vs MySQL"
    if "postgresql" in lower:
        return "PostgreSQL"
    if "mysql" in lower:
        return "MySQL"
    if "python" in lower:
        return "Python"

    # Remove common question preambles
    pattern = r"^(?:what is|what are|explain|how does|tell me about|who built|why is|compare)\s+(?:the\s+|a\s+|an\s+)?"
    cleaned_subject = re.sub(pattern, "", clean, flags=re.IGNORECASE).strip()
    return cleaned_subject or clean


def rewrite_follow_up_query(
    query: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> str:
    """
    Rewrite a follow-up query to preserve conversational context for web search retrieval.
    Resolves pronouns ('it', 'its', 'they', 'this') and conversational ellipsis
    using the entities from previous conversation turns.
    """
    if not query or not query.strip():
        return ""

    raw_query = query.strip()
    if not history:
        return raw_query

    # Find the most recent user query from history
    last_user_query = ""
    for turn in reversed(history):
        if turn.get("role") == "user" and turn.get("content"):
            last_user_query = turn["content"].strip()
            break

    if not last_user_query:
        return raw_query

    prev_subject = extract_core_subject(last_user_query)
    if not prev_subject or prev_subject.lower() in raw_query.lower():
        return raw_query

    # Check for pronoun references: it, its, they, them, their, this
    pronoun_pattern = re.compile(r"\b(it|its|they|them|their|this)\b", re.IGNORECASE)
    if pronoun_pattern.search(raw_query):
        # Replace pronouns with the previous subject
        def repl(m):
            word = m.group(1).lower()
            if word == "its":
                return f"{prev_subject}'s"
            return prev_subject
        return pronoun_pattern.sub(repl, raw_query)

    # Check for comparative ellipsis: "Compare with Hubble", "Vs Hubble", "And with Hubble"
    comp_ellipsis = re.match(r"^(?:compare\s+(?:it\s+)?with|compare\s+to|vs\.?|versus|and\s+with)\s+(.+)$", raw_query, re.IGNORECASE)
    if comp_ellipsis:
        target_b = comp_ellipsis.group(1).strip()
        return f"Compare {prev_subject} and {target_b}"

    # Check for question ellipsis: "What about ...", "How about ...", "What is its ..."
    ellipsis_match = re.match(r"^(?:what\s+about|how\s+about|and)\s+(.+)$", raw_query, re.IGNORECASE)
    if ellipsis_match:
        facet = ellipsis_match.group(1).strip()
        return f"{prev_subject} {facet}"

    return raw_query
