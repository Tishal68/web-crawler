# Web Crawler Analytics Web Application

A modern, production-grade **Web Crawler Analytics & Mining Application** built in Python with **Streamlit**, designed for academic Web Mining, Machine Learning, and Information Retrieval contexts.

The application allows users to supply a seed URL and maximum depth, initiates a Breadth-First Search (BFS) crawl, extracts hyperlinks, avoids redundant and circular visits, tolerates HTTP and network failures gracefully, persists crawl history to SQLite, and provides an interactive visual dashboard with Plotly charts and network graph analysis.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Key Features](#key-features)
3. [Technologies Used](#technologies-used)
4. [Project Architecture](#project-architecture)
5. [Installation & Setup](#installation--setup)
6. [Running the Application](#running-the-application)
7. [Deploying to Streamlit Community Cloud](#deploying-to-streamlit-community-cloud)
8. [How Crawling Depth Works](#how-crawling-depth-works)
9. [How Duplicate URLs Are Prevented](#how-duplicate-urls-are-prevented)
10. [Error Handling & Fault Tolerance](#error-handling--fault-tolerance)
11. [Database Schema (SQLite)](#database-schema-sqlite)
12. [Running Tests](#running-tests)
13. [Ethical & Responsible Web Crawling](#ethical--responsible-web-crawling)
14. [Limitations & Future Enhancements](#limitations--future-enhancements)

---

## Project Overview

In web mining and search engine architecture, web crawlers are fundamental for discovery, indexing, and link analysis. This project satisfies all core academic requirements while offering a clean, modern user experience:
- **Seed Input**: User-provided starting URL.
- **Configurable Traversal**: User-specified crawling depth (0 to 5) and page cap.
- **Graph Traversal**: Strict Queue-based Breadth-First Search (BFS).
- **Data Mining Metrics**: Page title extraction, status codes, total hyperlinks, unique internal vs. external links, latency, and content-type detection.
- **Resilience**: Complete immunity to broken links, 4xx/5xx HTTP codes, timeouts, and non-HTML assets.
- **Interactive UI**: Live streaming status updates without screen flickering, Plotly analytics, deep-dive link inspector, CSV/JSON data export, and SQLite crawl history.

---

## Key Features

- **Queue-Based BFS Traversal Engine**: Decoupled, modular Python engine (`WebCrawler`) with generator streaming for responsive live feedback.
- **Hyperlink Classification**: Automatically distinguishes between *Internal* links (belonging to the target domain or its subdomains) and *External* links (cross-domain outbound links).
- **URL Normalization**: Canonicalizes URLs by stripping URL fragments (`#section`), normalizing default ports, handling casing, and sorting query strings.
- **Duplicate & Cycle Prevention**: High-performance set hashing to guarantee no webpage is crawled more than once, preventing infinite loops.
- **Polite Crawling Protections**: Built-in support for `robots.txt` parsing, configurable request delays, timeouts, and non-HTML / binary asset skipping (`.pdf`, `.png`, `.zip`, etc.).
- **Domain Guardrails**: Optional "Stay on starting domain" toggle to keep the crawl bounded to the target host.
- **Interactive Plotly Visualizations**:
  - Pages crawled by depth level (bar chart)
  - Success vs. Failure ratio (donut chart)
  - Internal vs. External link distribution (pie chart)
  - Top discovered outbound domains (horizontal ranking)
  - Response time performance scatter plot
  - 2D BFS Crawl Traversal Network Graph (interactive node-link diagram via NetworkX + Plotly)
- **Deep-Dive URL Explorer**: Inspect any crawled URL to view its exact metadata and full lists of discovered internal and external hyperlinks.
- **Data Export**: One-click downloads for crawled pages (CSV), failed URLs (CSV), full session JSON (including hyperlink arrays), and session summary reports.
- **SQLite Crawl History**: Automatically archives past crawl sessions so users can reload historical results into the dashboard or review historical stats.

---

## Technologies Used

| Technology | Purpose |
| :--- | :--- |
| **Python 3.10+** | Core programming language |
| **Streamlit** | Web application framework & reactive dashboard UI |
| **Requests** | HTTP client for network retrieval with timeouts & header control |
| **BeautifulSoup4** | HTML DOM parsing, title extraction, and hyperlink discovery |
| **Pandas** | Tabular data representation, filtering, and CSV export |
| **Plotly** | High-performance interactive charts and graph visualizations |
| **NetworkX** | Graph structure modeling and spring layout coordinate computation |
| **SQLite3** | Zero-configuration relational database for session persistence |
| **Pytest** | Automated unit and integration testing suite |

---

## Project Architecture

The project adheres to a strict separation of concerns, providing **two independent interfaces** (Interactive Streamlit Web Dashboard and Professional Terminal CLI) over the same decoupled, reusable crawler engine:

```
┌──────────────────────────────────────────────────┐
│                WebCrawler Engine                 │
│      (crawler/crawler.py & crawler/models.py)    │
└────────────────────────┬─────────────────────────┘
                         │
           ┌─────────────┴─────────────┐
           ▼                           ▼
┌──────────────────────┐    ┌──────────────────────┐
│  Streamlit Dashboard │    │ Terminal CLI Utility │
│   (app.py & ui/)     │    │  (scripts/cli.py)    │
└──────────────────────┘    └──────────────────────┘
```

```
web_crawler/
│
├── app.py                     # Streamlit web application & analytics dashboard
├── requirements.txt           # Project dependencies
├── README.md                  # Comprehensive documentation
├── .gitignore                 # Standard Python/SQLite/Streamlit ignore rules
│
├── crawler/                   # Standalone, UI-agnostic Crawler Engine
│   ├── __init__.py            # Clean public API exports
│   ├── models.py              # Strongly-typed Dataclasses (PageResult, CrawlFailure, etc.)
│   ├── url_utils.py           # URL normalization, domain matching, fragment stripping
│   ├── parser.py              # BeautifulSoup HTML parsing & link classification
│   ├── robots.py              # robots.txt parser & domain cache manager
│   ├── crawler.py             # BFS WebCrawler with event generator & error resilience
│   └── database.py            # SQLite session and page storage repository
│
├── cli/                       # Terminal CLI Presentation Layer
│   ├── __init__.py            # CLI package exports
│   ├── terminal.py            # Color management (ANSI with safe fallback) & progress bar
│   ├── formatters.py          # Summary boxes, depth traversal tree, results tables
│   └── runner.py              # Interactive prompts, argument parser & crawl executor
│
├── ui/                        # Streamlit Presentation Layer
│   ├── __init__.py
│   ├── components.py          # Custom CSS, KPI cards, banners, status badges
│   ├── charts.py              # Plotly visualizers (depth, ratios, domains, network graph)
│   └── dashboard.py           # Dashboard sections (results table, explorer, history, failures)
│
├── scripts/                   # CLI Entrypoints & Automated Verifiers
│   ├── cli.py                 # Direct CLI launcher (py scripts/cli.py)
│   └── verify_real_crawling.py# End-to-end live crawler test script
│
├── data/                      # Local data directory
│   └── crawler.db             # Auto-generated SQLite database
│
└── tests/                     # Automated Test Suite (39 unit & integration tests)
    ├── __init__.py
    ├── test_url_utils.py      # Normalization, fragments, schemes, domain logic
    ├── test_parser.py         # Title parsing, link classification, deduplication
    ├── test_crawler.py        # Depth 0/1/2 tests, duplicates, 404/500/timeout mocks
    └── test_cli.py            # CLI parser, prompts, exports, and mock execution
```

---

## Installation & Setup

### 1. Prerequisites
Ensure Python 3.10, 3.11, or 3.12 is installed on your system.

### 2. Navigate to Project Directory
```bash
cd web_crawler
```

### 3. (Optional) Create and Activate Virtual Environment
```bash
# Windows
py -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## Running the Application

The project offers **two complementary ways** to operate the crawler:

### Interface 1: Streamlit Web Dashboard (GUI Mode)

Launch the interactive web analytics dashboard with:

```bash
streamlit run app.py
```
*(On Windows systems, you can also run `py -m streamlit run app.py`)*

Open your browser to **`http://localhost:8501`** to explore:
- Real-time animated progress bars and live activity logs.
- Interactive Plotly visualizations (depth bar chart, success/failure donut, link distribution pie, top domains, response time scatter).
- 2D BFS Crawl Traversal Network Graph (interactive node-link diagram).
- Deep-dive URL explorer with internal and external link breakdowns.
- Searchable, sortable results table with one-click CSV and JSON downloads.
- Historical crawl sessions browser powered by SQLite.

---

### Interface 2: Professional Terminal CLI (CMD Mode)

The CLI provides a fast, developer-friendly terminal utility designed like an industrial networking tool.

#### Interactive Mode (Guided Setup)
Simply run without arguments:
```bash
py scripts/cli.py
```
*(or `python scripts/cli.py`)*

The tool will interactively prompt for parameters with sensible defaults (press `Enter` to accept defaults):
- `Enter starting URL [https://en.wikipedia.org/wiki/Web_crawler]:`
- `Enter maximum crawling depth [2]:`
- `Enter maximum pages cap [50]:`
- `Enter request timeout in seconds [10.0]:`
- `Enter polite delay in seconds [0.2]:`
- `Stay on starting domain? [Y/n]:`
- `Respect robots.txt rules? [Y/n]:`
- `Save results to file? (.csv or .json, Enter to skip):`

#### Direct Command-Line Arguments Mode
Pass flags directly for scripted or automated runs:

```bash
# Basic Depth-1 Crawl with CSV Export
py scripts/cli.py --url https://example.com --depth 1 --max-pages 20 --output results.csv

# Depth-2 Crawl with JSON Export
py scripts/cli.py --url https://example.com --depth 2 --max-pages 50 --output results.json

# Fast Polling with Custom Timeout and Delay
py scripts/cli.py --url https://example.com --depth 1 --timeout 5.0 --delay 0.1

# Plain Text Mode (without ANSI colors)
py scripts/cli.py --url https://example.com --depth 1 --no-color
```

#### Supported CLI Arguments

| Argument | Type | Default | Description |
| :--- | :---: | :---: | :--- |
| `--url` | String | `None` | Seed starting URL (triggers non-interactive mode when provided) |
| `--depth` | Int | `2` | Maximum crawling depth ($0 \le \text{depth} \le 5$) |
| `--max-pages` | Int | `50` | Maximum pages safety cap |
| `--timeout` | Float | `10.0` | Request timeout in seconds |
| `--delay` | Float | `0.2` | Polite delay between requests in seconds |
| `--same-domain` | Flag | `True` | Restrict crawling strictly to starting domain |
| `--allow-external` | Flag | `False` | Allow crawling discovered cross-domain URLs |
| `--respect-robots` | Flag | `True` | Honor host `robots.txt` exclusion rules |
| `--ignore-robots` | Flag | `False` | Ignore `robots.txt` rules |
| `--output`, `-o` | String | `None` | Path to export file (`.csv` or `.json`) |
| `--no-color` | Flag | `False` | Disable ANSI terminal coloring |
| `--no-tree` | Flag | `False` | Omit the hierarchical traversal tree visualization |
| `--no-table` | Flag | `False` | Omit the detailed ASCII results table |
| `--no-db` | Flag | `False` | Do not persist session to SQLite database |

---

## Deploying to Streamlit Community Cloud

This project is fully configured for continuous 1-click deployment on [Streamlit Community Cloud](https://share.streamlit.io/) with automatic GitHub synchronization.

### Step 1: Push Repository to GitHub

1. Ensure Git is initialized in the `web_crawler` directory:
   ```bash
   # Initialize repository on main branch
   git init -b main

   # Stage all configured project files
   git add .

   # Commit
   git commit -m "feat: complete web crawler analytics app ready for Streamlit Cloud"
   ```

2. Create a new empty repository on [GitHub](https://github.com/new) (e.g. `web-crawler-analytics`).

3. Link your remote and push your code:
   ```bash
   git remote add origin https://github.com/<YOUR-USERNAME>/<YOUR-REPO-NAME>.git
   git push -u origin main
   ```

### Step 2: Deploy on Streamlit Community Cloud

1. Go to **[share.streamlit.io](https://share.streamlit.io/)** and sign in with your GitHub account.
2. Click the **"New app"** button.
3. Fill in the deployment form:
   - **Repository**: `<YOUR-USERNAME>/<YOUR-REPO-NAME>`
   - **Branch**: `main`
   - **Main file path**: `app.py`
4. Click **"Deploy!"**.

> [!NOTE]
> Streamlit Cloud will automatically detect `requirements.txt`, install all required Python packages (`requests`, `beautifulsoup4`, `pandas`, `plotly`, `networkx`), apply the dark cyber-analytics theme defined in `.streamlit/config.toml`, and initialize SQLite persistence in `data/`. Any future git commits pushed to `main` will automatically trigger a zero-downtime redeploy.

---

## How Crawling Depth Works

The crawler employs a **Queue-Based Breadth-First Search (BFS)** algorithm:

$$\text{Queue: } [(\text{URL}, \text{depth}, \text{parent\_url})]$$

- **Depth 0**: Crawls **only** the user-provided starting webpage. All links present on the seed page are extracted and recorded in the discovered list, but none of them are enqueued for crawling.
- **Depth 1**: Crawls the starting webpage (depth 0) and then visits all directly linked pages (depth 1) discovered on the seed.
- **Depth 2**: Crawls the starting webpage (depth 0), visits its directly linked pages (depth 1), and then crawls all pages directly linked from those depth 1 pages (depth 2).
- **Depth $K$**: Traversal halts expansion when `current_depth == max_depth`. Pages at `max_depth` have their hyperlinks parsed and counted, but child links are not scheduled for further crawling.

---

## How Duplicate URLs Are Prevented

In web crawling, circular references ($A \to B \to A$) and multiple pages pointing to the same resource ($A \to C$, $B \to C$) can quickly lead to infinite loops and redundant resource consumption.

This application employs a two-tier duplicate prevention mechanism:

1. **Canonical Normalization (`crawler/url_utils.py`)**:
   - Lowercases scheme (`HTTPS` $\to$ `https`) and hostname (`EXAMPLE.COM` $\to$ `example.com`).
   - Removes URL fragments (`https://example.com/page#team` $\to$ `https://example.com/page`).
   - Normalizes default port numbers (`:80` for HTTP, `:443` for HTTPS).
   - Eliminates duplicate consecutive slashes (`//about//team/` $\to$ `/about/team`).
   - Strips trailing slashes uniformly so `https://example.com/about` and `https://example.com/about/` produce identical keys.
   - Deterministically sorts query parameters (`?b=2&a=1` $\to$ `?a=1&b=2`).
2. **Immediate Visited Set Membership (`visited_urls`)**:
   - When a URL is queued for processing, it is immediately registered in `self.visited_urls`.
   - Before adding any discovered link to the queue, the crawler tests `link not in self.visited_urls`.
   - This $O(1)$ hash set check guarantees that no URL can ever be enqueued or fetched more than once.

---

## Error Handling & Fault Tolerance

The crawler is engineered to never crash or abort execution because of a single failing URL:

- **Invalid URLs**: Validated against RFC formats and required `http`/`https` schemes before attempting network calls.
- **HTTP Status Code Errors**: Responses with codes $\ge 400$ (e.g. 403 Forbidden, 404 Not Found, 429 Rate Limited, 500 Internal Error) are recorded in `failures` without interrupting queue traversal.
- **Network & DNS Failures**: `requests.exceptions.ConnectionError` and DNS resolution failures are captured and categorized.
- **Timeouts**: Individual requests that exceed the configurable timeout threshold are aborted cleanly without stalling subsequent requests.
- **SSL / TLS Certificate Issues**: `requests.exceptions.SSLError` exceptions are caught and logged.
- **Non-HTML Resources**: Direct binary extensions (`.png`, `.pdf`, `.zip`, `.exe`, etc.) are proactively filtered before queuing. If an unexpected binary stream is encountered, its `Content-Type` header is inspected, and non-HTML responses are skipped.
- **Malformed Markup**: BeautifulSoup handles unclosed tags, malformed attributes, and empty documents with sensible fallbacks (e.g., fallback to `<h1>` or `"Untitled Page"`).

---

## Database Schema (SQLite)

The optional SQLite database (`data/crawler.db`) persists crawl sessions and page metrics across restarts:

### `sessions` Table
- `session_id` (TEXT, PK): Unique timestamped identifier (e.g., `crawl_20260905_104523_a1b2c3`)
- `start_url` (TEXT): Seed URL
- `max_depth` (INTEGER): Configured depth limit
- `max_pages` (INTEGER): Configured page safety cap
- `start_time` / `end_time` (TEXT): ISO timestamps
- `elapsed_seconds` (REAL): Total execution time
- `pages_crawled` (INTEGER): Successfully crawled count
- `discovered_urls_count` (INTEGER): Unique discovered links count
- `failed_urls_count` (INTEGER): Number of failures
- `total_internal_links` / `total_external_links` (INTEGER)
- `stay_on_domain` (INTEGER): Boolean flag
- `max_depth_reached` (INTEGER): Deepest level visited

### `crawled_pages` Table
- `id` (INTEGER, PK AUTOINCREMENT)
- `session_id` (TEXT, FK): Linked to `sessions`
- `url` (TEXT): Crawled page URL
- `title` (TEXT): Webpage title
- `depth` (INTEGER): Depth level
- `status_code` (INTEGER): HTTP status code (200)
- `total_links` / `unique_links` / `internal_links_count` / `external_links_count` (INTEGER)
- `response_time` (REAL): Latency in seconds
- `content_type` (TEXT): MIME type
- `domain` (TEXT): Page hostname
- `parent_url` (TEXT): URL from which this page was discovered
- `internal_urls_json` (TEXT): JSON array of discovered internal links
- `external_urls_json` (TEXT): JSON array of discovered external links

### `failed_urls` Table
- `id` (INTEGER, PK AUTOINCREMENT)
- `session_id` (TEXT, FK): Linked to `sessions`
- `url` (TEXT): Failed URL
- `depth` (INTEGER): Traversal depth
- `error_type` (TEXT): Error classification (e.g. `HTTP 404`, `Timeout Error`)
- `error_message` (TEXT): Detailed description

---

## Running Tests

The test suite contains **39 automated unit and integration tests** covering URL parsing, HTML extraction, BFS depth limits, duplicate detection, CLI argument parsing, interactive prompts, file exports, and SQLite persistence. All tests run fast without external network dependencies using mocked HTTP fixtures.

Run the test suite with:

```bash
pytest tests/ -v
```

---

## Ethical & Responsible Web Crawling

Web crawlers consume server bandwidth, CPU, and network resources of the target websites. This application incorporates essential ethical crawling practices:

1. **User-Agent Identification**: Transmits an identifiable User-Agent string informing webmasters of the crawler's identity.
2. **Robots.txt Compliance**: Automatically queries and respects `robots.txt` disallow directives before fetching pages.
3. **Polite Request Delays**: Introduces a configurable delay (default `0.2s` to `1.0s`) between consecutive requests to prevent overwhelming target web servers.
4. **Safety Page Caps**: Enforces strict maximum-pages thresholds (default `30` to `50` pages) to prevent runaway crawls.
5. **Domain Scoping**: Defaults to "Stay on starting domain", preventing unintentional traversals onto external websites.

---

## Limitations & Future Enhancements

- **Client-Side JavaScript**: The crawler uses `requests` and `BeautifulSoup4`, which parse server-rendered HTML. Single Page Applications (SPAs) built entirely with client-side JavaScript rendering (e.g. React/Vue client routes) require a headless browser engine like Playwright for DOM hydration.
- **Distributed Crawling**: The engine runs in a single process using BFS queues; high-throughput web-scale crawlers typically employ distributed message queues (e.g., Kafka / Celery) and partitioned storage.
- **Sitemap.xml Integration**: Future releases can ingest XML sitemaps to seed initial frontier queues.
