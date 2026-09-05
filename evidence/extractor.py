"""
Web evidence extractor: Fetches web pages, extracts metadata, published dates,
filters low-information/promotional boilerplate and foreign language leakage,
and extracts clean structured text passages with hierarchical heading context.
"""

import re
import json
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup

from .models import EvidencePassage, ExtractedPageEvidence
from crawler.url_utils import get_domain, safe_http_get
from search.source_quality import classify_source

# Stopword sets for lightweight language detection
COMMON_SPANISH_WORDS = {
    "el", "la", "de", "que", "en", "los", "del", "se", "las", "por", "un", "para",
    "con", "no", "una", "su", "al", "lo", "como", "mas", "más", "pero", "sus", "le",
    "ya", "este", "sí", "porque", "esta", "son", "entre", "está", "cuando", "muy",
    "sin", "sobre", "también", "tambien", "hasta", "hay", "donde", "desde", "todos",
    "nos", "durante", "uno", "les", "contra", "otros", "ese", "eso", "ante", "ellos",
    "esto", "antes", "algunos", "unos", "otro", "otras", "otra", "él", "tanto", "esa",
    "estos", "mucho", "quienes", "nada", "muchos", "cual", "sea", "poco", "ella"
}

COMMON_FRENCH_WORDS = {
    "le", "la", "de", "du", "des", "et", "en", "un", "une", "que", "est", "pour",
    "dans", "sur", "avec", "par", "ce", "ces", "qui", "pas", "sont", "aux", "au",
    "plus", "il", "elle", "se", "ne", "ont", "mais", "nous", "vous", "ils", "elles",
    "tout", "tous", "comme", "ou", "faire", "fait"
}

COMMON_GERMAN_WORDS = {
    "der", "die", "das", "und", "in", "den", "von", "zu", "dem", "mit", "sich",
    "des", "auf", "für", "ist", "im", "nicht", "eine", "als", "auch", "es", "an",
    "werden", "aus", "er", "hat", "dass", "sie", "nach", "wird", "bei", "einer"
}

PROMOTIONAL_PATTERNS = [
    r"cookie(s)?\s+(policy|settings|notice|consent)",
    r"all\s+rights\s+reserved",
    r"privacy\s+policy",
    r"terms\s+of\s+(service|use)",
    r"sign\s+up\s+for\s+(our\s+)?newsletter",
    r"subscribe\s+to\s+(our\s+)?newsletter",
    r"subscribe\s+now",
    r"advertisement",
    r"please\s+enable\s+javascript",
    r"skip\s+to\s+(main\s+)?content",
    r"share\s+.*(facebook|twitter|linkedin|reddit|whatsapp)",
    r"follow\s+us\s+on\s+(twitter|instagram|facebook|linkedin|youtube)",
    r"leave\s+a\s+(comment|reply)",
    r"trending\s+(now|topics|stories)",
    r"table\s+of\s+contents",
    r"read\s+more\s+about",
    r"related\s+(articles|posts|stories|reading)",
    r"fun\s+facts\s+about",
    r"trivia\s+and\s+fun\s+facts",
    r"click\s+here\s+to",
    r"affiliate\s+links?",
    r"sponsored\s+content",
    r"buy\s+now",
    r"add\s+to\s+cart",
    r"special\s+offer",
    r"discount\s+code",
    r"join\s+our\s+community",
    r"download\s+the\s+app",
    r"^credit\s*:",
    r"^photo\s+credit",
    r"^image\s+credit",
    r"^source\s*:",
    r"image\s+courtesy\s+of",
    r"photo\s+courtesy\s+of",
]


def detect_language(text: str) -> str:
    """
    Lightweight language detector based on distinctive stopword frequency.
    Returns ISO language code (e.g. 'en', 'es', 'fr', 'de').
    """
    if not text:
        return "en"
    words = re.findall(r"\b[a-zA-Z\u00C0-\u017F]{2,}\b", text.lower())
    if len(words) < 5:
        return "en"

    total_words = len(words)
    es_matches = sum(1 for w in words if w in COMMON_SPANISH_WORDS)
    fr_matches = sum(1 for w in words if w in COMMON_FRENCH_WORDS)
    de_matches = sum(1 for w in words if w in COMMON_GERMAN_WORDS)

    scores = {"es": es_matches, "fr": fr_matches, "de": de_matches}
    best_lang, best_count = max(scores.items(), key=lambda x: x[1])

    if best_count >= 3 and (best_count / total_words) >= 0.08:
        return best_lang
    return "en"



def is_low_information(text: str) -> bool:
    """
    Detects whether a text snippet is promotional fluff, boilerplate,
    or low-information navigational text that degrades answer synthesis.
    """
    if not text:
        return True
    lower = text.lower().strip()
    words = lower.split()
    if len(words) < 7 or len(text) < 40:
        return True

    # Check promotional regex patterns
    for pat in PROMOTIONAL_PATTERNS:
        if re.search(pat, lower):
            return True

    # Check alphanumeric ratio (e.g., symbols, prices, or ascii art)
    alpha_chars = sum(1 for c in text if c.isalpha())
    if len(text) > 0 and (alpha_chars / len(text)) < 0.55:
        return True

    # Low lexical diversity (repetitive strings / spam)
    unique_words = set(words)
    if len(words) >= 15 and (len(unique_words) / len(words)) < 0.40:
        return True

    return False


