"""
Thread-safe TTL search cache.
Caches SearchResultSet by normalized query, provider name, and result limit.
"""

import hashlib
import time
import threading
from typing import Optional, Dict, Any
from .provider import SearchResultSet


class SearchCache:
    """In-memory thread-safe TTL cache for search results."""

    def __init__(self, default_ttl_seconds: int = 1800):
        self.default_ttl = default_ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def _make_key(self, query: str, provider_name: str, num_results: int) -> str:
        norm = f"{query.strip().lower()}|{provider_name.strip().lower()}|{num_results}"
        return hashlib.sha256(norm.encode("utf-8")).hexdigest()

    def get(self, query: str, provider_name: str, num_results: int = 10) -> Optional[SearchResultSet]:
        """Retrieve cached SearchResultSet if valid and unexpired."""
        key = self._make_key(query, provider_name, num_results)
        with self._lock:
            entry = self._cache.get(key)
            if not entry:
                self._misses += 1
                return None

            if time.time() > entry["expires_at"]:
                del self._cache[key]
                self._misses += 1
                return None

            self._hits += 1
            return entry["data"]

    def set(
        self,
        query: str,
        provider_name: str,
        result_set: SearchResultSet,
        num_results: int = 10,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Cache a SearchResultSet."""
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        key = self._make_key(query, provider_name, num_results)
        with self._lock:
            self._cache[key] = {
                "data": result_set,
                "expires_at": time.time() + ttl,
                "created_at": time.time(),
            }

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> Dict[str, Any]:
        """Return cache performance statistics."""
        with self._lock:
            # Clean expired items
            now = time.time()
            expired = [k for k, v in self._cache.items() if now > v["expires_at"]]
            for k in expired:
                del self._cache[k]

            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0
            return {
                "size": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate_pct": round(hit_rate, 1),
            }
