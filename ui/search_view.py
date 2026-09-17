"""
Search View UI Component.
Renders the Web Search & Information Retrieval interface, featuring live search queries,
grounded AI research answers, citation badges, and a two-column intelligence canvas.
"""

import html
import json
import re
import time
from typing import Optional, List, Dict, Any
import streamlit as st

from search.pipeline import SearchPipeline, SearchPipelineResult
from crawler.database import CrawlDatabase
from answer.word_count import count_words
from ui.components import render_callout, render_empty_state


def format_text_with_citations(raw_text: str) -> str:
    """Safely format markdown bold and transform [1], [2] citations into interactive purple badges."""
    if not raw_text:
        return ""
    escaped = html.escape(raw_text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b style='color: #F8FAFC; font-weight: 700;'>\1</b>", escaped)
    def _rep(m):
        sid = m.group(1)
        return (
            f'<span class="citation-pill" title="Source [{sid}]">[{sid}]</span>'
        )
    return re.sub(r"\[(\d+)\]", _rep, escaped)


EXAMPLE_QUERIES = [
    "Quantum computing 2026",
    "Latest AI research",
    "Climate change evidence",
    "Solid-state batteries",
    "James Webb discoveries",
    "Python history",
]


def render_real_input_cyber_animator():
    """No-op backward compatible helper."""
    pass


def set_search_query_callback(query_text: str):
    """Callback for example chips to immediately populate search input and trigger auto-search."""
    st.session_state["search_query_input"] = query_text
    st.session_state["trigger_auto_search"] = True


def render_search_view(pipeline: SearchPipeline, db: CrawlDatabase):
    """Render the 2026 AI Search & Research Workspace."""

    # 1. Top Search Area
    col_input, col_btn = st.columns([5.5, 1.5])

    def on_search_query_submit():
        st.session_state["trigger_auto_search"] = True

    if "search_query_input" not in st.session_state:
        st.session_state["search_query_input"] = "latest developments in quantum computing"

    with col_input:
        query_val = st.text_input(
            "Search Input",
            placeholder="Ask a question or enter a research query...",
            key="search_query_input",
            label_visibility="collapsed",
            on_change=on_search_query_submit,
        )

    with col_btn:
        btn_search = st.button("➔ Search", type="primary", use_container_width=True, key="btn_run_web_search")

    # Example Chips Row
    st.markdown('<div style="font-size: 0.74rem; color: #64748B; font-weight: 600; margin-top: 0.2rem; margin-bottom: 0.3rem;">Try an example:</div>', unsafe_allow_html=True)
    chip_cols = st.columns(len(EXAMPLE_QUERIES))
    for idx, ex_q in enumerate(EXAMPLE_QUERIES):
        with chip_cols[idx]:
            st.button(
                ex_q,
                key=f"btn_chip_{idx}",
                use_container_width=True,
                on_click=set_search_query_callback,
                args=(ex_q,),
            )

    # Advanced Search Options Expander
    with st.expander("⚙️ Advanced Search Options", expanded=False):
        c_prov, c_num, c_wc = st.columns([3, 2.5, 2.5])
        with c_prov:
            provider_opt = st.selectbox(
                "Search Provider Engine",
                [
                    "Auto-Select (Best Available)",
                    "Google Custom Search JSON API",
                    "Multi-Engine Open Index (Bing + DuckDuckGo + Wiki)",
                ],
                index=0,
                key="search_provider_choice",
                help="Google uses official API if configured. Multi-Engine operates out-of-the-box without keys.",
            )
        with c_num:
            num_sources = st.slider(
                "Max Sources to Verify",
                min_value=3,
                max_value=15,
                value=8,
                step=1,
                key="search_num_sources",
                help="Higher values cross-check more independent sources for stronger corroboration.",
            )
        with c_wc:
            st.markdown("""
                <div style="font-size: 0.76rem; color: #94A3B8; padding-top: 1.2rem;">
                    💡 <b>Exact Word Count:</b> Type e.g. <i>"in exactly 300 words"</i> directly into your query.
                </div>
            """, unsafe_allow_html=True)

    # Search Execution Trigger
    should_run = btn_search or st.session_state.pop("trigger_auto_search", False)

    if should_run:
        clean_q = query_val.strip()
        if not clean_q:
            st.warning("Please enter a valid search query.")
            return

        pref = "auto"
        if "Google" in provider_opt:
            pref = "google"
        elif "Multi-Engine" in provider_opt:
            pref = "multi"

        st.session_state["search_lifecycle"] = "SEARCHING"
        try:
            with st.status(f"🔍 Researching: \"{clean_q}\" across the live web...", expanded=True) as status:
                progress_bar = st.progress(0.0)

                def _update_ui(msg: str, pct: float):
                    status.write(f"▸ {msg}")
                    progress_bar.progress(min(1.0, pct))

                if "search_conversation_history" not in st.session_state:
                    st.session_state["search_conversation_history"] = []

                search_result = pipeline.run(
                    query=clean_q,
                    num_sources=num_sources,
                    provider_preference=pref,
                    progress_callback=_update_ui,
                    conversation_history=st.session_state["search_conversation_history"],
                )
                status.update(label=f"✓ Research complete ({search_result.total_elapsed:.2f}s) — Grounded answer ready", state="complete", expanded=False)

            if search_result and search_result.answer:
                st.session_state["search_conversation_history"].append({
                    "role": "user",
                    "content": clean_q,
                })
                st.session_state["search_conversation_history"].append({
                    "role": "assistant",
                    "content": search_result.answer.direct_answer,
                })

            st.session_state["active_search_result"] = search_result
            st.session_state["search_lifecycle"] = "COMPLETE"
        except Exception as e:
            st.session_state["search_lifecycle"] = "ERROR"
            st.error(f"Search pipeline encountered an error: {e}")
            return

    # 2. Render State: Empty State vs Two-Column Research Canvas
    active_res: Optional[SearchPipelineResult] = st.session_state.get("active_search_result")

    if not active_res:
        st.markdown("<div style='margin-top: 1.2rem;'></div>", unsafe_allow_html=True)
        st.markdown("""
            <div class="empty-state-container">
                <div class="empty-icon">🌐</div>
                <div class="empty-title">Start your research</div>
                <div class="empty-desc">
                    Ask a question and Nexus Crawler will search the live web, extract answering passages,
                    verify facts across independent sources, and synthesize grounded evidence.
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("""
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1rem; margin-top: 1.2rem;">
                <div class="metric-card-box">
                    <div style="font-size: 1.1rem; margin-bottom: 0.4rem;">⚛️</div>
                    <div style="font-size: 0.88rem; font-weight: 700; color: #FFFFFF; margin-bottom: 0.2rem;">Quantum Computing</div>
                    <div style="font-size: 0.74rem; color: #94A3B8;">Recent breakthroughs in qubit coherence and fault-tolerant algorithms.</div>
                </div>
                <div class="metric-card-box">
                    <div style="font-size: 1.1rem; margin-bottom: 0.4rem;">🔋</div>
                    <div style="font-size: 0.88rem; font-weight: 700; color: #FFFFFF; margin-bottom: 0.2rem;">Solid-State Batteries</div>
                    <div style="font-size: 0.74rem; color: #94A3B8;">Commercial density roadmaps and automotive manufacturing timelines.</div>
                </div>
                <div class="metric-card-box">
                    <div style="font-size: 1.1rem; margin-bottom: 0.4rem;">🤖</div>
                    <div style="font-size: 0.88rem; font-weight: 700; color: #FFFFFF; margin-bottom: 0.2rem;">Autonomous AI Agents</div>
                    <div style="font-size: 0.74rem; color: #94A3B8;">Multi-agent consensus, memory persistence, and tool invocation standards.</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        return

    # Post-Search Two-Column Layout
    answer = active_res.answer
    confidence = active_res.confidence
    verification = active_res.verification
    ind_domains = verification.get("independent_domains", []) if verification else []
    contradictions = verification.get("contradictions", []) if verification else []
    query_text = active_res.query
    actual_words = count_words(answer.direct_answer) if answer else 0

    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
    col_left, col_right = st.columns([6.8, 3.2])

    with col_left:
        tab_ans, tab_src, tab_evid, tab_rel = st.tabs([
            "✦ AI Answer",
            f"📄 Sources ({len(active_res.ranked_results)})",
            f"🔬 Evidence ({len(getattr(active_res, 'top_passages', []))})",
            "💡 Related Questions",
        ])

        with tab_ans:
            if answer:
                citations_count = len(answer.citations) if answer.citations else 0
                st.markdown(f"""
                    <div class="glass-panel" style="padding: 1.4rem 1.6rem; border-top: 2px solid #A855F7;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.1rem; flex-wrap: wrap; gap: 0.6rem;">
                            <div style="display: flex; align-items: center; gap: 0.55rem;">
                                <span style="color: #A855F7; font-size: 1.2rem;">✦</span>
                                <span style="font-size: 1.1rem; font-weight: 800; color: #FFFFFF;">AI Research Answer</span>
                            </div>
                            <div style="display: flex; gap: 0.5rem; align-items: center;">
                                <span style="font-size: 0.72rem; color: #CBD5E1; background: rgba(168, 85, 247, 0.12); border: 1px solid rgba(168, 85, 247, 0.3); border-radius: 6px; padding: 0.2rem 0.6rem; font-weight: 600;">
                                    ⚡ {citations_count} Sources Cited
                                </span>
                                <span style="font-size: 0.72rem; color: #CBD5E1; background: rgba(249, 115, 22, 0.12); border: 1px solid rgba(249, 115, 22, 0.3); border-radius: 6px; padding: 0.2rem 0.6rem; font-weight: 600;">
                                    📝 {actual_words} Words
                                </span>
                            </div>
                        </div>
                        <div style="font-size: 0.96rem; line-height: 1.75; color: #F1F5F9;">
                """, unsafe_allow_html=True)

                # Render direct answer markdown
                st.markdown(answer.direct_answer)

                # Key Takeaway highlight panel
                key_takeaway = getattr(answer, "key_takeaway", None)
                if not key_takeaway and answer.direct_answer:
                    first_sent = answer.direct_answer.split(". ")[0].strip()
                    if len(first_sent) > 20:
                        key_takeaway = first_sent + ("." if not first_sent.endswith(".") else "")

                if key_takeaway:
                    safe_takeaway = html.escape(key_takeaway)
                    st.markdown(f"""
                        <div style="background: rgba(249, 115, 22, 0.08); border: 1px solid rgba(249, 115, 22, 0.3); border-radius: 10px; padding: 1rem 1.2rem; margin-top: 1.3rem; display: flex; gap: 0.8rem; align-items: flex-start;">
                            <span style="font-size: 1.2rem; color: #F97316;">💡</span>
                            <div>
                                <div style="font-size: 0.78rem; font-weight: 700; color: #FB923C; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.2rem;">
                                    Key Takeaway
                                </div>
                                <div style="font-size: 0.88rem; color: #E2E8F0; line-height: 1.55;">
                                    {safe_takeaway}
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                st.markdown("</div></div>", unsafe_allow_html=True)

            # Sources shelf at the bottom
            if active_res.ranked_results:
                st.markdown('<div style="font-size: 0.78rem; font-weight: 700; color: #FB923C; text-transform: uppercase; letter-spacing: 0.08em; margin: 1.2rem 0 0.6rem 0;">Top Grounding Sources</div>', unsafe_allow_html=True)
                src_cols = st.columns(min(4, len(active_res.ranked_results)))
                for s_i, r in enumerate(active_res.ranked_results[:4]):
                    with src_cols[s_i]:
                        safe_title = html.escape(r.title[:45] + "..." if len(r.title) > 45 else r.title)
                        safe_domain = html.escape(getattr(r, "display_domain", getattr(r, "domain", "")))
                        st.markdown(f"""
                            <a href="{html.escape(r.url, quote=True)}" target="_blank" style="text-decoration: none;">
                                <div class="metric-card-box" style="padding: 0.8rem 0.95rem; height: 100%;">
                                    <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.35rem;">
                                        <span style="background: rgba(168, 85, 247, 0.2); color: #C084FC; font-size: 0.70rem; font-weight: 800; border-radius: 4px; padding: 0.1rem 0.4rem;">
                                            {s_i + 1}
                                        </span>
                                        <span style="font-size: 0.72rem; color: #94A3B8; font-weight: 600;">{safe_domain}</span>
                                    </div>
                                    <div style="font-size: 0.82rem; font-weight: 700; color: #FFFFFF; line-height: 1.35;">
                                        {safe_title}
                                    </div>
                                </div>
                            </a>
                        """, unsafe_allow_html=True)

        with tab_src:
            for s_idx, res in enumerate(active_res.ranked_results, 1):
                safe_url = html.escape(res.url, quote=True)
                score_val = getattr(res, "relevance_score", getattr(res, "final_score", 0.0))
                res_domain = html.escape(getattr(res, "display_domain", getattr(res, "domain", "")))
                st.markdown(f"""
                    <div class="glass-panel" style="padding: 0.9rem 1.1rem; margin-bottom: 0.7rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem;">
                            <span style="font-size: 0.82rem; font-weight: 700; color: #A855F7;">[{s_idx}] {html.escape(res.title)}</span>
                            <span style="font-size: 0.72rem; color: #34D399; background: rgba(16,185,129,0.1); padding: 0.1rem 0.5rem; border-radius: 4px;">Score: {score_val:.2f}</span>
                        </div>
                        <div style="font-size: 0.78rem; color: #94A3B8; margin-bottom: 0.4rem; line-height: 1.45;">{html.escape(res.snippet)}</div>
                        <a href="{safe_url}" target="_blank" style="font-size: 0.74rem; color: #F97316; text-decoration: none; font-family: 'JetBrains Mono', monospace;">
                            🔗 {res_domain} ➔
                        </a>
                    </div>
                """, unsafe_allow_html=True)

        with tab_evid:
            passages_list = getattr(active_res, "top_passages", [])
            if passages_list:
                for e_idx, p in enumerate(passages_list[:8], 1):
                    st.markdown(f"""
                        <div class="glass-panel" style="padding: 0.9rem 1.1rem; margin-bottom: 0.7rem;">
                            <div style="display: flex; justify-content: space-between; font-size: 0.72rem; color: #64748B; margin-bottom: 0.3rem;">
                                <span>PASSAGE {e_idx} &bull; {html.escape(getattr(p, "source_domain", getattr(p, "domain", "")))}</span>
                            <span style="color: #FB923C;">Relevance: {p.relevance_score:.2f}</span>
                            </div>
                            <div style="font-size: 0.84rem; color: #E2E8F0; line-height: 1.5; font-style: italic;">
                                "{html.escape(p.text)}"
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No extracted evidence passages available.")

        with tab_rel:
            rel_suggestions = []
            if active_res.query_analysis:
                rel_suggestions = active_res.query_analysis.follow_up_suggestions or active_res.query_analysis.search_variations
            if rel_suggestions:
                for dq in rel_suggestions:
                    st.button(f"🔍 {dq}", key=f"btn_rel_{hash(dq)}", on_click=set_search_query_callback, args=(dq,))
            else:
                st.info("No related questions generated for this query.")

    with col_right:
        # Search Details Card
        st.markdown(f"""
            <div class="glass-panel" style="padding: 1.2rem 1.35rem; margin-bottom: 1rem;">
                <div style="font-size: 0.76rem; font-weight: 800; color: #FB923C; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.9rem; display: flex; align-items: center; gap: 0.45rem;">
                    <span>📋 Search Details</span>
                </div>
                <div style="display: flex; flex-direction: column; gap: 0.65rem; font-size: 0.80rem;">
                    <div style="display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 0.4rem;">
                        <span style="color: #94A3B8;">Query</span>
                        <span style="color: #FFFFFF; font-weight: 600; text-align: right; max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{html.escape(query_text)}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 0.4rem;">
                        <span style="color: #94A3B8;">Sources Found</span>
                        <span style="color: #FFFFFF; font-weight: 700;">{len(active_res.ranked_results)}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 0.4rem;">
                        <span style="color: #94A3B8;">Domains Verified</span>
                        <span style="color: #FFFFFF; font-weight: 700;">{len(ind_domains)}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 0.4rem;">
                        <span style="color: #94A3B8;">Answer Length</span>
                        <span style="color: #FB923C; font-weight: 700;">{actual_words} words</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 0.4rem;">
                        <span style="color: #94A3B8;">Grounding Score</span>
                        <span style="color: #34D399; font-weight: 700;">{confidence.score:.2f} / 1.00</span>
                    </div>
                </div>
                <div style="margin-top: 1rem; background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 6px; padding: 0.4rem 0.75rem; font-size: 0.72rem; color: #34D399; text-align: center; font-weight: 700;">
                    ✓ Completed in {active_res.total_elapsed:.2f}s
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Search Engines Used Card
        google_on = pipeline.google_provider.is_available()
        st.markdown(f"""
            <div class="glass-panel" style="padding: 1.2rem 1.35rem; margin-bottom: 1rem;">
                <div style="font-size: 0.76rem; font-weight: 800; color: #FB923C; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.8rem;">
                    🌐 Search Engines Used
                </div>
                <div style="display: flex; flex-direction: column; gap: 0.5rem; font-size: 0.82rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="color: #E2E8F0;">Google API</span>
                        <span style="color: {'#34D399' if google_on else '#F59E0B'};">{'✓' if google_on else 'Standby'}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="color: #E2E8F0;">Bing Instant Index</span>
                        <span style="color: #34D399;">✓</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="color: #E2E8F0;">DuckDuckGo</span>
                        <span style="color: #34D399;">✓</span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Related Research Topics
        st.markdown("""
            <div class="glass-panel" style="padding: 1.2rem 1.35rem;">
                <div style="font-size: 0.76rem; font-weight: 800; color: #A855F7; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.8rem;">
                    ⚡ Related Research Topics
                </div>
            </div>
        """, unsafe_allow_html=True)
        suggested = [
            f"{query_text} applications",
            f"{query_text} future roadmap",
            f"{query_text} technical analysis",
        ]
        for s_topic in suggested:
            st.button(f"{s_topic} ➔", key=f"btn_sug_{hash(s_topic)}", use_container_width=True, on_click=set_search_query_callback, args=(s_topic,))


def render_search_history_view(db: CrawlDatabase):
    """Render the Search Query History section."""
    queries = db.get_search_history(limit=50)

    if not queries:
        st.markdown("""
            <div class="empty-state-container">
                <div class="empty-icon">🕒</div>
                <div class="empty-title">No Search Queries Recorded</div>
                <div class="empty-desc">
                    Search queries executed in the Search & Research canvas will appear here for audit and replay.
                </div>
            </div>
        """, unsafe_allow_html=True)
        return

    st.markdown(f"<div style='font-size: 0.76rem; color: #94A3B8; margin-bottom: 0.8rem;'>Displaying {len(queries)} recent research queries</div>", unsafe_allow_html=True)

    for idx, q in enumerate(queries):
        q_id = q.get("id") or idx
        q_query = q.get("query") or ""
        q_time = q.get("timestamp") or ""
        q_results = q.get("results_count", 0)
        q_provider = q.get("provider_name", "Open Index")
        session_data = q.get("session_data") or {}
        q_latency = session_data.get("elapsed_seconds") or 0.0

        col_q, col_act = st.columns([5.5, 1.5])
        with col_q:
            st.markdown(f"""
                <div class="glass-panel" style="padding: 0.75rem 1rem; margin-bottom: 0.5rem; border-left: 3px solid #A855F7;">
                    <div style="font-size: 0.88rem; font-weight: 700; color: #FFFFFF;">{html.escape(q_query)}</div>
                    <div style="font-size: 0.70rem; color: #94A3B8; margin-top: 0.2rem;">
                        {html.escape(str(q_time))} &bull; <span style="color: #FB923C;">{q_results} sources</span> &bull; Provider: {html.escape(str(q_provider))}
                    </div>
                </div>
            """, unsafe_allow_html=True)
        with col_act:
            st.button("Replay ➔", key=f"btn_hist_{q_id}_{idx}", use_container_width=True, on_click=set_search_query_callback, args=(q_query,))



render_futuristic_direct_answer = render_search_view
render_ai_research_canvas = render_search_view
