#!/usr/bin/env python
"""
Web Crawler Analytics - Direct CMD / Terminal Entrypoint.

Usage:
    # 1. Direct URL Crawl (interactive or flag-based):
    python main.py --url https://quotes.toscrape.com/ --depth 1 --max-pages 10

    # 2. Minimal / Quiet mode (just crawling, no visualizations or ASCII tables):
    python main.py https://quotes.toscrape.com/ --quiet --max-pages 5

    # 3. Internet Search Crawl (crawl across the web for words or sentences):
    python main.py "Python web crawling tutorial" --max-pages 5 --quiet

    # 4. Export crawl results to CSV or JSON:
    python main.py https://quotes.toscrape.com/ --quiet --output results.csv
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from cli.runner import main

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCrawl interrupted by user.")
        sys.exit(130)
