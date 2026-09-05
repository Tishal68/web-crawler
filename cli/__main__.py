#!/usr/bin/env python
"""
Web Crawler Analytics - Module execution entrypoint (python -m cli).
"""

import sys
import os

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
