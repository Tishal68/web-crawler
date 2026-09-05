"""
Web Crawler Analytics Web Application.
Academic Machine Learning / Data Mining / Web Mining project.
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

# Initialize page settings
st.set_page_config(
    page_title="Web Crawler Analytics // Control Center",
    page_icon="🕸️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Apply futuristic cyber-analytics styling
apply_custom_styles()

# Initialize SQLite database repository
db = CrawlDatabase()

# Quick Test Target Presets
PRESETS = {
    "Wikipedia: Web Crawler": {
        "url": "https://en.wikipedia.org/wiki/Web_crawler",
        "depth": 2,
        "pages": 30,
        "desc": "High-density encyclopedic link graph with multi-level references.",
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


# --- Main Cyber Command Center ---
render_header()

# --- Unified Global Command Bar (Always visible across all views) ---
st.markdown("""
    <div class="crawl-command-bar">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.55rem;">
            <div style="font-size: 0.78rem; font-weight: 800; letter-spacing: 0.08em; color: #FFFFFF; display: flex; align-items: center; gap: 0.45rem;">
                ⚡ GLOBAL CRAWL COMMAND DECK
            </div>
            <div style="font-size: 0.68rem; color: #22D3EE; font-family: 'JetBrains Mono', monospace; letter-spacing: 0.05em;">
                BFS TRAVERSAL // PROTOCOL READY
            </div>
        </div>
