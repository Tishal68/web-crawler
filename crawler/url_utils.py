"""
URL utility functions for normalization, validation, domain matching,
and filtering.
"""

from urllib.parse import urlparse, urlunparse, urljoin, parse_qsl, urlencode
import posixpath
import re
from typing import Optional

# Common binary and non-HTML media extensions to skip crawling
BINARY_EXTENSIONS = {
    # Images
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".bmp", ".tif", ".tiff",
    # Documents
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods",
    # Archives
    ".zip", ".tar", ".gz", ".7z", ".rar", ".bz2", ".xz", ".tgz",
    # Audio/Video
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".webm", ".m4a",
    # Executables & System
    ".exe", ".msi", ".dmg", ".bin", ".iso", ".apk", ".deb", ".rpm",
    # Web assets that are not navigable HTML pages
    ".css", ".js", ".json", ".xml", ".rss", ".atom", ".woff", ".woff2", ".ttf", ".eot",
}

# Supported protocols
VALID_SCHEMES = {"http", "https"}


def is_valid_url(url: str) -> bool:
    """
    Check if a URL is structurally valid, uses http or https, and has valid host and port.
    """
    if not url or not isinstance(url, str):
        return False
    
    url = url.strip()
    if not url:
        return False

    try:
        parsed = urlparse(url)
        if parsed.scheme.lower() not in VALID_SCHEMES:
            return False
        if not parsed.netloc:
            return False
        # Disallow unencoded whitespace in netloc
        if re.search(r"\s", parsed.netloc):
            return False
        
        # Validate port range if present
        try:
            port = parsed.port
            if port is not None and not (1 <= port <= 65535):
                return False
        except ValueError:
            return False

        # Hostname must be present
        if not parsed.hostname:
            return False

        return True
    except Exception:
        return False


def is_binary_url(url: str) -> bool:
    """
    Check if a URL points directly to a known binary, image, or non-HTML resource
    based on its file extension in the URL path.
    """
    if not url:
        return False
    try:
        parsed = urlparse(url)
        path = parsed.path.lower()
        # Find file extension in the last path segment
        last_segment = posixpath.basename(path)
        if "." in last_segment:
            ext = "." + last_segment.split(".")[-1]
            if ext in BINARY_EXTENSIONS:
                return True
        return False
    except Exception:
        return False


def get_domain(url: str) -> str:
    """
    Extract the clean domain (hostname) in lowercase without port, userinfo, or IPv6 brackets.
    """
    if not url:
        return ""
    try:
        # If url doesn't have scheme, prefix dummy scheme for parsing
        parse_target = url if "://" in url else f"http://{url}"
        parsed = urlparse(parse_target)
        hostname = parsed.hostname or ""
        return hostname.lower().strip()
    except Exception:
        return ""


def is_same_domain(url: str, base_domain: str, allow_subdomains: bool = True) -> bool:
    """
    Determine if a URL belongs to the same domain as base_domain.
    If allow_subdomains is True, sub.domain.com will match domain.com.
    """
    url_domain = get_domain(url)
    base = get_domain(base_domain) or base_domain.lower().strip()
    
    if not url_domain or not base:
        return False
        
    if url_domain == base:
        return True
        
    if allow_subdomains:
        if url_domain.endswith("." + base):
            return True
            
    return False


def normalize_url(url: str, base_url: Optional[str] = None) -> Optional[str]:
    """
    Normalize a URL with RFC 3986 compliance:
    - Resolves relative URLs against base_url
    - Rejects invalid schemes (mailto:, javascript:, tel:, etc.)
    - Converts scheme and host to lowercase
    - Handles IPv6 hosts formatting ([::1])
    - Preserves userinfo (user:pass@) if present
    - Normalizes standard default ports (:80 for http, :443 for https)
    - Validates port numbers (returns None on invalid/overflow ports)
    - Normalizes percent-encoding of unreserved characters (RFC 3986 Section 2.3)
    - Normalizes redundant slashes in path
    - Normalizes root path and non-root trailing slashes for deterministic deduplication
    - Sorts query parameters deterministically while preserving multi-value keys and blank values
    - Strips fragments (#section) completely
    """
    if not url or not isinstance(url, str):
        return None

    cleaned_url = url.strip()
    if not cleaned_url:
        return None

    # Handle javascript:, mailto:, tel:, file:, etc.
    lower_check = cleaned_url.lower()
    if lower_check.startswith(("javascript:", "mailto:", "tel:", "data:", "file:", "ftp:", "callto:")):
        return None

    # Resolve relative URL if base_url is provided
    if base_url:
        try:
            cleaned_url = urljoin(base_url, cleaned_url)
        except Exception:
            return None

    if not is_valid_url(cleaned_url):
        return None

    try:
        parsed = urlparse(cleaned_url)
        scheme = parsed.scheme.lower()
        
        # Validate and extract port
        try:
            port = parsed.port
        except ValueError:
            return None

        if port is not None and not (1 <= port <= 65535):
            return None

        # Extract hostname and format IPv6 if needed
        raw_hostname = (parsed.hostname or "").lower()
        if not raw_hostname:
            return None

        host_str = f"[{raw_hostname}]" if ":" in raw_hostname else raw_hostname

        # Remove standard default ports
        if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
            port_str = ""
        elif port is not None:
            port_str = f":{port}"
        else:
            port_str = ""

        # Preserve userinfo if present
        userinfo = ""
        if parsed.username is not None:
            if parsed.password is not None:
                userinfo = f"{parsed.username}:{parsed.password}@"
            else:
                userinfo = f"{parsed.username}@"

        netloc = f"{userinfo}{host_str}{port_str}"

        # Normalize path
        path = parsed.path or ""
        if path:
            # Decode percent-encoded unreserved characters (ALPHA / DIGIT / "-" / "." / "_" / "~")
            def _decode_unreserved(match):
                val = int(match.group(1), 16)
                char = chr(val)
                if char.isalnum() or char in "-_.~":
                    return char
                return match.group(0).upper()

            path = re.sub(r"%([0-9a-fA-F]{2})", _decode_unreserved, path)
            # Replace multiple consecutive slashes with a single slash
            path = re.sub(r"/+", "/", path)
            # Normalize root and trailing slash for deterministic deduplication
            if path == "/":
                path = ""
            elif len(path) > 1 and path.endswith("/"):
                path = path[:-1]

        # Normalize query parameters by sorting deterministically
        query = ""
        if parsed.query:
            params = parse_qsl(parsed.query, keep_blank_values=True)
            if params:
                sorted_params = sorted(params, key=lambda kv: (kv[0], kv[1]))
                query = urlencode(sorted_params)

        # Build normalized URL without fragment
        normalized = urlunparse((
            scheme,
            netloc,
            path,
            parsed.params,
            query,
            "",  # Strip fragment completely
        ))
        return normalized
    except Exception:
        return None
