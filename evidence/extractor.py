"""
Web evidence extractor: Fetches web pages, extracts metadata, published dates,
and extracts clean structured text passages with hierarchical heading context.
"""

import re
import json
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup

from .models import EvidencePassage, ExtractedPageEvidence
from crawler.url_utils import get_domain
from search.source_quality import classify_source


class EvidenceExtractor:
    """Extracts structured evidence passages and publication dates from web sources."""

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36 WebSearchEngine/2.0"
    )

    BOILERPLATE_PATTERNS = [
        r"cookie(s)?\s+(policy|settings|notice|consent)",
        r"all\s+rights\s+reserved",
        r"privacy\s+policy",
        r"terms\s+of\s+(service|use)",
        r"sign\s+up\s+for\s+(our\s+)?newsletter",
        r"subscribe\s+to\s+(our\s+)?newsletter",
        r"advertisement",
        r"please\s+enable\s+javascript",
        r"skip\s+to\s+(main\s+)?content",
    ]

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
        """Check if text snippet is common webpage boilerplate."""
        lower = text.lower()
        if len(text.split()) < 4:
            return True
        for pattern in self.BOILERPLATE_PATTERNS:
            if re.search(pattern, lower):
                return True
        return False

    def extract_from_html(
        self,
        html: str,
        url: str,
        title: str = "",
        snippet: str = "",
    ) -> ExtractedPageEvidence:
        """Parse HTML and extract clean text passages with structural metadata."""
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
        for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav", "aside", "form"]):
            tag.decompose()

        # 4. Extract hierarchical passages
        passages: List[EvidencePassage] = []
        current_heading = ""
        seen_texts = set()

        body = soup.find("body") or soup

        for elem in body.find_all(["h1", "h2", "h3", "p", "li", "blockquote", "td"]):
            tag_name = elem.name.lower()

            if tag_name in ("h1", "h2", "h3"):
                h_text = elem.get_text(separator=" ", strip=True)
                if h_text and len(h_text) < 120:
                    current_heading = h_text
                continue

            raw_txt = elem.get_text(separator=" ", strip=True)
            cleaned_txt = " ".join(raw_txt.split())

            if not cleaned_txt or len(cleaned_txt) < 35:
                continue

            if self._is_boilerplate(cleaned_txt):
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
            )
            passages.append(passage)

        # If page had no block paragraphs extracted, use snippet fallback
        if not passages and snippet:
            passages.append(EvidencePassage(
                text=snippet,
                source_url=url,
                source_domain=dom,
                source_title=title,
                heading_context="Search Snippet",
                published_date=published_date,
                source_type=source_type,
                passage_id=f"{dom}_snip",
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
    ) -> ExtractedPageEvidence:
        """Fetch URL over HTTP and extract structured evidence."""
        dom = get_domain(url)
        source_type = classify_source(url, title).value

        try:
            resp = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            if resp.status_code == 200:
                content_type = resp.headers.get("Content-Type", "").lower()
                if "text/html" in content_type or "application/xhtml" in content_type or not content_type:
                    return self.extract_from_html(
                        html=resp.text,
                        url=url,
                        title=title,
                        snippet=snippet,
                    )
            # Non-200 or non-HTML: fallback with search snippet
            fallback_passage = EvidencePassage(
                text=snippet,
                source_url=url,
                source_domain=dom,
                source_title=title or dom,
                heading_context="Search Snippet",
                source_type=source_type,
                passage_id=f"{dom}_snip",
            ) if snippet else None

            return ExtractedPageEvidence(
                url=url,
                title=title or dom,
                domain=dom,
                source_type=source_type,
                passages=[fallback_passage] if fallback_passage else [],
                top_passage=fallback_passage,
                fetch_success=False,
                error_message=f"HTTP {resp.status_code}",
            )
        except Exception as e:
            fallback_passage = EvidencePassage(
                text=snippet,
                source_url=url,
                source_domain=dom,
                source_title=title or dom,
                heading_context="Search Snippet",
                source_type=source_type,
                passage_id=f"{dom}_snip",
            ) if snippet else None

            return ExtractedPageEvidence(
                url=url,
                title=title or dom,
                domain=dom,
                source_type=source_type,
                passages=[fallback_passage] if fallback_passage else [],
                top_passage=fallback_passage,
                fetch_success=False,
                error_message=str(e),
            )

    def extract_from_search_results(
        self,
        results: List[Any],
        max_workers: int = 4,
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
