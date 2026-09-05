"""
CLI runner and orchestrator.
Handles argument parsing, interactive configuration prompts,
live crawl execution, keyboard interruption handling, and file exporting.
"""

import sys
import os
import argparse
import json
import pandas as pd
from typing import Optional, List, Dict, Any

from crawler.models import CrawlConfig, CrawlSessionSummary, PageResult, CrawlFailure
from crawler.crawler import WebCrawler
from crawler.database import CrawlDatabase
from crawler.url_utils import normalize_url, is_valid_url, sanitize_dataframe_for_csv
from .terminal import ColorManager, format_progress_bar
from .formatters import (
    format_header,
    format_config_box,
    format_page_event,
    format_depth_tree,
    format_summary_box,
    format_failed_urls,
    format_results_table,
)


def prompt_url(colors: ColorManager) -> str:
    """Prompt user for target URL with validation and retry."""
    default = "https://en.wikipedia.org/wiki/Web_crawler"
    while True:
        try:
            val = input(f"Enter starting URL [{colors.dim(default)}]: ").strip()
            if not val:
                val = default

            normalized = normalize_url(val)
            if normalized and is_valid_url(normalized):
                return normalized
            print(colors.red("  [!] Invalid URL. Must be a valid HTTP or HTTPS address. Try again."))
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            sys.exit(130)


def prompt_int(prompt: str, default: int, min_val: int, max_val: int, colors: ColorManager) -> int:
    """Prompt user for an integer within specified bounds."""
    while True:
        try:
            val_str = input(f"{prompt} [{colors.dim(str(default))}]: ").strip()
            if not val_str:
                return default
            val = int(val_str)
            if min_val <= val <= max_val:
                return val
            print(colors.red(f"  [!] Value must be between {min_val} and {max_val}. Try again."))
        except ValueError:
            print(colors.red("  [!] Invalid number. Please enter an integer."))
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            sys.exit(130)


def prompt_float(prompt: str, default: float, min_val: float, colors: ColorManager) -> float:
    """Prompt user for a positive float value."""
    while True:
        try:
            val_str = input(f"{prompt} [{colors.dim(str(default))}]: ").strip()
            if not val_str:
                return default
            val = float(val_str)
            if val >= min_val:
                return val
            print(colors.red(f"  [!] Value must be at least {min_val}. Try again."))
        except ValueError:
            print(colors.red("  [!] Invalid decimal number. Please enter a valid float."))
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            sys.exit(130)


def prompt_bool(prompt: str, default: bool, colors: ColorManager) -> bool:
    """Prompt user for a Yes/No boolean with default."""
    def_str = "Y/n" if default else "y/N"
    while True:
        try:
            val = input(f"{prompt} [{colors.dim(def_str)}]: ").strip().lower()
            if not val:
                return default
            if val in ("y", "yes", "1", "true"):
                return True
            if val in ("n", "no", "0", "false"):
                return False
            print(colors.red("  [!] Please enter 'y' for Yes or 'n' for No."))
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            sys.exit(130)


def prompt_output_path(colors: ColorManager) -> Optional[str]:
    """Prompt user for an optional output export filepath."""
    while True:
        try:
            val = input(f"Save results to file? (.csv or .json, Enter to skip) [{colors.dim('None')}]: ").strip()
            if not val:
                return None
            lower = val.lower()
            if lower.endswith(".csv") or lower.endswith(".json"):
                return val
            print(colors.red("  [!] File must have a .csv or .json extension. Try again."))
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            sys.exit(130)


