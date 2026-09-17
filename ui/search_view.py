"""
Search View UI Component.
Renders the Web Search & Information Retrieval interface, featuring live search queries,
grounded answers, explainable confidence badges, contradiction alerts, and verified source citations.
"""

import html
import json
import re
import time
from typing import Optional, List
import streamlit as st
import streamlit.components.v1 as components

from search.pipeline import SearchPipeline, SearchPipelineResult
from crawler.database import CrawlDatabase
from answer.word_count import count_words


def format_text_with_citations(raw_text: str) -> str:
    """Safely escape text for HTML, parse bold tags, and format [1], [2] citations into interactive clickable badges."""
    if not raw_text:
        return ""
    escaped = html.escape(raw_text)
    # Convert markdown bold **text** to styled <b>
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b style='color: #F8FAFC; font-weight: 700;'>\1</b>", escaped)
    def _rep(m):
        sid = m.group(1)
        return (
            f'<a href="#source-{sid}" target="_parent" class="cyber-citation-badge">[{sid}]</a>'
        )
    return re.sub(r"\[(\d+)\]", _rep, escaped)


SEARCH_PRESETS = {
    "⚛️ Quantum Computing": "latest developments in quantum computing",
    "🔬 Post-Quantum Cryptography": "post-quantum cryptography standards NIST",
    "🤖 Multi-Agent LLMs": "large language model autonomous multi-agent architectures 2026",
    "🔭 James Webb Discoveries": "James Webb Space Telescope recent exoplanet discoveries",
    "⚡ Solid-State Batteries": "solid-state battery commercialization timeline and density",
    "🐍 Python History & Creator": "who created Python programming language and when",
}

RADAR_QUERIES = list(SEARCH_PRESETS.values())


