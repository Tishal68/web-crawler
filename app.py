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
    render_kpi_cards,
    render_completion_banner,
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
from ui.search_view import render_search_view, render_search_history_view
from ui.source_inspector import render_source_inspector

# Initialize page settings
st.set_page_config(
    page_title="Web Search & Deep Crawler // Control Center",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="collapsed",
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

# Safety reset
st.session_state["is_crawling"] = False


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
            if st.button("🔎 Switch to Web Search & Answers", key="btn_switch_search_mode", use_container_width=True):
                st.session_state["search_query_input"] = raw_deck_input
                st.session_state["app_operational_mode"] = "🔎 Web Search & Answers"
                st.session_state["trigger_auto_search"] = True
                st.rerun()

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

    with col_url:
        start_url_input = st.text_input(
            "Target Seed URL or Words / Sentences",
            placeholder="Enter website URL (https://...) or words / sentence to crawl across internet...",
            key="input_target_url",
            label_visibility="collapsed",
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

        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            stay_on_domain = st.checkbox("Stay on Base Domain", value=True, key="chk_stay_domain")
        with col_c2:
            respect_robots = st.checkbox("Respect robots.txt", value=True, key="chk_robots")
        with col_c3:
            enable_sqlite = st.checkbox("Persist Session in SQLite", value=True, key="chk_sqlite")

    # Live Crawl Execution
    if btn_start:
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
            config_start_url = ""
            config_search_query = target_raw

        config = CrawlConfig(
            start_url=config_start_url,
            max_depth=int(max_depth),
            max_pages=int(max_pages),
            stay_on_domain=stay_on_domain,
            respect_robots=respect_robots,
            request_delay=float(delay_val),
            timeout=float(timeout_val),
            keyword_filter=keyword_filter_val.strip() if keyword_filter_val else None,
            search_query=config_search_query,
        )

        st.session_state["is_crawling"] = True
        progress_container, progress_bar, status_text, stat_pages, stat_queue, stat_elapsed = render_live_progress_container()

        crawler = WebCrawler(config=config)
        start_time = datetime.now()

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

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        st.session_state["is_crawling"] = False

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
                        Access details via tabs: <b>📋 Results Table</b> &bull; <b>🕸️ Network Topology</b> &bull; <b>📈 Traversal Analytics</b>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            render_completion_banner(summary)
            render_kpi_cards(summary, pages=pages)
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
            render_charts_section(pages)
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


# --- Application Header ---
render_header()

# --- Top Navigation Mode Switcher ---
app_mode = st.radio(
    "Operational Mode",
    ["🔎 Web Search & Answers", "🕸️ Deep Crawler & Analytics"],
    horizontal=True,
    key="app_operational_mode",
    label_visibility="collapsed",
)

if app_mode == "🔎 Web Search & Answers":
    tab_search, tab_inspector, tab_search_hist = st.tabs([
        "🎯 Grounded Search & Answers",
        "🔍 Source Evidence Inspector",
        "📜 Search History",
    ])
    with tab_search:
        render_search_view(search_pipeline, db)
    with tab_inspector:
        render_source_inspector(st.session_state.get("active_search_result"))
    with tab_search_hist:
        render_search_history_view(db)
else:
    render_deep_crawler_mode()
