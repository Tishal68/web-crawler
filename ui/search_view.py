"""
Search View UI Component.
Renders the Web Search & Information Retrieval interface, featuring live search queries,
grounded answers, explainable confidence badges, contradiction alerts, and verified source citations.
"""

import html
import time
from typing import Optional, List
import streamlit as st

from search.pipeline import SearchPipeline, SearchPipelineResult
from crawler.database import CrawlDatabase


SEARCH_PRESETS = {
    "⚛️ Quantum Computing": "latest developments in quantum computing",
    "🔬 Post-Quantum Cryptography": "post-quantum cryptography standards NIST",
    "🤖 Multi-Agent LLMs": "large language model autonomous multi-agent architectures 2026",
    "🔭 James Webb Discoveries": "James Webb Space Telescope recent exoplanet discoveries",
    "⚡ Solid-State Batteries": "solid-state battery commercialization timeline and density",
    "🐍 Python History & Creator": "who created Python programming language and when",
}


def render_search_view(pipeline: SearchPipeline, db: CrawlDatabase):
    """Renders the complete web search and grounded answer interface."""

    # 1. Search Query Deck & Preset Selector
    st.markdown("""
        <div class="crawl-command-bar" style="border-top: 2px solid #38BDF8; margin-top: 0.3rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.55rem; flex-wrap: wrap; gap: 0.5rem;">
                <div style="font-size: 0.78rem; font-weight: 800; letter-spacing: 0.08em; color: #FFFFFF; display: flex; align-items: center; gap: 0.45rem;">
                    🌐 WEB SEARCH &amp; INFORMATION RETRIEVAL ENGINE
                </div>
                <div style="font-size: 0.68rem; color: #38BDF8; font-family: 'JetBrains Mono', monospace; letter-spacing: 0.05em;">
                    FACTUAL GROUNDING // CONTRADICTION SCAN // CITATIONS
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    col_q, col_btn = st.columns([5.5, 1.5])

    with col_q:
        current_query = st.session_state.get("search_query_input", "latest developments in quantum computing")
        query_val = st.text_input(
            "Search Query",
            value=current_query,
            placeholder="Enter any topic, question, or research query across the public web...",
            key="search_query_input",
            label_visibility="collapsed",
        )

    with col_btn:
        btn_search = st.button("🔎 Search & Answer", type="primary", use_container_width=True, key="btn_run_web_search")

    # Quick Presets Row
    preset_cols = st.columns(len(SEARCH_PRESETS))
    for p_idx, (p_name, p_query) in enumerate(SEARCH_PRESETS.items()):
        with preset_cols[p_idx]:
            if st.button(p_name, key=f"btn_search_preset_{p_idx}", use_container_width=True):
                st.session_state["search_query_input"] = p_query
                st.session_state["trigger_auto_search"] = True
                st.rerun()

    # Search Configuration Expander
    with st.expander("⚙️ Search Engine & Evidence Parameters", expanded=False):
        c_prov, c_num, c_info = st.columns([2.5, 2.5, 3])
        with c_prov:
            provider_opt = st.selectbox(
                "Search Provider",
                [
                    "Auto-Select (Best Available)",
                    "Google Custom Search JSON API",
                    "Multi-Engine Open Index (Bing + Open Web)",
                ],
                index=0,
                key="search_provider_choice",
                help="Google uses official API if GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID are configured in environment or secrets. Multi-Engine operates out-of-the-box without keys.",
            )
        with c_num:
            num_sources = st.slider(
                "Max Sources to Fetch & Verify",
                min_value=3,
                max_value=15,
                value=8,
                step=1,
                key="search_num_sources",
                help="Higher values cross-check more independent sources for stronger corroboration.",
            )
        with c_info:
            google_avail = pipeline.google_provider.is_available()
            badge_text = "🟢 Active (Keys Found)" if google_avail else "🟡 Fallback (Zero-Config Open Engine Active)"
            st.markdown(f"""
                <div style="font-size: 0.74rem; color: #94A3B8; padding-top: 1.4rem;">
                    Google API Status: <b style="color: {'#22C55E' if google_avail else '#F59E0B'};">{badge_text}</b>
                </div>
            """, unsafe_allow_html=True)

    # Trigger Search Execution
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

        # Execute pipeline with live status tracker
        with st.status(f"🔎 Researching: \"{clean_q}\" across the public web...", expanded=True) as status:
            progress_bar = st.progress(0.0)

            def _update_ui(msg: str, pct: float):
                status.write(f"▸ {msg}")
                progress_bar.progress(min(1.0, pct))

            search_result = pipeline.run(
                query=clean_q,
                num_sources=num_sources,
                provider_preference=pref,
                progress_callback=_update_ui,
            )
            status.update(label=f"✓ Research complete ({search_result.total_elapsed:.2f}s) — Grounded answer ready", state="complete", expanded=False)

        st.session_state["active_search_result"] = search_result

    # 2. Render Results if Available
    active_res: Optional[SearchPipelineResult] = st.session_state.get("active_search_result")

    if not active_res:
        # Standby Guidance
        st.markdown("""
            <div class="standby-panel-glass" style="margin-top: 1.2rem;">
                <div style="font-size: 0.72rem; font-weight: 700; color: #38BDF8; letter-spacing: 0.09em; text-transform: uppercase; margin-bottom: 0.3rem;">
                    💡 REAL-TIME WEB SEARCH &amp; INFORMATION RETRIEVAL
                </div>
                <h3 style="color: #FFFFFF; font-weight: 800; margin-top: 0; margin-bottom: 0.4rem;">
                    Evidence-Backed Information Engine
                </h3>
                <p style="color: #94A3B8; font-size: 0.88rem; line-height: 1.6; margin-bottom: 0.8rem;">
                    Enter any question or research query above. The system discovers authoritative web sources,
                    fetches live pages, extracts and scores answering passages, cross-checks facts across independent domains,
                    identifies contradictions, and synthesizes a grounded answer with strict source citations.
                </p>
                <div style="font-size: 0.74rem; color: #64748B; line-height: 1.4;">
                    🔒 <b>Factual Integrity Guarantee:</b> The engine never displays "100% accurate". Instead, it provides explainable confidence ratings,
                    source diversity metrics, explicit contradiction alerts, and transparent citations linking back to original sources.
                </div>
            </div>
        """, unsafe_allow_html=True)
        return

    answer = active_res.answer
    confidence = active_res.confidence
    verification = active_res.verification

    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)

    # 3. Grounding & Confidence Telemetry Bar
    badge_label = confidence.badge_label if confidence else "🟡 Moderately Supported"
    conf_score = confidence.score if confidence else 0.65
    ind_domains = len(verification.get("independent_domains", [])) if verification else len(active_res.ranked_results)
    contradictions = verification.get("contradictions", []) if verification else []
    has_conflicts = len(contradictions) > 0

    col_b1, col_b2, col_b3, col_b4 = st.columns([2.5, 2, 2, 2])

    with col_b1:
        st.markdown(f"""
            <div class="kpi-card" style="padding: 0.9rem 1.1rem;">
                <div style="font-size: 0.70rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.2rem;">
                    Confidence Assessment
                </div>
                <div style="font-size: 1.1rem; font-weight: 800; color: #FFFFFF; margin-bottom: 0.2rem;">
                    {badge_label}
                </div>
                <div style="font-size: 0.70rem; color: #64748B;">
                    Multi-source cross-corroboration
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col_b2:
        st.markdown(f"""
            <div class="kpi-card" style="padding: 0.9rem 1.1rem;">
                <div style="font-size: 0.70rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.2rem;">
                    Grounding Score
                </div>
                <div style="font-size: 1.3rem; font-weight: 800; color: #38BDF8; margin-bottom: 0.2rem; font-family: 'JetBrains Mono', monospace;">
                    {conf_score:.2f} <span style="font-size: 0.78rem; color: #64748B;">/ 1.00</span>
                </div>
                <div style="font-size: 0.68rem; color: #64748B;">
                    Probabilistic score (Never 100%)
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col_b3:
        st.markdown(f"""
            <div class="kpi-card" style="padding: 0.9rem 1.1rem;">
                <div style="font-size: 0.70rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.2rem;">
                    Independent Domains
                </div>
                <div style="font-size: 1.3rem; font-weight: 800; color: #A78BFA; margin-bottom: 0.2rem; font-family: 'JetBrains Mono', monospace;">
                    {ind_domains}
                </div>
                <div style="font-size: 0.68rem; color: #64748B;">
                    Distinct root web domains
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col_b4:
        st.markdown(f"""
            <div class="kpi-card" style="padding: 0.9rem 1.1rem;">
                <div style="font-size: 0.70rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.2rem;">
                    Discrepancies
                </div>
                <div style="font-size: 1.3rem; font-weight: 800; color: {'#EF4444' if has_conflicts else '#22C55E'}; margin-bottom: 0.2rem; font-family: 'JetBrains Mono', monospace;">
                    {len(contradictions)}
                </div>
                <div style="font-size: 0.68rem; color: #64748B;">
                    {'Disagreements flagged' if has_conflicts else 'Zero conflicts detected'}
                </div>
            </div>
        """, unsafe_allow_html=True)

    # 4. Confidence Rationales Accordion
    if confidence and confidence.rationales:
        with st.expander("ℹ️ Why this confidence rating? (Explainable Verification Signals)", expanded=False):
            for rat in confidence.rationales:
                st.markdown(f"▸ {rat}")

    # 5. Direct Answer Hero Card
    if answer:
        st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(56, 189, 248, 0.08) 0%, rgba(139, 92, 246, 0.05) 100%), rgba(15, 23, 42, 0.85); border: 1px solid rgba(56, 189, 248, 0.35); border-left: 4px solid #38BDF8; border-radius: 10px; padding: 1.2rem 1.5rem; margin-top: 1rem; margin-bottom: 1.2rem; box-shadow: 0 8px 32px rgba(0, 0, 0, 0.45);">
                <div style="font-size: 0.72rem; font-weight: 800; color: #38BDF8; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 0.4rem;">
                    🎯 GROUNDED DIRECT ANSWER
                </div>
                <div style="font-size: 1.05rem; color: #F8FAFC; line-height: 1.65; font-weight: 500;">
                    {html.escape(answer.direct_answer)}
                </div>
            </div>
        """, unsafe_allow_html=True)

    # 5b. Deep Research & Thematic Synthesis Sections
    if answer and getattr(answer, "structured_sections", None):
        st.markdown("""
            <div style="font-size: 0.76rem; font-weight: 800; letter-spacing: 0.08em; color: #38BDF8; text-transform: uppercase; margin-top: 1.2rem; margin-bottom: 0.6rem;">
                🔬 IN-DEPTH RESEARCH &amp; THEMATIC SYNTHESIS
            </div>
        """, unsafe_allow_html=True)
        for sec in answer.structured_sections:
            status_style = {
                "fully_covered": ("🟢 Corroborated", "#22C55E", "rgba(34, 197, 94, 0.12)"),
                "partially_covered": ("🟡 Single Source", "#F59E0B", "rgba(245, 158, 11, 0.12)"),
                "uncovered": ("⚪ Unverified", "#94A3B8", "rgba(148, 163, 184, 0.12)"),
            }.get(sec.get("status"), ("🟢 Supported", "#38BDF8", "rgba(56, 189, 248, 0.12)"))

            st.markdown(f"""
                <div class="kpi-card" style="padding: 1rem 1.3rem; margin-bottom: 0.8rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; flex-wrap: wrap; gap: 0.4rem;">
                        <div style="font-size: 0.94rem; font-weight: 700; color: #FFFFFF;">
                            {html.escape(sec['title'])}
                        </div>
                        <div>
                            <span style="background: {status_style[2]}; border: 1px solid {status_style[1]}; color: {status_style[1]}; padding: 0.15rem 0.55rem; border-radius: 4px; font-size: 0.68rem; font-weight: 700;">
                                {status_style[0]}
                            </span>
                        </div>
                    </div>
                    <div style="font-size: 0.88rem; color: #E2E8F0; line-height: 1.65;">
                        {html.escape(sec['content'])}
                    </div>
                </div>
            """, unsafe_allow_html=True)

    # 5c. Follow-Up Research Prompt Chips
    follow_ups = getattr(answer, "follow_up_questions", [])
    if follow_ups:
        st.markdown("""
            <div style="font-size: 0.76rem; font-weight: 800; letter-spacing: 0.08em; color: #A78BFA; text-transform: uppercase; margin-top: 1.2rem; margin-bottom: 0.5rem;">
                💡 SUGGESTED FOLLOW-UP RESEARCH
            </div>
        """, unsafe_allow_html=True)
        f_cols = st.columns(min(len(follow_ups), 4))
        for f_idx, f_query in enumerate(follow_ups[:4]):
            with f_cols[f_idx]:
                if st.button(f"🔍 {f_query}", key=f"btn_follow_up_{f_idx}", use_container_width=True):
                    st.session_state["search_query_input"] = f_query
                    st.session_state["trigger_auto_search"] = True
                    st.rerun()

    # 5d. Coverage Telemetry Expander
    coverage = getattr(active_res, "coverage", None) or getattr(answer, "coverage_report", None)
    if coverage and hasattr(coverage, "clusters") and coverage.clusters:
        with st.expander(f"🧩 Information Coverage Telemetry ({coverage.covered_facets}/{coverage.total_facets} Requirements Verified)", expanded=False):
            st.markdown(f"""
                <div style="font-size: 0.82rem; color: #94A3B8; margin-bottom: 0.6rem;">
                    The research engine decomposed your query into <b>{coverage.total_facets} factual requirements</b>.
                    Overall verified coverage ratio: <b>{int(coverage.coverage_ratio * 100)}%</b> across {ind_domains} independent domain(s).
                </div>
            """, unsafe_allow_html=True)
            for cl in coverage.clusters:
                cl_status = "🟢 Fully Corroborated" if cl.status == "fully_covered" else ("🟡 Partially Covered" if cl.status == "partially_covered" else "⚠️ Unverified")
                doms_str = ", ".join(cl.corroborating_domains) if cl.corroborating_domains else "No sources"
                st.markdown(f"""
                    <div style="background: rgba(15, 23, 42, 0.45); border-left: 3px solid #38BDF8; padding: 0.5rem 0.8rem; margin-bottom: 0.4rem; border-radius: 4px;">
                        <div style="display: flex; justify-content: space-between; font-size: 0.82rem; font-weight: 700; color: #F1F5F9;">
                            <span>{html.escape(cl.title)}</span>
                            <span>{cl_status}</span>
                        </div>
                        <div style="font-size: 0.72rem; color: #64748B; margin-top: 0.2rem;">
                            Sources: {html.escape(doms_str)} &bull; {len(cl.passages)} passage(s) extracted
                        </div>
                    </div>
                """, unsafe_allow_html=True)


    # 6. Contradictions & Disagreements (if any)
    if contradictions:
        st.markdown("""
            <div style="font-size: 0.76rem; font-weight: 800; letter-spacing: 0.08em; color: #EF4444; text-transform: uppercase; margin-bottom: 0.4rem;">
                ⚠️ SOURCE DISAGREEMENTS &amp; CONTRADICTIONS DETECTED
            </div>
        """, unsafe_allow_html=True)
        for alert in contradictions:
            st.markdown(f"""
                <div style="background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.35); border-left: 4px solid #EF4444; border-radius: 8px; padding: 0.9rem 1.2rem; margin-bottom: 0.75rem;">
                    <div style="font-weight: 700; color: #FCA5A5; font-size: 0.85rem; margin-bottom: 0.3rem;">
                        ⚠️ Disagreement on {html.escape(alert.topic_or_entity)}:
                    </div>
                    <div style="font-size: 0.82rem; color: #E2E8F0; margin-bottom: 0.3rem;">
                        - <b>{html.escape(alert.source_a_domain)}</b> reports: <i>"{html.escape(alert.claim_a)}"</i>
                    </div>
                    <div style="font-size: 0.82rem; color: #E2E8F0; margin-bottom: 0.3rem;">
                        - <b>{html.escape(alert.source_b_domain)}</b> reports: <i>"{html.escape(alert.claim_b)}"</i>
                    </div>
                    <div style="font-size: 0.74rem; color: #94A3B8; margin-top: 0.4rem;">
                        {html.escape(alert.explanation)}
                    </div>
                </div>
            """, unsafe_allow_html=True)

    # 7. Key Findings & Supporting Evidence
    if answer and answer.key_findings:
        st.markdown("""
            <div style="font-size: 0.76rem; font-weight: 800; letter-spacing: 0.08em; color: #22D3EE; text-transform: uppercase; margin-top: 1rem; margin-bottom: 0.5rem;">
                🔍 KEY EVIDENCE FINDINGS &amp; CITATIONS
            </div>
        """, unsafe_allow_html=True)
        for finding in answer.key_findings:
            st.markdown(f"""
                <div style="background: rgba(15, 23, 42, 0.65); border: 1px solid rgba(255, 255, 255, 0.08); border-left: 3px solid #8B5CF6; border-radius: 6px; padding: 0.75rem 1rem; margin-bottom: 0.5rem; font-size: 0.86rem; color: #E2E8F0; line-height: 1.5;">
                    {html.escape(finding)}
                </div>
            """, unsafe_allow_html=True)

    # 8. Sources & Verified References
    citations = answer.citations if answer else []
    if citations:
        st.markdown("""
            <div style="font-size: 0.76rem; font-weight: 800; letter-spacing: 0.08em; color: #22D3EE; text-transform: uppercase; margin-top: 1.4rem; margin-bottom: 0.6rem;">
                📚 RETRIEVED SOURCES &amp; VERIFIED CITATIONS
            </div>
        """, unsafe_allow_html=True)

        for c in citations:
            safe_url = html.escape(c.url)
            safe_title = html.escape(c.title)
            safe_quote = html.escape(c.sample_quote) if c.sample_quote else ""
            date_str = f" · 📅 {c.published_date}" if c.published_date else ""

            st.markdown(f"""
                <div class="kpi-card" style="padding: 0.95rem 1.2rem; margin-bottom: 0.75rem;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.4rem;">
                        <div style="font-size: 0.92rem; font-weight: 700; color: #FFFFFF;">
                            <span style="color: #38BDF8; font-family: 'JetBrains Mono', monospace; font-weight: 800; margin-right: 0.35rem;">[{c.index}]</span>
                            {safe_title}
                        </div>
                        <div>
                            <span style="background: rgba(34, 211, 238, 0.12); border: 1px solid #22D3EE; color: #22D3EE; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.68rem; font-weight: 700;">
                                {c.source_type}
                            </span>
                        </div>
                    </div>
                    <div style="font-size: 0.75rem; color: #94A3B8; margin-bottom: 0.5rem; font-family: 'JetBrains Mono', monospace;">
                        <b>{c.domain}</b>{date_str} &bull; <a href="{safe_url}" target="_blank" style="color: #38BDF8; text-decoration: underline;">Open original source ↗</a>
                    </div>
                    {f'<div style="font-size: 0.78rem; color: #CBD5E1; font-style: italic; background: rgba(0,0,0,0.25); padding: 0.5rem 0.75rem; border-radius: 4px; border-left: 2px solid #64748B;">"{safe_quote}"</div>' if safe_quote else ''}
                </div>
            """, unsafe_allow_html=True)

    # 9. Grounding Caveats
    if answer and answer.caveats:
        st.markdown("<div style='margin-top: 1.2rem;'></div>", unsafe_allow_html=True)
        with st.expander("ℹ️ Grounding Guarantees & Verification Caveats", expanded=False):
            for cav in answer.caveats:
                st.markdown(f"- *{cav}*")


def render_search_history_view(db: CrawlDatabase):
    """Render SQLite history table for past web searches and evidence retrieval sessions."""
    st.markdown("""
        <div style="font-size: 0.76rem; font-weight: 800; letter-spacing: 0.08em; color: #38BDF8; text-transform: uppercase; margin-top: 0.4rem; margin-bottom: 0.4rem;">
            📜 PERSISTED WEB SEARCH &amp; GROUNDING HISTORY
        </div>
        <div style="font-size: 0.82rem; color: #94A3B8; margin-bottom: 1rem;">
            Review previously researched queries, confidence scores, and factual answers stored locally in SQLite.
        </div>
    """, unsafe_allow_html=True)

    records = db.get_search_history(limit=30)
    if not records:
        st.info("No search history recorded yet. Execute a web search query to start recording history.")
        return

    col_hdr, col_clr = st.columns([5, 2])
    with col_hdr:
        st.caption(f"Showing last {len(records)} search sessions.")
    with col_clr:
        if st.button("🧹 Clear All Search History", key="btn_clear_search_hist", use_container_width=True):
            db.clear_search_history()
            st.success("Search history cleared.")
            st.rerun()

    for item in records:
        h_id = item["id"]
        q_text = html.escape(item["query"])
        time_str = item["timestamp"][:19].replace("T", " ")
        badge = item.get("confidence_badge") or "🟡 Moderately Supported"
        score = item.get("confidence_score") or 0.65
        ans = html.escape(item.get("direct_answer") or "No answer synthesized.")

        st.markdown(f"""
            <div class="kpi-card" style="padding: 0.95rem 1.2rem; margin-bottom: 0.75rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem; flex-wrap: wrap; gap: 0.4rem;">
                    <div style="font-size: 0.96rem; font-weight: 800; color: #FFFFFF;">
                        🔎 "{q_text}"
                    </div>
                    <div>
                        <span style="font-size: 0.72rem; color: #38BDF8; font-family: 'JetBrains Mono', monospace; font-weight: 700; margin-right: 0.6rem;">
                            Score: {score:.2f}
                        </span>
                        <span style="font-size: 0.72rem; color: #CBD5E1;">
                            {badge}
                        </span>
                    </div>
                </div>
                <div style="font-size: 0.74rem; color: #94A3B8; margin-bottom: 0.5rem; font-family: 'JetBrains Mono', monospace;">
                    📅 {time_str} &bull; Engine: {item.get('provider_name', 'Web')} &bull; Sources: {item.get('results_count', 0)}
                </div>
                <div style="font-size: 0.84rem; color: #E2E8F0; line-height: 1.5; margin-bottom: 0.5rem;">
                    {ans}
                </div>
            </div>
        """, unsafe_allow_html=True)

        col_act1, col_act2 = st.columns([3, 1])
        with col_act1:
            q_label = item['query'][:35] + "..." if len(item['query']) > 35 else item['query']
            if st.button(f"⚡ Re-run \"{q_label}\"", key=f"btn_rerun_h_{h_id}", use_container_width=True):
                st.session_state["search_query_input"] = item["query"]
                st.session_state["trigger_auto_search"] = True
                st.rerun()
        with col_act2:
            if st.button("🗑️ Delete", key=f"btn_del_h_{h_id}", use_container_width=True):
                db.delete_search_history(h_id)
                st.rerun()