def render_real_input_cyber_animator():
    """Renders the Real Search Input Kinetic Typing Animator & Web Audio SFX Engine.
    Operates directly on the real search box (div[data-testid='stTextInput'] input)
    with zero visible demo windows, preserving native text, caret, selection, and keyboard navigation.
    """
    animator_html = """
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
      html, body { width: 0; height: 0; margin: 0; padding: 0; overflow: hidden; }
    </style>
    </head>
    <body>
    <script>
      (function() {
        let audioCtx = null;
        function getAudioContext() {
          if (!audioCtx) {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
          }
          if (audioCtx.state === 'suspended') {
            audioCtx.resume();
          }
          return audioCtx;
        }

        function playSound(type) {
          try {
            const ctx = getAudioContext();
            const now = ctx.currentTime;
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();

            if (type === 'space') {
              osc.type = 'triangle';
              osc.frequency.setValueAtTime(200, now);
              osc.frequency.exponentialRampToValueAtTime(75, now + 0.05);
              gain.gain.setValueAtTime(0.08, now);
              gain.gain.exponentialRampToValueAtTime(0.001, now + 0.05);
              osc.connect(gain);
              gain.connect(ctx.destination);
              osc.start(now);
              osc.stop(now + 0.05);
            } else if (type === 'backspace') {
              osc.type = 'sine';
              osc.frequency.setValueAtTime(900, now);
              osc.frequency.exponentialRampToValueAtTime(300, now + 0.04);
              gain.gain.setValueAtTime(0.05, now);
              gain.gain.exponentialRampToValueAtTime(0.001, now + 0.04);
              osc.connect(gain);
              gain.connect(ctx.destination);
              osc.start(now);
              osc.stop(now + 0.04);
            } else if (type === 'enter') {
              const osc2 = ctx.createOscillator();
              const gain2 = ctx.createGain();
              osc.type = 'sine';
              osc2.type = 'sine';
              osc.frequency.setValueAtTime(520, now);
              osc2.frequency.setValueAtTime(1040, now);
              gain.gain.setValueAtTime(0.06, now);
              gain.gain.exponentialRampToValueAtTime(0.001, now + 0.15);
              gain2.gain.setValueAtTime(0.04, now);
              gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.15);
              osc.connect(gain);
              gain.connect(ctx.destination);
              osc2.connect(gain2);
              gain2.connect(ctx.destination);
              osc.start(now);
              osc.stop(now + 0.15);
              osc2.start(now);
              osc2.stop(now + 0.15);
            } else {
              osc.type = 'sine';
              const freq = 850 + Math.random() * 400;
              osc.frequency.setValueAtTime(freq, now);
              osc.frequency.exponentialRampToValueAtTime(300, now + 0.035);
              gain.gain.setValueAtTime(0.04, now);
              gain.gain.exponentialRampToValueAtTime(0.001, now + 0.035);
              osc.connect(gain);
              gain.connect(ctx.destination);
              osc.start(now);
              osc.stop(now + 0.035);
            }
          } catch (e) {}
        }

        function initInput() {
          try {
            const parentDoc = window.parent.document;
            // Mark the iframe container so parent CSS collapses it completely
            if (window.frameElement) {
              window.frameElement.setAttribute("data-testid", "cyber-script-frame");
              window.frameElement.style.display = "none";
              window.frameElement.style.height = "0";
              window.frameElement.style.margin = "0";
              window.frameElement.style.padding = "0";
              const compParent = window.frameElement.closest("div[data-testid='stCustomComponentV1']");
              if (compParent) {
                compParent.style.display = "none";
                compParent.style.height = "0";
                compParent.style.margin = "0";
                compParent.style.padding = "0";
              }
            }

            const inputContainers = parentDoc.querySelectorAll("div[data-testid='stTextInput']");
            inputContainers.forEach((container) => {
              const input = container.querySelector("input");
              if (!input || input.__cyberKineticBound) return;
              input.__cyberKineticBound = true;

              container.style.position = "relative";

              let popLayer = container.querySelector(".cyber-pop-layer");
              if (!popLayer) {
                popLayer = parentDoc.createElement("div");
                popLayer.className = "cyber-pop-layer";
                container.appendChild(popLayer);
              }

              const canvas = parentDoc.createElement("canvas");
              const ctx = canvas.getContext("2d");

              input.addEventListener("keydown", (e) => {
                let soundType = "char";
                if (e.key === " ") soundType = "space";
                else if (e.key === "Backspace") soundType = "backspace";
                else if (e.key === "Enter") soundType = "enter";

                playSound(soundType);
                input.classList.add("cyber-typing-active");
                setTimeout(() => input.classList.remove("cyber-typing-active"), 250);

                if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
                  const compStyle = window.parent.getComputedStyle(input);
                  ctx.font = `${compStyle.fontSize} ${compStyle.fontFamily}`;

                  const caretPos = input.selectionStart || 0;
                  const textBefore = (input.value || "").substring(0, caretPos);
                  const textMetrics = ctx.measureText(textBefore);

                  const paddingLeft = parseFloat(compStyle.paddingLeft) || 16;
                  const paddingTop = parseFloat(compStyle.paddingTop) || 12;
                  const charX = paddingLeft + textMetrics.width - input.scrollLeft;
                  const charY = paddingTop;

                  const pop = parentDoc.createElement("span");
                  pop.className = "cyber-kinetic-pop";
                  pop.textContent = e.key;
                  pop.style.left = `${charX}px`;
                  pop.style.top = `${charY}px`;

                  popLayer.appendChild(pop);
                  setTimeout(() => pop.remove(), 280);
                }
              });
            });
          } catch (e) {}
        }

        initInput();
        try {
          const parentDoc = window.parent.document;
          if (!window.parent.__cyberObserver) {
            const observer = new MutationObserver(() => {
              initInput();
            });
            observer.observe(parentDoc.body, { childList: true, subtree: true });
            window.parent.__cyberObserver = observer;
          }
        } catch (e) {}
      })();
    </script>
    </body>
    </html>
    """
    components.html(animator_html, height=0)


def render_futuristic_direct_answer(active_res: SearchPipelineResult):
    """Renders the Direct Grounded Answer in a futuristic cyberpunk streaming typewriter terminal."""
    answer = active_res.answer
    if not answer or not answer.direct_answer:
        return

    confidence = active_res.confidence
    verification = active_res.verification
    conf_score = confidence.score if confidence else 0.65
    ind_domains = len(verification.get("independent_domains", [])) if verification else len(active_res.ranked_results)
    citations_count = len(answer.citations)
    elapsed = active_res.total_elapsed

    actual_words = count_words(answer.direct_answer)
    raw_req = getattr(answer, "requested_word_count", None)
    req_words = int(raw_req) if raw_req else None

    if req_words:
        word_count_pill = f'<span class="stat-pill" style="color: #38BDF8; border-color: rgba(56, 189, 248, 0.5); font-weight: 800;">📝 {actual_words} / {req_words} words</span>'
        word_count_foot = f'<span class="foot-tag">📝 WORD COUNT: {actual_words} / {req_words}</span>'
    else:
        word_count_pill = f'<span class="stat-pill">📝 {actual_words} words</span>'
        word_count_foot = f'<span class="foot-tag">📝 WORD COUNT: {actual_words}</span>'

    formatted_direct_answer = format_text_with_citations(answer.direct_answer)
    safe_json_answer = json.dumps(formatted_direct_answer)

    # Calculate optimal component container height based on length
    char_len = len(answer.direct_answer)
    est_lines = max(2, char_len // 52 + 1)
    calc_height = max(210, min(560, 130 + est_lines * 30))

    terminal_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
      * {{ box-sizing: border-box; margin: 0; padding: 0; }}
      body {{
        background: transparent;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        color: #F8FAFC;
        overflow-y: auto;
        padding: 0.15rem 0;
      }}
      .cyber-terminal-box {{
        background: linear-gradient(135deg, rgba(56, 189, 248, 0.08) 0%, rgba(139, 92, 246, 0.05) 100%), rgba(11, 16, 32, 0.95);
        border: 1px solid rgba(56, 189, 248, 0.40);
        border-left: 4px solid #38BDF8;
        border-radius: 10px;
        padding: 1.1rem 1.4rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5), 0 0 20px rgba(56, 189, 248, 0.12), inset 0 0 15px rgba(56, 189, 248, 0.03);
        position: relative;
      }}
      .terminal-top {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid rgba(56, 189, 248, 0.20);
        padding-bottom: 0.55rem;
        margin-bottom: 0.85rem;
        flex-wrap: wrap;
        gap: 0.5rem;
      }}
      .terminal-tag-group {{
        display: flex;
        align-items: center;
        gap: 0.45rem;
        font-size: 0.72rem;
        font-weight: 800;
        color: #38BDF8;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        font-family: 'JetBrains Mono', Consolas, monospace;
      }}
      .pulse-dot {{
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #22C55E;
        box-shadow: 0 0 10px #22C55E, 0 0 18px rgba(34, 197, 94, 0.6);
        animation: pGlow 1.5s infinite;
      }}
      .terminal-controls {{
        display: flex;
        align-items: center;
        gap: 0.45rem;
        flex-wrap: wrap;
      }}
      .stat-pill {{
        font-size: 0.68rem;
        font-family: 'JetBrains Mono', Consolas, monospace;
        background: rgba(56, 189, 248, 0.12);
        border: 1px solid rgba(56, 189, 248, 0.30);
        color: #38BDF8;
        padding: 0.15rem 0.5rem;
        border-radius: 4px;
        font-weight: 700;
      }}
      .action-btn {{
        font-size: 0.68rem;
        font-family: 'JetBrains Mono', Consolas, monospace;
        background: rgba(139, 92, 246, 0.18);
        border: 1px solid rgba(139, 92, 246, 0.45);
        color: #C4B5FD;
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
        font-weight: 700;
        cursor: pointer;
        transition: all 0.2s ease;
      }}
      .action-btn:hover {{
        background: rgba(139, 92, 246, 0.35);
        color: #FFFFFF;
        box-shadow: 0 0 12px rgba(139, 92, 246, 0.4);
      }}
      .terminal-body {{
        font-size: 1.05rem;
        color: #F8FAFC;
        line-height: 1.7;
        font-weight: 500;
        letter-spacing: 0.01em;
        min-height: 2.8rem;
      }}
      .cyber-cursor {{
        display: inline-block;
        color: #38BDF8;
        font-weight: 900;
        text-shadow: 0 0 8px #38BDF8, 0 0 18px rgba(56, 189, 248, 0.7);
        animation: cBlink 0.8s infinite;
        margin-left: 2px;
        vertical-align: baseline;
      }}
      .cyber-citation-badge {{
        background: rgba(56, 189, 248, 0.22);
        border: 1px solid rgba(56, 189, 248, 0.45);
        color: #38BDF8;
        padding: 0.1rem 0.42rem;
        border-radius: 4px;
        text-decoration: none;
        font-weight: 700;
        font-size: 0.76rem;
        margin: 0 0.2rem;
        font-family: 'JetBrains Mono', Consolas, monospace;
        display: inline-block;
        transition: all 0.2s ease;
      }}
      .cyber-citation-badge:hover {{
        background: rgba(56, 189, 248, 0.45);
        color: #FFFFFF;
        box-shadow: 0 0 12px rgba(56, 189, 248, 0.6);
      }}
      .terminal-bottom {{
        display: flex;
        justify-content: flex-start;
        gap: 1.2rem;
        margin-top: 0.95rem;
        padding-top: 0.65rem;
        border-top: 1px solid rgba(255, 255, 255, 0.06);
        flex-wrap: wrap;
      }}
      .foot-tag {{
        font-size: 0.65rem;
        font-family: 'JetBrains Mono', Consolas, monospace;
        color: #64748B;
        letter-spacing: 0.05em;
      }}
      @keyframes cBlink {{ 0%, 49% {{ opacity: 1; }} 50%, 100% {{ opacity: 0; }} }}
      @keyframes pGlow {{ 0%, 100% {{ transform: scale(0.95); opacity: 0.8; }} 50% {{ transform: scale(1.2); opacity: 1; }} }}
    </style>
    </head>
    <body>
    <div class="cyber-terminal-box">
      <div class="terminal-top">
        <div class="terminal-tag-group">
          <span id="statusPulse" class="pulse-dot"></span>
          <span id="statusText">🎯 GROUNDED DIRECT ANSWER // NEURAL STREAM</span>
        </div>
        <div class="terminal-controls">
          <span class="stat-pill">Score: {conf_score:.2f}</span>
          <span class="stat-pill">⚡ {citations_count} Sources</span>
          {word_count_pill}
          <button id="btnInstant" class="action-btn" onclick="showInstant()">⚡ Instant View</button>
          <button id="btnReplay" class="action-btn" onclick="replayStream()">↺ Replay</button>
        </div>
      </div>
      <div id="rawContent" style="display: none;"></div>
      <div class="terminal-body">
        <span id="terminalText"></span><span id="cyberCursor" class="cyber-cursor">█</span>
      </div>
      <div class="terminal-bottom">
        <span class="foot-tag">🔒 PROBABILISTIC GROUNDING (NEVER 100%)</span>
        <span class="foot-tag">🌐 {ind_domains} INDEPENDENT DOMAINS VERIFIED</span>
        {word_count_foot}
        <span class="foot-tag">⏱️ {elapsed:.2f}s TOTAL PIPELINE LATENCY</span>
      </div>
    </div>
    <script>
      const formattedHtml = {safe_json_answer};
      const raw = document.getElementById("rawContent");
      const term = document.getElementById("terminalText");
      const cursor = document.getElementById("cyberCursor");
      const statusTxt = document.getElementById("statusText");
      let timer = null;

      raw.innerHTML = formattedHtml;

      function buildSteps() {{
        const steps = [];
        function traverse(node, container) {{
          if (node.nodeType === Node.TEXT_NODE) {{
            const txt = node.nodeValue;
            for (let i = 0; i < txt.length; i++) {{
              steps.push({{ type: 'char', char: txt[i], container: container }});
            }}
          }} else if (node.nodeType === Node.ELEMENT_NODE) {{
            if (node.tagName === 'A' && node.classList.contains('cyber-citation-badge')) {{
              const clone = node.cloneNode(true);
              steps.push({{ type: 'node', node: clone, container: container }});
            }} else if (node.tagName === 'BR') {{
              const clone = node.cloneNode(false);
              steps.push({{ type: 'node', node: clone, container: container }});
            }} else {{
              const clone = node.cloneNode(false);
              container.appendChild(clone);
              for (let child of node.childNodes) {{
                traverse(child, clone);
              }}
            }}
          }}
        }}
        for (let child of raw.childNodes) {{
          traverse(child, term);
        }}
        return steps;
      }}

      function finish() {{
        if (timer) clearTimeout(timer);
        term.innerHTML = raw.innerHTML;
        cursor.style.display = 'none';
        statusTxt.textContent = '✓ SYNTHESIS COMPLETE // GROUNDED EVIDENCE READY';
      }}

      function showInstant() {{
        finish();
      }}

      function replayStream() {{
        if (timer) clearTimeout(timer);
        term.innerHTML = '';
        cursor.style.display = 'inline-block';
        statusTxt.textContent = '🎯 GROUNDED DIRECT ANSWER // NEURAL STREAM';

        try {{
          const steps = buildSteps();
          let idx = 0;
          function step() {{
            if (idx >= steps.length) {{
              finish();
              return;
            }}
            const item = steps[idx];
            if (item.type === 'char') {{
              item.container.appendChild(document.createTextNode(item.char));
            }} else if (item.type === 'node') {{
              item.container.appendChild(item.node);
            }}
            idx++;
            let delay = 16;
            if (item.type === 'char') {{
              if (item.char === '.' || item.char === '!' || item.char === '?') delay = 130;
              else if (item.char === ',' || item.char === ';') delay = 50;
            }}
            timer = setTimeout(step, delay);
          }}
          step();
        }} catch (err) {{
          finish();
        }}
      }}

      replayStream();
    </script>
    <noscript>
      <div style="font-size: 1.05rem; color: #F8FAFC; line-height: 1.7;">{formatted_direct_answer}</div>
    </noscript>
    </body>
    </html>
    """
    components.html(terminal_html, height=calc_height)


def render_discovered_search_results(active_res: SearchPipelineResult):
    """Renders the real discovered web search results in structured cards with status, snippets, and domains."""
    ranked = getattr(active_res, "ranked_results", [])
    if not ranked:
        return

    # Map extracted evidence by URL for crawl status reporting
    evidence_by_url = {}
    for ev in getattr(active_res, "extracted_evidence", []):
        if ev.url:
            evidence_by_url[ev.url] = ev

    st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 1.2rem; margin-bottom: 0.6rem; flex-wrap: wrap; gap: 0.5rem;">
            <div style="font-size: 0.78rem; font-weight: 800; letter-spacing: 0.08em; color: #38BDF8; text-transform: uppercase;">
                🌐 DISCOVERED WEB SEARCH RESULTS ({len(ranked)} Sources Discovered)
            </div>
            <div style="font-size: 0.68rem; color: #94A3B8; font-family: 'JetBrains Mono', monospace;">
                SEARCH DISCOVERY ➔ EVIDENCE EXTRACTION ➔ CRAWL READY
            </div>
        </div>
    """, unsafe_allow_html=True)

    for idx, res in enumerate(ranked):
        r_rank = idx + 1
        r_title = html.escape(res.title or "Untitled Web Result")
        r_url = res.url or ""
        r_safe_url = html.escape(r_url)
        r_domain = html.escape(res.display_domain or "web")
        r_snippet = html.escape(res.snippet or "No preview snippet available for this discovered web source.")
        r_type = html.escape(getattr(res, "source_type", "Web Source"))

        ev = evidence_by_url.get(r_url)
        if ev and getattr(ev, "fetch_success", True) and not getattr(ev, "error_message", None):
            passages_count = len(getattr(ev, "passages", []))
            crawl_badge = f'<span style="background: rgba(34, 197, 94, 0.15); border: 1px solid #22C55E; color: #22C55E; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.68rem; font-weight: 700;">✓ Crawled &amp; Analyzed ({passages_count} passages)</span>'
        elif ev:
            err = getattr(ev, "error_message", None) or "Partial"
            crawl_badge = f'<span style="background: rgba(245, 158, 11, 0.15); border: 1px solid #F59E0B; color: #F59E0B; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.68rem; font-weight: 700;">⚠️ Fetch Notice ({html.escape(err)})</span>'
        else:
            crawl_badge = '<span style="background: rgba(56, 189, 248, 0.15); border: 1px solid #38BDF8; color: #38BDF8; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.68rem; font-weight: 700;">🟢 Discovered &amp; Ranked</span>'

        st.markdown(f"""
            <div class="kpi-card" style="padding: 0.95rem 1.2rem; margin-bottom: 0.75rem; border-left: 3px solid #38BDF8;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.35rem;">
                    <div style="font-size: 0.96rem; font-weight: 800; color: #FFFFFF;">
                        <span style="color: #38BDF8; font-family: 'JetBrains Mono', monospace; margin-right: 0.4rem;">[#{r_rank}]</span>
                        <a href="{r_safe_url}" target="_blank" rel="noopener noreferrer" style="color: #FFFFFF; text-decoration: none; border-bottom: 1px dotted #38BDF8;">{r_title}</a>
                    </div>
                    <div style="display: flex; gap: 0.4rem; align-items: center;">
                        <span style="background: rgba(139, 92, 246, 0.15); border: 1px solid #8B5CF6; color: #C4B5FD; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.68rem; font-weight: 700;">
                            {r_type}
                        </span>
                        {crawl_badge}
                    </div>
                </div>
                <div style="font-size: 0.74rem; color: #94A3B8; font-family: 'JetBrains Mono', monospace; margin-bottom: 0.45rem;">
                    <b>{r_domain}</b> &bull; <a href="{r_safe_url}" target="_blank" rel="noopener noreferrer" style="color: #38BDF8; text-decoration: underline;">{r_safe_url}</a>
                </div>
                <div style="font-size: 0.84rem; color: #CBD5E1; line-height: 1.5; margin-bottom: 0.4rem;">
                    {r_snippet}
                </div>
            </div>
        """, unsafe_allow_html=True)