class EvidenceExtractor:
    """Extracts structured evidence passages and publication dates from web sources."""

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36 WebSearchEngine/2.0"
    )

    def __init__(self, timeout: float = 6.0):

        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def extract_date(self, soup: BeautifulSoup, html: str) -> Optional[str]:
        """Extract publication or update date from HTML metadata."""
        # 1. JSON-LD date extraction
        for script in soup.find_all("script", type="application/ld+json"):
            if not script.string:
                continue
            try:
                data = json.loads(script.string)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if isinstance(item, dict):
                        for key in ("datePublished", "dateModified", "uploadDate"):
                            val = item.get(key)
                            if val and isinstance(val, str):
                                m = re.search(r"(\d{4}-\d{2}-\d{2})", val)
                                if m:
                                    return m.group(1)
            except Exception:
                continue

        # 2. OpenGraph and meta tags
        meta_names = [
            {"property": "article:published_time"},
            {"property": "article:modified_time"},
            {"property": "og:published_time"},
            {"name": "publication_date"},
            {"name": "publish_date"},
            {"name": "date"},
            {"name": "dc.date"},
            {"name": "dcterms.date"},
        ]
        for query in meta_names:
            meta = soup.find("meta", attrs=query)
            if meta and meta.get("content"):
                m = re.search(r"(\d{4}-\d{2}-\d{2})", meta["content"])
                if m:
                    return m.group(1)

        # 3. HTML5 <time> tag
        time_tag = soup.find("time")
        if time_tag:
            dt = time_tag.get("datetime") or time_tag.get_text()
            if dt:
                m = re.search(r"(\d{4}-\d{2}-\d{2})", dt)
                if m:
                    return m.group(1)

        # 4. Text regex fallback (e.g., "Updated: Oct 14, 2024" or "Published: 2025-01-12")
        m = re.search(r"\b(202[0-9]|201[8-9])[-/.](0[1-9]|1[0-2])[-/.](0[1-9]|[12][0-9]|3[01])\b", html)
        if m:
            return m.group(0)

        return None

    def _is_boilerplate(self, text: str) -> bool:
        """Check if text snippet is low-information or boilerplate."""
        return is_low_information(text)

    def extract_from_html(
        self,
        html: str,
        url: str,
        title: str = "",
        snippet: str = "",
        target_language: Optional[str] = "en",
        filter_foreign_language: bool = False,
    ) -> ExtractedPageEvidence:
        """
        Parse HTML and extract clean, informative text passages with structural metadata.
        Filters out promotional boilerplate and foreign language passages.
        """
        dom = get_domain(url)
        source_type = classify_source(url, title).value

        if not html:
            # Fallback to search snippet if HTML is empty
            passages = []
            if snippet:
                passages.append(EvidencePassage(
                    text=snippet,
                    source_url=url,
                    source_domain=dom,
                    source_title=title or dom,
                    heading_context="Search Snippet",
                    source_type=source_type,
                    passage_id=f"{dom}_snip",
                    language=detect_language(snippet),
                ))
            return ExtractedPageEvidence(
                url=url,
                title=title or dom,
                domain=dom,
                source_type=source_type,
                passages=passages,
                top_passage=passages[0] if passages else None,
                fetch_success=False,
                error_message="Empty HTML content",
            )

        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception as e:
            return ExtractedPageEvidence(
                url=url,
                title=title or dom,
                domain=dom,
                source_type=source_type,
                fetch_success=False,
                error_message=f"HTML parse error: {e}",
            )

        # 1. Resolve Title
        if not title:
            title_tag = soup.find("title")
            if title_tag and title_tag.string:
                title = title_tag.string.strip()
            elif soup.find("h1"):
                title = soup.find("h1").get_text().strip()
            else:
                title = dom
        title = " ".join(title.split())

        # 2. Resolve Date
        published_date = self.extract_date(soup, html)

        # 3. Strip non-content elements
        for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav", "aside", "form", "dialog"]):
            tag.decompose()

        # 4. Target Primary Article / Main Content Container
        content_root = None
        main_candidates = soup.find_all(["main", "article"])
        for candidate in main_candidates:
            if len(candidate.get_text(strip=True)) > 250:
                content_root = candidate
                break

        if not content_root:
            # Check by common id or class names
            class_id_patterns = re.compile(
                r"(article-body|post-content|entry-content|mw-parser-output|main-content|story-body|article__body)",
                re.I
            )
            container = soup.find(attrs={"id": class_id_patterns}) or soup.find(attrs={"class": class_id_patterns})
            if container and len(container.get_text(strip=True)) > 250:
                content_root = container

        if not content_root:
            content_root = soup.find("body") or soup

        # 5. Extract hierarchical passages
        passages: List[EvidencePassage] = []
        current_heading = ""
        seen_texts = set()

        for elem in content_root.find_all(["h1", "h2", "h3", "p", "li", "blockquote", "td"]):
            tag_name = elem.name.lower()

            if tag_name in ("h1", "h2", "h3"):
                h_text = elem.get_text(separator=" ", strip=True)
                h_lower = h_text.lower()
                if h_text and 3 <= len(h_text) < 120 and not any(re.search(pat, h_lower) for pat in PROMOTIONAL_PATTERNS):
                    current_heading = h_text
                continue


            raw_txt = elem.get_text(separator=" ", strip=True)
            cleaned_txt = " ".join(raw_txt.split())

            if not cleaned_txt or len(cleaned_txt) < 40:
                continue

            # Filter low information / promotional text
            if is_low_information(cleaned_txt):
                continue

            # Language detection and tagging
            passage_lang = detect_language(cleaned_txt)
            if filter_foreign_language and target_language and passage_lang != target_language:
                continue

            # Deduplicate similar passages
            fingerprint = cleaned_txt[:100].lower()
            if fingerprint in seen_texts:
                continue
            seen_texts.add(fingerprint)

            passage = EvidencePassage(
                text=cleaned_txt,
                source_url=url,
                source_domain=dom,
                source_title=title,
                heading_context=current_heading,
                published_date=published_date,
                source_type=source_type,
                passage_id=f"{dom}_{len(passages) + 1}",
                language=passage_lang,
            )
            passages.append(passage)

        # Fallback if no block paragraphs extracted
        if not passages and snippet:
            snip_lang = detect_language(snippet)
            passages.append(EvidencePassage(
                text=snippet,
                source_url=url,
                source_domain=dom,
                source_title=title,
                heading_context="Search Snippet",
                published_date=published_date,
                source_type=source_type,
                passage_id=f"{dom}_snip",
                language=snip_lang,
            ))

        return ExtractedPageEvidence(
            url=url,
            title=title,
            domain=dom,
            source_type=source_type,
            published_date=published_date,
            passages=passages,
            top_passage=passages[0] if passages else None,
            fetch_success=True,
        )

    def fetch_and_extract(
        self,
        url: str,
        title: str = "",
        snippet: str = "",
        target_language: Optional[str] = "en",
        filter_foreign_language: bool = False,
    ) -> ExtractedPageEvidence:
        """Fetch URL over HTTP and extract structured evidence with full SSRF protection."""
        dom = get_domain(url)
        source_type = classify_source(url, title).value

        resp, err = safe_http_get(
            url,
            session=self.session,
            timeout=self.timeout,
            max_redirects=5,
            max_bytes=2 * 1024 * 1024,
        )

        if resp and resp.status_code == 200:
            content_type = resp.headers.get("Content-Type", "").lower()
            if "text/html" in content_type or "application/xhtml" in content_type or not content_type:
                return self.extract_from_html(
                    html=resp.text,
                    url=resp.url,
                    title=title,
                    snippet=snippet,
                    target_language=target_language,
                    filter_foreign_language=filter_foreign_language,
                )

        # Fallback with search snippet if HTTP request failed, was blocked, or returned non-HTML
        fallback_passage = EvidencePassage(
            text=snippet,
            source_url=url,
            source_domain=dom,
            source_title=title or dom,
            heading_context="Search Snippet",
            source_type=source_type,
            passage_id=f"{dom}_snip",
            language=detect_language(snippet) if snippet else "en",
        ) if snippet else None

        error_msg = err or (f"HTTP {resp.status_code}" if resp else "Fetch failed")
        return ExtractedPageEvidence(
            url=url,
            title=title or dom,
            domain=dom,
            source_type=source_type,
            passages=[fallback_passage] if fallback_passage else [],
            top_passage=fallback_passage,
            fetch_success=False,
            error_message=error_msg,
        )

    def extract_from_search_results(
        self,
        results: List[Any],
        max_workers: int = 4,
        target_language: Optional[str] = "en",
    ) -> List[ExtractedPageEvidence]:
        """Concurrently fetch and extract evidence from a list of SearchResults."""
        evidence_list: List[ExtractedPageEvidence] = []
        if not results:
            return evidence_list

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_item = {
                executor.submit(
                    self.fetch_and_extract,
                    item.url,
                    item.title,
                    item.snippet,
                    target_language,
                ): item
                for item in results
            }

            for future in as_completed(future_to_item):
                try:
                    ev = future.result()
                    evidence_list.append(ev)
                except Exception:
                    pass

        # Sort extracted pages to match original search result ranking order
        url_order = {item.url: idx for idx, item in enumerate(results)}
        evidence_list.sort(key=lambda x: url_order.get(x.url, 999))
        return evidence_list

