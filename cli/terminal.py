"""
Terminal color management, ANSI sequences, and formatting helpers.
Supports graceful fallback for environments without ANSI color support.
"""

import os
import sys
from typing import Optional


class ColorManager:
    """Manages semantic terminal coloring with automatic environment detection."""

    # ANSI Escape Sequences
    _RESET = "\033[0m"
    _BOLD = "\033[1m"
    _DIM = "\033[2m"
    _RED = "\033[91m"
    _GREEN = "\033[92m"
    _YELLOW = "\033[93m"
    _BLUE = "\033[94m"
    _CYAN = "\033[96m"
    _WHITE = "\033[97m"

    def __init__(self, force_no_color: bool = False):
        self.enabled = self._detect_color_support(force_no_color)
        if self.enabled and sys.platform == "win32":
            # Enable ANSI escape processing in Windows console
            try:
                os.system("")
            except Exception:
                pass

    def _detect_color_support(self, force_no_color: bool) -> bool:
        if force_no_color:
            return False
        if "NO_COLOR" in os.environ:
            return False
        if not hasattr(sys.stdout, "isatty"):
            return False
        return sys.stdout.isatty()

    def red(self, text: str) -> str:
        return f"{self._RED}{text}{self._RESET}" if self.enabled else text

    def green(self, text: str) -> str:
        return f"{self._GREEN}{text}{self._RESET}" if self.enabled else text

    def yellow(self, text: str) -> str:
        return f"{self._YELLOW}{text}{self._RESET}" if self.enabled else text

    def blue(self, text: str) -> str:
        return f"{self._BLUE}{text}{self._RESET}" if self.enabled else text

    def cyan(self, text: str) -> str:
        return f"{self._CYAN}{text}{self._RESET}" if self.enabled else text

    def bold(self, text: str) -> str:
        return f"{self._BOLD}{text}{self._RESET}" if self.enabled else text

    def dim(self, text: str) -> str:
        return f"{self._DIM}{text}{self._RESET}" if self.enabled else text

    def success(self, text: str) -> str:
        return f"{self._BOLD}{self._GREEN}{text}{self._RESET}" if self.enabled else text

    def failure(self, text: str) -> str:
        return f"{self._BOLD}{self._RED}{text}{self._RESET}" if self.enabled else text

    def warning(self, text: str) -> str:
        return f"{self._BOLD}{self._YELLOW}{text}{self._RESET}" if self.enabled else text

    def info(self, text: str) -> str:
        return f"{self._BOLD}{self._CYAN}{text}{self._RESET}" if self.enabled else text


def setup_terminal_encoding():
    """Ensure standard output and error handle UTF-8 smoothly without cp1252 exceptions."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


setup_terminal_encoding()


def truncate(text: str, max_len: int = 60, suffix: str = "...") -> str:
    """Intelligently truncate long strings with a suffix."""
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    cutoff = max_len - len(suffix)
    return text[:cutoff] + suffix


def format_progress_bar(current: int, total: int, width: int = 20) -> str:
    """Generate a clean ASCII progress bar string."""
    if total <= 0:
        return f"[{' ' * width}] 0/0"
    ratio = min(1.0, max(0.0, current / total))
    filled = int(round(ratio * width))
    bar = "=" * filled + "-" * (width - filled)
    percent = int(ratio * 100)
    return f"[{bar}] {current}/{total} ({percent}%)"
