#!/usr/bin/env python
"""
Web Crawler Analytics - Command Line Interface (CLI) Entrypoint.
Usage:
    py scripts/cli.py
    py scripts/cli.py --url https://example.com --depth 2 --max-pages 50
"""

import sys
import os

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from cli.runner import main

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCrawl interrupted by user.")
        sys.exit(130)
