"""
Formatting templates and display renderers for the terminal CLI interface.
"""

import sys
from typing import List, Optional
from collections import defaultdict

from crawler.models import (
    CrawlConfig,
    PageResult,
    CrawlFailure,
    CrawlProgressEvent,
    CrawlSessionSummary,
)
from .terminal import ColorManager, truncate


DIVIDER_WIDTH = 64


def format_header(colors: ColorManager) -> str:
    """Return the professional CLI header banner."""
    lines = [
        "=" * DIVIDER_WIDTH,
        colors.bold("WEB CRAWLER ENGINE v1.0"),
        colors.dim("Academic Web Mining & Analytics Terminal Utility"),
        "=" * DIVIDER_WIDTH,
    ]
    return "\n".join(lines)


def format_config_box(
    config: CrawlConfig,
    output_path: Optional[str],
    colors: ColorManager
) -> str:
    """Format the crawl configuration block."""
    domain_status = "ENABLED (Stay on domain)" if config.stay_on_domain else "DISABLED (Cross-domain allowed)"
    robots_status = "ENABLED (Honor rules)" if config.respect_robots else "DISABLED (Ignore robots.txt)"
    out_display = output_path if output_path else "None (Terminal display only)"

    lines = [
        colors.cyan("[CONFIGURATION]"),
        f"  Target URL     : {colors.bold(config.start_url)}",
        f"  Maximum Depth  : {config.max_depth}",
        f"  Maximum Pages  : {config.max_pages}",
        f"  Timeout        : {config.timeout}s",
        f"  Request Delay  : {config.request_delay}s",
        f"  Domain Scope   : {domain_status}",
        f"  Robots.txt     : {robots_status}",
        f"  Output File    : {out_display}",
        "=" * DIVIDER_WIDTH,
        colors.green("CRAWL STARTED"),
        "-" * DIVIDER_WIDTH,
    ]
    return "\n".join(lines)


def format_page_event(event: CrawlProgressEvent, colors: ColorManager) -> Optional[str]:
    """Format live page event for terminal display."""
    if event.event_type == "success" and event.page_result:
        p = event.page_result
        tag = colors.green("[OK]")
        title_disp = truncate(p.title, 40)
        url_disp = truncate(p.url, 60)
        lines = [
            f"[DEPTH {p.depth}] {tag} {colors.bold(url_disp)}",
            f"  Title: {title_disp} | Status: {p.status_code} | Links: {p.unique_links} (Int: {p.internal_links_count}, Ext: {p.external_links_count}) | Latency: {p.response_time:.3f}s",
        ]
        return "\n".join(lines)

    elif event.event_type == "failure" and event.failure:
        f = event.failure
        tag = colors.red("[FAIL]")
        url_disp = truncate(f.url, 60)
        lines = [
            f"[DEPTH {f.depth}] {tag} {colors.bold(url_disp)}",
            f"  Error: {colors.red(f.error_type)} - {f.error_message}",
        ]
        return "\n".join(lines)

    elif event.event_type == "skipped" and event.failure:
        f = event.failure
        tag = colors.yellow("[SKIP]")
        url_disp = truncate(f.url, 60)
        lines = [
            f"[DEPTH {f.depth}] {tag} {colors.bold(url_disp)}",
            f"  Reason: {colors.yellow(f.error_type)} - {f.error_message}",
        ]
        return "\n".join(lines)

    return None


def format_depth_tree(pages: List[PageResult], colors: ColorManager) -> str:
    """
    Format a clean tree visualization of crawled pages grouped by depth level.
    """
    if not pages:
        return ""

    depth_groups = defaultdict(list)
    for p in pages:
        depth_groups[p.depth].append(p)

    lines = [
        "=" * DIVIDER_WIDTH,
        colors.cyan("CRAWL TRAVERSAL TREE"),
        "=" * DIVIDER_WIDTH,
    ]

    # Check whether stdout supports unicode tree connectors
    branch_conn = "|-- "
    last_conn = "\\-- "
    try:
        "└── ".encode(sys.stdout.encoding or "utf-8")
        branch_conn = "├── "
        last_conn = "└── "
    except Exception:
        pass

    sorted_depths = sorted(depth_groups.keys())
    for d in sorted_depths:
        lines.append(colors.bold(f"DEPTH {d}"))
        group = depth_groups[d]
        for i, page in enumerate(group):
            is_last = (i == len(group) - 1)
            connector = last_conn if is_last else branch_conn
            title_part = f" ({truncate(page.title, 35)})" if page.title and page.title != "Untitled Page" else ""
            lines.append(f"{connector}{page.url}{colors.dim(title_part)}")
        lines.append("")

    return "\n".join(lines).rstrip()


def format_summary_box(summary: CrawlSessionSummary, colors: ColorManager) -> str:
    """Format final crawl summary report."""
    status_str = colors.green("SUCCESS") if summary.pages_crawled > 0 else colors.red("NO PAGES CRAWLED")
    
    lines = [
        "=" * DIVIDER_WIDTH,
        colors.bold("CRAWL COMPLETE"),
        "=" * DIVIDER_WIDTH,
        f"  Target URL             : {colors.bold(summary.start_url)}",
        f"  Maximum Depth Config   : {summary.max_depth}",
        f"  Max Depth Reached      : {summary.max_depth_reached}",
        f"  Pages Crawled          : {colors.bold(str(summary.pages_crawled))} / {summary.max_pages}",
        f"  Unique URLs Discovered : {summary.discovered_urls_count}",
        f"  Failed URLs            : {colors.red(str(summary.failed_urls_count)) if summary.failed_urls_count > 0 else '0'}",
        f"  Total Internal Links   : {summary.total_internal_links}",
        f"  Total External Links   : {summary.total_external_links}",
        f"  Total Crawl Time       : {summary.elapsed_seconds:.2f}s",
        f"  Status                 : {status_str}",
        "=" * DIVIDER_WIDTH,
    ]
    return "\n".join(lines)


def format_failed_urls(failures: List[CrawlFailure], colors: ColorManager) -> str:
    """Format failed URL error report."""
    if not failures:
        return ""

    lines = [
        colors.red(f"FAILED URLS ({len(failures)})"),
        "-" * DIVIDER_WIDTH,
    ]
    for f in failures:
        lines.append(f"[{colors.red(f.error_type)}] {f.url}")
        lines.append(f"  Reason: {f.error_message}")

    lines.append("-" * DIVIDER_WIDTH)
    return "\n".join(lines)


def format_results_table(pages: List[PageResult], colors: ColorManager) -> str:
    """
    Format tabular summary of crawled pages suitable for standard 80-120 column terminals.
    """
    if not pages:
        return ""

    lines = [
        "=" * DIVIDER_WIDTH,
        colors.cyan("DETAILED RESULTS TABLE"),
        "=" * DIVIDER_WIDTH,
    ]

    header = f"{'Depth':<6} | {'Status':<6} | {'Title':<25} | {'URL':<32} | {'Links':<5} | {'Int':<4} | {'Ext':<4} | {'Latency'}"
    sep = "-" * len(header)
    lines.append(colors.bold(header))
    lines.append(sep)

    for p in pages:
        t_title = truncate(p.title, 25)
        t_url = truncate(p.url, 32)
        row = (
            f"{p.depth:<6} | {p.status_code:<6} | {t_title:<25} | {t_url:<32} | "
            f"{p.unique_links:<5} | {p.internal_links_count:<4} | {p.external_links_count:<4} | {p.response_time:.3f}s"
        )
        lines.append(row)

    lines.append(sep)
    return "\n".join(lines)
