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
from crawler.search_discovery import is_search_query
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
    """Prompt user for target URL or words/sentence with validation and retry."""
    default = "https://en.wikipedia.org/wiki/Web_crawler"
    while True:
        try:
            val = input(f"Enter starting URL or search words/sentence [{colors.dim(default)}]: ").strip()
            if not val:
                return default

            if is_search_query(val):
                return val

            norm = val
            if "://" not in norm:
                norm = "https://" + norm
            normalized = normalize_url(norm)
            if normalized and is_valid_url(normalized):
                return normalized
            print(colors.red("  [!] Invalid URL or search query. Must be a valid HTTP/HTTPS address or words/sentence."))
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
    parser.add_argument("target", nargs="?", default=None, help="Target starting URL (http/https) or search words/sentence")
    parser.add_argument("--url", "-u", type=str, default=None, help="Target starting URL (http/https)")
    parser.add_argument("--query", "-s", type=str, default=None, help="Words, phrase, or sentence to search and crawl across internet")
    parser.add_argument("--keyword", "-k", type=str, default=None, help="Target word/phrase filter for sentence mining")
    parser.add_argument("--depth", "-d", type=int, default=2, help="Maximum crawling depth (default: 2)")
    parser.add_argument("--max-pages", "-m", type=int, default=50, help="Maximum pages cap (default: 50)")
    parser.add_argument("--timeout", "-t", type=float, default=10.0, help="HTTP request timeout in seconds (default: 10.0)")
    parser.add_argument("--delay", type=float, default=0.2, help="Polite delay between requests in seconds (default: 0.2)")
    parser.add_argument("--same-domain", dest="same_domain", action="store_true", default=True, help="Stay on starting domain (default: True)")
    parser.add_argument("--allow-external", dest="same_domain", action="store_false", help="Allow traversing external domains")
    parser.add_argument("--respect-robots", dest="respect_robots", action="store_true", default=True, help="Respect robots.txt policies (default: True)")
    parser.add_argument("--ignore-robots", dest="respect_robots", action="store_false", help="Ignore robots.txt policies")
    parser.add_argument("--answer", "-a", dest="answer_mode", action="store_true", help="Execute web search, evidence extraction, and grounded answer retrieval")
    parser.add_argument("--output", "-o", type=str, default=None, help="Output results file (.csv or .json)")
    parser.add_argument("--quiet", "-q", "--minimal", dest="quiet", action="store_true", help="Minimal mode: just crawl without visualizations, tree, or tables")
    parser.add_argument("--json", action="store_true", help="Output results JSON to stdout")
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

    raw_target = args.query or args.url or args.target
    search_query = None

    # Web Search & Grounded Answer retrieval mode
    if args.answer_mode:
        q_target = raw_target or prompt_url(colors)
        q_clean = q_target.strip()
        from search.pipeline import SearchPipeline
        pipeline = SearchPipeline()
        if not args.quiet and not args.json:
            print(colors.cyan(f"\n🔎 Researching: \"{q_clean}\" across the public web..."))
        res = pipeline.run(query=q_clean, num_sources=min(12, max(4, args.max_pages)))
        ans = res.answer
        conf = res.confidence
        if args.json:
            print(json.dumps(res.to_dict(), indent=2))
            return 0
        if ans and conf:
            print(colors.green(f"\n{conf.badge_label} (Confidence Score: {conf.score:.2f} / 1.00)"))
            print(colors.dim(f"Synthesized across {len(res.ranked_results)} sources and {conf.independent_sources_count} independent domain(s).\n"))
            print(colors.bold("🎯 DIRECT ANSWER:"))
            print(ans.direct_answer + "\n")
            if res.verification.get("contradictions"):
                print(colors.red("⚠️ SOURCE DISAGREEMENTS DETECTED:"))
                for c in res.verification["contradictions"]:
                    print(colors.yellow(f"  - {c.topic_or_entity}: {c.source_a_domain} vs {c.source_b_domain}"))
                    print(colors.dim(f"    {c.explanation}\n"))
            if ans.key_findings:
                print(colors.cyan("🔍 KEY FINDINGS & EVIDENCE:"))
                for f in ans.key_findings:
                    print(f"  • {f}")
                print()
            if ans.citations:
                print(colors.bold("📚 VERIFIED SOURCES:"))
                for c in ans.citations:
                    d_str = f" ({c.published_date})" if c.published_date else ""
                    print(f"  [{c.index}] {c.title} - {c.url}")
                    print(colors.dim(f"      {c.domain} · {c.source_type}{d_str}"))
                print()
            if ans.caveats:
                print(colors.dim("ℹ️ GROUNDING NOTES:"))
                for cav in ans.caveats:
                    print(colors.dim(f"  * {cav}"))
                print()
        return 0

    # Determine configuration (CLI args vs Interactive Prompts)
    if raw_target:
        raw_clean = raw_target.strip()
        is_query = bool(args.query) or is_search_query(raw_clean)

        if is_query:
            start_url = raw_clean
            search_query = raw_clean
            # By default allow traversing across discovered internet domains unless explicit same_domain
            stay_on_domain = False if "--same-domain" not in (argv or sys.argv) else args.same_domain
        else:
            norm_target = raw_clean
            if "://" not in norm_target:
                norm_target = "https://" + norm_target
            normalized_url = normalize_url(norm_target)
            if not normalized_url or not is_valid_url(normalized_url):
                print(colors.red(f"[!] Error: Invalid starting URL '{raw_target}'. Must be valid http/https."))
                return 1
            start_url = normalized_url
            stay_on_domain = args.same_domain

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
        respect_robots = args.respect_robots
    else:
        # Interactive mode
        if not args.quiet and not args.json:
            print(colors.cyan("Entering Interactive Setup (press Enter for defaults):"))
        start_raw = prompt_url(colors)
        if is_search_query(start_raw):
            start_url = start_raw
            search_query = start_raw
            default_same_domain = False
        else:
            start_url = start_raw
            default_same_domain = True

        depth = prompt_int("Enter maximum crawling depth", default=2, min_val=0, max_val=5, colors=colors)
        max_pages = prompt_int("Enter maximum pages cap", default=50, min_val=1, max_val=500, colors=colors)
        timeout = prompt_float("Enter request timeout in seconds", default=10.0, min_val=0.5, colors=colors)
        delay = prompt_float("Enter polite delay in seconds", default=0.2, min_val=0.0, colors=colors)
        stay_on_domain = prompt_bool("Stay on starting domain?", default=default_same_domain, colors=colors)
        respect_robots = prompt_bool("Respect robots.txt rules?", default=True, colors=colors)
        output_path = prompt_output_path(colors)
        if not args.quiet and not args.json:
            print()

    config = CrawlConfig(
        start_url=start_url,
        max_depth=depth,
        max_pages=max_pages,
        timeout=timeout,
        request_delay=delay,
        stay_on_domain=stay_on_domain,
        respect_robots=respect_robots,
        search_query=search_query,
        keyword_filter=args.keyword,
    )

    if not args.quiet and not args.json:
        # Print initial header & config box
        print(format_header(colors))
        print()
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

            # In quiet / minimal mode: print clean minimal lines without ASCII boxes
            if args.quiet and not args.json:
                if event.event_type == "searching":
                    print(colors.magenta(f"🔍 [SEARCH] Resolving seed targets across internet for: '{event.current_url}'..."), flush=True)
                elif event.event_type == "success" and event.page_result:
                    p = event.page_result
                    w_info = f", words: {p.word_count}" if p.word_count else ""
                    m_info = f", matches: {p.match_count}" if p.match_count > 0 else ""
                    print(f"[{p.status_code}] D{p.depth} {p.url} (links: {p.unique_links}{w_info}{m_info})", flush=True)
                elif event.event_type in ("failure", "skipped") and event.failure:
                    f = event.failure
                    lbl = colors.red("[FAIL]") if event.event_type == "failure" else colors.yellow("[SKIP]")
                    print(f"{lbl} D{f.depth} {f.url} ({f.error_type}: {f.error_message})", flush=True)
            elif not args.json:
                event_text = format_page_event(event, colors)
                if event_text:
                    print(event_text, flush=True)

                # Print progress bar line on fetching / success / skipped
                if event.event_type in ("fetching", "success", "failure", "skipped"):
                    p_bar = format_progress_bar(event.pages_crawled, config.max_pages, width=20)
                    stats_str = f"Depth: {event.current_depth}/{config.max_depth} | Discovered: {event.discovered_count} | OK: {event.pages_crawled} | Fail: {event.failed_count}"
                    print(colors.dim(f"  {p_bar} | {stats_str}"), flush=True)

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
            search_query=search_query,
        )

    # Output presentation based on mode
    if args.json:
        data: Dict[str, Any] = {
            "summary": summary.to_dict() if summary else {},
            "pages": [p.to_dict() for p in crawler.page_results],
            "failures": [f.to_dict() for f in crawler.failures],
        }
        print(json.dumps(data, indent=2))
    elif args.quiet:
        if summary:
            print(colors.green(f"\n[DONE] Finished in {summary.elapsed_seconds:.2f}s: {summary.pages_crawled} pages crawled, {summary.discovered_urls_count} discovered, {summary.failed_urls_count} failed."))
    else:
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
            if not args.quiet and not args.json:
                print(colors.dim(f"[INFO] Crawl session archived in SQLite ({db.db_path})"))
        except Exception:
            pass

    # 6. Output Export
    if output_path:
        if not args.quiet and not args.json:
            print()
        export_results(crawler.page_results, crawler.failures, summary, output_path, colors)

    return 130 if interrupted else 0
