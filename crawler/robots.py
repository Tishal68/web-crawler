"""
Robots.txt parser and policy manager.
Fetches and caches robots.txt rules per domain with timeout and fallback protection.
"""

from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse
import requests
from typing import Dict, Optional


class RobotsManager:
    """Manages fetching, parsing, and caching of robots.txt across domains."""

    def __init__(self, timeout: float = 5.0, user_agent: str = "*"):
        self.timeout = timeout
        self.user_agent = user_agent
        self._cache: Dict[str, Optional[RobotFileParser]] = {}

    def _get_robots_url(self, url: str) -> str:
        """Construct the robots.txt URL for a given target URL."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    def fetch_rules(self, url: str) -> Optional[RobotFileParser]:
        """Fetch and cache robots.txt for the host domain."""
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        
        if host in self._cache:
            return self._cache[host]

        robots_url = self._get_robots_url(url)
        rp = RobotFileParser()
        rp.set_url(robots_url)

        try:
            headers = {"User-Agent": self.user_agent}
            resp = requests.get(robots_url, headers=headers, timeout=self.timeout)
            if resp.status_code in (200, 203):
                rp.parse(resp.text.splitlines())
                self._cache[host] = rp
                return rp
            else:
                # 404 or any other non-200 means no disallow rules apply
                self._cache[host] = None
                return None
        except Exception:
            # On network/timeout/SSL errors, default to permissive to prevent crawler blockage
            self._cache[host] = None
            return None

    def is_allowed(self, url: str, user_agent: Optional[str] = None) -> bool:
        """
        Check if a URL is permitted to be crawled according to robots.txt.
        If robots.txt is missing, unreachable, or parsing fails, returns True.
        """
        ua = user_agent or self.user_agent
        rp = self.fetch_rules(url)
        if rp is None:
            return True
        try:
            return rp.can_fetch(ua, url)
        except Exception:
            return True
