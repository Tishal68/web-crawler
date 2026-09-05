"""
Source Inspector Component.
Provides deep-dive inspection into retrieved web pages, extracted passages,
heading hierarchies, publication dates, and evidence relevance scores.
"""

import html
from typing import Optional, List
import streamlit as st
from search.pipeline import SearchPipelineResult
from evidence.models import ExtractedPageEvidence, EvidencePassage


def render_source_inspector(search_result: Optional[SearchPipelineResult] = None):
    """Render interactive inspector for all extracted source evidence."""
    if not search_result or not search_result.extracted_evidence:
        st.markdown("""
            <div class="standby-panel-glass" style="margin-top: 1rem;">
                <div style="font-size: 0.72rem; font-weight: 700; color: #22D3EE; letter-spacing: 0.09em; text-transform: uppercase; margin-bottom: 0.3rem;">
                    🔍 SOURCE INSPECTOR // STANDBY
                </div>
                <h4 style="color: #FFFFFF; font-weight: 700; margin-top: 0; margin-bottom: 0.4rem;">
                    No Active Search Evidence Loaded
                </h4>
                <p style="color: #94A3B8; font-size: 0.85rem; line-height: 1.5; margin-bottom: 0;">
                    Execute a web search query in the <b>🔎 Web Search &amp; Answers</b> tab to inspect the full text passages,
                    heading hierarchies, and authority ratings extracted across independent sources.
                </p>
            </div>
        """, unsafe_allow_html=True)
        return

    st.markdown("""
        <div style="font-size: 0.76rem; font-weight: 800; letter-spacing: 0.08em; color: #22D3EE; text-transform: uppercase; margin-top: 0.5rem; margin-bottom: 0.4rem;">
            🔍 DEEP SOURCE &amp; PASSAGE EVIDENCE INSPECTOR
        </div>
        <div style="font-size: 0.82rem; color: #94A3B8; margin-bottom: 1rem;">
            Inspect original text passages extracted from retrieved web pages, verify heading contexts, and check passage relevance scores.
        </div>
    """, unsafe_allow_html=True)

    sources = search_result.extracted_evidence
    source_labels = [
        f"[{idx + 1}] {s.domain} — {s.title[:45]}..." if len(s.title) > 45 else f"[{idx + 1}] {s.domain} — {s.title}"
        for idx, s in enumerate(sources)
    ]

    selected_label = st.selectbox(
        "Select Source to Inspect",
        source_labels,
        key="inspector_source_select",
    )
    selected_idx = source_labels.index(selected_label)
    target_source: ExtractedPageEvidence = sources[selected_idx]

    # Source Telemetry Card
    date_display = target_source.published_date or "Not specified in metadata"
    status_color = "#22C55E" if target_source.fetch_success else "#F59E0B"
    status_text = "Page Fetched & Parsed (200 OK)" if target_source.fetch_success else f"Search Snippet Fallback ({target_source.error_message or 'Fetch Error'})"

    safe_url = html.escape(target_source.url)
    safe_title = html.escape(target_source.title)

    st.markdown(f"""
        <div class="kpi-card" style="padding: 1.1rem 1.3rem; margin-bottom: 1.2rem;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 0.8rem; margin-bottom: 0.8rem;">
                <div>
                    <div style="font-size: 0.70rem; font-weight: 700; color: #22D3EE; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 0.2rem;">
                        SOURCE [{selected_idx + 1}] TELEMETRY
                    </div>
                    <div style="font-size: 1.1rem; font-weight: 800; color: #FFFFFF; margin-bottom: 0.3rem;">
                        {safe_title}
                    </div>
                    <div style="font-size: 0.78rem; font-family: 'JetBrains Mono', monospace; word-break: break-all;">
                        <a href="{safe_url}" target="_blank" style="color: #38BDF8; text-decoration: underline;">
                            {safe_url} ↗
                        </a>
                    </div>
                </div>
                <div style="text-align: right;">
                    <span style="background: rgba(34, 211, 238, 0.12); border: 1px solid #22D3EE; color: #22D3EE; padding: 0.25rem 0.6rem; border-radius: 4px; font-size: 0.72rem; font-weight: 700;">
                        {target_source.source_type}
                    </span>
                    <div style="font-size: 0.72rem; color: {status_color}; font-weight: 600; margin-top: 0.4rem;">
                        ● {status_text}
                    </div>
                </div>
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.8rem; border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 0.8rem;">
                <div>
                    <span style="color: #64748B; font-size: 0.72rem; text-transform: uppercase;">Domain:</span>
                    <div style="color: #F8FAFC; font-weight: 600; font-size: 0.82rem;">{target_source.domain}</div>
                </div>
                <div>
                    <span style="color: #64748B; font-size: 0.72rem; text-transform: uppercase;">Publication Date:</span>
                    <div style="color: #F8FAFC; font-weight: 600; font-size: 0.82rem;">{date_display}</div>
                </div>
                <div>
                    <span style="color: #64748B; font-size: 0.72rem; text-transform: uppercase;">Extracted Passages:</span>
                    <div style="color: #22D3EE; font-weight: 700; font-size: 0.82rem;">{len(target_source.passages)} blocks</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Passages Filter / Search
    filter_q = st.text_input(
        "Filter Passages by Keyword",
        placeholder="Type to filter passages from this source...",
        key="inspector_passage_filter",
    )

    passages = target_source.passages
    if filter_q.strip():
        q_low = filter_q.strip().lower()
        passages = [p for p in passages if q_low in p.text.lower() or (p.heading_context and q_low in p.heading_context.lower())]

    st.markdown(f"""
        <div style="font-size: 0.72rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; margin-bottom: 0.6rem;">
            Showing {len(passages)} Extracted Passage(s)
        </div>
    """, unsafe_allow_html=True)

    if not passages:
        st.info("No passages matched the filter keyword.")
        return

    for p_idx, p in enumerate(passages, start=1):
        heading_badge = f"<span style='background: rgba(139, 92, 246, 0.18); border: 1px solid #8B5CF6; color: #C4B5FD; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.68rem; font-weight: 700;'>§ {html.escape(p.heading_context)}</span>" if p.heading_context else ""
        rel_color = "#22C55E" if p.relevance_score >= 0.6 else ("#F59E0B" if p.relevance_score >= 0.3 else "#94A3B8")
        safe_text = html.escape(p.text)

        st.markdown(f"""
            <div style="background: rgba(15, 23, 42, 0.75); border: 1px solid rgba(255, 255, 255, 0.08); border-left: 3px solid #22D3EE; border-radius: 6px; padding: 0.85rem 1.1rem; margin-bottom: 0.65rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.45rem; flex-wrap: wrap; gap: 0.4rem;">
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <span style="color: #22D3EE; font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; font-weight: 700;">#{p_idx}</span>
                        {heading_badge}
                    </div>
                    <div style="font-size: 0.70rem; color: {rel_color}; font-family: 'JetBrains Mono', monospace; font-weight: 700;">
                        Relevance: {p.relevance_score:.2f}
                    </div>
                </div>
                <div style="color: #E2E8F0; font-size: 0.84rem; line-height: 1.55;">
                    {safe_text}
                </div>
            </div>
        """, unsafe_allow_html=True)
