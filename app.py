"""
Web Crawler & Evidence-Backed Search Engine.
Main entry point for Streamlit application.
Futuristic Cyber-Analytics Command Center visual theme.
"""

from datetime import datetime
import html
import streamlit as st

from crawler.models import CrawlConfig, CrawlSessionSummary
from crawler.crawler import WebCrawler
from crawler.database import CrawlDatabase
from crawler.url_utils import is_valid_url, normalize_url
from crawler.search_discovery import is_search_query
from ui.components import (
    apply_custom_styles,
    render_header,
    render_platform_header,
    render_app_topbar,
    render_workspace_hero,
    render_kpi_cards,
    render_completion_banner,
    render_empty_state,
    render_callout,
)
from ui.dashboard import (
    render_live_progress_container,
    render_results_section,
    render_network_graph_section,
    render_charts_section,
    render_url_explorer,
    render_failed_section,
    render_history_section,
)
from search.pipeline import SearchPipeline
from ui.search_view import (
    render_search_view,
    render_search_history_view,
    render_real_input_cyber_animator,
)
from ui.source_inspector import render_source_inspector
from ui.settings_view import render_settings_view

# Initialize page settings
st.set_page_config(
    page_title="Nexus Research // AI Search & Deep Web Crawler",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply futuristic cyber-analytics styling
apply_custom_styles()

# Initialize SQLite database repository
db = CrawlDatabase()

# Initialize Web Search Pipeline
if "search_pipeline" not in st.session_state:
    st.session_state["search_pipeline"] = SearchPipeline(db=db)
search_pipeline = st.session_state["search_pipeline"]

# Quick Test Target Presets (Direct URLs & Internet Search Queries)
PRESETS = {
    "Wikipedia: Web Crawler": {
        "url": "https://en.wikipedia.org/wiki/Web_crawler",
        "depth": 2,
        "pages": 30,
        "desc": "High-density encyclopedic link graph with multi-level references.",
    },
    "Internet Search: Artificial Intelligence": {
        "url": "Artificial intelligence algorithms and neural networks",
        "depth": 1,
        "pages": 15,
        "desc": "Cross-internet web crawl mining articles, papers, and definitions on AI.",
    },
    "Quotes to Scrape (Sandbox)": {
        "url": "https://quotes.toscrape.com/",
        "depth": 2,
        "pages": 20,
        "desc": "Safe scraping sandbox with author pages, tags, and pagination links.",
    },
    "Books to Scrape (Sandbox)": {
        "url": "https://books.toscrape.com/",
        "depth": 2,
        "pages": 25,
        "desc": "E-commerce catalog hierarchy with multi-category navigational links.",
    },
    "Internet Search: Python Web Crawlers": {
        "url": "web scraping architecture and distributed crawling techniques",
        "depth": 1,
        "pages": 15,
        "desc": "Cross-internet multi-domain crawl for web crawler engineering tutorials.",
    },
    "Python 3 Documentation": {
        "url": "https://docs.python.org/3/",
        "depth": 1,
        "pages": 20,
        "desc": "Official Python technical documentation hierarchy and standard library indexes.",
    },
}

# Initialize session state for persistent results across reruns
if "crawl_summary" not in st.session_state:
    st.session_state["crawl_summary"] = None
if "page_results" not in st.session_state:
    st.session_state["page_results"] = []
if "failures" not in st.session_state:
    st.session_state["failures"] = []
if "graph_edges" not in st.session_state:
    st.session_state["graph_edges"] = []
if "discovered_urls" not in st.session_state:
    st.session_state["discovered_urls"] = []
if "input_target_url" not in st.session_state:
    st.session_state["input_target_url"] = "https://en.wikipedia.org/wiki/Web_crawler"
if "input_max_depth" not in st.session_state:
    st.session_state["input_max_depth"] = 2
if "input_max_pages" not in st.session_state:
    st.session_state["input_max_pages"] = 30

# State and lifecycle initialization
if "is_crawling" not in st.session_state:
    st.session_state["is_crawling"] = False
if "crawler_lifecycle" not in st.session_state:
    st.session_state["crawler_lifecycle"] = "IDLE"
if "search_lifecycle" not in st.session_state:
    st.session_state["search_lifecycle"] = "IDLE"


def on_preset_change():
    """Synchronize input state immediately when a preset is chosen from dropdown."""
    selected = st.session_state.get("console_preset_select")
    if selected and selected in PRESETS:
        spec = PRESETS[selected]
        st.session_state["input_target_url"] = spec["url"]
        st.session_state["input_max_depth"] = spec["depth"]
        st.session_state["input_max_pages"] = spec["pages"]


def load_preset_card_callback(preset_title: str):
    """Safe callback triggered before widget instantiation when a preset card button is clicked."""
    if preset_title in PRESETS:
        spec = PRESETS[preset_title]
        st.session_state["input_target_url"] = spec["url"]
        st.session_state["input_max_depth"] = spec["depth"]
        st.session_state["input_max_pages"] = spec["pages"]
        st.session_state["console_preset_select"] = preset_title


def on_workspace_nav_change():
    """Synchronize active workspace when sidebar radio navigation selection changes."""
    st.session_state["active_workspace"] = st.session_state["sidebar_nav_workspace"]


def switch_to_search_callback(query_text: str):
    """Safely transitions operational mode to search before widget instantiation."""
    st.session_state["search_query_input"] = query_text
    st.session_state["active_workspace"] = "🔎 Search & Research"
    st.session_state["sidebar_nav_workspace"] = "🔎 Search & Research"
    st.session_state["app_operational_mode"] = "🔎 Web Search & Answers"
    st.session_state["trigger_auto_search"] = True


def navigate_to_workspace_callback(workspace_name: str):
    """Safely transitions active workspace before widget instantiation."""
    st.session_state["active_workspace"] = workspace_name
    st.session_state["sidebar_nav_workspace"] = workspace_name


def reset_crawl_state_callback():
    """Reset active session state and restore default configuration safely before widget instantiation."""
    st.session_state["crawl_summary"] = None
    st.session_state["page_results"] = []
    st.session_state["failures"] = []
    st.session_state["graph_edges"] = []
    st.session_state["discovered_urls"] = []
    st.session_state["input_target_url"] = "https://en.wikipedia.org/wiki/Web_crawler"
    st.session_state["input_max_depth"] = 2
    st.session_state["input_max_pages"] = 30
    st.session_state["input_timeout"] = 10.0
    st.session_state["input_delay"] = 0.2
    st.session_state["chk_stay_domain"] = True
    st.session_state["chk_robots"] = True
    st.session_state["chk_sqlite"] = True
    st.session_state["console_preset_select"] = "⚡ Presets: Select Target..."
    st.session_state["is_crawling"] = False
    st.session_state["crawler_lifecycle"] = "IDLE"
    st.session_state.pop("results_search_box", None)
    st.session_state.pop("results_depth_select", None)
    st.session_state.pop("results_status_select", None)
    st.session_state.pop("explorer_url_select", None)
    st.session_state.pop("history_session_select", None)
    st.session_state.pop("history_loaded_notification", None)


def render_deep_crawler_mode():
    """Render the full BFS Crawler Command Deck, Traversal Engine, and Analytics Dashboards."""
    raw_deck_input = st.session_state.get("input_target_url", "").strip()
    is_search_mode = is_search_query(raw_deck_input) if raw_deck_input else False
    mode_badge_html = (
        '<span style="background: rgba(168, 85, 247, 0.15); border: 1px solid #A855F7; color: #D8B4FE; padding: 0.2rem 0.55rem; border-radius: 6px; font-size: 0.68rem; font-weight: 700; letter-spacing: 0.04em;">🌐 INTERNET SEARCH &amp; MINING</span>'
        if is_search_mode
        else '<span style="background: rgba(249, 115, 22, 0.15); border: 1px solid #F97316; color: #FB923C; padding: 0.2rem 0.55rem; border-radius: 6px; font-size: 0.68rem; font-weight: 700; letter-spacing: 0.04em;">🎯 DIRECT TARGET SEED URL</span>'
    )

    col_deck_left, col_deck_right = st.columns([5.5, 4.5])

    with col_deck_left:
        st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.6rem; flex-wrap: wrap; gap: 0.5rem;">
                <div style="font-size: 0.76rem; font-weight: 800; letter-spacing: 0.08em; color: #F97316; text-transform: uppercase;">
                    ⚡ CRAWLER CONFIGURATION
                </div>
                <div>{mode_badge_html}</div>
            </div>
        """, unsafe_allow_html=True)

        if is_search_mode:
            st.markdown(f"""
                <div style="font-size: 0.74rem; color: #D8B4FE; padding: 0.3rem 0; margin-bottom: 0.4rem;">
                    💡 <b>Research Query Detected:</b> Want verified evidence and a direct answer for <i>"{html.escape(raw_deck_input[:40])}..."</i>?
                </div>
            """, unsafe_allow_html=True)
            st.button(
                "🔎 Switch to Search & Research Canvas",
                key="btn_switch_search_mode",
                use_container_width=True,
                on_click=switch_to_search_callback,
                args=(raw_deck_input,),
            )

        # Real-time kinetic typing animator for crawler command deck input
        render_real_input_cyber_animator()

        def on_crawl_input_submit():
            st.session_state["trigger_auto_crawl"] = True

        start_url_input = st.text_input(
            "Target Seed URL or Words / Sentences",
            placeholder="Enter website URL (https://...) or topic to crawl...",
            key="input_target_url",
            label_visibility="collapsed",
            on_change=on_crawl_input_submit,
        )

        col_preset, col_btn_go, col_btn_clr = st.columns([2.5, 1.5, 1])
        with col_preset:
            preset_names = ["⚡ Presets: Select Target..."] + list(PRESETS.keys())
            st.selectbox(
                "Quick Target Presets",
                preset_names,
                key="console_preset_select",
                on_change=on_preset_change,
                label_visibility="collapsed",
            )
        with col_btn_go:
            btn_start = st.button("▶ Start Crawl", type="primary", use_container_width=True)
        with col_btn_clr:
            btn_clear = st.button("🧹 Clear", type="secondary", use_container_width=True, on_click=reset_crawl_state_callback)

        with st.expander("⚙️ Traversal Parameters & Politeness Policies", expanded=False):
            col_d, col_p = st.columns(2)
            with col_d:
                max_depth = st.number_input(
                    "Max Traversal Depth",
                    min_value=0,
                    step=1,
                    key="input_max_depth",
                )
            with col_p:
                max_pages = st.number_input(
                    "Max Pages Safety Cap",
                    min_value=1,
                    step=5,
                    key="input_max_pages",
                )

            col_t, col_w = st.columns(2)
            with col_t:
                timeout_val = st.number_input(
                    "HTTP Timeout (seconds)",
                    min_value=1.0,
                    max_value=60.0,
                    value=10.0,
                    step=1.0,
                    key="input_timeout",
                )
            with col_w:
                delay_val = st.number_input(
                    "Politeness Delay (seconds)",
                    min_value=0.0,
                    max_value=5.0,
                    value=0.2,
                    step=0.1,
                    key="input_delay",
                )

            keyword_filter_val = st.text_input(
                "Target Word / Sentence Match Filter (Optional)",
                placeholder="Highlight & extract specific sentences containing these words...",
                key="input_keyword_filter",
                help="Optional words or phrases to mine and extract from crawled web pages.",
            )

            col_c1, col_c2 = st.columns(2)
            with col_c1:
                stay_on_domain = st.checkbox("Stay on Base Domain", value=True, key="chk_stay_domain")
                respect_robots = st.checkbox("Respect robots.txt", value=True, key="chk_robots")
            with col_c2:
                enable_sqlite = st.checkbox("Persist Session in SQLite", value=True, key="chk_sqlite")
                render_js = st.checkbox("⚡ Render JavaScript (SPAs)", value=False, key="chk_render_js", help="Use headless Chromium browser to execute client-side JavaScript for modern SPAs.")
                if render_js:
                    from crawler.browser_fetcher import PlaywrightBrowserManager
                    if not PlaywrightBrowserManager.is_available():
                        st.warning("⚠️ Headless browser engine not detected. Crawl will fall back to HTTP.")

    # Retrieve active session state
    summary: CrawlSessionSummary = st.session_state.get("crawl_summary")
    pages = st.session_state.get("page_results", [])
    failures = st.session_state.get("failures", [])
    edges = st.session_state.get("graph_edges", [])

    # Right column status / monitor
    with col_deck_right:
        if st.session_state.get("is_crawling"):
            # Live crawl placeholder handled in execution block below
            pass
        elif summary is not None:
            st.markdown(f"""
                <div class="kpi-card" style="padding: 1.1rem 1.3rem; border-top: 3px solid #10B981; margin-bottom: 0.6rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.6rem;">
                        <div style="font-size: 0.72rem; font-weight: 700; color: #10B981; text-transform: uppercase;">
                            ● CRAWL SESSION READY
                        </div>
                        <div style="font-size: 0.70rem; color: #94A3B8; font-family: 'JetBrains Mono', monospace;">
                            ID: {summary.session_id}
                        </div>
                    </div>
                    <div style="font-size: 1.25rem; font-weight: 800; color: #FFFFFF; margin-bottom: 0.4rem;">
                        {summary.pages_crawled} Pages Crawled
                    </div>
                    <div style="font-size: 0.80rem; color: #94A3B8; line-height: 1.5; margin-bottom: 0.8rem;">
                        Traversal explored depth frontier <b>D{summary.max_depth_reached}</b> across <b>{summary.elapsed_seconds:.1f}s</b>.
                        Found {summary.discovered_urls_count} total links and {summary.failed_urls_count} failures.
                    </div>
                </div>
            """, unsafe_allow_html=True)
            col_sw1, col_sw2 = st.columns(2)
            with col_sw1:
                st.button(
                    "📁 Open Results ➔",
                    key="btn_deck_open_results",
                    use_container_width=True,
                    on_click=navigate_to_workspace_callback,
                    args=("📁 Results & Evidence",),
                )
            with col_sw2:
                st.button(
                    "📊 Open Analytics ➔",
                    key="btn_deck_open_analytics",
                    use_container_width=True,
                    on_click=navigate_to_workspace_callback,
                    args=("📊 Visual Analytics",),
                )
        else:
            st.markdown("""
                <div class="kpi-card" style="padding: 1.1rem 1.3rem; border-top: 3px solid #F97316; min-height: 160px; display: flex; flex-direction: column; justify-content: space-between;">
                    <div>
                        <div style="font-size: 0.72rem; font-weight: 700; color: #FB923C; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 0.4rem;">
                            ENGINE STANDBY // READY FOR TRAVERSAL
                        </div>
                        <div style="font-size: 1.1rem; font-weight: 800; color: #FFFFFF; margin-bottom: 0.3rem;">
                            Autonomous BFS Web Crawler
                        </div>
                        <div style="font-size: 0.80rem; color: #94A3B8; line-height: 1.5;">
                            Configure seed URL and limits on the left, or select a rapid preset. The engine executes Breadth-First Search, respects robots.txt, and indexes link topology in real time.
                        </div>
                    </div>
                    <div style="font-size: 0.70rem; color: #64748B; font-family: 'JetBrains Mono', monospace; margin-top: 0.6rem;">
                        POLITENESS: ENABLED &bull; CIRCULAR LOOP GUARD: ACTIVE
                    </div>
                </div>
            """, unsafe_allow_html=True)

    # Live Crawl Execution
    should_crawl = btn_start or st.session_state.pop("trigger_auto_crawl", False)
    if should_crawl:
        target_raw = start_url_input.strip()
        is_query_mode = is_search_query(target_raw)

        if not target_raw:
            st.warning("Please specify a starting target URL or search query.")
            return

        if not is_query_mode:
            target_url = target_raw
            if "://" not in target_url:
                target_url = "https://" + target_url
            norm_url = normalize_url(target_url)
            if not norm_url or not is_valid_url(norm_url):
                st.error("Invalid URL format. Please enter a valid HTTP or HTTPS address.")
                return
            config_start_url = norm_url
            config_search_query = None
        else:
            config_start_url = target_raw
            config_search_query = target_raw

        config = CrawlConfig(
            start_url=config_start_url,
            max_depth=int(max_depth),
            max_pages=int(max_pages),
            stay_on_domain=stay_on_domain if not is_query_mode else False,
            respect_robots=respect_robots,
            request_delay=float(delay_val),
            timeout=float(timeout_val),
            keyword_filter=keyword_filter_val.strip() if keyword_filter_val else None,
            search_query=config_search_query,
            render_js=render_js,
        )

        st.session_state["is_crawling"] = True
        st.session_state["crawler_lifecycle"] = "CRAWLING"
        progress_container, progress_bar, status_text, stat_pages, stat_queue, stat_elapsed = render_live_progress_container()

        crawler = WebCrawler(config=config)
        start_time = datetime.now()

        try:
            with progress_container:
                terminal_placeholder = st.empty()
                recent_logs = []

                for event in crawler.crawl_stream():
                    pct = min(1.0, event.pages_crawled / max(1, config.max_pages))
                    progress_bar.progress(pct)
                    status_text.text(f"BFS Active (Depth {event.current_depth}) // {event.current_url}")
                    stat_pages.metric("Pages Crawled", event.pages_crawled)
                    q_size = getattr(event, "queue_size", None)
                    if q_size is None:
                        q_size = max(0, event.discovered_count - event.pages_crawled - event.failed_count)
                    stat_queue.metric("URLs Queued", q_size)
                    cur_elapsed = (datetime.now() - start_time).total_seconds()
                    stat_elapsed.metric("Elapsed Time", f"{cur_elapsed:.1f}s")

                    status_glyph = "✓" if (getattr(event, "status", None) or event.event_type) == "success" else "✗"
                    log_line = f"[{status_glyph}] [D:{event.current_depth}] {event.current_url}"
                    recent_logs.append(log_line)
                    if len(recent_logs) > 6:
                        recent_logs.pop(0)

                    terminal_placeholder.markdown(f"""
                        <div style="background: rgba(16, 20, 34, 0.8); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; margin-top: 0.6rem; margin-bottom: 0.6rem; padding: 0.8rem 1rem;">
                            <div style="font-size: 0.70rem; font-weight: 800; color: #F97316; letter-spacing: 0.06em; margin-bottom: 0.3rem;">
                                LIVE BFS PACKET STREAM
                            </div>
                            <div style="font-size: 0.76rem; color: #94A3B8; font-family: 'JetBrains Mono', monospace; line-height: 1.5;">
                                {"<br>".join([html.escape(l) for l in recent_logs])}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
            st.session_state["crawler_lifecycle"] = "COMPLETE"
        except Exception as crawl_err:
            st.session_state["crawler_lifecycle"] = "ERROR"
            st.error(f"Crawl execution encountered an error: {crawl_err}")
        finally:
            st.session_state["is_crawling"] = False

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        exec_summary = CrawlSessionSummary(
            session_id=str(datetime.now().strftime("%Y%m%d_%H%M%S")),
            start_url=config_start_url or f"Search: {config_search_query}",
            max_depth=config.max_depth,
            max_pages=config.max_pages,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            elapsed_seconds=elapsed,
            pages_crawled=len(crawler.crawled_urls),
            discovered_urls_count=len(crawler.discovered_urls),
            failed_urls_count=len(crawler.failures),
            total_internal_links=sum(p.internal_links_count for p in crawler.page_results),
            total_external_links=sum(p.external_links_count for p in crawler.page_results),
            stay_on_domain=config.stay_on_domain,
            max_depth_reached=max((p.depth for p in crawler.page_results), default=0),
            search_query=config_search_query,
        )

        st.session_state["crawl_summary"] = exec_summary
        st.session_state["page_results"] = crawler.page_results
        st.session_state["failures"] = crawler.failures
        st.session_state["graph_edges"] = crawler.graph_edges
        st.session_state["discovered_urls"] = list(crawler.discovered_urls)

        if st.session_state.get("chk_sqlite", True) and exec_summary:
            db.save_session(
                summary=exec_summary,
                pages=crawler.page_results,
                failures=crawler.failures,
            )

        st.rerun()

    st.markdown("<div style='margin-top: 1.2rem;'></div>", unsafe_allow_html=True)

    tab_results, tab_explorer, tab_graph, tab_charts, tab_failed, tab_history = st.tabs([
        "📋 Crawled Pages",
        "🔍 URL Inspector",
        "🕸️ Link Topology Graph",
        "📈 Traversal Analytics",
        "⚠️ Failures & Exclusions",
        "📜 Session Archive",
    ])

    with tab_results:
        if pages:
            render_results_section(pages, summary=summary)
        else:
            render_empty_state("📋", "No Crawled Pages Yet", "Launch a crawl session above to populate the interactive data grid.")

    with tab_explorer:
        if pages:
            render_url_explorer(pages)
        else:
            render_empty_state("🔍", "No Page Selected", "Inspect page content snippets, headers, and outbound links once crawled.")

    with tab_graph:
        if pages and edges:
            render_network_graph_section(pages, edges)
        else:
            render_empty_state("🕸️", "Network Topology Standby", "The 2D physics-directed link graph renders node hierarchies once a crawl completes.")

    with tab_charts:
        if pages:
            render_charts_section(pages, failures=failures, summary=summary, edges=edges)
        else:
            render_empty_state("📈", "Analytics Standby", "Traversal depth, link distribution, and HTTP status donuts will display after crawling.")

    with tab_failed:
        if summary is not None:
            render_failed_section(failures)
        else:
            render_empty_state("⚠️", "No Failures Logged", "Network timeouts and policy exclusions will be reported here.")

    with tab_history:
        render_history_section(db)


def render_results_and_evidence_workspace(pages, summary, failures):
    """Render unified Results & Evidence Explorer workspace."""
    total_pages = len(pages)
    unique_domains = len({p.domain for p in pages if p.domain})
    total_failures = len(failures) if failures else 0
    active_search = st.session_state.get("active_search_result")
    evidence_count = len(active_search.extracted_evidence) if active_search and active_search.extracted_evidence else 0

    st.markdown(f"""
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.8rem; margin-bottom: 1.2rem;">
            <div class="kpi-card" style="padding: 0.9rem 1.1rem; border-top: 3px solid #F97316;">
                <div style="font-size: 0.70rem; font-weight: 700; color: #94A3B8; text-transform: uppercase;">Total Crawled Pages</div>
                <div style="font-size: 1.35rem; font-weight: 800; color: #FB923C;">{total_pages:,}</div>
            </div>
            <div class="kpi-card" style="padding: 0.9rem 1.1rem; border-top: 3px solid #A855F7;">
                <div style="font-size: 0.70rem; font-weight: 700; color: #94A3B8; text-transform: uppercase;">Unique Domains</div>
                <div style="font-size: 1.35rem; font-weight: 800; color: #C084FC;">{unique_domains:,}</div>
            </div>
            <div class="kpi-card" style="padding: 0.9rem 1.1rem; border-top: 3px solid #10B981;">
                <div style="font-size: 0.70rem; font-weight: 700; color: #94A3B8; text-transform: uppercase;">Search Evidence Blocks</div>
                <div style="font-size: 1.35rem; font-weight: 800; color: #34D399;">{evidence_count}</div>
            </div>
            <div class="kpi-card" style="padding: 0.9rem 1.1rem; border-top: 3px solid #EF4444;">
                <div style="font-size: 0.70rem; font-weight: 700; color: #94A3B8; text-transform: uppercase;">Failed Requests</div>
                <div style="font-size: 1.35rem; font-weight: 800; color: #F87171;">{total_failures}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    tab_pages, tab_explorer, tab_evidence, tab_failures = st.tabs([
        "📋 Crawled Pages Table",
        "🔍 URL Deep-Dive Inspector",
        "🔬 Search Evidence Passages",
        "⚠️ Network & Policy Failures",
    ])
    with tab_pages:
        if pages:
            render_results_section(pages, summary=summary)
        else:
            render_empty_state(
                "📋",
                "No Crawled Pages Available",
                "Execute a crawl session from the Deep Web Crawler workspace to populate the interactive data grid and export CSV/JSON datasets."
            )
    with tab_explorer:
        if pages:
            render_url_explorer(pages)
        else:
            render_empty_state(
                "🔍",
                "No URLs Ready to Inspect",
                "Crawled page headers, status codes, and outbound links will appear here once a crawl session completes."
            )
    with tab_evidence:
        if active_search:
            render_source_inspector(active_search)
        else:
            render_empty_state(
                "🔬",
                "No Search Evidence Retrieved",
                "Run a search query in Search & Research to inspect parsed web passages, relevance scores, and source grounding."
            )
    with tab_failures:
        if summary is not None:
            render_failed_section(failures)
        else:
            render_empty_state(
                "🛡️",
                "No Active Crawl Session",
                "Any network timeouts, HTTP 4xx/5xx errors, or robots.txt exclusions encountered during crawling will be reported here."
            )


def render_visual_analytics_workspace(pages, edges, failures, summary):
    """Render dedicated Visual Analytics workspace with high-impact charts & key insights."""
    total_pages = len(pages)
    unique_domains = len({p.domain for p in pages if p.domain})
    avg_latency = (sum(p.response_time for p in pages) / max(1, total_pages)) if pages else 0.0
    success_rate = ((total_pages / max(1, total_pages + (len(failures) if failures else 0))) * 100) if pages else 100.0

    st.markdown(f"""
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.8rem; margin-bottom: 1.2rem;">
            <div class="kpi-card" style="padding: 0.9rem 1.1rem; border-top: 3px solid #A855F7;">
                <div style="font-size: 0.70rem; font-weight: 700; color: #94A3B8; text-transform: uppercase;">Indexed Pages</div>
                <div style="font-size: 1.35rem; font-weight: 800; color: #C084FC;">{total_pages:,}</div>
            </div>
            <div class="kpi-card" style="padding: 0.9rem 1.1rem; border-top: 3px solid #F97316;">
                <div style="font-size: 0.70rem; font-weight: 700; color: #94A3B8; text-transform: uppercase;">Unique Domains</div>
                <div style="font-size: 1.35rem; font-weight: 800; color: #FB923C;">{unique_domains:,}</div>
            </div>
            <div class="kpi-card" style="padding: 0.9rem 1.1rem; border-top: 3px solid #10B981;">
                <div style="font-size: 0.70rem; font-weight: 700; color: #94A3B8; text-transform: uppercase;">Traversal Success</div>
                <div style="font-size: 1.35rem; font-weight: 800; color: #34D399;">{success_rate:.1f}%</div>
            </div>
            <div class="kpi-card" style="padding: 0.9rem 1.1rem; border-top: 3px solid #8B5CF6;">
                <div style="font-size: 0.70rem; font-weight: 700; color: #94A3B8; text-transform: uppercase;">Avg Latency</div>
                <div style="font-size: 1.35rem; font-weight: 800; color: #E9D5FF;">{avg_latency * 1000:.0f} ms</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    tab_charts, tab_graph = st.tabs([
        "📈 Traversal Distribution & Performance",
        "🕸️ Interactive Network Topology Graph",
    ])
    with tab_charts:
        if pages:
            render_charts_section(pages, failures=failures, summary=summary, edges=edges)

            # Key Insights Cards (Inspired by Reference Design)
            domain_counts = {}
            for p in pages:
                if p.domain:
                    domain_counts[p.domain] = domain_counts.get(p.domain, 0) + 1
            top_dom = max(domain_counts.items(), key=lambda x: x[1])[0] if domain_counts else "None"
            max_depth = max((p.depth for p in pages), default=0)
            fastest_page = min(pages, key=lambda p: p.response_time) if pages else None

            st.markdown("""
                <div style="margin-top: 1.5rem; margin-bottom: 0.8rem;">
                    <div style="font-size: 0.72rem; font-weight: 700; letter-spacing: 0.08em; color: #A855F7; text-transform: uppercase; margin-bottom: 0.2rem;">
                        AUTOMATED INTELLIGENCE
                    </div>
                    <h3 style="margin: 0; color: #FFFFFF; font-weight: 800; font-size: 1.25rem;">Key Crawl Insights</h3>
                </div>
            """, unsafe_allow_html=True)

            col_i1, col_i2, col_i3 = st.columns(3)
            with col_i1:
                st.markdown(f"""
                    <div class="kpi-card" style="padding: 1rem 1.2rem; border-top: 3px solid #F97316;">
                        <div style="font-size: 0.70rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; margin-bottom: 0.2rem;">
                            Top Indexed Domain
                        </div>
                        <div style="font-size: 1.1rem; font-weight: 800; color: #FFFFFF; word-break: break-all;">
                            {top_dom}
                        </div>
                        <div style="font-size: 0.72rem; color: #FB923C; margin-top: 0.3rem;">
                            {domain_counts.get(top_dom, 0)} pages crawled
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            with col_i2:
                st.markdown(f"""
                    <div class="kpi-card" style="padding: 1rem 1.2rem; border-top: 3px solid #A855F7;">
                        <div style="font-size: 0.70rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; margin-bottom: 0.2rem;">
                            Maximum Traversal Depth
                        </div>
                        <div style="font-size: 1.1rem; font-weight: 800; color: #FFFFFF;">
                            Depth {max_depth}
                        </div>
                        <div style="font-size: 0.72rem; color: #C084FC; margin-top: 0.3rem;">
                            Frontier reached successfully
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            with col_i3:
                fastest_ms = f"{fastest_page.response_time * 1000:.0f} ms" if fastest_page else "N/A"
                st.markdown(f"""
                    <div class="kpi-card" style="padding: 1rem 1.2rem; border-top: 3px solid #10B981;">
                        <div style="font-size: 0.70rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; margin-bottom: 0.2rem;">
                            Fastest Response Time
                        </div>
                        <div style="font-size: 1.1rem; font-weight: 800; color: #34D399;">
                            {fastest_ms}
                        </div>
                        <div style="font-size: 0.72rem; color: #94A3B8; margin-top: 0.3rem;">
                            Lowest HTTP latency recorded
                        </div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            render_empty_state(
                "📈",
                "Visual Analytics Telemetry Standby",
                "Plotly interactive charts (status breakdown donut, crawl depth distribution, top domains, and fetch latencies) will render once pages are crawled."
            )
    with tab_graph:
        if pages and edges:
            render_network_graph_section(pages, edges)
        else:
            render_empty_state(
                "🕸️",
                "Network Topology Graph Standby",
                "The 2D physics-directed link graph renders node hierarchies and inter-page connections once a crawl session with hyperlinks completes."
            )


def render_research_history_workspace(db: CrawlDatabase):
    """Render unified Research History workspace."""
    tab_search_hist, tab_crawl_hist = st.tabs([
        "🔎 Web Search Query History",
        "🕸️ Crawl Session Archives",
    ])
    with tab_search_hist:
        render_search_history_view(db)
    with tab_crawl_hist:
        render_history_section(db)

# --- Persistent Sidebar Navigation ---
WORKSPACES = [
    "🔎 Search & Research",
    "🕸️ Deep Web Crawler",
    "📁 Results & Evidence",
    "📊 Visual Analytics",
    "📜 Research History",
    "⚙️ Settings & System",
]

if "active_workspace" not in st.session_state:
    st.session_state["active_workspace"] = "🔎 Search & Research"

# Synchronize with legacy app_operational_mode if altered
if "app_operational_mode" in st.session_state:
    legacy_mode = st.session_state["app_operational_mode"]
    if "Search" in legacy_mode and st.session_state["active_workspace"] not in WORKSPACES:
        st.session_state["active_workspace"] = "🔎 Search & Research"
    elif "Crawler" in legacy_mode and st.session_state["active_workspace"] not in WORKSPACES:
        st.session_state["active_workspace"] = "🕸️ Deep Web Crawler"

with st.sidebar:
    st.markdown("""
        <div class="sidebar-brand-box">
            <div class="brand-glyph-box">⚡</div>
            <div>
                <div class="brand-title-text">NEXUS CRAWLER</div>
                <div class="brand-sub-text">AI RESEARCH PLATFORM</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    active_ws = st.session_state.get("active_workspace", WORKSPACES[0])
    if active_ws not in WORKSPACES:
        active_ws = WORKSPACES[0]
        st.session_state["active_workspace"] = active_ws

    if "sidebar_nav_workspace" not in st.session_state or st.session_state["sidebar_nav_workspace"] != active_ws:
        st.session_state["sidebar_nav_workspace"] = active_ws

    selected_workspace = st.radio(
        "Platform Workspaces",
        WORKSPACES,
        key="sidebar_nav_workspace",
        on_change=on_workspace_nav_change,
        label_visibility="collapsed",
    )
    st.session_state["active_workspace"] = selected_workspace

    st.markdown("""
        <div class="sidebar-system-card">
            <div class="sys-online-row">
                <span class="status-dot green-pulse"></span>
                <span class="sys-online-title">System Online</span>
            </div>
            <div class="sys-status-item">
                <span>Search Engine</span>
                <span class="sys-status-badge">Ready</span>
            </div>
            <div class="sys-status-item">
                <span>Crawler Engine</span>
                <span class="sys-status-badge">Ready</span>
            </div>
            <div class="sys-status-item">
                <span>AI Models</span>
                <span class="sys-status-badge">Ready</span>
            </div>
            <div class="sys-status-item">
                <span>Database</span>
                <span class="sys-status-badge">Connected</span>
            </div>
        </div>
        <div class="sidebar-release-meta">
            NEXUS v2.5 PRO<br>Evidence for a smarter world.
        </div>
    """, unsafe_allow_html=True)

# Render Application Top Bar (Global Command Prompt & Engine Indicator)
render_app_topbar()

# Retrieve active crawl state for workspace routing
pages = st.session_state.get("page_results", [])
summary = st.session_state.get("crawl_summary")
failures = st.session_state.get("failures", [])
edges = st.session_state.get("graph_edges", [])

# Workspace Routing
if selected_workspace == "🔎 Search & Research":
    render_workspace_hero(
        eyebrow="SEARCH & RESEARCH",
        title_part1="Ask. Discover.",
        title_accent="Get Evidence.",
        subtitle="Search the live web, verify information from multiple sources, and get an AI-powered, evidence-backed answer.",
        accent_type="purple",
    )
    render_search_view(search_pipeline, db)

elif selected_workspace == "🕸️ Deep Web Crawler":
    render_workspace_hero(
        eyebrow="DEEP WEB CRAWLER",
        title_part1="Explore",
        title_accent="the Web Deeper",
        subtitle="Crawl websites, extract structured data, and discover deeper relationships.",
        accent_type="orange",
    )
    render_deep_crawler_mode()

elif selected_workspace == "📁 Results & Evidence":
    render_workspace_hero(
        eyebrow="RESULTS & EVIDENCE",
        title_part1="Explore",
        title_accent="What the Web Revealed",
        subtitle="Browse crawled pages, verify sources, and examine evidence in detail.",
        accent_type="orange",
    )
    render_results_and_evidence_workspace(pages, summary, failures)

elif selected_workspace == "📊 Visual Analytics":
    render_workspace_hero(
        eyebrow="VISUAL ANALYTICS",
        title_part1="Insights",
        title_accent="from Real Web Data",
        subtitle="Analyze crawl data, discover patterns, and explore the web at scale.",
        accent_type="purple",
    )
    render_visual_analytics_workspace(pages, edges, failures, summary)

elif selected_workspace == "📜 Research History":
    render_workspace_hero(
        eyebrow="RESEARCH HISTORY",
        title_part1="Revisit. Continue.",
        title_accent="Go Deeper.",
        subtitle="Your past searches, crawls, and discoveries — all in one place.",
        accent_type="purple",
    )
    render_research_history_workspace(db)

elif selected_workspace == "⚙️ Settings & System":
    render_workspace_hero(
        eyebrow="SETTINGS & SYSTEM",
        title_part1="System Architecture",
        title_accent="& Preferences",
        subtitle="Manage AI models, search credentials, crawler defaults, and SQLite database storage.",
        accent_type="orange",
    )
    render_settings_view(db)
