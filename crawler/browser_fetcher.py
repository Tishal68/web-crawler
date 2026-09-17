"""
Headless browser rendering manager using Playwright.
Enables full client-side JavaScript execution for Single Page Applications (SPAs),
React/Vue/Angular web apps, and dynamic platforms like Hotstar, Netflix, and X/Twitter.
"""

from __future__ import annotations

import logging
import time
from typing import Optional, Tuple, Any

from crawler.url_utils import is_safe_target_url

logger = logging.getLogger(__name__)

# Playwright availability detection
_PLAYWRIGHT_INSTALLED = False
try:
    from playwright.sync_api import sync_playwright, Playwright, Browser, BrowserContext, TimeoutError as PlaywrightTimeoutError
    _PLAYWRIGHT_INSTALLED = True
except (ImportError, Exception):
    _PLAYWRIGHT_INSTALLED = False
    PlaywrightTimeoutError = Exception


_AVAILABLE_CACHE: Optional[bool] = None


def _has_installed_chromium() -> bool:
    """Fast check for installed Chromium or system browser without starting Playwright driver."""
    import os
    import glob

    candidates = []
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        candidates.append(os.path.join(local_app_data, "ms-playwright", "chromium*", "**", "chrome.exe"))

    user_home = os.path.expanduser("~")
    candidates.append(os.path.join(user_home, "Library", "Caches", "ms-playwright", "chromium*", "**", "chrome"))
    candidates.append(os.path.join(user_home, ".cache", "ms-playwright", "chromium*", "**", "chrome"))

    for pattern in candidates:
        try:
            matches = glob.glob(pattern, recursive=True)
            if any(os.path.isfile(m) for m in matches):
                return True
        except Exception:
            pass

    system_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]
    for p in system_paths:
        try:
            if os.path.isfile(p):
                return True
        except Exception:
            pass

    return False


class PlaywrightBrowserManager:
    """
    Manages a persistent headless Chromium browser instance across a crawl session.
    Reuses browser and context to maintain high traversal performance while
    rendering client-side JavaScript and dynamically populated DOMs.
    """

    def __init__(
        self,
        headless: bool = True,
        user_agent: Optional[str] = None,
        default_wait_time: float = 2.0,
    ):
        self.headless = headless
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 WebCrawlerAnalytics/1.0"
        )
        self.default_wait_time = default_wait_time
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._is_active: bool = False

    @classmethod
    def is_available(cls, force_refresh: bool = False) -> bool:
        """Verify if Playwright library and a usable browser engine are installed."""
        global _AVAILABLE_CACHE
        if not force_refresh and _AVAILABLE_CACHE is not None:
            return _AVAILABLE_CACHE

        if not _PLAYWRIGHT_INSTALLED:
            _AVAILABLE_CACHE = False
            return False

        if _has_installed_chromium():
            _AVAILABLE_CACHE = True
            return True

        try:
            with sync_playwright() as p:
                _AVAILABLE_CACHE = p.chromium.executable_path is not None
                return _AVAILABLE_CACHE
        except Exception:
            _AVAILABLE_CACHE = False
            return False

    @classmethod
    def reset_availability_cache(cls) -> None:
        """Reset cached availability state (useful for unit testing)."""
        global _AVAILABLE_CACHE
        _AVAILABLE_CACHE = None

    def start(self) -> bool:
        """
        Initialize the Playwright process and launch the headless Chromium instance.
        Returns True if successful, False otherwise.
        """
        if self._is_active and self._context is not None:
            return True

        if not _PLAYWRIGHT_INSTALLED:
            logger.warning("Playwright is not installed in the current Python environment.")
            return False

        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                ],
            )
            self._context = self._browser.new_context(
                user_agent=self.user_agent,
                viewport={"width": 1280, "height": 800},
                java_script_enabled=True,
                ignore_https_errors=False,
            )
            self._is_active = True
            logger.info("Playwright headless Chromium browser initialized successfully.")
            return True
        except Exception as e:
            logger.error("Failed to start Playwright browser: %s", e)
            self.close()
            return False

    def fetch_page(
        self,
        url: str,
        timeout: float = 20.0,
        wait_seconds: Optional[float] = None,
    ) -> Tuple[Optional[str], int, float, Optional[str], Optional[str], str]:
        """
        Navigate to a webpage using headless Chromium, execute JavaScript,
        and retrieve the fully hydrated DOM content.

        Returns:
            (rendered_html, status_code, elapsed_time, error_type, error_message, final_url)
        """
        start_time = time.perf_counter()

        # Pre-navigation SSRF Security Check
        is_safe, ssrf_err = is_safe_target_url(url, resolve_dns=True)
        if not is_safe:
            elapsed = time.perf_counter() - start_time
            return None, 0, elapsed, "SSRF Blocked", f"URL prohibited by security policy: {ssrf_err}", url

        # Ensure browser is started
        if not self._is_active or self._context is None:
            if not self.start():
                elapsed = time.perf_counter() - start_time
                return None, 0, elapsed, "Browser Error", "Headless browser failed to initialize or Playwright is not installed.", url

        page = None
        wait_time = self.default_wait_time if wait_seconds is None else wait_seconds
        timeout_ms = max(5000, int(timeout * 1000))

        try:
            page = self._context.new_page()

            # Navigate and wait for DOM content loaded
            response = page.goto(
                url,
                timeout=timeout_ms,
                wait_until="domcontentloaded",
            )

            # Allow client-side frameworks (React/Vue/Angular) to mount and hydrate
            if wait_time > 0:
                page.wait_for_timeout(int(wait_time * 1000))

            final_url = page.url or url
            status_code = response.status if response is not None else 200

            # Pre-navigation SSRF Check on final redirected URL
            if final_url != url:
                is_safe_redirect, redirect_err = is_safe_target_url(final_url, resolve_dns=True)
                if not is_safe_redirect:
                    elapsed = time.perf_counter() - start_time
                    return None, status_code, elapsed, "SSRF Blocked", f"Redirect to {final_url} prohibited by security policy: {redirect_err}", final_url

            rendered_html = page.content()
            elapsed = time.perf_counter() - start_time

            return rendered_html, status_code, elapsed, None, None, final_url

        except PlaywrightTimeoutError as e:
            elapsed = time.perf_counter() - start_time
            return None, 0, elapsed, "Read Timeout", f"Browser navigation timed out after {timeout}s: {e}", url
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            err_name = type(e).__name__
            return None, 0, elapsed, f"Browser {err_name}", f"Navigation failed: {e}", url
        finally:
            if page is not None:
                try:
                    page.close()
                except Exception:
                    pass

    def close(self) -> None:
        """Safely terminate context, browser instance, and Playwright process."""
        if self._context is not None:
            try:
                self._context.close()
            except Exception:
                pass
            self._context = None

        if self._browser is not None:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None

        if self._playwright is not None:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
            try:
                time.sleep(0.08)
            except Exception:
                pass

        self._is_active = False
        logger.info("Playwright browser instance closed cleanly.")

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass
