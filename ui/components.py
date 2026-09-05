"""
Futuristic Cyber-Analytics UI Components, design system, KPI cards, and glass panels.
"""

from typing import Optional, List
import html
import streamlit as st
from crawler.models import CrawlSessionSummary, PageResult


def apply_custom_styles():
    """Inject high-end cyber-analytics visual styling, glassmorphism, and neon gradients."""
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

        /* === DESIGN SYSTEM CSS VARIABLES === */
        :root {
            --bg-primary: #070A12;
            --bg-secondary: #0B1020;
            --bg-surface: rgba(15, 23, 42, 0.65);
            --glass-bg: rgba(15, 23, 42, 0.65);
            --glass-bg-hover: rgba(24, 35, 60, 0.80);
            --glass-border: rgba(255, 255, 255, 0.10);
            --glass-border-hover: rgba(34, 211, 238, 0.40);
            
            --text-primary: #F8FAFC;
            --text-secondary: #94A3B8;
            --text-muted: #64748B;
            
            --cyan: #22D3EE;
            --violet: #8B5CF6;
            --pink: #EC4899;
            --success: #22C55E;
            --danger: #F43F5E;
            --warning: #F59E0B;
            
            --glow-cyan: 0 0 25px rgba(34, 211, 238, 0.35);
            --glow-violet: 0 0 25px rgba(139, 92, 246, 0.35);
            --glow-green: 0 0 25px rgba(34, 197, 94, 0.35);
            --glow-red: 0 0 25px rgba(244, 63, 94, 0.35);
            
            --radius: 12px;
            --radius-sm: 8px;
        }

        /* === GLOBAL THEME & VISIBLE ATMOSPHERIC BACKGROUND === */
        html, body, .stApp, [data-testid="stAppViewContainer"], section.main {
            background-color: #070A12 !important;
            background-image: 
                radial-gradient(ellipse 85% 55% at 18% -5%, rgba(34, 211, 238, 0.16) 0%, transparent 60%),
                radial-gradient(ellipse 75% 55% at 85% 15%, rgba(139, 92, 246, 0.18) 0%, transparent 60%),
                radial-gradient(ellipse 65% 60% at 50% 90%, rgba(14, 165, 233, 0.12) 0%, transparent 60%),
                linear-gradient(rgba(34, 211, 238, 0.05) 1px, transparent 1px),
                linear-gradient(90deg, rgba(34, 211, 238, 0.05) 1px, transparent 1px) !important;
            background-size: 100% 100%, 100% 100%, 100% 100%, 36px 36px, 36px 36px !important;
            background-attachment: fixed !important;
            color: #F8FAFC !important;
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        }

        header[data-testid="stHeader"] {
            background: transparent !important;
        }

        /* Streamlit Content Container Spacing */
        .block-container {
            padding-top: 0.75rem !important;
            padding-bottom: 2rem !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
            max-width: 1480px !important;
        }

        /* === COMPACT CYBER HEADER BAR === */
        .cyber-header-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.01) 100%), rgba(11, 16, 32, 0.75);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.09);
            border-top: 2px solid #22D3EE;
            border-radius: var(--radius-sm);
            padding: 0.55rem 1.2rem;
            margin-bottom: 0.85rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4), 0 0 20px rgba(34, 211, 238, 0.10);
        }
        .cyber-header-left {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        .cyber-logo-glyph {
            font-size: 1.3rem;
            line-height: 1;
            filter: drop-shadow(0 0 8px #22D3EE);
        }
        .cyber-title-compact {
            font-size: 1.2rem;
            font-weight: 800;
            letter-spacing: -0.01em;
            color: #FFFFFF;
            line-height: 1;
            text-transform: uppercase;
        }
        .cyber-version-tag {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.68rem;
            font-weight: 600;
            color: #94A3B8;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 4px;
            padding: 0.2rem 0.5rem;
            letter-spacing: 0.04em;
        }
        .cyber-header-right {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        .cyber-status-pill-compact {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            background: rgba(34, 211, 238, 0.08);
            border: 1px solid rgba(34, 211, 238, 0.30);
            border-radius: 12px;
            padding: 0.25rem 0.7rem;
            font-size: 0.70rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            color: #22D3EE;
            text-transform: uppercase;
            box-shadow: 0 0 14px rgba(34, 211, 238, 0.20);
        }

        .pulse-beacon-cyan {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: #22D3EE;
            box-shadow: 0 0 10px #22D3EE;
            animation: pulse-beacon 2s infinite ease-in-out;
        }
        .pulse-beacon-green {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: #22C55E;
            box-shadow: 0 0 10px #22C55E;
            animation: pulse-beacon 2s infinite ease-in-out;
        }
        @keyframes pulse-beacon {
            0%, 100% { opacity: 1; transform: scale(1); box-shadow: 0 0 12px currentColor; }
            50% { opacity: 0.35; transform: scale(0.75); box-shadow: 0 0 3px currentColor; }
        }
        .cyber-title-gradient {
            background: linear-gradient(135deg, #22D3EE 0%, #8B5CF6 55%, #EC4899 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            filter: drop-shadow(0 0 25px rgba(34, 211, 238, 0.4));
            display: inline-block;
        }

        /* === CRAWL COMPLETION PANEL (GLASS - NO SOLID GREEN) === */
        .completion-panel-glass, .glass-status-panel, .completion-banner {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.06) 0%, rgba(255, 255, 255, 0.01) 100%), rgba(11, 16, 32, 0.80) !important;
            backdrop-filter: blur(20px) saturate(180%) !important;
            -webkit-backdrop-filter: blur(20px) saturate(180%) !important;
            border: 1px solid rgba(34, 197, 94, 0.30) !important;
            border-top: 3px solid #22C55E !important;
            border-radius: var(--radius) !important;
            padding: 1.4rem 1.8rem !important;
            margin-bottom: 2rem !important;
            box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.6), 0 0 35px rgba(34, 197, 94, 0.15), inset 0 1px 1px 0 rgba(255, 255, 255, 0.15) !important;
            position: relative;
            overflow: hidden;
        }
        .completion-panel-glass::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(34, 197, 94, 0.7), transparent);
        }
        .completion-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            padding-bottom: 0.85rem;
            margin-bottom: 1.1rem;
        }
        .completion-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.6rem;
            font-size: 0.86rem;
            font-weight: 700;
            letter-spacing: 0.09em;
            color: #22C55E;
            text-transform: uppercase;
        }
        .session-id-tag {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.76rem;
            color: #64748B;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.08);
            padding: 0.25rem 0.65rem;
            border-radius: 4px;
        }
        .seed-url-pill {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.76rem;
            color: #22D3EE;
            background: rgba(34, 211, 238, 0.08);
            border: 1px solid rgba(34, 211, 238, 0.25);
            padding: 0.25rem 0.65rem;
            border-radius: 4px;
            max-width: 420px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            display: inline-block;
        }
        .completion-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 1.4rem;
        }
        .completion-stat {
            display: flex;
            flex-direction: column;
        }
        .comp-num {
            font-size: 1.75rem;
            font-weight: 800;
            color: #FFFFFF;
            line-height: 1.1;
            font-family: 'Plus Jakarta Sans', sans-serif;
        }
        .comp-lbl {
            font-size: 0.70rem;
            font-weight: 700;
            color: #64748B;
            letter-spacing: 0.07em;
            text-transform: uppercase;
            margin-top: 0.35rem;
        }

        /* === REAL GLASSMORPHISM KPI CARDS === */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1.1rem;
            margin-bottom: 2rem;
        }
        .kpi-card, div[data-testid="stMetric"] {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0.02) 100%), rgba(15, 23, 42, 0.65) !important;
            backdrop-filter: blur(16px) saturate(180%) !important;
            -webkit-backdrop-filter: blur(16px) saturate(180%) !important;
            border: 1px solid rgba(255, 255, 255, 0.10) !important;
            border-radius: var(--radius) !important;
            padding: 1.3rem 1.2rem !important;
            position: relative;
            overflow: hidden;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.45), inset 0 1px 1px 0 rgba(255, 255, 255, 0.15) !important;
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }
        .kpi-card:hover {
            transform: translateY(-4px) !important;
            box-shadow: 0 12px 38px 0 rgba(0, 0, 0, 0.6), inset 0 1px 1px 0 rgba(255, 255, 255, 0.25) !important;
        }
        .kpi-card-cyan {
            border-top: 2px solid #22D3EE !important;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.45), 0 0 25px rgba(34, 211, 238, 0.15), inset 0 1px 1px 0 rgba(255, 255, 255, 0.15) !important;
        }
        .kpi-card-cyan:hover {
            box-shadow: 0 12px 38px 0 rgba(0, 0, 0, 0.6), 0 0 35px rgba(34, 211, 238, 0.35), inset 0 1px 1px 0 rgba(255, 255, 255, 0.25) !important;
            border-color: rgba(34, 211, 238, 0.40) !important;
        }
        .kpi-card-violet {
            border-top: 2px solid #8B5CF6 !important;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.45), 0 0 25px rgba(139, 92, 246, 0.15), inset 0 1px 1px 0 rgba(255, 255, 255, 0.15) !important;
        }
        .kpi-card-violet:hover {
            box-shadow: 0 12px 38px 0 rgba(0, 0, 0, 0.6), 0 0 35px rgba(139, 92, 246, 0.35), inset 0 1px 1px 0 rgba(255, 255, 255, 0.25) !important;
            border-color: rgba(139, 92, 246, 0.40) !important;
        }
        .kpi-card-red {
            border-top: 2px solid #F43F5E !important;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.45), 0 0 25px rgba(244, 63, 94, 0.20), inset 0 1px 1px 0 rgba(255, 255, 255, 0.15) !important;
        }
        .kpi-card-red:hover {
            box-shadow: 0 12px 38px 0 rgba(0, 0, 0, 0.6), 0 0 35px rgba(244, 63, 94, 0.40), inset 0 1px 1px 0 rgba(255, 255, 255, 0.25) !important;
            border-color: rgba(244, 63, 94, 0.40) !important;
        }
        .kpi-card-green {
            border-top: 2px solid #22C55E !important;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.45), 0 0 25px rgba(34, 197, 94, 0.15), inset 0 1px 1px 0 rgba(255, 255, 255, 0.15) !important;
        }
        .kpi-card-green:hover {
            box-shadow: 0 12px 38px 0 rgba(0, 0, 0, 0.6), 0 0 35px rgba(34, 197, 94, 0.35), inset 0 1px 1px 0 rgba(255, 255, 255, 0.25) !important;
            border-color: rgba(34, 197, 94, 0.40) !important;
        }
        .kpi-card-sky {
            border-top: 2px solid #0EA5E9 !important;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.45), 0 0 25px rgba(14, 165, 233, 0.15), inset 0 1px 1px 0 rgba(255, 255, 255, 0.15) !important;
        }
        .kpi-card-sky:hover {
            box-shadow: 0 12px 38px 0 rgba(0, 0, 0, 0.6), 0 0 35px rgba(14, 165, 233, 0.35), inset 0 1px 1px 0 rgba(255, 255, 255, 0.25) !important;
            border-color: rgba(14, 165, 233, 0.40) !important;
        }
        .kpi-card-purple {
            border-top: 2px solid #C084FC !important;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.45), 0 0 25px rgba(192, 132, 252, 0.15), inset 0 1px 1px 0 rgba(255, 255, 255, 0.15) !important;
        }
        .kpi-card-purple:hover {
            box-shadow: 0 12px 38px 0 rgba(0, 0, 0, 0.6), 0 0 35px rgba(192, 132, 252, 0.35), inset 0 1px 1px 0 rgba(255, 255, 255, 0.25) !important;
            border-color: rgba(192, 132, 252, 0.40) !important;
        }

        .kpi-header {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 0.75rem;
        }
        .kpi-dot {
            font-size: 0.85rem;
            line-height: 1;
        }
        .dot-cyan { color: #22D3EE; text-shadow: 0 0 10px rgba(34, 211, 238, 0.8); }
        .dot-violet { color: #8B5CF6; text-shadow: 0 0 10px rgba(139, 92, 246, 0.8); }
        .dot-red { color: #F43F5E; text-shadow: 0 0 10px rgba(244, 63, 94, 0.8); }
        .dot-green { color: #22C55E; text-shadow: 0 0 10px rgba(34, 197, 94, 0.8); }
        .dot-sky { color: #0EA5E9; text-shadow: 0 0 10px rgba(14, 165, 233, 0.8); }
        .dot-purple { color: #C084FC; text-shadow: 0 0 10px rgba(192, 132, 252, 0.8); }

        .kpi-label {
            font-size: 0.74rem;
            font-weight: 700;
            letter-spacing: 0.09em;
            text-transform: uppercase;
            color: #94A3B8;
        }
        .kpi-value {
            font-size: 2.2rem;
            font-weight: 800;
            line-height: 1.1;
            letter-spacing: -0.02em;
            color: #FFFFFF;
            margin-bottom: 0.4rem;
            font-family: 'Plus Jakarta Sans', sans-serif;
        }
        .val-cyan { color: #22D3EE !important; text-shadow: 0 0 18px rgba(34, 211, 238, 0.5); }
        .val-violet { color: #A78BFA !important; text-shadow: 0 0 18px rgba(167, 139, 250, 0.5); }
        .val-red { color: #F43F5E !important; text-shadow: 0 0 18px rgba(244, 63, 94, 0.5); }
        .val-green { color: #22C55E !important; text-shadow: 0 0 18px rgba(34, 197, 94, 0.5); }

        .kpi-subtext {
            font-size: 0.74rem;
            color: #64748B;
            font-weight: 500;
        }

        /* === STREAMLIT METRIC NATIVE OVERRIDE === */
        div[data-testid="stMetricValue"] {
            color: #22D3EE !important;
            font-weight: 800 !important;
            text-shadow: 0 0 18px rgba(34, 211, 238, 0.5) !important;
        }
        div[data-testid="stMetricLabel"] {
            color: #94A3B8 !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.08em !important;
        }

        /* === LIVE TERMINAL MONITORING PANEL === */
        .live-stream-box {
            background: rgba(10, 14, 24, 0.88);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(34, 211, 238, 0.25);
            border-left: 4px solid #22D3EE;
            border-radius: var(--radius-sm);
            padding: 1.1rem 1.3rem;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.84rem;
            color: #E2E8F0;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.5), inset 0 0 25px rgba(34, 211, 238, 0.05);
            margin-bottom: 1.2rem;
            line-height: 1.6;
        }
        .stream-title {
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.10em;
            color: #22D3EE;
            text-transform: uppercase;
            margin-bottom: 0.6rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .stream-success { color: #22C55E; font-weight: 700; }
        .stream-fail { color: #F43F5E; font-weight: 700; }
        .stream-depth { color: #A78BFA; font-weight: 600; }

        /* === STREAMLIT TAB STYLING OVERRIDES === */
        .stTabs [data-baseweb="tab-list"] {
            background: rgba(15, 23, 42, 0.65) !important;
            backdrop-filter: blur(16px) !important;
            -webkit-backdrop-filter: blur(16px) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: var(--radius) !important;
            padding: 6px !important;
            gap: 6px !important;
            margin-bottom: 1.8rem !important;
        }
        .stTabs [data-baseweb="tab"] {
            color: #94A3B8 !important;
            border-radius: var(--radius-sm) !important;
            font-size: 0.86rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.02em !important;
            padding: 10px 20px !important;
            border: none !important;
            background: transparent !important;
            transition: all 0.2s ease !important;
        }
        .stTabs [data-baseweb="tab"]:hover {
            color: #FFFFFF !important;
            background: rgba(255, 255, 255, 0.05) !important;
        }
        .stTabs [aria-selected="true"] {
            color: #22D3EE !important;
            background: rgba(34, 211, 238, 0.12) !important;
            box-shadow: 0 0 20px rgba(34, 211, 238, 0.25) !important;
            border-bottom: 2px solid #22D3EE !important;
        }

        /* === PRIMARY CTA BUTTON (START CRAWLING) === */
        div.stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #22D3EE 0%, #8B5CF6 100%) !important;
            color: #070A12 !important;
            font-weight: 800 !important;
            font-size: 0.96rem !important;
            letter-spacing: 0.08em !important;
            text-transform: uppercase !important;
            border: none !important;
            border-radius: var(--radius-sm) !important;
            padding: 0.75rem 1.6rem !important;
            box-shadow: 0 0 25px rgba(34, 211, 238, 0.5), 0 0 50px rgba(139, 92, 246, 0.3) !important;
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }
        div.stButton > button[kind="primary"]:hover {
            box-shadow: 0 0 35px rgba(34, 211, 238, 0.8), 0 0 70px rgba(139, 92, 246, 0.5) !important;
            transform: translateY(-2px) !important;
            filter: brightness(1.15) !important;
            color: #000000 !important;
        }
        div.stButton > button[kind="primary"]:active {
            transform: translateY(1px) !important;
        }

        /* Secondary Button (Clear Results) */
        div.stButton > button[kind="secondary"] {
            background: rgba(255, 255, 255, 0.04) !important;
            color: #94A3B8 !important;
            border: 1px solid rgba(255, 255, 255, 0.10) !important;
            border-radius: var(--radius-sm) !important;
            font-weight: 600 !important;
            font-size: 0.88rem !important;
            transition: all 0.2s ease !important;
        }
        div.stButton > button[kind="secondary"]:hover {
            background: rgba(255, 255, 255, 0.08) !important;
            color: #FFFFFF !important;
            border-color: rgba(255, 255, 255, 0.22) !important;
        }

        /* === COMPLETELY REMOVE SIDEBAR & COLLAPSE CONTROLS === */
        section[data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        button[data-testid="stSidebarCollapseButton"],
        [data-testid="stSidebarNav"] {
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            pointer-events: none !important;
        }

        /* === UNIFIED CYBER COMMAND BAR === */
        .crawl-command-bar {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.06) 0%, rgba(255, 255, 255, 0.01) 100%), rgba(11, 16, 32, 0.85);
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            border: 1px solid rgba(34, 211, 238, 0.25);
            border-top: 2px solid #22D3EE;
            border-radius: var(--radius-sm);
            padding: 0.75rem 1.1rem;
            margin-bottom: 0.75rem;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.45), 0 0 20px rgba(34, 211, 238, 0.10);
        }

        /* Equal height & vertical centering for controls */
        div.stButton > button {
            height: 42px !important;
            min-height: 42px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        div[data-baseweb="input"],
        div[data-baseweb="base-input"],
        div[data-baseweb="select"] > div {
            height: 42px !important;
            min-height: 42px !important;
            background-color: rgba(15, 23, 42, 0.85) !important;
            border: 1px solid rgba(255, 255, 255, 0.14) !important;
            border-radius: 6px !important;
            color: #FFFFFF !important;
            transition: all 0.2s ease !important;
        }
        div[data-baseweb="input"]:focus-within,
        div[data-baseweb="base-input"]:focus-within,
        div[data-baseweb="select"]:focus-within {
            border-color: #22D3EE !important;
            box-shadow: 0 0 16px rgba(34, 211, 238, 0.40) !important;
        }
        input[type="text"], input[type="number"] {
            font-size: 0.88rem !important;
            color: #FFFFFF !important;
            font-family: 'JetBrains Mono', monospace !important;
        }
        button[data-testid="stNumberInputStepDown"],
        button[data-testid="stNumberInputStepUp"] {
            width: 24px !important;
            height: 26px !important;
            min-width: 24px !important;
            max-width: 24px !important;
            padding: 0 !important;
            color: #94A3B8 !important;
            border: none !important;
            background: transparent !important;
        }
        button[data-testid="stNumberInputStepDown"]:hover,
        button[data-testid="stNumberInputStepUp"]:hover {
            color: #22D3EE !important;
            background: rgba(34, 211, 238, 0.15) !important;
        }

        /* Cyber Checkboxes */
        .stCheckbox {
            padding-top: 0.2rem !important;
            margin-bottom: 0.2rem !important;
        }
        .stCheckbox label {
            display: flex !important;
            align-items: center !important;
            gap: 0.5rem !important;
            font-size: 0.82rem !important;
            font-weight: 500 !important;
            color: #CBD5E1 !important;
            cursor: pointer !important;
        }
        .stCheckbox label:hover {
            color: #FFFFFF !important;
        }

        /* Settings Expander Styling */
        div[data-testid="stExpander"] {
            background: rgba(11, 16, 32, 0.70) !important;
            backdrop-filter: blur(16px) !important;
            -webkit-backdrop-filter: blur(16px) !important;
            border: 1px solid rgba(255, 255, 255, 0.10) !important;
            border-radius: var(--radius-sm) !important;
            margin-top: 0.3rem !important;
            margin-bottom: 0.8rem !important;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3) !important;
        }
        div[data-testid="stExpander"] summary {
            font-size: 0.78rem !important;
            font-weight: 700 !important;
            color: #94A3B8 !important;
            letter-spacing: 0.06em !important;
            text-transform: uppercase !important;
        }
        div[data-testid="stExpander"] summary:hover {
            color: #22D3EE !important;
        }
        div[data-testid="stExpander"] [data-testid="stExpanderDetails"] {
            padding: 0.75rem 1rem !important;
            border-top: 1px solid rgba(255, 255, 255, 0.06) !important;
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: var(--radius) !important;
            overflow: hidden;
            box-shadow: 0 4px 24px rgba(0, 0, 0, 0.35) !important;
        }

        /* === PROGRESS BAR THEME === */
        div[data-testid="stProgress"] > div > div > div {
            background: linear-gradient(90deg, #22D3EE 0%, #8B5CF6 100%) !important;
            box-shadow: 0 0 15px rgba(34, 211, 238, 0.5) !important;
        }

        /* === REDUCED MOTION PREFERENCE === */
        @media (prefers-reduced-motion: reduce) {
            *, ::before, ::after {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }
        }
        </style>
    """, unsafe_allow_html=True)


def render_control_label(label: str):
    """Render compact cyan uppercase section label with subtle horizontal accent rule."""
    safe_label = html.escape(label)
    st.markdown(f"""
        <div style="font-size: 0.68rem; font-weight: 800; letter-spacing: 0.10em; color: #22D3EE; text-transform: uppercase; margin-bottom: 0.22rem; display: flex; align-items: center; gap: 0.4rem;">
            <span>{safe_label}</span>
            <div style="flex: 1; height: 1px; background: linear-gradient(90deg, rgba(34, 211, 238, 0.45), transparent);"></div>
        </div>
    """, unsafe_allow_html=True)


render_sidebar_label = render_control_label  # Backward-compatible alias


def render_header():
    """Render futuristic compact cyber-analytics command bar."""
    st.markdown("""
        <div class="cyber-header-bar">
            <div class="cyber-header-left">
                <span class="cyber-logo-glyph">🕸️</span>
                <div class="cyber-title-compact">
                    WEB CRAWLER <span class="cyber-title-gradient">ANALYTICS</span>
                </div>
                <span class="cyber-version-tag">BFS ENGINE // v2.4</span>
            </div>
            <div class="cyber-header-right">
                <div class="cyber-status-pill-compact">
                    <span class="pulse-beacon-cyan"></span> SYSTEM ONLINE
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_completion_banner(summary: CrawlSessionSummary):
    """Render the futuristic glass command status panel with executive session flight telemetry."""
    elapsed = max(0.01, summary.elapsed_seconds)
    velocity = summary.pages_crawled / elapsed
    total_attempts = summary.pages_crawled + summary.failed_urls_count
    success_rate = (summary.pages_crawled / total_attempts * 100) if total_attempts > 0 else 100.0
    
    seed_display = summary.start_url
    if len(seed_display) > 52:
        seed_display = seed_display[:49] + "..."
        
    safe_seed_display = html.escape(seed_display)
    safe_seed_url = html.escape(summary.start_url, quote=True)
    safe_session_id = html.escape(summary.session_id)

    policy_str = "DOMAIN-SCOPED" if summary.stay_on_domain else "CROSS-DOMAIN"
    fail_color = 'val-red' if summary.failed_urls_count > 0 else 'val-green'
    
    st.markdown(f"""
        <div class="completion-panel-glass">
            <div class="completion-top">
                <div class="completion-badge">
                    <span class="pulse-beacon-green"></span> CRAWL COMPLETED // SESSION TELEMETRY
                </div>
                <div style="display: flex; gap: 0.6rem; align-items: center; flex-wrap: wrap;">
                    <span class="seed-url-pill" title="{safe_seed_url}">🎯 SEED: {safe_seed_display}</span>
                    <span class="session-id-tag">ID: {safe_session_id}</span>
                </div>
            </div>
            <div class="completion-grid">
                <div class="completion-stat">
                    <div class="comp-num val-cyan">{velocity:.1f} <span style="font-size: 0.85rem; color: #94A3B8;">p/s</span></div>
                    <div class="comp-lbl">CRAWL VELOCITY</div>
                </div>
                <div class="completion-stat">
                    <div class="comp-num val-green">{summary.elapsed_seconds:.2f}s</div>
                    <div class="comp-lbl">TIME ELAPSED</div>
                </div>
                <div class="completion-stat">
                    <div class="comp-num val-violet">D{summary.max_depth_reached} <span style="font-size: 0.85rem; color: #64748B;">/ D{summary.max_depth}</span></div>
                    <div class="comp-lbl">FRONTIER DEPTH</div>
                </div>
                <div class="completion-stat">
                    <div class="comp-num {'val-green' if success_rate >= 95 else 'val-red'}">{success_rate:.1f}%</div>
                    <div class="comp-lbl">SUCCESS RATE</div>
                </div>
                <div class="completion-stat">
                    <div class="comp-num val-cyan">{summary.pages_crawled}</div>
                    <div class="comp-lbl">PAGES PARSED</div>
                </div>
                <div class="completion-stat">
                    <div class="comp-num val-violet" style="font-size: 1.15rem; font-family: 'JetBrains Mono', monospace; padding-top: 0.4rem;">{policy_str}</div>
                    <div class="comp-lbl">TRAVERSAL POLICY</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_kpi_cards(summary: CrawlSessionSummary, pages: Optional[List[PageResult]] = None):
    """Render 6 real glassmorphic KPI cards with distinct, non-redundant metrics."""
    fail_color = 'val-red' if summary.failed_urls_count > 0 else 'val-green'
    fail_dot = 'dot-red' if summary.failed_urls_count > 0 else 'dot-green'
    
    # Compute average latency
    if pages and len(pages) > 0:
        latencies = [p.response_time for p in pages if p.response_time is not None]
        avg_latency = (sum(latencies) / len(latencies)) if latencies else 0.0
    else:
        avg_latency = 0.0

    latency_str = f"{avg_latency * 1000:.0f} ms" if avg_latency < 1.0 else f"{avg_latency:.2f} s"
    
    st.markdown(f"""
        <div class="kpi-grid">
            <div class="kpi-card kpi-card-cyan">
                <div class="kpi-header">
                    <span class="kpi-dot dot-cyan">◉</span>
                    <span class="kpi-label">Pages Crawled</span>
                </div>
                <div class="kpi-value val-cyan">{summary.pages_crawled}</div>
                <div class="kpi-subtext">Safety Cap: {summary.max_pages} pages</div>
            </div>
            <div class="kpi-card kpi-card-violet">
                <div class="kpi-header">
                    <span class="kpi-dot dot-violet">◉</span>
                    <span class="kpi-label">Discovered URLs</span>
                </div>
                <div class="kpi-value val-violet">{summary.discovered_urls_count:,}</div>
                <div class="kpi-subtext">Unique Extracted Links</div>
            </div>
            <div class="kpi-card kpi-card-red">
                <div class="kpi-header">
                    <span class="kpi-dot {fail_dot}">◉</span>
                    <span class="kpi-label">Failed Requests</span>
                </div>
                <div class="kpi-value {fail_color}">{summary.failed_urls_count}</div>
                <div class="kpi-subtext">Network & Policy Blocks</div>
            </div>
            <div class="kpi-card kpi-card-green">
                <div class="kpi-header">
                    <span class="kpi-dot dot-green">◉</span>
                    <span class="kpi-label">Avg Fetch Latency</span>
                </div>
                <div class="kpi-value val-green">{latency_str}</div>
                <div class="kpi-subtext">Roundtrip HTTP Timing</div>
            </div>
            <div class="kpi-card kpi-card-sky">
                <div class="kpi-header">
                    <span class="kpi-dot dot-sky">◉</span>
                    <span class="kpi-label">Internal Links</span>
                </div>
                <div class="kpi-value val-cyan">{summary.total_internal_links:,}</div>
                <div class="kpi-subtext">Domain-Scoped Traversal</div>
            </div>
            <div class="kpi-card kpi-card-purple">
                <div class="kpi-header">
                    <span class="kpi-dot dot-purple">◉</span>
                    <span class="kpi-label">External Outbound</span>
                </div>
                <div class="kpi-value val-violet">{summary.total_external_links:,}</div>
                <div class="kpi-subtext">Third-Party References</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
