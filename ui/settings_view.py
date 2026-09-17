"""
Settings and System Telemetry UI Component.
Provides real-time inspection and management for:
- AI Model Provider & Fallback Engine
- Search Engine Credentials & Multi-Engine Index
- Headless Browser (Playwright Chromium) Engine
- Local SQLite Database & Storage Management
"""

import os
import sqlite3
import streamlit as st
from crawler.database import CrawlDatabase


def render_settings_view(db: CrawlDatabase):
    """Render the Settings & System Telemetry view."""

    # 1. System Health & Connectivity Telemetry Cards
    groq_api_key = os.environ.get("GROQ_API_KEY")
    google_api_key = os.environ.get("GOOGLE_SEARCH_API_KEY")
    google_cx = os.environ.get("GOOGLE_SEARCH_ENGINE_ID")

    try:
        if not groq_api_key and "GROQ_API_KEY" in st.secrets:
            groq_api_key = st.secrets["GROQ_API_KEY"]
        if not google_api_key and "GOOGLE_SEARCH_API_KEY" in st.secrets:
            google_api_key = st.secrets["GOOGLE_SEARCH_API_KEY"]
        if not google_cx and "GOOGLE_SEARCH_ENGINE_ID" in st.secrets:
            google_cx = st.secrets["GOOGLE_SEARCH_ENGINE_ID"]
    except Exception:
        pass

    has_groq = bool(groq_api_key)
    has_google = bool(google_api_key and google_cx)

    has_playwright = False
    try:
        from crawler.browser_fetcher import PlaywrightBrowserManager
        has_playwright = PlaywrightBrowserManager.is_available()
    except Exception:
        has_playwright = False

    # Query DB stats
    total_sessions = 0
    total_pages = 0
    total_queries = 0
    db_size_kb = 0.0

    try:
        if os.path.exists(db.db_path):
            db_size_kb = os.path.getsize(db.db_path) / 1024.0
        with db._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM sessions")
            total_sessions = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM crawled_pages")
            total_pages = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM search_history")
            total_queries = cur.fetchone()[0]
    except Exception:
        pass

    st.markdown("""
        <div style="font-size: 0.72rem; font-weight: 800; letter-spacing: 0.08em; color: #F97316; text-transform: uppercase; margin-bottom: 0.8rem;">
            ⚡ PLATFORM RUNTIME &amp; ENGINE HEALTH
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        ai_status = "🟢 Groq Cloud" if has_groq else "🟡 Deterministic Fallback"
        ai_color = "#10B981" if has_groq else "#F59E0B"
        st.markdown(f"""
            <div class="kpi-card" style="padding: 1rem 1.2rem; border-top: 3px solid #A855F7;">
                <div style="font-size: 0.70rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; margin-bottom: 0.2rem;">
                    AI Synthesis Engine
                </div>
                <div style="font-size: 1.05rem; font-weight: 800; color: {ai_color}; margin-bottom: 0.2rem;">
                    {ai_status}
                </div>
                <div style="font-size: 0.68rem; color: #64748B;">
                    llama-3.3-70b-versatile
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        search_status = "🟢 Google API + Multi" if has_google else "🟢 Multi-Engine Index"
        search_color = "#F97316"
        st.markdown(f"""
            <div class="kpi-card" style="padding: 1rem 1.2rem; border-top: 3px solid #F97316;">
                <div style="font-size: 0.70rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; margin-bottom: 0.2rem;">
                    Search Discovery
                </div>
                <div style="font-size: 1.05rem; font-weight: 800; color: {search_color}; margin-bottom: 0.2rem;">
                    {search_status}
                </div>
                <div style="font-size: 0.68rem; color: #64748B;">
                    Bing + DuckDuckGo + Wiki
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        browser_status = "🟢 Chromium Ready" if has_playwright else "⚪ HTTP Engine"
        browser_color = "#10B981" if has_playwright else "#94A3B8"
        st.markdown(f"""
            <div class="kpi-card" style="padding: 1rem 1.2rem; border-top: 3px solid #10B981;">
                <div style="font-size: 0.70rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; margin-bottom: 0.2rem;">
                    Headless Browser
                </div>
                <div style="font-size: 1.05rem; font-weight: 800; color: {browser_color}; margin-bottom: 0.2rem;">
                    {browser_status}
                </div>
                <div style="font-size: 0.68rem; color: #64748B;">
                    Playwright JS Renderer
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
            <div class="kpi-card" style="padding: 1rem 1.2rem; border-top: 3px solid #8B5CF6;">
                <div style="font-size: 0.70rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; margin-bottom: 0.2rem;">
                    SQLite Repository
                </div>
                <div style="font-size: 1.05rem; font-weight: 800; color: #C084FC; margin-bottom: 0.2rem;">
                    💾 {db_size_kb:.1f} KB
                </div>
                <div style="font-size: 0.68rem; color: #64748B;">
                    {total_sessions} sessions &bull; {total_pages} pages
                </div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)

    # 2. Detailed Configuration & Diagnostics Tabs
    tab_ai, tab_search, tab_crawler, tab_db = st.tabs([
        "🤖 AI Model & Synthesizer",
        "🌐 Search Engine APIs",
        "🕸️ Crawler & Browser Defaults",
        "💾 SQLite Database Storage",
    ])

    with tab_ai:
        st.markdown("""
            <div style="font-size: 0.88rem; color: #E2E8F0; margin-bottom: 0.8rem; line-height: 1.6;">
                The platform uses <b>Groq Cloud's Llama 3.3 70B Versatile</b> for fast neural answer synthesis.
                If an API key is not supplied, the platform automatically switches to its <b>Zero-Crash Deterministic Research Synthesizer</b>,
                guaranteeing full extraction of passages, citations, and confidence scores locally.
            </div>
        """, unsafe_allow_html=True)

        if has_groq:
            masked_key = groq_api_key[:6] + "..." + groq_api_key[-4:] if len(groq_api_key) > 10 else "******"
            st.success(f"✓ Groq API Key Detected: `{masked_key}`")
        else:
            st.info("ℹ️ No Groq API Key found in environment or secrets. Running in high-precision Deterministic Mode.")

        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Active LLM Model", value="llama-3.3-70b-versatile", disabled=True)
        with c2:
            st.text_input("Synthesis Temperature", value="0.2 (High Precision)", disabled=True)

    with tab_search:
        st.markdown("""
            <div style="font-size: 0.88rem; color: #E2E8F0; margin-bottom: 0.8rem; line-height: 1.6;">
                Web discovery operates out-of-the-box via our resilient Multi-Engine Open Index (Bing Instant + DuckDuckGo + Wikipedia).
                Optional official Google Custom Search JSON API keys can be supplied for enterprise quota discovery.
            </div>
        """, unsafe_allow_html=True)

        if has_google:
            st.success("✓ Google Custom Search JSON API configured and active.")
        else:
            st.info("ℹ️ Google Custom Search API keys not configured. Multi-Engine Open Index is actively serving web discovery without rate limits.")

    with tab_crawler:
        st.markdown("""
            <div style="font-size: 0.88rem; color: #E2E8F0; margin-bottom: 0.8rem; line-height: 1.6;">
                Configure global defaults for the autonomous Breadth-First Search traversal engine and headless browser renderer.
            </div>
        """, unsafe_allow_html=True)

        c_d, c_p, c_t, c_w = st.columns(4)
        with c_d:
            st.number_input("Default Max Depth", min_value=0, max_value=5, value=2, disabled=True, help="Default traversal depth used for new crawls.")
        with c_p:
            st.number_input("Default Safety Cap (Pages)", min_value=5, max_value=200, value=30, disabled=True)
        with c_t:
            st.number_input("Default Timeout (s)", min_value=1.0, max_value=60.0, value=10.0, disabled=True)
        with c_w:
            st.number_input("Default Politeness Delay (s)", min_value=0.0, max_value=5.0, value=0.2, disabled=True)

    with tab_db:
        st.markdown(f"""
            <div style="font-size: 0.88rem; color: #E2E8F0; margin-bottom: 0.8rem; line-height: 1.6;">
                Local persistence is managed with an ACID-compliant SQLite repository located at:
                <br><code style="color: #FB923C;">{db.db_path}</code>
            </div>
        """, unsafe_allow_html=True)

        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            st.metric("Total Crawl Sessions", total_sessions)
        with col_d2:
            st.metric("Total Crawled Pages", total_pages)
        with col_d3:
            st.metric("Total Search Queries", total_queries)

        st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)

        col_act1, col_act2 = st.columns(2)
        with col_act1:
            if st.button("🗑️ Clear Search Query History", use_container_width=True):
                if db.clear_search_history():
                    st.success("Search query history cleared.")
                    st.rerun()
                else:
                    st.error("Failed to clear search history.")

        with col_act2:
            if st.button("🧹 Optimize & Vacuum SQLite Database", use_container_width=True):
                try:
                    with db._get_connection() as conn:
                        conn.execute("VACUUM;")
                    st.success("Database optimized successfully.")
                except Exception as e:
                    st.error(f"Optimization error: {e}")
