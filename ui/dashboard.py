"""
Futuristic Cyber-Analytics Dashboard views:
- Live crawl runner & telemetry monitor
- Results explorer & multi-filter table
- Failed requests report panel
- Single URL inspector with extracted links
- Interactive Plotly analytics & network graph
- Export options (CSV & JSON)
- SQLite historical crawl session browser
"""

import json
import html
from typing import List, Dict, Any, Optional

import streamlit as st
import pandas as pd

from crawler.models import (
    PageResult,
    CrawlFailure,
    CrawlSessionSummary,
)
from crawler.database import CrawlDatabase
from crawler.url_utils import sanitize_dataframe_for_csv
from .components import (
    render_kpi_cards,
    render_completion_banner,
)
from .charts import (
    create_depth_bar_chart,
    create_status_donut_chart,
    create_links_distribution_chart,
    create_top_domains_chart,
    create_response_time_chart,
    create_crawl_network_graph,
)


def render_live_progress_container():
    """
    Creates and returns references to empty Streamlit placeholders
    for live streaming of crawl metrics in a futuristic cyber-console format.
    """
    st.markdown("""
        <div style="font-size: 0.78rem; font-weight: 700; letter-spacing: 0.08em; color: #22D3EE; text-transform: uppercase; margin-bottom: 0.4rem;">
            // ACTIVE CRAWL MONITORING TELEMETRY
        </div>
    """, unsafe_allow_html=True)

    status_text = st.empty()
    progress_bar = st.progress(0.0)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_crawled = st.empty()
    with col2:
        metric_discovered = st.empty()
    with col3:
        metric_failed = st.empty()
    with col4:
        metric_depth = st.empty()

    live_console = st.empty()

    return {
        "status_text": status_text,
        "progress_bar": progress_bar,
        "metric_crawled": metric_crawled,
        "metric_discovered": metric_discovered,
        "metric_failed": metric_failed,
        "metric_depth": metric_depth,
        "live_console": live_console,
    }


