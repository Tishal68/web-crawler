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
        '<span style="background: rgba(168, 85, 247, 0.2); border: 1px solid #A855F7; color: #D8B4FE; padding: 0.2rem 0.55rem; border-radius: 4px; font-size: 0.68rem; font-weight: 700; letter-spacing: 0.04em;">🌐 INTERNET SEARCH &amp; MINING</span>'
        if is_search_mode
        else '<span style="background: rgba(6, 182, 212, 0.15); border: 1px solid #06B6D4; color: #22D3EE; padding: 0.2rem 0.55rem; border-radius: 4px; font-size: 0.68rem; font-weight: 700; letter-spacing: 0.04em;">🎯 DIRECT TARGET SEED URL</span>'
    )

    st.markdown(f"""
        <div class="crawl-command-bar">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.55rem; flex-wrap: wrap; gap: 0.5rem;">
                <div style="font-size: 0.78rem; font-weight: 800; letter-spacing: 0.08em; color: #FFFFFF; display: flex; align-items: center; gap: 0.45rem;">
                    ⚡ GLOBAL CRAWL COMMAND DECK
                </div>
                <div style="font-size: 0.68rem; color: #22D3EE; font-family: 'JetBrains Mono', monospace; letter-spacing: 0.05em; display: flex; align-items: center; gap: 0.6rem;">
                    {mode_badge_html}
                    <span style="color: #94A3B8;">BFS TRAVERSAL // PROTOCOL READY</span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if is_search_mode:
        col_tip, col_sw = st.columns([5.5, 2.5])
        with col_tip:
            st.markdown(f"""
                <div style="font-size: 0.74rem; color: #D8B4FE; padding: 0.2rem 0;">
                    💡 <b>Research Query Detected:</b> Want verified evidence and a direct answer for <i>"{html.escape(raw_deck_input[:40])}..."</i>?
                </div>
            """, unsafe_allow_html=True)
        with col_sw:
            st.button(
                "🔎 Switch to Web Search & Answers",
                key="btn_switch_search_mode",
                use_container_width=True,
                on_click=switch_to_search_callback,
                args=(raw_deck_input,),
            )

    # Real-time kinetic typing animator for crawler command deck input
    render_real_input_cyber_animator()

    col_pre, col_url, col_btn, col_clr = st.columns([1.8, 4.5, 1.6, 1.1])

    with col_pre:
        preset_names = ["⚡ Presets: Select Target..."] + list(PRESETS.keys())
        st.selectbox(
            "Quick Target Presets",
            preset_names,
            key="console_preset_select",
            on_change=on_preset_change,
            label_visibility="collapsed",
        )

    def on_crawl_input_submit():
        st.session_state["trigger_auto_crawl"] = True

    with col_url:
        start_url_input = st.text_input(
            "Target Seed URL or Words / Sentences",
            placeholder="Enter website URL (https://...) or words / sentence to crawl across internet...",
            key="input_target_url",
            label_visibility="collapsed",
            on_change=on_crawl_input_submit,
        )

    with col_btn:
        btn_start = st.button("⚡ Start Crawl", type="primary", use_container_width=True)

    with col_clr:
        btn_clear = st.button("🧹 Clear", type="secondary", use_container_width=True, on_click=reset_crawl_state_callback)

    with st.expander("⚙️ Traversal Parameters & Politeness Policies", expanded=False):
        col_d, col_p, col_t, col_w = st.columns(4)
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
            placeholder="Highlight & extract specific sentences containing these words across crawled pages...",
            key="input_keyword_filter",
            help="Optional words or phrases to mine and extract from crawled web pages.",
        )

        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        with col_c1:
            stay_on_domain = st.checkbox("Stay on Base Domain", value=True, key="chk_stay_domain")
        with col_c2:
            respect_robots = st.checkbox("Respect robots.txt", value=True, key="chk_robots")
        with col_c3:
            enable_sqlite = st.checkbox("Persist Session in SQLite", value=True, key="chk_sqlite")
        with col_c4:
            render_js = st.checkbox("⚡ Render JavaScript (SPAs / Hotstar)", value=False, key="chk_render_js", help="Use headless Chromium browser to execute client-side JavaScript for modern React/Vue SPAs like Hotstar or Netflix.")
            if render_js:
                from crawler.browser_fetcher import PlaywrightBrowserManager
                if not PlaywrightBrowserManager.is_available():
                    st.warning("⚠️ Headless browser engine not detected. Crawl will fall back to HTTP.")

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
                        <div class="live-stream-box" style="margin-top: 0.5rem; margin-bottom: 0.5rem; padding: 0.6rem 0.8rem;">
                            <div class="stream-title" style="margin-bottom: 0.3rem;">
                                <span class="stream-beacon"></span> LIVE BFS PACKET STREAM
                            </div>
                            <div style="font-size: 0.76rem; color: #94A3B8; font-family: 'JetBrains Mono', monospace;">
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

    # Retrieve active session state
    summary: CrawlSessionSummary = st.session_state.get("crawl_summary")
    pages = st.session_state.get("page_results", [])
    failures = st.session_state.get("failures", [])
    edges = st.session_state.get("graph_edges", [])

    tab_mission, tab_results, tab_graph, tab_charts, tab_explorer, tab_failed, tab_history = st.tabs([
        "⚡ Mission",
        "📋 Results",
        "🕸️ Network",
        "📈 Analytics",
        "🔍 URL Dive",
        "⚠️ Failures",
        "📜 History",
    ])

    with tab_mission:
        if summary is not None:
            st.markdown(f"""
                <div class="results-ready-bar">
                    <div style="font-size: 0.84rem;">
                        <b style="color: #22C55E;">✓ CRAWL SESSION READY:</b>
                        <span style="color: #F8FAFC; margin-left: 0.35rem;">{summary.pages_crawled} pages analyzed across depth frontier {summary.max_depth_reached}.</span>
                    </div>
                    <div style="color: #94A3B8; font-size: 0.76rem;">
                        Detailed insights available across workspaces: <b>📁 Results &amp; Evidence</b> &bull; <b>📊 Visual Analytics</b>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            render_completion_banner(summary)
            render_kpi_cards(summary, pages=pages)

            st.markdown("<div style='margin-top: 1.1rem;'></div>", unsafe_allow_html=True)
            col_nav1, col_nav2 = st.columns(2)
            with col_nav1:
                st.button(
                    "📁 Open Results & Evidence Explorer ➔",
                    key="btn_open_results_ws",
                    use_container_width=True,
                    on_click=navigate_to_workspace_callback,
                    args=("📁 Results & Evidence",),
                )
            with col_nav2:
                st.button(
                    "📊 Open Visual Analytics Dashboard ➔",
                    key="btn_open_analytics_ws",
                    use_container_width=True,
                    on_click=navigate_to_workspace_callback,
                    args=("📊 Visual Analytics",),
                )
        else:
            st.markdown("""
                <div class="standby-panel-glass">
                    <div style="font-size: 0.72rem; font-weight: 700; color: #22D3EE; letter-spacing: 0.09em; text-transform: uppercase; margin-bottom: 0.3rem; display: flex; align-items: center; gap: 0.45rem;">
                        <span class="pulse-beacon-cyan"></span> SYSTEM READY // STANDBY MODE
                    </div>
                    <h3 style="color: #FFFFFF; font-size: 1.35rem; font-weight: 800; margin-top: 0; margin-bottom: 0.4rem;">
                        Autonomous Web Crawler &amp; Topology Engine
                    </h3>
                    <p style="color: #94A3B8; font-size: 0.88rem; line-height: 1.55; margin-bottom: 0;">
                        Configure seed URL and traversal limits in the command deck above, or click a rapid preset below.
                        The engine executes Breadth-First Search traversal, prevents circular loops, parses hyperlinks, and renders real-time interactive telemetry.
                    </p>
                </div>
            """, unsafe_allow_html=True)

            preset_items = list(PRESETS.items())
            row_size = 3
            global_card_idx = 0
            for r_start in range(0, len(preset_items), row_size):
                chunk = preset_items[r_start : r_start + row_size]
                p_cols = st.columns(len(chunk))
                for c_idx, (p_title, p_spec) in enumerate(chunk):
                    with p_cols[c_idx]:
                        safe_preset_title = html.escape(p_title)
                        safe_preset_url = html.escape(p_spec['url'])
                        safe_preset_desc = html.escape(p_spec['desc'])
                        st.markdown(f"""
                            <div class="kpi-card preset-card" style="padding: 0.85rem 1rem; min-height: 130px; display: flex; flex-direction: column; justify-content: space-between; margin-bottom: 0.4rem;">
                                <div>
                                    <div style="font-size: 0.82rem; font-weight: 800; color: #FFFFFF; margin-bottom: 0.2rem;">
                                        {safe_preset_title}
                                    </div>
                                    <div style="font-size: 0.70rem; color: #22D3EE; font-family: 'JetBrains Mono', monospace; word-break: break-all; margin-bottom: 0.3rem;">
                                        {safe_preset_url}
                                    </div>
                                    <div style="font-size: 0.72rem; color: #94A3B8; line-height: 1.35;">
                                        {safe_preset_desc}
                                    </div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        st.button(
                            f"⚡ Load {p_title.split(':')[0]}",
                            key=f"btn_preset_card_{global_card_idx}",
                            use_container_width=True,
                            on_click=load_preset_card_callback,
                            args=(p_title,),
                        )
                        global_card_idx += 1

    with tab_results:
        if pages:
            render_results_section(pages, summary=summary)
        else:
            st.info("No crawled pages recorded yet. Start a crawl session above to populate the data grid.")

    with tab_graph:
        if pages and edges:
            render_network_graph_section(pages, edges)
        else:
            st.info("Network topology graph will appear once a crawl session with link connections completes.")

    with tab_charts:
        if pages:
            render_charts_section(pages, failures=failures, summary=summary, edges=edges)
        else:
            st.info("Traversal distribution metrics will render once pages are crawled.")

    with tab_explorer:
        if pages:
            render_url_explorer(pages)
        else:
            st.info("No crawled pages available to inspect. Launch a crawl session first.")

    with tab_failed:
        if summary is not None:
            render_failed_section(failures)
        else:
            st.info("No active crawl session. Run a crawl to view network exceptions or policy exclusions.")

    with tab_history:
        render_history_section(db)


def render_results_and_evidence_workspace(pages, summary, failures):
    """Render unified Results & Evidence Explorer workspace."""
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
        active_search = st.session_state.get("active_search_result")
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
    """Render dedicated Visual Analytics workspace."""
    tab_graph, tab_charts = st.tabs([
        "🕸️ Interactive Network Topology Graph",
        "📈 Traversal Distribution & Metrics",
    ])
    with tab_graph:
        if pages and edges:
            render_network_graph_section(pages, edges)
        else:
            render_empty_state(
                "🕸️",
                "Network Topology Graph Standby",
                "The 2D physics-directed link graph renders node hierarchies and inter-page connections once a crawl session with hyperlinks completes."
            )
    with tab_charts:
        if pages:
            render_charts_section(pages, failures=failures, summary=summary, edges=edges)
        else:
            render_empty_state(
                "📈",
                "Visual Analytics Telemetry Standby",
                "Plotly interactive charts (status breakdown donut, crawl depth distribution, top domains, and fetch latencies) will render once pages are crawled."
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
        <div class="sidebar-brand">
            <div class="sidebar-logo-mark">⚡</div>
            <div class="sidebar-brand-text">
                <div class="sidebar-title">NEXUS CRAWLER</div>
                <div class="sidebar-subtitle">AI RESEARCH PLATFORM</div>
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
        <div class="sidebar-footer">
            <div class="sidebar-telemetry-row">
                <span class="telemetry-label">Status:</span>
                <span class="telemetry-value"><span class="telemetry-dot"></span>Online</span>
            </div>
            <div class="sidebar-telemetry-row">
                <span class="telemetry-label">Engine:</span>
                <span class="telemetry-value">BFS + Neural</span>
            </div>
            <div class="sidebar-telemetry-row">
                <span class="telemetry-label">Database:</span>
                <span class="telemetry-value">SQLite ACID</span>
            </div>
            <div class="sidebar-telemetry-row">
                <span class="telemetry-label">Release:</span>
                <span class="telemetry-value">v2.5 Pro</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

# Retrieve active crawl state for workspace routing
pages = st.session_state.get("page_results", [])
summary = st.session_state.get("crawl_summary")
failures = st.session_state.get("failures", [])
edges = st.session_state.get("graph_edges", [])

# Workspace Routing
if selected_workspace == "🔎 Search & Research":
    render_platform_header(
        title="SEARCH & INTELLIGENCE CANVAS",
        subtitle="Evidence-Backed Multi-Engine Retrieval & AI Neural Synthesis"
    )
    render_search_view(search_pipeline, db)

elif selected_workspace == "🕸️ Deep Web Crawler":
    render_platform_header(
        title="DEEP WEB TRAVERSAL ENGINE",
        subtitle="Autonomous Breadth-First Search & Graph Crawler"
    )
    render_deep_crawler_mode()

elif selected_workspace == "📁 Results & Evidence":
    render_platform_header(
        title="RESULTS & EVIDENCE EXPLORER",
        subtitle="Structured Page Inspection, Passages & Dataset Exports"
    )
    render_results_and_evidence_workspace(pages, summary, failures)

elif selected_workspace == "📊 Visual Analytics":
    render_platform_header(
        title="VISUAL ANALYTICS DASHBOARD",
        subtitle="Network Topology Graph, Crawl Depth & Domain Distributions"
    )
    render_visual_analytics_workspace(pages, edges, failures, summary)

elif selected_workspace == "📜 Research History":
    render_platform_header(
        title="RESEARCH & AUDIT ARCHIVES",
        subtitle="Persisted Web Search Queries & Crawl Session Logs"
    )
    render_research_history_workspace(db)

elif selected_workspace == "⚙️ Settings & System":
    render_platform_header(
        title="SETTINGS & SYSTEM TELEMETRY",
        subtitle="AI Providers, Search Engines, Headless Browser & Database"
    )
    render_settings_view(db)
