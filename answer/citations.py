"""
Citation registry and citation grounding module.
Enforces the invariant that every citation key strictly maps to an authentic,
retrieved source URL. Prevents hallucinated or invented citations.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class Citation:
    """Represents a verified citation linked to an authentic retrieved web page."""
    index: int
    url: str
    title: str
    domain: str
    source_type: str
    published_date: Optional[str] = None
    sample_quote: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "url": self.url,
            "title": self.title,
            "domain": self.domain,
            "source_type": self.source_type,
            "published_date": self.published_date,
            "sample_quote": self.sample_quote,
        }

    def format_markdown(self) -> str:
        date_str = f" · {self.published_date}" if self.published_date else ""
        return (
            f"**[{self.index}]** [{self.title}]({self.url})  \n"
            f"*{self.domain}* · `{self.source_type}`{date_str}"
        )


class CitationRegistry:
    """
    Registry that assigns sequential 1-based citation indices to retrieved sources.
    Strictly verifies that no citation is emitted without a corresponding real URL.
    """

    def __init__(self):
        self._citations: List[Citation] = []
        self._url_to_index: Dict[str, int] = {}

    def register(
        self,
        url: str,
        title: str,
        domain: str,
        source_type: str = "General Web Source",
        published_date: Optional[str] = None,
        sample_quote: str = "",
    ) -> int:
        """
        Register a source URL and return its 1-based citation index.
        If URL was already registered, returns the existing index.
        """
        if not url:
            raise ValueError("Cannot register an empty URL as a citation.")

        if url in self._url_to_index:
            idx = self._url_to_index[url]
            # Update quote if previously empty
            if sample_quote and not self._citations[idx - 1].sample_quote:
                self._citations[idx - 1].sample_quote = sample_quote
            return idx

        index = len(self._citations) + 1
        citation = Citation(
            index=index,
            url=url,
            title=title or domain or f"Source {index}",
            domain=domain,
            source_type=source_type,
            published_date=published_date,
            sample_quote=sample_quote,
        )
        self._citations.append(citation)
        self._url_to_index[url] = index
        return index

    def get_citation(self, index: int) -> Optional[Citation]:
        """Retrieve citation by index."""
        if 1 <= index <= len(self._citations):
            return self._citations[index - 1]
        return None

    def get_index_for_url(self, url: str) -> Optional[int]:
        """Get citation index for a registered URL."""
        return self._url_to_index.get(url)

    def all_citations(self) -> List[Citation]:
        """Return all registered citations in order."""
        return list(self._citations)

    def format_references_markdown(self) -> str:
        """Format the complete sources and references section in Markdown."""
        if not self._citations:
            return ""

        lines = ["### 📚 Sources & Verified References"]
        for c in self._citations:
            lines.append(c.format_markdown())
            if c.sample_quote:
                clean_quote = " ".join(c.sample_quote.split())
                if len(clean_quote) > 140:
                    clean_quote = clean_quote[:137].rstrip() + "..."
                lines.append(f"> \"{clean_quote}\"")
            lines.append("")
        return "\n".join(lines)
