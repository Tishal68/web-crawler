"""
Robots.txt parser and policy manager conforming to RFC 9309.
Fetches, parses, and caches robots.txt rules per host with explicit error categorization.
"""

from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse
from typing import Dict, Optional, Tuple, NamedTuple
import requests


class RobotsCheckResult(NamedTuple):
    """Structured result of a robots.txt authorization check."""
    allowed: bool
    status: str
    reason: str


class HostRobotsEntry:
    """Cached robots policy state for a specific network host."""

    def __init__(
        self,
        status: str,
        parser: Optional[RobotFileParser] = None,
        status_code: Optional[int] = None,
        error_message: Optional[str] = None,
    ):
        self.status = status
        self.parser = parser
        self.status_code = status_code
        self.error_message = error_message


class RobotsManager:
    """
    Manages fetching, parsing, and caching of robots.txt across domains.
    Implements RFC 9309 (Robots Exclusion Protocol) rules:
    - HTTP 200/203: parse and evaluate directives for user-agent
    - HTTP 4xx (e.g. 404): No robots rules exist -> ALLOW
    - HTTP 5xx: Server error -> FAIL-CLOSED (disallow) per RFC 9309 § 2.3.1.3
    - Network / Timeout / SSL failure -> FAIL-CLOSED with explicit reason
    """

    def __init__(self, timeout: float = 5.0, user_agent: str = "*"):
        self.timeout = timeout
        self.user_agent = user_agent
        self._cache: Dict[str, HostRobotsEntry] = {}

    def _get_robots_url(self, url: str) -> str:
        """Construct the canonical robots.txt URL for a given target URL."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    def fetch_rules(self, url: str) -> HostRobotsEntry:
        """Fetch, parse, and cache robots.txt for the host domain."""
        parsed = urlparse(url)
        host = parsed.netloc.lower()

        if host in self._cache:
            return self._cache[host]

        robots_url = self._get_robots_url(url)
        rp = RobotFileParser()
        rp.set_url(robots_url)

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/plain,text/html,*/*",
        }

        try:
            resp = requests.get(robots_url, headers=headers, timeout=self.timeout)
            status_code = resp.status_code

            if status_code in (200, 203):
                try:
                    rp.parse(resp.text.splitlines())
                    entry = HostRobotsEntry(
                        status="200_OK",
                        parser=rp,
                        status_code=status_code,
                    )
                except Exception as parse_err:
                    entry = HostRobotsEntry(
                        status="MALFORMED",
                        status_code=status_code,
                        error_message=f"Malformed robots.txt content: {parse_err}",
                    )
            elif 400 <= status_code < 500:
                # RFC 9309 § 2.3.1.2: 4xx indicates no robots exclusion policy exists
                entry = HostRobotsEntry(
                    status="4XX_NOT_FOUND",
                    status_code=status_code,
                    error_message=f"No robots.txt policy found (HTTP {status_code}).",
                )
            elif status_code >= 500:
                # RFC 9309 § 2.3.1.3: 5xx indicates server failure -> fail closed
                entry = HostRobotsEntry(
                    status="5XX_SERVER_ERROR",
                    status_code=status_code,
                    error_message=f"Robots.txt returned server error (HTTP {status_code}).",
                )
            else:
                entry = HostRobotsEntry(
                    status=f"HTTP_{status_code}",
                    status_code=status_code,
                    error_message=f"Unexpected status code {status_code} for robots.txt.",
                )

        except requests.exceptions.SSLError as ssl_err:
            entry = HostRobotsEntry(
                status="SSL_ERROR",
                error_message=f"SSL certificate error fetching robots.txt: {ssl_err}",
            )
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout, requests.exceptions.Timeout) as t_err:
            entry = HostRobotsEntry(
                status="TIMEOUT",
                error_message=f"Timeout fetching robots.txt after {self.timeout}s: {t_err}",
            )
        except requests.exceptions.ConnectionError as conn_err:
            entry = HostRobotsEntry(
                status="CONNECTION_ERROR",
                error_message=f"Network connection failed fetching robots.txt: {conn_err}",
            )
        except Exception as exc:
            entry = HostRobotsEntry(
                status="FETCH_ERROR",
                error_message=f"Unexpected error fetching robots.txt: {type(exc).__name__}: {exc}",
            )

        self._cache[host] = entry
        return entry

    def check_allowed(self, url: str, user_agent: Optional[str] = None) -> RobotsCheckResult:
        """
        Evaluate robots.txt policy and return structured check result.
        """
        ua = user_agent or self.user_agent
        entry = self.fetch_rules(url)

        if entry.status == "200_OK" and entry.parser:
            try:
                allowed = entry.parser.can_fetch(ua, url)
                if allowed:
                    return RobotsCheckResult(True, "ALLOWED", "Permitted by host robots.txt policy.")
                else:
                    return RobotsCheckResult(False, "DISALLOWED", "Disallowed by host robots.txt policy.")
            except Exception as e:
                # Fallback on parser query error
                return RobotsCheckResult(True, "PARSE_FALLBACK", f"Allowed (parser evaluation error: {e})")

        elif entry.status == "4XX_NOT_FOUND":
            return RobotsCheckResult(
                True,
                "ALLOWED_NO_POLICY",
                f"Allowed: Host has no robots.txt file (HTTP {entry.status_code}).",
            )

        elif entry.status == "5XX_SERVER_ERROR":
            return RobotsCheckResult(
                False,
                "SERVER_ERROR_DISALLOWED",
                f"Disallowed (RFC 9309 § 2.3.1.3): robots.txt returned HTTP {entry.status_code} server error.",
            )

        elif entry.status in ("TIMEOUT", "CONNECTION_ERROR", "SSL_ERROR", "FETCH_ERROR"):
            return RobotsCheckResult(
                False,
                entry.status,
                f"Disallowed: Unable to verify host permissions ({entry.error_message}).",
            )

        elif entry.status == "MALFORMED":
            # Malformed robots.txt with HTTP 200: permissive fallback per RFC guidelines
            return RobotsCheckResult(
                True,
                "MALFORMED_PERMISSIVE",
                f"Allowed: robots.txt was malformed ({entry.error_message}).",
            )

        return RobotsCheckResult(True, "DEFAULT_ALLOW", "Allowed by default.")

    def is_allowed(self, url: str, user_agent: Optional[str] = None) -> bool:
        """
        Boolean query method for backwards compatibility with existing crawler and tests.
        """
        return self.check_allowed(url, user_agent=user_agent).allowed

    def clear_cache(self) -> None:
        """Clear cached host policies."""
        self._cache.clear()