def set_search_query_callback(query_text: str):
    """Safely updates search query and flags auto-search before widget instantiation."""
    st.session_state["search_query_input"] = query_text
    st.session_state["trigger_auto_search"] = True


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

    # Real-Time Kinetic Typing Animator & Web Audio SFX Engine (inside real search input)
    render_real_input_cyber_animator()

    col_q, col_btn = st.columns([5.5, 1.5])

    def on_search_query_submit():
        st.session_state["trigger_auto_search"] = True

    if "search_query_input" not in st.session_state:
        st.session_state["search_query_input"] = "latest developments in quantum computing"

    with col_q:
        query_val = st.text_input(
            "Search Query",
            placeholder="Enter any topic, question, or research query across the public web...",
            key="search_query_input",
            label_visibility="collapsed",
            on_change=on_search_query_submit,
        )

    with col_btn:
        btn_search = st.button("🔎 Search & Answer", type="primary", use_container_width=True, key="btn_run_web_search")

    # Quick Presets Row
    preset_cols = st.columns(len(SEARCH_PRESETS))
    for p_idx, (p_name, p_query) in enumerate(SEARCH_PRESETS.items()):
        with preset_cols[p_idx]:
            st.button(
                p_name,
                key=f"btn_search_preset_{p_idx}",
                use_container_width=True,
                on_click=set_search_query_callback,
                args=(p_query,),
            )

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

    if "search_lifecycle" not in st.session_state:
        st.session_state["search_lifecycle"] = "IDLE"

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

        st.session_state["search_lifecycle"] = "SEARCHING"
        try:
            # Execute pipeline with live status tracker
            with st.status(f"🔎 Researching: \"{clean_q}\" across the public web...", expanded=True) as status:
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

    # 4b. Discovered Web Search Results Deck (Real Search Items)
    render_discovered_search_results(active_res)

    # 5. Direct Answer Hero Card (Futuristic Cyber Typewriter Terminal)
    if answer:
        render_futuristic_direct_answer(active_res)

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

            formatted_sec = format_text_with_citations(sec.get("content", ""))
            st.markdown(f"""
                <div class="kpi-card" style="padding: 1rem 1.3rem; margin-bottom: 0.8rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; flex-wrap: wrap; gap: 0.4rem;">
                        <div style="font-size: 0.94rem; font-weight: 700; color: #FFFFFF;">
                            {html.escape(sec.get('title', ''))}
                        </div>
                        <div>
                            <span style="background: {status_style[2]}; border: 1px solid {status_style[1]}; color: {status_style[1]}; padding: 0.15rem 0.55rem; border-radius: 4px; font-size: 0.68rem; font-weight: 700;">
                                {status_style[0]}
                            </span>
                        </div>
                    </div>
                    <div style="font-size: 0.88rem; color: #E2E8F0; line-height: 1.65;">
                        {formatted_sec}
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
                st.button(
                    f"🔍 {f_query}",
                    key=f"btn_follow_up_{f_idx}",
                    use_container_width=True,
                    on_click=set_search_query_callback,
                    args=(f_query,),
                )

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

    # 7. Key Findings & Supporting Evidence (Cyber Categorized Cards)
    if answer and answer.key_findings:
        st.markdown("""
            <div style="font-size: 0.76rem; font-weight: 800; letter-spacing: 0.08em; color: #22D3EE; text-transform: uppercase; margin-top: 1rem; margin-bottom: 0.5rem;">
                🔍 KEY EVIDENCE FINDINGS &amp; CITATIONS
            </div>
        """, unsafe_allow_html=True)
        for finding in answer.key_findings:
            # Check if finding starts with categorized bold label: **Category**: rest
            cat_match = re.match(r"^\*\*([^*]+)\*\*:\s*(.+)$", finding)
            if cat_match:
                cat_name = cat_match.group(1).strip()
                cat_body = cat_match.group(2).strip()
                formatted_body = format_text_with_citations(cat_body)
                st.markdown(f"""
                    <div class="kpi-card" style="padding: 0.8rem 1.1rem; margin-bottom: 0.6rem; border-left: 3px solid #8B5CF6; display: flex; align-items: flex-start; gap: 0.65rem; flex-wrap: wrap;">
                        <span style="background: rgba(139, 92, 246, 0.18); border: 1px solid rgba(139, 92, 246, 0.45); color: #C4B5FD; padding: 0.15rem 0.55rem; border-radius: 4px; font-weight: 800; font-size: 0.70rem; font-family: 'JetBrains Mono', monospace; text-transform: uppercase; white-space: nowrap; margin-top: 0.1rem;">
                            {html.escape(cat_name)}
                        </span>
                        <div style="font-size: 0.88rem; color: #E2E8F0; line-height: 1.55; flex-grow: 1;">
                            {formatted_body}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            else:
                formatted_finding = format_text_with_citations(finding)
                st.markdown(f"""
                    <div class="kpi-card" style="padding: 0.8rem 1.1rem; margin-bottom: 0.6rem; border-left: 3px solid #8B5CF6; font-size: 0.88rem; color: #E2E8F0; line-height: 1.55;">
                        {formatted_finding}
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
            raw_url = c.url or ""
            safe_href = html.escape(raw_url, quote=True) if raw_url.startswith(("http://", "https://")) else "#"
            safe_title = html.escape(c.title or "Untitled Source")
            safe_quote = html.escape(c.sample_quote) if c.sample_quote else ""
            date_str = f" · 📅 {html.escape(c.published_date)}" if c.published_date else ""
            safe_domain = html.escape(c.domain or "")
            safe_source_type = html.escape(str(c.source_type or "Web Source"))

            st.markdown(f"""
                <div id="source-{c.index}" class="kpi-card" style="padding: 0.95rem 1.2rem; margin-bottom: 0.75rem;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.4rem;">
                        <div style="font-size: 0.92rem; font-weight: 700; color: #FFFFFF;">
                            <span style="color: #38BDF8; font-family: 'JetBrains Mono', monospace; font-weight: 800; margin-right: 0.35rem;">[{c.index}]</span>
                            {safe_title}
                        </div>
                        <div>
                            <span style="background: rgba(34, 211, 238, 0.12); border: 1px solid #22D3EE; color: #22D3EE; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.68rem; font-weight: 700;">
                                {safe_source_type}
                            </span>
                        </div>
                    </div>
                    <div style="font-size: 0.75rem; color: #94A3B8; margin-bottom: 0.5rem; font-family: 'JetBrains Mono', monospace;">
                        <b>{safe_domain}</b>{date_str} &bull; <a href="{safe_href}" target="_blank" rel="noopener noreferrer" style="color: #38BDF8; text-decoration: underline;">Open original source ↗</a>
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
        badge = html.escape(str(item.get("confidence_badge") or "🟡 Moderately Supported"))
        score = item.get("confidence_score") or 0.65
        ans = html.escape(item.get("direct_answer") or "No answer synthesized.")
        prov = html.escape(str(item.get('provider_name', 'Web')))

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
                    📅 {time_str} &bull; Engine: {prov} &bull; Sources: {item.get('results_count', 0)}
                </div>
                <div style="font-size: 0.84rem; color: #E2E8F0; line-height: 1.5; margin-bottom: 0.5rem;">
                    {ans}
                </div>
            </div>
        """, unsafe_allow_html=True)

        col_act1, col_act2 = st.columns([3, 1])
        with col_act1:
            q_label = item['query'][:35] + "..." if len(item['query']) > 35 else item['query']
            st.button(
                f"⚡ Re-run \"{q_label}\"",
                key=f"btn_rerun_h_{h_id}",
                use_container_width=True,
                on_click=set_search_query_callback,
                args=(item["query"],),
            )
        with col_act2:
            if st.button("🗑️ Delete", key=f"btn_del_h_{h_id}", use_container_width=True):
                db.delete_search_history(h_id)
                st.rerun()
