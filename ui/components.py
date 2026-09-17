"""
Futuristic Dark Premium UI Components & Unified Design System.
Primary Accent: Orange / Amber (#F97316, #FB923C, #EA580C)
Secondary Accent: Purple / Violet (#A855F7, #8B5CF6, #7C3AED)
Surfaces: Charcoal, Deep Warm Navy, Glassmorphism, 10-14px Rounded Borders.
"""

from typing import Optional, List, Dict, Any, Tuple
import html
import streamlit as st
from crawler.models import CrawlSessionSummary, PageResult


def apply_custom_styles():
    """Inject high-end dark premium visual styling, glassmorphism, and orange/purple accents."""
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

        /* === 2026 NEXUS AI RESEARCH PLATFORM DESIGN TOKENS === */
        :root {
            --bg-base: #07090E;
            --bg-primary: #07090E;
            --bg-secondary: #0B0E17;
            --bg-surface: #0E1320;
            --bg-surface-elevated: #141A2B;
            --bg-card: rgba(14, 19, 32, 0.75);
            --bg-card-hover: rgba(22, 29, 48, 0.85);

            --border-subtle: rgba(255, 255, 255, 0.07);
            --border-card: rgba(255, 255, 255, 0.09);
            --border-card-hover: rgba(249, 115, 22, 0.35);

            --text-primary: #F8FAFC;
            --text-secondary: #94A3B8;
            --text-muted: #64748B;

            /* Primary Accent: Orange / Amber */
            --orange-500: #F97316;
            --orange-400: #FB923C;
            --orange-600: #EA580C;
            --orange-glow: rgba(249, 115, 22, 0.20);
            --orange-soft: rgba(249, 115, 22, 0.12);

            /* Secondary Accent: Purple / Violet */
            --purple-500: #A855F7;
            --purple-400: #C084FC;
            --purple-600: #9333EA;
            --purple-glow: rgba(168, 85, 247, 0.20);
            --purple-soft: rgba(168, 85, 247, 0.12);

            /* Semantic Statuses */
            --success: #10B981;
            --success-glow: rgba(16, 185, 129, 0.20);
            --danger: #EF4444;
            --danger-glow: rgba(239, 68, 68, 0.20);
            --warning: #F59E0B;

            --radius-sm: 6px;
            --radius-md: 10px;
            --radius-lg: 14px;
            --radius-xl: 18px;
        }

        /* === GLOBAL THEME & ATMOSPHERIC HORIZON BACKGROUND === */
        html, body, .stApp, [data-testid="stAppViewContainer"], section.main {
            background-color: #07090E !important;
            background-image:
                radial-gradient(ellipse 75% 45% at 85% 4%, rgba(249, 115, 22, 0.08) 0%, transparent 60%),
                radial-gradient(ellipse 65% 45% at 15% 8%, rgba(168, 85, 247, 0.08) 0%, transparent 60%),
                radial-gradient(ellipse 70% 50% at 50% 95%, rgba(234, 88, 12, 0.04) 0%, transparent 70%) !important;
            background-attachment: fixed !important;
            color: #F8FAFC !important;
            font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, sans-serif !important;
            overflow-x: hidden !important;
            max-width: 100vw !important;
            box-sizing: border-box !important;
        }

        *, *::before, *::after {
            box-sizing: border-box !important;
        }

        /* === HIDE STREAMLIT DEFAULT PLATFORM CHROME === */
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
            overflow: hidden !important;
            pointer-events: none !important;
        }

        /* === RESPONSIVE STREAMLIT CONTENT CONTAINER === */
        .block-container {
            padding-top: 0.6rem !important;
            padding-bottom: 2rem !important;
            padding-left: 1.6rem !important;
            padding-right: 1.6rem !important;
            max-width: 1540px !important;
        }
        @media (max-width: 1024px) {
            .block-container {
                padding-left: 1rem !important;
                padding-right: 1rem !important;
                padding-top: 0.5rem !important;
            }
        }
        @media (max-width: 640px) {
            .block-container {
                padding-left: 0.6rem !important;
                padding-right: 0.6rem !important;
                padding-top: 0.4rem !important;
            }
        }

        /* === APPLICATION TOP BAR === */
        .nexus-topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(11, 14, 23, 0.75);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 0.55rem 1.1rem;
            margin-bottom: 1.1rem;
            gap: 1rem;
        }
        .topbar-search-slot {
            display: flex;
            align-items: center;
            gap: 0.65rem;
            background: rgba(15, 20, 33, 0.65);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 8px;
            padding: 0.4rem 0.85rem;
            flex: 1;
            max-width: 520px;
        }
        .topbar-search-icon {
            color: #94A3B8;
            font-size: 0.85rem;
        }
        .topbar-search-placeholder {
            font-size: 0.82rem;
            color: #64748B;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            user-select: none;
        }
        .topbar-kbd {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.66rem;
            color: #94A3B8;
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            padding: 0.15rem 0.4rem;
            margin-left: auto;
            letter-spacing: 0.04em;
        }
        .topbar-right-slot {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        .topbar-status-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            background: rgba(16, 185, 129, 0.08);
            border: 1px solid rgba(16, 185, 129, 0.30);
            border-radius: 20px;
            padding: 0.28rem 0.75rem;
            font-size: 0.70rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            color: #34D399;
            text-transform: uppercase;
        }

        /* === WORKSPACE HERO BANNER (ATMOSPHERIC TITLE) === */
        .workspace-hero-banner {
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: relative;
            background: linear-gradient(135deg, rgba(14, 19, 32, 0.65) 0%, rgba(11, 14, 23, 0.45) 100%);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 16px;
            padding: 1.25rem 1.6rem;
            margin-bottom: 1.3rem;
            overflow: hidden;
        }
        .workspace-hero-banner::after {
            content: '';
            position: absolute;
            top: 0;
            right: 0;
            width: 380px;
            height: 100%;
            background: radial-gradient(circle at 85% 30%, rgba(249, 115, 22, 0.14) 0%, rgba(168, 85, 247, 0.08) 50%, transparent 75%);
            pointer-events: none;
        }
        .hero-left {
            z-index: 1;
            max-width: 820px;
        }
        .hero-eyebrow {
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.12em;
            color: #FB923C;
            text-transform: uppercase;
            margin-bottom: 0.35rem;
        }
        .hero-headline {
            font-size: 1.75rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            color: #FFFFFF;
            line-height: 1.25;
            margin: 0 0 0.35rem 0;
        }
        .hero-headline .accent-orange {
            color: #F97316;
            background: linear-gradient(135deg, #FB923C 0%, #F97316 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .hero-headline .accent-purple {
            color: #A855F7;
            background: linear-gradient(135deg, #C084FC 0%, #A855F7 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .hero-subtitle {
            font-size: 0.88rem;
            color: #94A3B8;
            margin: 0;
            line-height: 1.55;
        }

        /* === STATUS PULSES === */
        .status-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            display: inline-block;
        }
        .status-dot.green-pulse {
            background-color: #10B981;
            box-shadow: 0 0 8px #10B981;
            animation: pulse-dot-green 2.2s infinite ease-in-out;
        }
        .status-dot.orange-pulse {
            background-color: #F97316;
            box-shadow: 0 0 8px #F97316;
            animation: pulse-dot-orange 2.2s infinite ease-in-out;
        }
        @keyframes pulse-dot-green {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.45; transform: scale(0.85); }
        }
        @keyframes pulse-dot-orange {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.45; transform: scale(0.85); }
        }

        /* === PRODUCTION-GRADE AI PLATFORM SIDEBAR & NAVIGATION === */
        section[data-testid="stSidebar"] {
            background-color: #0B0E17 !important;
            border-right: 1px solid rgba(255, 255, 255, 0.07) !important;
            width: 285px !important;
            min-width: 285px !important;
        }
        section[data-testid="stSidebar"] > div:first-child {
            padding: 1.1rem 0.95rem 1.2rem 0.95rem !important;
            background: #0B0E17 !important;
        }

        /* Sidebar Brand */
        .sidebar-brand-box {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.4rem 0.4rem 1.1rem 0.4rem;
            margin-bottom: 0.9rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.07);
        }
        .brand-glyph-box {
            font-size: 1.25rem;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 38px;
            height: 38px;
            border-radius: 10px;
            background: linear-gradient(135deg, rgba(249, 115, 22, 0.22) 0%, rgba(168, 85, 247, 0.15) 100%);
            border: 1px solid rgba(249, 115, 22, 0.35);
            box-shadow: 0 0 16px rgba(249, 115, 22, 0.2);
        }
        .brand-title-text {
            font-size: 0.98rem;
            font-weight: 800;
            letter-spacing: 0.06em;
            color: #FFFFFF;
            line-height: 1.15;
        }
        .brand-sub-text {
            font-size: 0.65rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            color: #64748B;
            text-transform: uppercase;
        }

        /* TRANSFORM STREAMLIT RADIO INTO SLEEK NAVIGATION CARDS (NO RADIO CIRCLES) */
        section[data-testid="stSidebar"] div[data-testid="stRadio"] > div[role="radiogroup"] {
            background: transparent !important;
            border: none !important;
            padding: 0 !important;
            gap: 0.38rem !important;
            display: flex !important;
            flex-direction: column !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stRadio"] > div[role="radiogroup"] label {
            background: rgba(14, 19, 32, 0.45) !important;
            border: 1px solid rgba(255, 255, 255, 0.05) !important;
            border-radius: 10px !important;
            padding: 0.72rem 0.9rem !important;
            font-size: 0.86rem !important;
            font-weight: 600 !important;
            color: #94A3B8 !important;
            cursor: pointer !important;
            transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1) !important;
            display: flex !important;
            align-items: center !important;
            width: 100% !important;
            margin: 0 !important;
        }
        /* Completely eliminate the circular radio indicator */
        section[data-testid="stSidebar"] div[data-testid="stRadio"] input {
            display: none !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stRadio"] label > div:first-child {
            display: none !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stRadio"] label:hover {
            color: #F8FAFC !important;
            background: rgba(249, 115, 22, 0.07) !important;
            border-color: rgba(249, 115, 22, 0.25) !important;
            transform: translateX(2px) !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stRadio"] label[data-checked="true"],
        section[data-testid="stSidebar"] div[data-testid="stRadio"] label:has(input:checked) {
            background: linear-gradient(90deg, rgba(249, 115, 22, 0.16) 0%, rgba(168, 85, 247, 0.06) 100%) !important;
            border: 1px solid rgba(249, 115, 22, 0.38) !important;
            border-left: 3px solid #F97316 !important;
            color: #FFFFFF !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35), 0 0 16px rgba(249, 115, 22, 0.12) !important;
            transform: translateX(2px) !important;
        }

        /* Compact Sidebar System Status */
        .sidebar-system-card {
            background: rgba(14, 19, 32, 0.65);
            border: 1px solid rgba(255, 255, 255, 0.07);
            border-radius: 12px;
            padding: 0.85rem 0.95rem;
            margin-top: 1.8rem;
        }
        .sys-online-row {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 0.65rem;
            padding-bottom: 0.55rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        }
        .sys-online-title {
            font-size: 0.74rem;
            font-weight: 700;
            color: #10B981;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }
        .sys-status-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.72rem;
            color: #94A3B8;
            margin-bottom: 0.3rem;
        }
        .sys-status-badge {
            font-size: 0.68rem;
            font-weight: 600;
            color: #34D399;
            background: rgba(16, 185, 129, 0.1);
            border-radius: 4px;
            padding: 0.1rem 0.4rem;
        }
        .sidebar-release-meta {
            font-size: 0.66rem;
            color: #475569;
            text-align: center;
            margin-top: 0.9rem;
            line-height: 1.4;
            font-family: 'JetBrains Mono', monospace;
        }

        /* === BUTTONS & INTERACTION STATES === */
        /* Primary Buttons (Orange Gradient) */
        .stButton > button[kind="primary"],
        button[data-testid="baseButton-primary"] {
            background: linear-gradient(135deg, #F97316 0%, #EA580C 100%) !important;
            color: #FFFFFF !important;
            border: 1px solid rgba(251, 146, 60, 0.4) !important;
            border-radius: 10px !important;
            padding: 0.6rem 1.4rem !important;
            font-size: 0.88rem !important;
            font-weight: 700 !important;
            letter-spacing: 0.02em !important;
            box-shadow: 0 4px 16px rgba(249, 115, 22, 0.28) !important;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
        }
        .stButton > button[kind="primary"]:hover,
        button[data-testid="baseButton-primary"]:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 22px rgba(249, 115, 22, 0.42) !important;
            filter: brightness(1.06) !important;
        }
        /* Secondary Buttons */
        .stButton > button[kind="secondary"],
        button[data-testid="baseButton-secondary"],
        .stButton > button:not([kind="primary"]) {
            background: rgba(14, 19, 32, 0.75) !important;
            color: #E2E8F0 !important;
            border: 1px solid rgba(255, 255, 255, 0.09) !important;
            border-radius: 10px !important;
            padding: 0.55rem 1.1rem !important;
            font-size: 0.86rem !important;
            font-weight: 600 !important;
            transition: all 0.2s ease !important;
        }
        .stButton > button:not([kind="primary"]):hover {
            background: rgba(22, 29, 48, 0.9) !important;
            border-color: rgba(249, 115, 22, 0.35) !important;
            color: #FFFFFF !important;
            transform: translateY(-1px) !important;
        }

        /* === INPUTS & TEXT AREAS === */
        input[type="text"],
        input[type="number"],
        div[data-baseweb="input"] input,
        textarea {
            background-color: rgba(14, 19, 32, 0.85) !important;
            border: 1px solid rgba(255, 255, 255, 0.10) !important;
            border-radius: 10px !important;
            color: #F8FAFC !important;
            font-size: 0.90rem !important;
            transition: all 0.18s ease !important;
        }
        div[data-baseweb="input"]:focus-within {
            border-color: #F97316 !important;
            box-shadow: 0 0 0 1px #F97316, 0 0 16px rgba(249, 115, 22, 0.2) !important;
        }

        /* === TABS STYLING (SEGMENTED ORANGE / PURPLE) === */
        div[data-baseweb="tab-list"] {
            background: rgba(14, 19, 32, 0.6) !important;
            border: 1px solid rgba(255, 255, 255, 0.07) !important;
            border-radius: 12px !important;
            padding: 0.35rem 0.45rem !important;
            gap: 0.35rem !important;
            margin-bottom: 1.1rem !important;
        }
        button[data-baseweb="tab"] {
            border-radius: 8px !important;
            padding: 0.5rem 1rem !important;
            font-size: 0.84rem !important;
            font-weight: 600 !important;
            color: #94A3B8 !important;
            background: transparent !important;
            border: none !important;
            transition: all 0.18s ease !important;
        }
        button[data-baseweb="tab"]:hover {
            color: #F8FAFC !important;
            background: rgba(255, 255, 255, 0.04) !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            color: #FFFFFF !important;
            background: rgba(249, 115, 22, 0.15) !important;
            border: 1px solid rgba(249, 115, 22, 0.35) !important;
            font-weight: 700 !important;
        }

        /* === METRIC CARDS & GLASS PANELS === */
        .glass-panel {
            background: rgba(14, 19, 32, 0.72);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 14px;
            padding: 1.15rem 1.35rem;
            margin-bottom: 1rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }
        .metric-card-box {
            background: rgba(14, 19, 32, 0.72);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 1rem 1.2rem;
            transition: transform 0.2s ease, border-color 0.2s ease;
        }
        .metric-card-box:hover {
            border-color: rgba(249, 115, 22, 0.3);
            transform: translateY(-2px);
        }
        .metric-card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.72rem;
            font-weight: 700;
            color: #94A3B8;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.35rem;
        }
        .metric-card-val {
            font-size: 1.55rem;
            font-weight: 800;
            color: #FFFFFF;
            letter-spacing: -0.02em;
            line-height: 1.1;
        }
        .metric-card-sub {
            font-size: 0.72rem;
            color: #64748B;
            margin-top: 0.25rem;
        }

        /* === EMPTY STATES === */
        .empty-state-container {
            background: rgba(14, 19, 32, 0.55);
            border: 1px dashed rgba(255, 255, 255, 0.12);
            border-radius: 16px;
            padding: 2.8rem 2rem;
            text-align: center;
            margin: 1.2rem 0;
        }
        .empty-icon {
            font-size: 2.4rem;
            margin-bottom: 0.75rem;
            opacity: 0.85;
        }
        .empty-title {
            font-size: 1.15rem;
            font-weight: 700;
            color: #F8FAFC;
            margin-bottom: 0.35rem;
        }
        .empty-desc {
            font-size: 0.86rem;
            color: #94A3B8;
            max-width: 540px;
            margin: 0 auto;
            line-height: 1.55;
        }

        /* === INTERACTIVE EXAMPLE CHIPS === */
        .search-chips-row {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            flex-wrap: wrap;
            margin-top: 0.65rem;
        }
        .chips-label {
            font-size: 0.75rem;
            color: #64748B;
            font-weight: 600;
        }
        .chip-pill {
            display: inline-flex;
            align-items: center;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            padding: 0.25rem 0.75rem;
            font-size: 0.76rem;
            color: #CBD5E1;
            cursor: pointer;
            transition: all 0.15s ease;
            text-decoration: none;
        }
        .chip-pill:hover {
            background: rgba(249, 115, 22, 0.12);
            border-color: rgba(249, 115, 22, 0.35);
            color: #FFFFFF;
        }

        /* === SCROLLBAR STYLING === */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        ::-webkit-scrollbar-track {
            background: #07090E;
        }
        ::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.15);
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(249, 115, 22, 0.4);
        }
        </style>
    """, unsafe_allow_html=True)


def render_app_topbar():
    """Render top application infrastructure header with global search prompt and engine status."""
    st.markdown("""
        <div class="nexus-topbar">
            <div class="topbar-search-slot">
                <span class="topbar-search-icon">🔍</span>
                <span class="topbar-search-placeholder">Search past research, crawls, or enter query...</span>
                <span class="topbar-kbd">Ctrl K</span>
            </div>
            <div class="topbar-right-slot">
                <div class="topbar-status-badge">
                    <span class="status-dot green-pulse"></span>
                    <span>ENGINE READY</span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_workspace_hero(
    eyebrow: str,
    title_part1: str,
    title_accent: str,
    title_part2: str = "",
    subtitle: str = "",
    accent_type: str = "orange",
):
    """
    Render standardized workspace hero header matching the reference visual direction.
    accent_type: 'orange' or 'purple'
    """
    safe_eyebrow = html.escape(eyebrow)
    safe_p1 = html.escape(title_part1)
    safe_acc = html.escape(title_accent)
    safe_p2 = html.escape(title_part2)
    safe_sub = html.escape(subtitle)
    accent_class = "accent-purple" if accent_type == "purple" else "accent-orange"

    st.markdown(f"""
        <div class="workspace-hero-banner">
            <div class="hero-left">
                <div class="hero-eyebrow">{safe_eyebrow}</div>
                <h1 class="hero-headline">{safe_p1} <span class="{accent_class}">{safe_acc}</span> {safe_p2}</h1>
                <p class="hero-subtitle">{safe_sub}</p>
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_platform_header(
    title: str = "SEARCH & INTELLIGENCE CANVAS",
    subtitle: str = "Evidence-Backed Multi-Engine Retrieval & AI Neural Synthesis",
):
    """Backward-compatible platform header wrapper."""
    parts = title.split()
    if len(parts) >= 3:
        p1 = " ".join(parts[:2])
        acc = parts[2]
        p2 = " ".join(parts[3:]) if len(parts) > 3 else ""
    elif len(parts) == 2:
        p1 = parts[0]
        acc = parts[1]
        p2 = ""
    else:
        p1 = title
        acc = ""
        p2 = ""
    render_workspace_hero(
        eyebrow="NEXUS AI PLATFORM",
        title_part1=p1,
        title_accent=acc,
        title_part2=p2,
        subtitle=subtitle,
    )


def render_header(title: Optional[str] = None, subtitle: Optional[str] = None):
    """Backward-compatible header alias."""
    render_platform_header(
        title or "SEARCH & INTELLIGENCE CANVAS",
        subtitle or "Evidence-Backed Multi-Engine Retrieval & AI Neural Synthesis",
    )


def render_empty_state(icon: str, title: str, description: str):
    """Render a clean, professional empty state card."""
    safe_icon = html.escape(icon)
    safe_title = html.escape(title)
    safe_desc = html.escape(description)
    st.markdown(f"""
        <div class="empty-state-container">
            <div class="empty-icon">{safe_icon}</div>
            <div class="empty-title">{safe_title}</div>
            <div class="empty-desc">{safe_desc}</div>
        </div>
    """, unsafe_allow_html=True)


def render_callout(text: str, level: str = "info"):
    """Render clean callout box with Orange/Purple/Green semantic borders."""
    safe_text = html.escape(text)
    colors = {
        "info": ("#A855F7", "rgba(168, 85, 247, 0.10)", "ℹ️"),
        "success": ("#10B981", "rgba(16, 185, 129, 0.10)", "✓"),
        "warning": ("#F97316", "rgba(249, 115, 22, 0.10)", "⚠️"),
        "danger": ("#EF4444", "rgba(239, 68, 68, 0.10)", "✗"),
    }
    color, bg, glyph = colors.get(level, colors["info"])
    st.markdown(f"""
        <div style="background: {bg}; border-left: 3px solid {color}; border-radius: 8px; padding: 0.75rem 1rem; margin: 0.8rem 0; font-size: 0.86rem; color: #F1F5F9; display: flex; align-items: flex-start; gap: 0.6rem;">
            <span style="color: {color}; font-weight: 700;">{glyph}</span>
            <div style="line-height: 1.5;">{safe_text}</div>
        </div>
    """, unsafe_allow_html=True)


def render_control_label(label: str):
    """Render compact section label with subtle horizontal accent rule."""
    safe_label = html.escape(label)
    st.markdown(f"""
        <div style="font-size: 0.72rem; font-weight: 700; letter-spacing: 0.08em; color: #F97316; text-transform: uppercase; margin-bottom: 0.25rem; display: flex; align-items: center; gap: 0.45rem;">
            <span>{safe_label}</span>
            <div style="flex: 1; height: 1px; background: linear-gradient(90deg, rgba(249, 115, 22, 0.35), transparent);"></div>
        </div>
    """, unsafe_allow_html=True)


render_sidebar_label = render_control_label


def render_completion_banner(summary: CrawlSessionSummary):
    """Render executive crawl session summary panel with orange/purple accents."""
    elapsed = max(0.01, summary.elapsed_seconds)
    velocity = summary.pages_crawled / elapsed
    total_attempts = summary.pages_crawled + summary.failed_urls_count
    success_rate = (summary.pages_crawled / total_attempts * 100) if total_attempts > 0 else 100.0

    seed_display = summary.start_url
    if len(seed_display) > 52:
        seed_display = seed_display[:49] + "..."

    safe_seed_display = html.escape(seed_display)
    safe_session_id = html.escape(summary.session_id)
    policy_str = "DOMAIN-SCOPED" if summary.stay_on_domain else "CROSS-DOMAIN"
    seed_tag = f"🔍 QUERY: {safe_seed_display}" if summary.search_query else f"🌐 TARGET: {safe_seed_display}"

    st.markdown(f"""
        <div class="glass-panel" style="border-top: 2px solid #F97316; margin-bottom: 1.2rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.6rem;">
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span class="status-dot green-pulse"></span>
                    <span style="font-size: 0.76rem; font-weight: 700; color: #10B981; letter-spacing: 0.06em; text-transform: uppercase;">
                        Crawl Session Completed
                    </span>
                </div>
                <div style="display: flex; gap: 0.6rem; align-items: center; flex-wrap: wrap;">
                    <span style="font-size: 0.72rem; color: #CBD5E1; background: rgba(255,255,255,0.06); padding: 0.2rem 0.6rem; border-radius: 6px; border: 1px solid rgba(255,255,255,0.08);">
                        {seed_tag}
                    </span>
                    <span style="font-size: 0.70rem; color: #64748B; font-family: 'JetBrains Mono', monospace;">
                        ID: {safe_session_id}
                    </span>
                </div>
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 0.8rem;">
                <div class="metric-card-box">
                    <div class="metric-card-header">Pages Crawled</div>
                    <div class="metric-card-val" style="color: #F97316;">{summary.pages_crawled}</div>
                    <div class="metric-card-sub">Cap: {summary.max_pages} pages</div>
                </div>
                <div class="metric-card-box">
                    <div class="metric-card-header">Time Elapsed</div>
                    <div class="metric-card-val" style="color: #10B981;">{summary.elapsed_seconds:.1f}s</div>
                    <div class="metric-card-sub">{velocity:.1f} p/s velocity</div>
                </div>
                <div class="metric-card-box">
                    <div class="metric-card-header">Frontier Depth</div>
                    <div class="metric-card-val" style="color: #A855F7;">D{summary.max_depth_reached} <span style="font-size: 0.8rem; color: #64748B;">/ D{summary.max_depth}</span></div>
                    <div class="metric-card-sub">{policy_str}</div>
                </div>
                <div class="metric-card-box">
                    <div class="metric-card-header">Success Rate</div>
                    <div class="metric-card-val" style="color: {'#10B981' if success_rate >= 95 else '#EF4444'};"><span style="color: inherit;">{success_rate:.1f}%</span></div>
                    <div class="metric-card-sub">{summary.failed_urls_count} failed requests</div>
                </div>
                <div class="metric-card-box">
                    <div class="metric-card-header">Discovered URLs</div>
                    <div class="metric-card-val" style="color: #FB923C;">{summary.discovered_urls_count:,}</div>
                    <div class="metric-card-sub">Extracted hyperlinks</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_kpi_cards(summary: CrawlSessionSummary, pages: Optional[List[PageResult]] = None):
    """Render 4 to 6 clean metric cards across the results summary."""
    if pages and len(pages) > 0:
        latencies = [p.response_time for p in pages if p.response_time is not None]
        avg_latency = (sum(latencies) / len(latencies)) if latencies else 0.0
    else:
        avg_latency = 0.0
    latency_str = f"{avg_latency * 1000:.0f} ms" if avg_latency < 1.0 else f"{avg_latency:.2f} s"

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f"""
            <div class="metric-card-box">
                <div class="metric-card-header">Total Pages</div>
                <div class="metric-card-val" style="color: #F97316;">{summary.pages_crawled}</div>
                <div class="metric-card-sub">Crawled pages</div>
            </div>
        """, unsafe_allow_html=True)
    with c2:
        domains_count = len({p.domain for p in pages if p.domain}) if pages else 1
        st.markdown(f"""
            <div class="metric-card-box">
                <div class="metric-card-header">Unique Domains</div>
                <div class="metric-card-val" style="color: #FB923C;">{domains_count}</div>
                <div class="metric-card-sub">Different domains</div>
            </div>
        """, unsafe_allow_html=True)
    with c3:
        fail_color = '#EF4444' if summary.failed_urls_count > 0 else '#10B981'
        st.markdown(f"""
            <div class="metric-card-box">
                <div class="metric-card-header">Failed Requests</div>
                <div class="metric-card-val" style="color: {fail_color};">{summary.failed_urls_count}</div>
                <div class="metric-card-sub">Errors encountered</div>
            </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
            <div class="metric-card-box">
                <div class="metric-card-header">Discovered URLs</div>
                <div class="metric-card-val" style="color: #A855F7;">{summary.discovered_urls_count:,}</div>
                <div class="metric-card-sub">Hyperlinks found</div>
            </div>
        """, unsafe_allow_html=True)
    with c5:
        st.markdown(f"""
            <div class="metric-card-box">
                <div class="metric-card-header">Avg Response</div>
                <div class="metric-card-val" style="color: #10B981;">{latency_str}</div>
                <div class="metric-card-sub">Across all requests</div>
            </div>
        """, unsafe_allow_html=True)