def render_results_section(pages: List[PageResult], summary: CrawlSessionSummary):
    """Render interactive results table with search, depth filter, and downloads."""
    st.markdown("""
        <div style="font-size: 0.78rem; font-weight: 700; letter-spacing: 0.08em; color: #22D3EE; text-transform: uppercase; margin-bottom: 0.3rem;">
            // CRAWLED WEBPAGES TELEMETRY
        </div>
        <h3 style="margin-top: 0; color: #FFFFFF; font-weight: 700; font-size: 1.35rem;">Crawled Webpages Results</h3>
    """, unsafe_allow_html=True)

    if not pages:
        st.info("No pages were crawled.")
        return

    records = [p.to_dict() for p in pages]
    df = pd.DataFrame(records)

    col_filter1, col_filter2, col_filter3 = st.columns([2, 1, 1])
    with col_filter1:
        search_query = st.text_input(
            "Search Query",
            placeholder="Search URL, Title, or Domain...",
            key="results_search_box",
            label_visibility="collapsed",
        )
    with col_filter2:
        depth_options = ["All Depths"] + sorted(list({f"Depth {p.depth}" for p in pages}))
        if "results_depth_select" in st.session_state and st.session_state["results_depth_select"] not in depth_options:
            st.session_state["results_depth_select"] = depth_options[0]
        selected_depth = st.selectbox("Depth Filter", depth_options, key="results_depth_select", label_visibility="collapsed")
    with col_filter3:
        status_options = ["All Status Codes"] + sorted(list({str(p.status_code) for p in pages}))
        if "results_status_select" in st.session_state and st.session_state["results_status_select"] not in status_options:
            st.session_state["results_status_select"] = status_options[0]
        selected_status = st.selectbox("Status Filter", status_options, key="results_status_select", label_visibility="collapsed")

    filtered_df = df.copy()
    if search_query:
        query_lower = search_query.lower()
        # Literal string match (regex=False) to prevent errors on special regex characters
        mask = (
            filtered_df["URL"].astype(str).str.lower().str.contains(query_lower, regex=False, na=False) |
            filtered_df["Title"].astype(str).str.lower().str.contains(query_lower, regex=False, na=False) |
            filtered_df["Domain"].astype(str).str.lower().str.contains(query_lower, regex=False, na=False)
        )
        filtered_df = filtered_df[mask]

    if selected_depth != "All Depths":
        target_d = int(selected_depth.replace("Depth ", ""))
        filtered_df = filtered_df[filtered_df["Depth"] == target_d]

    if selected_status != "All Status Codes":
        filtered_df = filtered_df[filtered_df["Status"] == int(selected_status)]

    # Quick telemetry strip for filtered view
    if filtered_df.empty:
        status_200_count = 0
        avg_latency = 0.0
        total_extracted = 0
    else:
        status_200_count = int((filtered_df["Status"] == 200).sum())
        avg_latency = float(filtered_df["Response Time (s)"].mean()) if "Response Time (s)" in filtered_df else 0.0
        total_extracted = int(filtered_df["Links"].sum()) if "Links" in filtered_df else 0

    st.markdown(f"""
        <div style="display: flex; gap: 0.8rem; margin-bottom: 0.8rem; flex-wrap: wrap; font-size: 0.78rem;">
            <span style="background: rgba(34, 211, 238, 0.08); border: 1px solid rgba(34, 211, 238, 0.25); padding: 0.25rem 0.65rem; border-radius: 4px; color: #22D3EE;">
                <b>Showing:</b> {len(filtered_df)} of {len(df)} Pages
            </span>
            <span style="background: rgba(34, 197, 94, 0.08); border: 1px solid rgba(34, 197, 94, 0.25); padding: 0.25rem 0.65rem; border-radius: 4px; color: #22C55E;">
                <b>200 OK:</b> {status_200_count}
            </span>
            <span style="background: rgba(139, 92, 246, 0.08); border: 1px solid rgba(139, 92, 246, 0.25); padding: 0.25rem 0.65rem; border-radius: 4px; color: #A78BFA;">
                <b>Avg Latency:</b> {avg_latency * 1000:.0f} ms
            </span>
            <span style="background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.10); padding: 0.25rem 0.65rem; border-radius: 4px; color: #94A3B8;">
                <b>Discovered Links:</b> {total_extracted:,}
            </span>
        </div>
    """, unsafe_allow_html=True)

    st.dataframe(
        filtered_df[[
            "URL", "Title", "Depth", "Status", "Links", "Internal", "External",
            "Response Time (s)", "Domain"
        ]],
        column_config={
            "URL": st.column_config.LinkColumn("Target Webpage", max_chars=60),
            "Title": st.column_config.TextColumn("Webpage Title", width="medium"),
            "Depth": st.column_config.NumberColumn("Depth", format="D%d", width="small"),
            "Status": st.column_config.NumberColumn("Status", format="%d", width="small"),
            "Links": st.column_config.NumberColumn("Links", width="small"),
            "Internal": st.column_config.NumberColumn("Internal", width="small"),
            "External": st.column_config.NumberColumn("External", width="small"),
            "Response Time (s)": st.column_config.NumberColumn("Latency", format="%.3f s", width="small"),
            "Domain": st.column_config.TextColumn("Domain Host", width="small"),
        },
        use_container_width=True,
        hide_index=True,
        height=380,
    )

    col_dl1, col_dl2, col_dl3 = st.columns(3)
    safe_sid = "".join(c for c in summary.session_id if c.isalnum() or c in ("-", "_"))
    with col_dl1:
        csv_data = sanitize_dataframe_for_csv(filtered_df).to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇ Download Results (CSV)",
            data=csv_data,
            file_name=f"crawled_pages_{safe_sid}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col_dl2:
        full_json = json.dumps([p.to_dict() for p in pages], indent=2).encode("utf-8")
        st.download_button(
            label="⬇ Download Full Data (JSON)",
            data=full_json,
            file_name=f"crawl_full_{safe_sid}.json",
            mime="application/json",
            use_container_width=True,
        )
    with col_dl3:
        summary_csv = sanitize_dataframe_for_csv(pd.DataFrame([summary.to_dict()])).to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇ Download Session Report (CSV)",
            data=summary_csv,
            file_name=f"crawl_report_{safe_sid}.csv",
            mime="text/csv",
            use_container_width=True,
        )