def export_results(
    pages: List[PageResult],
    failures: List[CrawlFailure],
    summary: Optional[CrawlSessionSummary],
    output_path: str,
    colors: ColorManager
) -> bool:
    """Export crawl results to CSV or JSON."""
    try:
        norm_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(norm_path), exist_ok=True) if os.path.dirname(norm_path) else None

        if norm_path.lower().endswith(".csv"):
            if pages:
                df = pd.DataFrame([p.to_dict() for p in pages])
            else:
                df = pd.DataFrame(columns=["URL", "Title", "Depth", "Status", "Links", "Internal", "External", "Response Time (s)", "Domain"])
            df_sanitized = sanitize_dataframe_for_csv(df)
            df_sanitized.to_csv(norm_path, index=False, encoding="utf-8")
        elif norm_path.lower().endswith(".json"):
            data: Dict[str, Any] = {
                "summary": summary.to_dict() if summary else {},
                "pages": [p.__dict__ for p in pages],
                "failures": [f.to_dict() for f in failures],
            }
            with open(norm_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        else:
            print(colors.red(f"[!] Unsupported file extension for export: {output_path}"))
            return False

        print(colors.success(f"[OK] Results successfully saved to: {norm_path}"))
        return True
    except Exception as e:
        print(colors.red(f"[!] Failed to export results to {output_path}: {e}"))
        return False


def build_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="cli.py",
        description="Web Crawler Analytics - Professional Terminal CLI Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--url", type=str, default=None, help="Target starting URL (http/https)")
    parser.add_argument("--depth", type=int, default=2, help="Maximum crawling depth (default: 2)")
    parser.add_argument("--max-pages", type=int, default=50, help="Maximum pages cap (default: 50)")
    parser.add_argument("--timeout", type=float, default=10.0, help="HTTP request timeout in seconds (default: 10.0)")
    parser.add_argument("--delay", type=float, default=0.2, help="Polite delay between requests in seconds (default: 0.2)")
    parser.add_argument("--same-domain", dest="same_domain", action="store_true", default=True, help="Stay on starting domain (default: True)")
    parser.add_argument("--allow-external", dest="same_domain", action="store_false", help="Allow traversing external domains")
    parser.add_argument("--respect-robots", dest="respect_robots", action="store_true", default=True, help="Respect robots.txt policies (default: True)")
    parser.add_argument("--ignore-robots", dest="respect_robots", action="store_false", help="Ignore robots.txt policies")
    parser.add_argument("--output", "-o", type=str, default=None, help="Output results file (.csv or .json)")
    parser.add_argument("--no-color", action="store_true", help="Disable terminal ANSI colors")
    parser.add_argument("--no-tree", action="store_true", help="Omit the crawl traversal tree visualization")
    parser.add_argument("--no-table", action="store_true", help="Omit detailed results table")
    parser.add_argument("--no-db", action="store_true", help="Do not save session to SQLite database")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """CLI execution entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    colors = ColorManager(force_no_color=args.no_color)

    # Print initial header
    print(format_header(colors))
    print()

    # Determine configuration (CLI args vs Interactive Prompts)
    if args.url:
        normalized_url = normalize_url(args.url.strip())
        if not normalized_url or not is_valid_url(normalized_url):
            print(colors.red(f"[!] Error: Invalid starting URL '{args.url}'. Must be valid http/https."))
            return 1
        start_url = normalized_url
        if args.depth < 0:
            print(colors.red(f"[!] Error: Invalid depth {args.depth}. Depth must be >= 0."))
            return 1
        depth = args.depth

        if args.max_pages < 1:
            print(colors.red(f"[!] Error: Invalid max-pages {args.max_pages}. Max pages must be >= 1."))
            return 1
        max_pages = args.max_pages

        if args.timeout <= 0:
            print(colors.red(f"[!] Error: Invalid timeout {args.timeout}. Timeout must be > 0."))
            return 1
        timeout = args.timeout

        if args.delay < 0:
            print(colors.red(f"[!] Error: Invalid delay {args.delay}. Delay must be >= 0."))
            return 1
        delay = args.delay

        if args.output:
            out_lower = args.output.lower()
            if not (out_lower.endswith(".csv") or out_lower.endswith(".json")):
                print(colors.red(f"[!] Error: Invalid output path '{args.output}'. File must have a .csv or .json extension."))
                return 1
        output_path = args.output
        stay_on_domain = args.same_domain
        respect_robots = args.respect_robots
    else:
        # Interactive mode
        print(colors.cyan("Entering Interactive Setup (press Enter for defaults):"))
        start_url = prompt_url(colors)
        depth = prompt_int("Enter maximum crawling depth", default=2, min_val=0, max_val=5, colors=colors)
        max_pages = prompt_int("Enter maximum pages cap", default=50, min_val=1, max_val=500, colors=colors)
        timeout = prompt_float("Enter request timeout in seconds", default=10.0, min_val=0.5, colors=colors)
        delay = prompt_float("Enter polite delay in seconds", default=0.2, min_val=0.0, colors=colors)
        stay_on_domain = prompt_bool("Stay on starting domain?", default=True, colors=colors)
        respect_robots = prompt_bool("Respect robots.txt rules?", default=True, colors=colors)
        output_path = prompt_output_path(colors)
        print()

    config = CrawlConfig(
        start_url=start_url,
        max_depth=depth,
        max_pages=max_pages,
        timeout=timeout,
        request_delay=delay,
        stay_on_domain=stay_on_domain,
        respect_robots=respect_robots,
    )

    # Display configuration overview
    print(format_config_box(config, output_path, colors))
    print()

    crawler = WebCrawler(config=config)
    summary: Optional[CrawlSessionSummary] = None
    interrupted = False

    try:
        # Execute BFS crawl stream
        stream = crawler.crawl_stream(config)
        while True:
            event = next(stream)
            event_text = format_page_event(event, colors)
            if event_text:
                print(event_text)

            # Print progress bar line on fetching / success / skipped
            if event.event_type in ("fetching", "success", "failure", "skipped"):
                p_bar = format_progress_bar(event.pages_crawled, config.max_pages, width=20)
                stats_str = f"Depth: {event.current_depth}/{config.max_depth} | Discovered: {event.discovered_count} | OK: {event.pages_crawled} | Fail: {event.failed_count}"
                print(colors.dim(f"  {p_bar} | {stats_str}"))

    except StopIteration as e:
        summary = e.value
    except KeyboardInterrupt:
        interrupted = True
        print()
        print(colors.warning("Crawl interrupted by user (Ctrl+C). Preparing session summary..."))
        # Construct summary from current state
        summary = CrawlSessionSummary(
            session_id="interrupted_session",
            start_url=start_url,
            max_depth=config.max_depth,
            max_pages=config.max_pages,
            start_time="",
            end_time="",
            elapsed_seconds=0.0,
            pages_crawled=len(crawler.page_results),
            discovered_urls_count=len(crawler.discovered_urls),
            failed_urls_count=len(crawler.failures),
            total_internal_links=sum(p.internal_links_count for p in crawler.page_results),
            total_external_links=sum(p.external_links_count for p in crawler.page_results),
            stay_on_domain=config.stay_on_domain,
            max_depth_reached=max((p.depth for p in crawler.page_results), default=0),
        )

    # 1. Summary Report
    if summary:
        print()
        print(format_summary_box(summary, colors))

    # 2. Failed URLs Report
    if crawler.failures:
        print()
        print(format_failed_urls(crawler.failures, colors))

    # 3. Traversal Tree Visualization
    if not args.no_tree and crawler.page_results:
        print()
        print(format_depth_tree(crawler.page_results, colors))

    # 4. Tabular Results Table
    if not args.no_table and crawler.page_results:
        print()
        print(format_results_table(crawler.page_results, colors))

    # 5. SQLite Persistence
    if not args.no_db and summary and not interrupted:
        try:
            db = CrawlDatabase()
            db.save_session(summary, crawler.page_results, crawler.failures)
            print(colors.dim(f"[INFO] Crawl session archived in SQLite ({db.db_path})"))
        except Exception:
            pass

    # 6. Output Export
    if output_path:
        print()
        export_results(crawler.page_results, crawler.failures, summary, output_path, colors)

    return 130 if interrupted else 0