""", unsafe_allow_html=True)

# Bug 7 fix: wider action buttons so they don't wrap below 1280px
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
        "Target Seed URL",
        placeholder="Enter seed URL (e.g. https://example.com)...",
        key="input_target_url",
        label_visibility="collapsed",
    )

is_running = st.session_state.get("is_crawling", False)

with col_btn:
    btn_start = st.button("⚡ Start Crawl", type="primary", use_container_width=True, disabled=is_running)

with col_clr:
    btn_clear = st.button("🧹 Clear", type="secondary", use_container_width=True, on_click=reset_crawl_state_callback)

with st.expander("⚙️ Traversal Parameters & Politeness Policies", expanded=False):
    col_d, col_p, col_t, col_w = st.columns(4)
    with col_d:
        max_depth = st.number_input(
            "Max Traversal Depth",
            min_value=0,
            max_value=5,
            step=1,
            key="input_max_depth",
        )
    with col_p:
        max_pages = st.number_input(
            "Max Pages Safety Cap",
            min_value=1,
            max_value=200,
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

    col_chk1, col_chk2, col_chk3 = st.columns(3)
    with col_chk1:
        stay_on_domain = st.checkbox(
            "Stay on Domain (Block Outbound Hosts)",
            value=True,
            key="chk_stay_domain",
        )
    with col_chk2:
        respect_robots = st.checkbox(
            "Respect robots.txt (Disallow Directives)",
            value=True,
            key="chk_robots",
        )
    with col_chk3:
        save_to_db = st.checkbox(
            "Persist Session to SQLite Database",
            value=True,
            key="chk_sqlite",
        )



# Handle Crawl Execution
if btn_start:
    raw_url = st.session_state.get("input_target_url", "").strip()
    normalized_url = normalize_url(raw_url)
    if not normalized_url or not is_valid_url(normalized_url):
        st.error("❌ **Invalid Target URL:** Please provide a valid HTTP or HTTPS address (e.g. `https://example.com`).")
    else:
        config = CrawlConfig(
            start_url=normalized_url,
            max_depth=int(st.session_state.get("input_max_depth", 2)),
            max_pages=int(st.session_state.get("input_max_pages", 30)),
            timeout=float(st.session_state.get("input_timeout", 10.0)),
            request_delay=float(st.session_state.get("input_delay", 0.2)),
            stay_on_domain=bool(st.session_state.get("chk_stay_domain", True)),
            respect_robots=bool(st.session_state.get("chk_robots", True)),
        )

        crawler = WebCrawler(config=config)
        progress_ui = render_live_progress_container()

        exec_summary: CrawlSessionSummary = None
        stream_log = []

        st.session_state["is_crawling"] = True
        try:
            # Execute generator stream for live UI updates
            stream = crawler.crawl_stream(config)
            while True:
                event = next(stream)

                # Update live progress indicators
                pct = min(1.0, event.pages_crawled / max(1, config.max_pages))
                progress_ui["progress_bar"].progress(pct)

                progress_ui["metric_crawled"].metric("Pages Crawled", f"{event.pages_crawled} / {config.max_pages}")
                progress_ui["metric_discovered"].metric("Discovered Links", event.discovered_count)
                progress_ui["metric_failed"].metric("Failed Requests", event.failed_count)
                progress_ui["metric_depth"].metric("Current Frontier", f"Depth {event.current_depth}")

                display_url = event.current_url if len(event.current_url) <= 85 else event.current_url[:82] + "..."
                progress_ui["status_text"].markdown(f"**Active Target:** `{display_url}`")

                # Terminal-styled streaming console log with strict XSS escaping
                glyph = "✓" if event.event_type in ("page_crawled", "seed_started", "crawl_started", "success") else "✕"
                cls = "stream-success" if glyph == "✓" else "stream-fail"
                time_now = datetime.now().strftime("%H:%M:%S")
                short_url = event.current_url.replace("https://", "").replace("http://", "")
                if len(short_url) > 42:
                    short_url = short_url[:39] + "..."
                safe_short_url = html.escape(short_url)
                stream_log.append(f"[{time_now}] <span class='{cls}'>{glyph}</span> <span class='stream-depth'>DEPTH {event.current_depth}</span>  {safe_short_url}")
                if len(stream_log) > 5:
                    stream_log.pop(0)

                log_lines = "<br>".join(stream_log)
                progress_blocks = int(pct * 20)
                progress_ascii = "█" * progress_blocks + "░" * (20 - progress_blocks)
                progress_ui["live_console"].markdown(
                    f'''<div class="live-stream-box">
                        <div class="stream-title">⚡ LIVE CRAWL STREAM</div>
                        <div style="margin-bottom: 0.8rem; line-height: 1.6;">{log_lines}</div>
                        <div style="color: #94A3B8; font-size: 0.78rem;">
                            DEPTH &nbsp;&nbsp;&nbsp;&nbsp; {event.current_depth} / {config.max_depth}<br>
                            PROGRESS &nbsp;<span style="color: #22D3EE;">{progress_ascii}</span> {int(pct*100)}%
                        </div>
                    </div>''',
                    unsafe_allow_html=True,
                )
        except StopIteration as e:
            exec_summary = e.value
        finally:
            st.session_state["is_crawling"] = False

        # Save session state
        st.session_state["crawl_summary"] = exec_summary
        st.session_state["page_results"] = crawler.page_results
        st.session_state["failures"] = crawler.failures
        st.session_state["graph_edges"] = crawler.graph_edges
        st.session_state["discovered_urls"] = list(crawler.discovered_urls)

        # Persist to SQLite if enabled
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

# Fixed, stable tab headers — shortened to prevent truncation at 1280px viewport
tab_mission, tab_results, tab_graph, tab_charts, tab_explorer, tab_failed, tab_history = st.tabs([
    "⚡ Mission",
    "📋 Results",
    "🕸️ Network",
    "📈 Analytics",
    "🔍 URL Dive",
    "⚠️ Failures",
    "📜 History",
])

# ==============================================================================
# TAB 1: MISSION CONTROL (EXECUTIVE TELEMETRY & STANDBY GUIDANCE)
# ==============================================================================
with tab_mission:
    if summary is not None:
        st.markdown(f"""
            <div class="results-ready-bar">
                <div style="font-size: 0.84rem;">
                    <b style="color: #22C55E;">✓ CRAWL SESSION READY:</b>
                    <span style="color: #F8FAFC; margin-left: 0.35rem;">{summary.pages_crawled} pages analyzed across depth frontier {summary.max_depth_reached}.</span>
                </div>
                <div style="color: #94A3B8; font-size: 0.76rem;">
                    Access details via tabs: <b>📋 Results Table</b> &bull; <b>🕸️ Network Topology</b> &bull; <b>📈 Traversal Analytics</b> &bull; <b>🔍 URL Deep Dive</b>
                </div>
            </div>
        """, unsafe_allow_html=True)

        render_completion_banner(summary)
        render_kpi_cards(summary, pages=pages)
    else:
        # Futuristic Standby Guidance Panel
        st.markdown("""
            <div style="background: linear-gradient(135deg, rgba(255, 255, 255, 0.06) 0%, rgba(255, 255, 255, 0.01) 100%), rgba(15, 23, 42, 0.65); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.10); border-top: 3px solid #22D3EE; border-radius: 12px; padding: 1.2rem 1.6rem; box-shadow: 0 8px 32px rgba(0,0,0,0.4), 0 0 25px rgba(34, 211, 238, 0.12); margin-top: 0.5rem; margin-bottom: 1.2rem;">
                <div style="font-size: 0.72rem; font-weight: 700; color: #22D3EE; letter-spacing: 0.09em; text-transform: uppercase; margin-bottom: 0.3rem; display: flex; align-items: center; gap: 0.45rem;">
                    <span class="pulse-beacon-cyan"></span> SYSTEM READY // STANDBY MODE
                </div>
                <h3 style="color: #FFFFFF; font-size: 1.35rem; font-weight: 800; margin-top: 0; margin-bottom: 0.4rem; letter-spacing: -0.01em;">
                    Autonomous Web Crawler & Topology Engine
                </h3>
                <p style="color: #94A3B8; font-size: 0.88rem; line-height: 1.55; margin-bottom: 0;">
                    Configure seed URL and traversal limits in the command deck above, or click a rapid preset below.
                    The engine executes Breadth-First Search traversal, prevents circular loops, parses hyperlinks, and renders real-time interactive telemetry.
                </p>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("""
            <div style="font-size: 0.72rem; font-weight: 700; letter-spacing: 0.08em; color: #22D3EE; text-transform: uppercase; margin-bottom: 0.6rem;">
                // RAPID TEST TARGET PRESETS
            </div>
        """, unsafe_allow_html=True)
        p_cols = st.columns(4)
        for i, (p_title, p_spec) in enumerate(PRESETS.items()):
            with p_cols[i]:
                safe_preset_title = html.escape(p_title)
                safe_preset_url = html.escape(p_spec['url'])
                safe_preset_desc = html.escape(p_spec['desc'])
                st.markdown(f"""
                    <div class="kpi-card" style="padding: 0.85rem 1rem; min-height: 130px; display: flex; flex-direction: column; justify-content: space-between; margin-bottom: 0.4rem;">
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
                    key=f"btn_preset_card_{i}",
                    use_container_width=True,
                    on_click=load_preset_card_callback,
                    args=(p_title,),
                )

        # Engine Architecture Pillars
        st.markdown("<div style='margin-top: 1.2rem;'></div>", unsafe_allow_html=True)
        st.markdown("""
            <div style="font-size: 0.72rem; font-weight: 700; letter-spacing: 0.08em; color: #22D3EE; text-transform: uppercase; margin-bottom: 0.6rem;">
                // CORE ENGINE ARCHITECTURE GUARANTEES
            </div>
        """, unsafe_allow_html=True)
        col_arch1, col_arch2, col_arch3, col_arch4 = st.columns(4)
        with col_arch1:
            st.markdown("""
                <div class="kpi-card kpi-card-cyan" style="min-height: 90px; padding: 0.8rem 1rem;">
                    <div style="font-size: 0.80rem; font-weight: 700; color: #22D3EE; margin-bottom: 0.2rem;">
                        ⚡ BFS Traversal
                    </div>
                    <div style="font-size: 0.74rem; color: #94A3B8; line-height: 1.4;">
                        Level-synchronous queue expands seed neighbors completely before diving deeper.
                    </div>
                </div>
            """, unsafe_allow_html=True)
        with col_arch2:
            st.markdown("""
                <div class="kpi-card kpi-card-violet" style="min-height: 90px; padding: 0.8rem 1rem;">
                    <div style="font-size: 0.80rem; font-weight: 700; color: #A78BFA; margin-bottom: 0.2rem;">
                        🔄 Loop Mitigation
                    </div>
                    <div style="font-size: 0.74rem; color: #94A3B8; line-height: 1.4;">
                        Canonical URL hashing (scheme, port, fragments, sorted query) blocks circular paths.
                    </div>
                </div>
            """, unsafe_allow_html=True)
        with col_arch3:
            st.markdown("""
                <div class="kpi-card kpi-card-green" style="min-height: 90px; padding: 0.8rem 1rem;">
                    <div style="font-size: 0.80rem; font-weight: 700; color: #22C55E; margin-bottom: 0.2rem;">
                        🤖 robots.txt Rules
                    </div>
                    <div style="font-size: 0.74rem; color: #94A3B8; line-height: 1.4;">
                        Dynamic Disallow directive compliance with polite per-host delay throttling.
                    </div>
                </div>
            """, unsafe_allow_html=True)
        with col_arch4:
            st.markdown("""
                <div class="kpi-card kpi-card-sky" style="min-height: 90px; padding: 0.8rem 1rem;">
                    <div style="font-size: 0.80rem; font-weight: 700; color: #0EA5E9; margin-bottom: 0.2rem;">
                        💾 SQLite Storage
                    </div>
                    <div style="font-size: 0.74rem; color: #94A3B8; line-height: 1.4;">
                        Persistent relational session archive paired with 2D Spring network topology graph.
                    </div>
                </div>
            """, unsafe_allow_html=True)


# ==============================================================================
# TAB 2: CRAWLED WEBPAGES RESULTS TABLE & MULTI-FORMAT EXPORTS
# ==============================================================================
with tab_results:
    if pages and summary:
        render_results_section(pages, summary)
    else:
        st.info("No crawled pages to display yet. Configure target parameters in the command deck above and click **⚡ Start Crawl**.")


# ==============================================================================
# TAB 3: 2D BFS NETWORK TOPOLOGY GRAPH (SPRING FORCE LAYOUT)
# ==============================================================================
with tab_graph:
    if pages:
        render_network_graph_section(pages, edges)
    else:
        st.info("No network topology graph available. Launch a crawl session to visualize the hyperlink network.")


# ==============================================================================
# TAB 4: TRAVERSAL & LATENCY PERFORMANCE ANALYTICS
# ==============================================================================
with tab_charts:
    if pages and summary:
        render_charts_section(pages, failures, summary, edges)
    else:
        st.info("No telemetry charts available. Launch a crawl session to generate depth and latency metrics.")


# ==============================================================================
# TAB 5: URL DEEP DIVE & HYPERLINK EXPLORER
# ==============================================================================
with tab_explorer:
    if pages:
        render_url_explorer(pages)
    else:
        st.info("No crawled pages available to inspect. Launch a crawl session first.")


# ==============================================================================
# TAB 6: FAILED REQUESTS & EXCLUSION GUARDRAILS
# ==============================================================================
with tab_failed:
    if summary is not None:
        render_failed_section(failures)
    else:
        st.info("No active crawl session. Run a crawl to view network exceptions or policy exclusions.")


# ==============================================================================
# TAB 7: SQLITE RELATIONAL CRAWL HISTORY BROWSER
# ==============================================================================
with tab_history:
    render_history_section(db)