def render_failed_section(failures: List[CrawlFailure]):
    """Render the table of failed or skipped URLs with dark glass panel and red illumination."""
    st.markdown("""
        <div style="font-size: 0.78rem; font-weight: 700; letter-spacing: 0.08em; color: #F43F5E; text-transform: uppercase; margin-bottom: 0.3rem;">
            // EXCEPTION &amp; REJECTION LOG
        </div>
        <h3 style="margin-top: 0; color: #FFFFFF; font-weight: 700; font-size: 1.35rem;">Failed &amp; Excluded Requests</h3>
    """, unsafe_allow_html=True)

    if not failures:
        st.markdown("""
            <div style="background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.01) 100%), rgba(11, 24, 20, 0.75); border: 1px solid rgba(34, 197, 94, 0.3); border-left: 4px solid #22C55E; border-radius: var(--radius); padding: 1.1rem 1.4rem; color: #22C55E; font-weight: 600; box-shadow: 0 8px 30px rgba(0,0,0,0.4), 0 0 20px rgba(34, 197, 94, 0.12);">
                ✓ ZERO FAILURES DETECTED: All attempted network resources resolved successfully.
            </div>
        """, unsafe_allow_html=True)
        return

    records = [f.to_dict() for f in failures]
    df_fail = pd.DataFrame(records)

    st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(255, 255, 255, 0.04) 0%, rgba(255, 255, 255, 0.01) 100%), rgba(28, 14, 24, 0.80); border: 1px solid rgba(244, 63, 94, 0.35); border-left: 4px solid #F43F5E; border-radius: var(--radius); padding: 1.1rem 1.5rem; color: #F8FAFC; box-shadow: 0 8px 32px rgba(0,0,0,0.5), 0 0 25px rgba(244, 63, 94, 0.16); margin-bottom: 1.2rem;">
            <div style="font-size: 0.92rem; font-weight: 800; color: #F43F5E; letter-spacing: 0.06em; margin-bottom: 0.3rem;">
                ⚠ FAILED REQUESTS TELEMETRY
            </div>
            <div style="font-size: 0.85rem; color: #94A3B8;">
                <b style="color: #FFFFFF;">{len(failures)} failures detected</b> across network boundaries, HTTP status codes, or exclusion guardrails.
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.dataframe(
        df_fail[["URL", "Depth", "Error Type", "Error Message", "Timestamp"]],
        use_container_width=True,
        hide_index=True,
        height=260,
    )

    csv_fail = sanitize_dataframe_for_csv(df_fail).to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇ Download Failed URLs (CSV)",
        data=csv_fail,
        file_name="crawl_failed_urls.csv",
        mime="text/csv",
    )


