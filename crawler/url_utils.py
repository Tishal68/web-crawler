"""
URL utility functions for normalization, validation, domain matching,
and filtering.
"""

from urllib.parse import urlparse, urlunparse, urljoin, parse_qsl, urlencode
import posixpath
import re
import ipaddress
import socket
from typing import Optional, Tuple, Any, Union, Dict
import requests

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


# Prohibited private, loopback, and reserved IPv4 networks
PROHIBITED_IPV4_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),        # Current network
    ipaddress.ip_network("10.0.0.0/8"),       # RFC 1918 Private
    ipaddress.ip_network("100.64.0.0/10"),    # RFC 6598 Carrier-grade NAT
    ipaddress.ip_network("127.0.0.0/8"),      # Loopback
    ipaddress.ip_network("169.254.0.0/16"),   # Link-Local & Cloud Metadata
    ipaddress.ip_network("172.16.0.0/12"),    # RFC 1918 Private
    ipaddress.ip_network("192.0.0.0/24"),     # RFC 6890 IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),     # RFC 5737 TEST-NET-1
    ipaddress.ip_network("192.168.0.0/16"),   # RFC 1918 Private
    ipaddress.ip_network("198.18.0.0/15"),    # RFC 2544 Benchmarking
    ipaddress.ip_network("198.51.100.0/24"),  # RFC 5737 TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),   # RFC 5737 TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),      # Multicast
    ipaddress.ip_network("240.0.0.0/4"),      # Reserved
    ipaddress.ip_network("255.255.255.255/32"), # Broadcast
]

# Prohibited IPv6 networks
PROHIBITED_IPV6_NETWORKS = [
    ipaddress.ip_network("::/128"),           # Unspecified
    ipaddress.ip_network("::1/128"),          # Loopback
    ipaddress.ip_network("fc00::/7"),         # Unique Local Address (RFC 4193)
    ipaddress.ip_network("fe80::/10"),        # Link-Local Unicast
    ipaddress.ip_network("ff00::/8"),         # Multicast
    ipaddress.ip_network("2001:db8::/32"),    # Documentation
]

PROHIBITED_HOST_PATTERNS = {
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
    "metadata.google.internal",
    "instance-data",
}

PROHIBITED_DOMAIN_SUFFIXES = (
    ".localhost",
    ".local",
    ".internal",
    ".lan",
    ".arpa",
    ".home",
    ".corp",
)


def is_safe_ip(ip: Union[ipaddress.IPv4Address, ipaddress.IPv6Address]) -> bool:
    """
    Validate that an IP address is a publicly routable target, blocking loopback,
    private RFC 1918, link-local, carrier-grade NAT, cloud metadata, and reserved networks.
    """
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped

    if (
        ip.is_loopback or
        ip.is_private or
        ip.is_link_local or
        ip.is_multicast or
        ip.is_reserved or
        ip.is_unspecified
    ):
        return False

    if isinstance(ip, ipaddress.IPv4Address):
        for net in PROHIBITED_IPV4_NETWORKS:
            if ip in net:
                return False
        # Explicit check for AWS/GCP/Azure link-local cloud metadata (169.254.169.254)
        if str(ip) == "169.254.169.254":
            return False
    elif isinstance(ip, ipaddress.IPv6Address):
        for net in PROHIBITED_IPV6_NETWORKS:
            if ip in net:
                return False
        if str(ip) in ("::1", "fd00:ec2::254"):
            return False

    return True


def is_safe_target_url(url: str, resolve_dns: bool = True) -> Tuple[bool, Optional[str]]:
    """
    SSRF filter: verify that a URL does not target loopback, private networks,
    link-local services, cloud metadata services, or resolve to internal hosts.
    Returns: (is_safe, error_message_if_blocked)
    """
    if not is_valid_url(url):
        return False, "Invalid URL format or unsupported scheme"

    try:
        parsed = urlparse(url)
        raw_host = (parsed.hostname or "").lower().strip()
        if not raw_host:
            return False, "Missing hostname in target URL"

        # Check prohibited host names and domain suffixes
        if raw_host in PROHIBITED_HOST_PATTERNS or any(raw_host.endswith(sfx) for sfx in PROHIBITED_DOMAIN_SUFFIXES):
            return False, f"Prohibited internal host or domain suffix: {raw_host}"

        # Clean IPv6 bracket notation
        clean_host = raw_host.strip("[]")

        # Check if hostname is an IP literal
        try:
            ip_literal = ipaddress.ip_address(clean_host)
            if not is_safe_ip(ip_literal):
                return False, f"Prohibited IP address target: {clean_host} (private, loopback, or metadata)"
            return True, None
        except ValueError:
            pass

        # Check if hostname is an integer representation of an IP (e.g. 2130706433 for 127.0.0.1)
        if clean_host.isdigit():
            try:
                ip_int = ipaddress.ip_address(int(clean_host))
                if not is_safe_ip(ip_int):
                    return False, f"Prohibited integer IP address target: {clean_host}"
                return True, None
            except ValueError:
                pass

        if resolve_dns:
            port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
            try:
                addr_info = socket.getaddrinfo(clean_host, port, proto=socket.IPPROTO_TCP)
                if not addr_info:
                    return False, f"DNS resolution yielded no address records for host {clean_host}"

                for item in addr_info:
                    sockaddr = item[4]
                    ip_str = sockaddr[0]
                    try:
                        resolved_ip = ipaddress.ip_address(ip_str)
                        if not is_safe_ip(resolved_ip):
                            return False, f"Host {clean_host} resolved to prohibited IP {ip_str} (loopback/private/metadata)"
                    except ValueError:
                        return False, f"Host {clean_host} resolved to invalid IP {ip_str}"
            except socket.gaierror as e:
                return False, f"DNS resolution failed for {clean_host}: {e}"
            except Exception as e:
                return False, f"DNS verification failed for {clean_host}: {e}"

        return True, None
    except Exception as e:
        return False, f"URL security validation exception: {e}"


