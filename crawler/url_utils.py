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
    Check if a URL is structurally valid and uses http or https.
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
        # Disallow simple whitespace in hostname
        if re.search(r"\s", parsed.netloc):
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
    Extract the clean domain (hostname) in lowercase without port or userinfo.
    """
    if not url:
        return ""
    try:
        parsed = urlparse(url)
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
    base = base_domain.lower().strip()
    
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
    Normalize a URL:
    - Resolves relative URLs against base_url
    - Converts scheme and host to lowercase
    - Removes URL fragments (#section)
    - Normalizes default ports (:80, :443)
    - Normalizes redundant slashes in path
    - Sorts query parameters deterministically
    - Strips non-root trailing slash for uniform duplicate prevention
    - Rejects invalid schemes (mailto:, javascript:, tel:, etc.)
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
        
        # Normalize hostname and port
        hostname = (parsed.hostname or "").lower()
        port = parsed.port
        
        # Remove standard default ports
        if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
            netloc = hostname
        elif port is not None:
            netloc = f"{hostname}:{port}"
        else:
            netloc = hostname

        # Normalize path
        path = parsed.path or ""
        if path:
            # Replace multiple consecutive slashes with single slash
            path = re.sub(r"/+", "/", path)
            # Strip trailing slash for uniform duplicate prevention
            if path.endswith("/"):
                path = path[:-1]

        # Normalize query parameters by sorting keys deterministically
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