def render_url_explorer(pages: List[PageResult]):
    """Allow deep-dive inspection into an individual crawled page with glass telemetry panels."""
    st.markdown("""
        <div style="font-size: 0.78rem; font-weight: 700; letter-spacing: 0.08em; color: #22D3EE; text-transform: uppercase; margin-bottom: 0.3rem;">
            // NODE TELEMETRY INSPECTOR
        </div>
        <h3 style="margin-top: 0; color: #FFFFFF; font-weight: 700; font-size: 1.35rem;">URL Deep-Dive Explorer</h3>
    """, unsafe_allow_html=True)

    if not pages:
        st.info("No crawled pages available to inspect.")
        return

    page_map = {f"[{p.depth}] {p.title[:55]} ({p.url})": p for p in pages}
    if "explorer_url_select" in st.session_state and st.session_state["explorer_url_select"] not in page_map:
        st.session_state["explorer_url_select"] = list(page_map.keys())[0]

    selected_key = st.selectbox(
        "Select a webpage to inspect its metadata and extracted hyperlinks:",
        options=list(page_map.keys()),
        key="explorer_url_select"
    )

    page = page_map[selected_key]
    status_class = "dot-green" if page.status_code == 200 else "dot-red"

    # Futuristic Inspection Panel Glass Grid with strict XSS sanitization
    safe_url = html.escape(page.url)
    safe_title = html.escape(page.title)
    safe_domain = html.escape(page.domain)
    safe_type = html.escape(page.content_type or "text/html")

    st.markdown(f"""
        <div class="kpi-grid" style="margin-bottom: 1.2rem;">
            <div class="kpi-card kpi-card-cyan">
                <div class="kpi-header">
                    <span class="kpi-dot dot-cyan">◉</span>
                    <span class="kpi-label">Target URL</span>
                </div>
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.82rem; color: #22D3EE; word-break: break-all; margin-top: 0.2rem;">
                    {safe_url}
                </div>
                <div class="kpi-subtext">Host: {safe_domain}</div>
            </div>
            <div class="kpi-card kpi-card-violet">
                <div class="kpi-header">
                    <span class="kpi-dot dot-violet">◉</span>
                    <span class="kpi-label">Webpage Title</span>
                </div>
                <div style="font-size: 1.15rem; font-weight: 700; color: #FFFFFF; line-height: 1.3; margin-top: 0.2rem;">
                    {safe_title}
                </div>
                <div class="kpi-subtext">Type: {safe_type}</div>
            </div>
            <div class="kpi-card kpi-card-green">
                <div class="kpi-header">
                    <span class="kpi-dot {status_class}">◉</span>
                    <span class="kpi-label">Status & Depth</span>
                </div>
                <div class="kpi-value val-green" style="font-size: 1.8rem;">
                    {page.status_code} <span style="font-size: 1rem; color: #94A3B8;">/ D{page.depth}</span>
                </div>
                <div class="kpi-subtext">Latency: {page.response_time:.3f}s</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Secondary metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Depth Level", f"Depth {page.depth}")
    c2.metric("Total Links", page.total_links)
    c3.metric("Internal Links", page.internal_links_count)
    c4.metric("External Links", page.external_links_count)

    if page.parent_url:
        safe_parent = html.escape(page.parent_url)
        st.markdown(f"**Discovered From (Parent URL):** `{safe_parent}`")

    tab_int, tab_ext = st.tabs([
        f"Internal Links ({page.internal_links_count})",
        f"External Links ({page.external_links_count})"
    ])

    with tab_int:
        if page.internal_urls:
            st.caption("Hyperlinks targeting the same domain / subdomains:")
            df_int = pd.DataFrame({"Internal Hyperlinks": page.internal_urls})
            st.dataframe(df_int, use_container_width=True, hide_index=True, height=220)
        else:
            st.info("No internal hyperlinks found on this page.")

    with tab_ext:
        if page.external_urls:
            st.caption("Hyperlinks pointing to third-party external hosts:")
            df_ext = pd.DataFrame({"External Hyperlinks": page.external_urls})
            st.dataframe(df_ext, use_container_width=True, hide_index=True, height=220)
        else:
            st.info("No external hyperlinks found on this page.")


def render_network_graph_section(pages: List[PageResult], edges: List[Dict[str, Any]]):
    """Render full-width interactive 2D Spring Force crawl network topology graph."""
    if not pages:
        st.info("No crawled data available to visualize. Launch a crawl session first.")
        return

    st.markdown("""
        <div style="font-size: 0.78rem; font-weight: 700; letter-spacing: 0.08em; color: #22D3EE; text-transform: uppercase; margin-bottom: 0.2rem;">
            // TOPOLOGICAL TRAVERSAL GRAPH
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.8rem; flex-wrap: wrap;">
            <h3 style="margin-top: 0; margin-bottom: 0; color: #FFFFFF; font-weight: 700; font-size: 1.25rem;">2D BFS Network Graph (Spring Force Layout)</h3>
            <div style="font-size: 0.72rem; color: #94A3B8;">
                Pan, zoom, or hover nodes for instant URI & depth telemetry
            </div>
        </div>
    """, unsafe_allow_html=True)
    st.plotly_chart(create_crawl_network_graph(pages, edges, max_nodes=60), use_container_width=True)


def render_charts_section(pages: List[PageResult], failures: List[CrawlFailure], summary: CrawlSessionSummary, edges: Optional[List[Dict[str, Any]]] = None):
    """Render analytical charts for traversal depth, link distribution, HTTP status, and latency."""
    if not pages:
        st.info("No crawled data available to visualize. Launch a crawl session first.")
        return

    st.markdown("""
        <div style="font-size: 0.78rem; font-weight: 700; letter-spacing: 0.08em; color: #22D3EE; text-transform: uppercase; margin-bottom: 0.2rem;">
            // TRAVERSAL & PERFORMANCE ANALYTICS
        </div>
        <h3 style="margin-top: 0; color: #FFFFFF; font-weight: 700; font-size: 1.25rem; margin-bottom: 0.8rem;">Crawl Traversal & Latency Analytics</h3>
    """, unsafe_allow_html=True)

    col_t1, col_t2, col_t3 = st.columns([1.2, 1, 1])
    with col_t1:
        st.plotly_chart(create_depth_bar_chart(pages), use_container_width=True)
    with col_t2:
        st.plotly_chart(
            create_links_distribution_chart(summary.total_internal_links, summary.total_external_links),
            use_container_width=True
        )
    with col_t3:
        st.plotly_chart(
            create_status_donut_chart(len(pages), len(failures)),
            use_container_width=True
        )

    col_p1, col_p2 = st.columns([1.2, 1])
    with col_p1:
        st.plotly_chart(create_response_time_chart(pages), use_container_width=True)
    with col_p2:
        st.plotly_chart(create_top_domains_chart(pages), use_container_width=True)


def render_history_section(db: CrawlDatabase):
    """Render SQLite historical crawl sessions browser with reload and delete capabilities."""
    st.markdown("""
        <div style="font-size: 0.78rem; font-weight: 700; letter-spacing: 0.08em; color: #22D3EE; text-transform: uppercase; margin-bottom: 0.3rem;">
            // SQLITE RELATIONAL ARCHIVE
        </div>
        <h3 style="margin-top: 0; color: #FFFFFF; font-weight: 700; font-size: 1.35rem;">Historical Crawl Sessions</h3>
    """, unsafe_allow_html=True)

    sessions = db.get_all_sessions()
    if not sessions:
        st.info("No past crawl sessions found in SQLite. Run a crawl to persist records.")
        return

    df_sessions = pd.DataFrame(sessions)
    st.dataframe(
        df_sessions[[
            "session_id", "start_url", "max_depth", "pages_crawled",
            "discovered_urls_count", "failed_urls_count", "elapsed_seconds", "start_time"
        ]],
        use_container_width=True,
        hide_index=True,
    )

    session_options = [s["session_id"] for s in sessions]
    if "history_session_select" in st.session_state and st.session_state["history_session_select"] not in session_options:
        st.session_state["history_session_select"] = session_options[0]

    selected_session_id = st.selectbox(
        "Select a past session to inspect or reload into active dashboard:",
        session_options,
        key="history_session_select"
    )

    def _load_session_callback(database: CrawlDatabase, sid: str, sess_list: list):
        raw_pages = database.get_session_pages(sid)
        raw_failures = database.get_session_failures(sid)
        target = next((s for s in sess_list if s["session_id"] == sid), None)
        if not target:
            return

        loaded_pages = [
            PageResult(
                url=r["url"],
                title=r["title"] or "Untitled Page",
                depth=r["depth"],
                status_code=r["status_code"],
                total_links=r["total_links"],
                unique_links=r["unique_links"],
                internal_links_count=r["internal_links_count"],
                external_links_count=r["external_links_count"],
                internal_urls=r.get("internal_urls", []),
                external_urls=r.get("external_urls", []),
                response_time=r["response_time"],
                content_type=r["content_type"] or "",
                domain=r["domain"] or "",
                timestamp=r["timestamp"] or "",
                parent_url=r.get("parent_url"),
            ) for r in raw_pages
        ]

        loaded_failures = [
            CrawlFailure(
                url=f["url"],
                depth=f["depth"],
                error_type=f["error_type"],
                error_message=f["error_message"],
                timestamp=f["timestamp"] or "",
            ) for f in raw_failures
        ]

        loaded_summary = CrawlSessionSummary(
            session_id=target["session_id"],
            start_url=target["start_url"],
            max_depth=target["max_depth"],
            max_pages=target["max_pages"],
            start_time=target["start_time"],
            end_time=target["end_time"],
            elapsed_seconds=target["elapsed_seconds"],
            pages_crawled=target["pages_crawled"],
            discovered_urls_count=target["discovered_urls_count"],
            failed_urls_count=target["failed_urls_count"],
            total_internal_links=target["total_internal_links"],
            total_external_links=target["total_external_links"],
            stay_on_domain=bool(target["stay_on_domain"]),
            max_depth_reached=target["max_depth_reached"],
        )

        # Reconstruct graph topology from parent relationships AND discovered internal inter-links
        crawled_url_set = {p.url for p in loaded_pages}
        loaded_edges = []
        seen_edges = set()

        for p in loaded_pages:
            if p.parent_url and (p.parent_url, p.url) not in seen_edges:
                seen_edges.add((p.parent_url, p.url))
                loaded_edges.append((p.parent_url, p.url, p.depth))

        for p in loaded_pages:
            for tgt in p.internal_urls:
                if tgt in crawled_url_set and tgt != p.url and (p.url, tgt) not in seen_edges:
                    seen_edges.add((p.url, tgt))
                    loaded_edges.append((p.url, tgt, p.depth + 1))

        # Reconstruct discovered URLs list
        discovered_set = set()
        for p in loaded_pages:
            discovered_set.add(p.url)
            discovered_set.update(p.internal_urls)
            discovered_set.update(p.external_urls)

        st.session_state["crawl_summary"] = loaded_summary
        st.session_state["page_results"] = loaded_pages
        st.session_state["failures"] = loaded_failures
        st.session_state["graph_edges"] = loaded_edges
        st.session_state["discovered_urls"] = list(discovered_set)
        st.session_state["input_target_url"] = loaded_summary.start_url
        st.session_state["input_max_depth"] = loaded_summary.max_depth
        st.session_state["input_max_pages"] = loaded_summary.max_pages
        st.session_state["console_preset_select"] = "⚡ Presets: Select Target..."
        st.session_state["history_loaded_notification"] = sid

    c_load, c_del = st.columns([1, 1])
    with c_load:
        st.button(
            "Load Session Into Dashboard",
            use_container_width=True,
            on_click=_load_session_callback,
            args=(db, selected_session_id, sessions),
        )

    if st.session_state.get("history_loaded_notification"):
        st.success(f"Session `{st.session_state.pop('history_loaded_notification')}` loaded into active dashboard.")

    with c_del:
        if st.button("Delete Session from Database", type="secondary", use_container_width=True):
            db.delete_session(selected_session_id)
            st.success(f"Session `{selected_session_id}` deleted.")
            st.rerun()