def sanitize_csv_cell(val: Any) -> Any:
    """
    Sanitize values to protect against CSV Formula Injection (DDE injection).
    If a string starts with '=', '+', '-', '@', '\t', or '\r', prefix with a single quote.
    """
    if isinstance(val, str):
        if val and val[0] in ("=", "+", "-", "@", "\t", "\r"):
            return "'" + val
    return val


def sanitize_dataframe_for_csv(df: Any) -> Any:
    """
    Sanitize all string columns of a pandas DataFrame before CSV export
    to neutralize CSV Formula Injection.
    """
    try:
        import pandas as pd
        if not isinstance(df, pd.DataFrame):
            return df
        df_clean = df.copy()
        for col in df_clean.columns:
            if df_clean[col].dtype == object or pd.api.types.is_string_dtype(df_clean[col]):
                df_clean[col] = df_clean[col].apply(sanitize_csv_cell)
        return df_clean
    except Exception:
        return df


class SafeFetchResponse:
    """Safe response wrapper containing verified response data."""
    def __init__(
        self,
        status_code: int,
        text: str,
        content: bytes,
        headers: Dict[str, str],
        url: str,
    ):
        self.status_code = status_code
        self.text = text
        self.content = content
        self.headers = headers
        self.url = url


def safe_http_get(
    url: str,
    session: Optional[requests.Session] = None,
    timeout: float = 8.0,
    max_redirects: int = 5,
    max_bytes: int = 2 * 1024 * 1024,
    headers: Optional[Dict[str, str]] = None,
) -> Tuple[Optional[SafeFetchResponse], Optional[str]]:
    """
    Safely fetch a URL over HTTP/HTTPS with end-to-end SSRF protection:
    - Pre-validates every destination host against private, loopback, and metadata IPs before connecting.
    - Resolves DNS and inspects all returned A/AAAA records.
    - Disables uninspected redirects (allow_redirects=False) and verifies each redirect hop explicitly.
    - Caps redirect depth to prevent redirect loops.
    - Streams response with max_bytes limit (default 2MB) to prevent memory exhaustion (DoS).
    - Preserves TLS certificate validation.

    Returns:
        (SafeFetchResponse, None) on success
        (None, error_message) on failure or security block
    """
    if not is_valid_url(url):
        return None, "Invalid URL format or unsupported scheme"

    req_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if headers:
        req_headers.update(headers)

    client = session or requests.Session()
    current_url = url
    hops = 0

    while True:
        # Pre-connection SSRF inspection with DNS resolution
        is_safe, ssrf_err = is_safe_target_url(current_url, resolve_dns=True)
        if not is_safe:
            return None, f"Security policy blocked target: {ssrf_err}"

        try:
            resp = client.get(
                current_url,
                timeout=timeout,
                headers=req_headers,
                allow_redirects=False,
                stream=True,
                verify=True,
            )
        except requests.exceptions.SSLError as e:
            return None, f"TLS verification failure: {e}"
        except requests.exceptions.Timeout:
            return None, f"Connection timed out after {timeout} seconds"
        except requests.RequestException as e:
            return None, f"Network request failed: {e}"

        # Handle HTTP redirects explicitly
        if resp.is_redirect or resp.status_code in (301, 302, 303, 307, 308):
            hops += 1
            if hops > max_redirects:
                resp.close()
                return None, f"Exceeded maximum redirect limit of {max_redirects} hops"

            location = resp.headers.get("Location")
            resp.close()
            if not location:
                return None, "Redirect response missing Location header"

            next_url = urljoin(current_url, location.strip())
            current_url = next_url
            continue

        # Stream body with byte limit
        try:
            chunks = []
            total_size = 0
            for chunk in resp.iter_content(chunk_size=16384):
                total_size += len(chunk)
                if total_size > max_bytes:
                    resp.close()
                    return None, f"Content exceeded maximum allowed size of {max_bytes} bytes"
                chunks.append(chunk)

            raw_bytes = b"".join(chunks)
            encoding = resp.encoding or "utf-8"
            try:
                text_content = raw_bytes.decode(encoding, errors="replace")
            except (LookupError, TypeError):
                text_content = raw_bytes.decode("utf-8", errors="replace")

            return SafeFetchResponse(
                status_code=resp.status_code,
                text=text_content,
                content=raw_bytes,
                headers=dict(resp.headers),
                url=current_url,
            ), None
        except Exception as e:
            return None, f"Error streaming response body: {e}"
        finally:
            resp.close()

