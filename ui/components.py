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
            --accent-cyan: #22D3EE;  /* alias so var(--accent-cyan) resolves */
            --violet: #8B5CF6;
            --pink: #EC4899;
            --success: #22C55E;
            --danger: #F43F5E;       /* declared so var(--danger) resolves */
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
            overflow-x: hidden !important;
            max-width: 100vw !important;
            box-sizing: border-box !important;
        }

        *, *::before, *::after {
            box-sizing: border-box !important;
        }

        /* === COMPLETELY HIDE STREAMLIT PLATFORM HEADER (Share, Star, GitHub, Edit, Decoration) === */
        /* Our custom header lives inside .block-container, so the stHeader shell is not needed at all */
        header[data-testid="stHeader"],
        header[data-testid="stHeader"] * {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
            min-height: 0 !important;
            max-height: 0 !important;
            overflow: hidden !important;
            pointer-events: none !important;
        }
        /* Also target individual elements in case stHeader selector is shadowed */
        [data-testid="stToolbar"],
        [data-testid="stToolbarActions"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        [data-testid="stActionButton"],
        #MainMenu,
        #MainMenu * {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
            min-height: 0 !important;
            max-height: 0 !important;
            overflow: hidden !important;
            pointer-events: none !important;
        }


        /* === RESPONSIVE STREAMLIT CONTENT CONTAINER === */
        .block-container {
            padding-top: 0.75rem !important;
            padding-bottom: 2rem !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
            max-width: 1520px !important;
        }
        @media (max-width: 1024px) {
            .block-container {
                padding-left: 1rem !important;
                padding-right: 1rem !important;
                padding-top: 0.6rem !important;
            }
        }
        @media (max-width: 640px) {
            .block-container {
                padding-left: 0.55rem !important;
                padding-right: 0.55rem !important;
                padding-top: 0.4rem !important;
                padding-bottom: 1.5rem !important;
            }
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
            border-radius: 8px;
            padding: 0.55rem 1.2rem;
            margin-bottom: 0.85rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4), 0 0 20px rgba(34, 211, 238, 0.10);
            flex-wrap: wrap;
            gap: 0.5rem;
        }
        @media (max-width: 768px) {
            .cyber-header-bar {
                flex-direction: column !important;
                align-items: flex-start !important;
                gap: 0.45rem !important;
                padding: 0.65rem 0.9rem !important;
            }
            .cyber-header-left {
                width: 100% !important;
                justify-content: space-between !important;
            }
            .cyber-header-right {
                width: 100% !important;
                justify-content: flex-start !important;
            }
            .cyber-status-pill-compact {
                width: 100% !important;
                justify-content: center !important;
                padding: 0.35rem 0.6rem !important;
            }
            .cyber-title-compact {
                font-size: 1.05rem !important;
            }
        }
        @media (max-width: 420px) {
            .cyber-version-tag {
                display: none !important;
            }
            .cyber-title-compact {
                font-size: 0.95rem !important;
            }
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
            display: inline-block;
        }
        .pulse-beacon-green {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: #22C55E;
            box-shadow: 0 0 10px #22C55E;
            animation: pulse-beacon 2s infinite ease-in-out;
            display: inline-block;
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
            border-radius: 12px !important;
            padding: 1.4rem 1.8rem !important;
            margin-bottom: 1.5rem !important;
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
            flex-wrap: wrap;
            gap: 0.5rem;
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
            max-width: 100% !important;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            display: inline-block;
            word-break: break-all;
        }
        .completion-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
            gap: 1.2rem;
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
        @media (max-width: 768px) {
            .completion-panel-glass {
                padding: 1rem 1.1rem !important;
            }
            .completion-top {
                flex-direction: column !important;
                align-items: flex-start !important;
                gap: 0.5rem !important;
            }
            .completion-badge {
                font-size: 0.76rem !important;
            }
            .completion-grid {
                grid-template-columns: repeat(2, 1fr) !important;
                gap: 0.75rem !important;
            }
            .comp-num {
                font-size: 1.35rem !important;
            }
            .comp-lbl {
                font-size: 0.62rem !important;
            }
        }
        @media (max-width: 360px) {
            .completion-grid {
                grid-template-columns: 1fr !important;
            }
        }

        /* === REAL GLASSMORPHISM KPI CARDS === */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
            gap: 1rem;
            margin-bottom: 1.8rem;
        }
        @media (max-width: 1100px) {
            .kpi-grid {
                grid-template-columns: repeat(3, 1fr) !important;
                gap: 0.8rem !important;
            }
        }
        @media (max-width: 640px) {
            .kpi-grid {
                grid-template-columns: repeat(2, 1fr) !important;
                gap: 0.55rem !important;
                margin-bottom: 1.2rem !important;
            }
            .kpi-card {
                padding: 0.8rem 0.7rem !important;
                border-radius: 8px !important;
            }
            .kpi-value {
                font-size: 1.55rem !important;
                margin-bottom: 0.2rem !important;
            }
            .kpi-label {
                font-size: 0.64rem !important;
                letter-spacing: 0.06em !important;
            }
            .kpi-subtext {
                font-size: 0.64rem !important;
            }
            .kpi-header {
                margin-bottom: 0.4rem !important;
                gap: 0.35rem !important;
            }
        }
        @media (max-width: 360px) {
            .kpi-grid {
                grid-template-columns: 1fr !important;
            }
        }
        .kpi-card {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0.02) 100%), rgba(15, 23, 42, 0.65) !important;
            backdrop-filter: blur(16px) saturate(180%) !important;
            -webkit-backdrop-filter: blur(16px) saturate(180%) !important;
            border: 1px solid rgba(255, 255, 255, 0.10) !important;
            border-radius: 12px !important;
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

        /* === LIVE TERMINAL MONITORING PANEL === */
        .live-stream-box {
            background: rgba(10, 14, 24, 0.88);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(34, 211, 238, 0.25);
            border-left: 4px solid #22D3EE;
            border-radius: 8px;
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
        .stream-searching { color: #D8B4FE; font-weight: 700; }
        .stream-depth { color: #A78BFA; font-weight: 600; }

        /* === STREAMLIT TAB STYLING OVERRIDES === */
        .stTabs [data-baseweb="tab-list"] {
            background: rgba(15, 23, 42, 0.65) !important;
            backdrop-filter: blur(16px) !important;
            -webkit-backdrop-filter: blur(16px) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 12px !important;
            padding: 6px !important;
            gap: 4px !important;
            margin-bottom: 1.8rem !important;
            flex-wrap: nowrap !important;
            overflow-x: auto !important;
        }
        .stTabs [data-baseweb="tab"] {
            color: #94A3B8 !important;
            border-radius: 8px !important;
            font-size: 0.82rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.02em !important;
            padding: 8px 14px !important;
            border: none !important;
            background: transparent !important;
            transition: all 0.2s ease !important;
            white-space: nowrap !important;
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
            font-size: 0.90rem !important;
            letter-spacing: 0.06em !important;
            text-transform: uppercase !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 0.65rem 1.2rem !important;
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

        /* Secondary Button (Clear, Download, Load Session, Preset cards, etc.)
           Use broad selectors — Streamlit Cloud bleeds primaryColor border through kind="secondary" */
        div.stButton > button[kind="secondary"],
        div.stButton > button:not([kind="primary"]),
        div.stDownloadButton > button {
            background: rgba(15, 23, 42, 0.70) !important;
            color: #CBD5E1 !important;
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            font-size: 0.84rem !important;
            transition: all 0.2s ease !important;
            box-shadow: none !important;
            outline: none !important;
        }
        div.stButton > button[kind="secondary"]:hover,
        div.stButton > button:not([kind="primary"]):hover,
        div.stDownloadButton > button:hover {
            background: rgba(34, 211, 238, 0.08) !important;
            color: #FFFFFF !important;
            border-color: rgba(34, 211, 238, 0.35) !important;
            box-shadow: 0 0 12px rgba(34, 211, 238, 0.15) !important;
        }
        div.stButton > button[kind="secondary"]:focus,
        div.stButton > button:not([kind="primary"]):focus,
        div.stDownloadButton > button:focus {
            outline: none !important;
            box-shadow: 0 0 0 2px rgba(34, 211, 238, 0.30) !important;
            border-color: rgba(34, 211, 238, 0.35) !important;
        }


        /* === HEIGHT LOCK SCOPED TO COMMAND BAR ONLY === */
        /* Do NOT apply fixed height globally — it squashes download/load buttons */
        .crawl-command-bar div.stButton > button {
            height: 42px !important;
            min-height: 42px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        .crawl-command-bar div[data-baseweb="input"],
        .crawl-command-bar div[data-baseweb="base-input"] {
            height: 42px !important;
            min-height: 42px !important;
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
            border-radius: 8px;
            padding: 0.75rem 1.1rem;
            margin-bottom: 0.75rem;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.45), 0 0 20px rgba(34, 211, 238, 0.10);
        }

        /* Input & Select baseline styles (not forcing fixed height globally) */
        div[data-baseweb="input"],
        div[data-baseweb="base-input"] {
            background-color: rgba(15, 23, 42, 0.85) !important;
            border: 1px solid rgba(255, 255, 255, 0.14) !important;
            border-radius: 6px !important;
            color: #FFFFFF !important;
            transition: all 0.2s ease !important;
        }
        div[data-baseweb="select"] > div {
            min-height: 38px !important;
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
        /* Number input step buttons — no max-width to avoid unclickable touch targets */
        button[data-testid="stNumberInputStepDown"],
        button[data-testid="stNumberInputStepUp"] {
            width: 28px !important;
            height: 28px !important;
            min-width: 28px !important;
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
            border-radius: 8px !important;
            margin-top: 0.3rem !important;
            margin-bottom: 0.8rem !important;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3) !important;
        }
        div[data-testid="stExpander"] summary {
            font-size: 0.78rem !important;
            font-weight: 700 !important;
            color: #94A3B8 !important;
            letter-spacing: 0.06em !important;
        }
        div[data-testid="stExpander"] summary:hover {
            color: #22D3EE !important;
        }
        div[data-testid="stExpander"] [data-testid="stExpanderDetails"] {
            padding: 0.75rem 1rem !important;
            border-top: 1px solid rgba(255, 255, 255, 0.06) !important;
        }

        /* === RESPONSIVE STREAMLIT COLUMNS & HORIZONTAL BLOCKS === */
        [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
            gap: 0.5rem !important;
        }
        @media (max-width: 860px) {
            /* On tablet and mobile, prevent horizontal squishing of columns */
            [data-testid="stHorizontalBlock"] > [data-testid="column"] {
                min-width: 100% !important;
                flex: 1 1 100% !important;
            }
        }
        @media (min-width: 641px) and (max-width: 1024px) {
            /* On tablet for 4-column blocks (presets, parameters, pillars), adapt to 2x2 grid */
            [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(4)) > [data-testid="column"] {
                min-width: 46% !important;
                flex: 1 1 46% !important;
            }
        }

        /* === RESPONSIVE STANDBY PANEL & PRESET CARDS === */
        .standby-panel-glass {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.06) 0%, rgba(255, 255, 255, 0.01) 100%), rgba(15, 23, 42, 0.65) !important;
            backdrop-filter: blur(20px) !important;
            -webkit-backdrop-filter: blur(20px) !important;
            border: 1px solid rgba(255, 255, 255, 0.10) !important;
            border-top: 3px solid #22D3EE !important;
            border-radius: 12px !important;
            padding: 1.2rem 1.6rem !important;
            box-shadow: 0 8px 32px rgba(0,0,0,0.4), 0 0 25px rgba(34, 211, 238, 0.12) !important;
            margin-top: 0.5rem !important;
            margin-bottom: 1.2rem !important;
        }
        @media (max-width: 640px) {
            .standby-panel-glass {
                padding: 0.85rem 1rem !important;
            }
            .standby-panel-glass h3 {
                font-size: 1.15rem !important;
            }
            .standby-panel-glass p {
                font-size: 0.80rem !important;
                line-height: 1.45 !important;
            }
            .preset-card {
                min-height: auto !important;
                padding: 0.75rem 0.85rem !important;
            }
        }

        /* === RESPONSIVE DATAFRAMES & CODE OVERFLOW === */
        div[data-testid="stDataFrame"] {
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 12px !important;
            overflow-x: auto !important;
            max-width: 100% !important;
            -webkit-overflow-scrolling: touch !important;
            box-shadow: 0 4px 24px rgba(0, 0, 0, 0.35) !important;
        }
        @media (max-width: 640px) {
            div[data-testid="stDataFrame"] {
                border-radius: 8px !important;
            }
        }
        code, pre {
            word-break: break-all !important;
            white-space: pre-wrap !important;
            overflow-wrap: anywhere !important;
        }

        /* === PROGRESS BAR THEME === */
        div[data-testid="stProgress"] > div > div > div {
            background: linear-gradient(90deg, #22D3EE 0%, #8B5CF6 100%) !important;
            box-shadow: 0 0 15px rgba(34, 211, 238, 0.5) !important;
        }

        /* === RESULTS-READY NOTIFICATION BAR === */
        .results-ready-bar {
            background: linear-gradient(135deg, rgba(34, 197, 94, 0.08) 0%, rgba(34, 197, 94, 0.02) 100%), rgba(11, 16, 32, 0.75);
            border: 1px solid rgba(34, 197, 94, 0.25);
            border-left: 3px solid #22C55E;
            border-radius: 8px;
            padding: 0.65rem 1.1rem;
            margin-bottom: 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.5rem;
        }

        /* === TOUCH TARGET ACCESSIBILITY (PHONES & TABLETS) === */
        @media (pointer: coarse) {
            div.stButton > button,
            .stDownloadButton > button {
                min-height: 44px !important;
            }
            div[data-baseweb="select"] > div {
                min-height: 44px !important;
            }
            .stCheckbox label {
                padding: 0.35rem 0 !important;
            }
        }

        /* === REDUCED MOTION PREFERENCE === */
        /* Excluded: progress bar and spinner so they still animate during live crawl */
        @media (prefers-reduced-motion: reduce) {
            *:not([data-testid="stProgress"] *):not([data-testid="stSpinner"] *),
            ::before,
            ::after {
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
    seed_tag_text = f"🔍 SEARCH: {safe_seed_display}" if summary.search_query else f"🎯 SEED: {safe_seed_display}"

    st.markdown(f"""
        <div class="completion-panel-glass">
            <div class="completion-top">
                <div class="completion-badge">
                    <span class="pulse-beacon-green"></span> CRAWL COMPLETED // SESSION TELEMETRY
                </div>
                <div style="display: flex; gap: 0.6rem; align-items: center; flex-wrap: wrap;">
                    <span class="seed-url-pill" title="{safe_seed_url}">{seed_tag_text}</span>
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
                <div class="kpi-subtext">Network &amp; Policy Blocks</div>
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
