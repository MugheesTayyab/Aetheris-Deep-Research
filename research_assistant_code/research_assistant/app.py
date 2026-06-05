import os
import uuid
import html as html_lib
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import HumanMessage
from langgraph.types import Command
from graph import app as research_graph

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Aetheris · Deep Research",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS THEME  —  Aetheris design
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

/* ═══════════════════════════════════════════════════════════════
   DESIGN TOKENS  —  Aetheris v2 (refined earthy + modern depth)
   ═══════════════════════════════════════════════════════════════ */
:root {
    /* Sidebar — deep forest */
    --sb-grad-1: #2e3a2a;
    --sb-grad-2: #1f2a1c;
    --sb-hover:  rgba(255,255,255,.07);
    --sb-active: rgba(255,255,255,.13);
    --sb-bdr:    rgba(255,255,255,.08);
    --sb-text:   rgba(255,255,255,.92);
    --sb-muted:  rgba(255,255,255,.55);

    /* Surfaces — warm parchment */
    --bg-grad-1: #f1ece0;
    --bg-grad-2: #e8e1d0;
    --right-1:   #efe9db;
    --right-2:   #e6dfcc;
    --card:      #ffffff;
    --card-soft: #faf7f0;
    --bdr:       #d6cdb6;
    --bdr-soft:  #e3dbc7;

    /* Elevation */
    --shd-sm: 0 1px 2px rgba(40,30,15,.06);
    --shd:    0 4px 18px rgba(40,30,15,.07), 0 1px 3px rgba(40,30,15,.05);
    --shd-lg: 0 12px 38px rgba(40,30,15,.10), 0 2px 6px rgba(40,30,15,.06);

    /* Brand greens */
    --g1:  #2f3f29;
    --g2:  #4a6340;
    --g3:  #6c8a5d;
    --g-accent: #84a674;
    --g-glow:   rgba(108,138,93,.35);

    /* Type */
    --t1:  #1a261a;
    --t2:  #4a5b48;
    --t3:  #8a9885;

    /* Status — high-confidence */
    --conf-bg:  #e6f1de;
    --conf-tx:  #2f5d28;
    --conf-bd:  #a8c898;
    /* Status — medium-confidence */
    --med-bg:   #fbf3dc;
    --med-tx:   #7a5a00;
    --med-bd:   #d8b85a;

    /* Tag */
    --tag-bg:   #ede5d0;
    --tag-tx:   #4a5b48;

    /* Warn */
    --warn-bg:  #fdf4dc;
    --warn-bd:  #e6c870;
    --warn-tx:  #7a5a00;
    --warn-bd2: #5e4400;

    /* Radii */
    --r-sm: 8px;
    --r:    12px;
    --r-lg: 16px;
    --r-xl: 22px;
}

/* ═══════════════════════════════════════════════════════════════
   GLOBAL RESET
   ═══════════════════════════════════════════════════════════════ */
*, *::before, *::after { box-sizing: border-box; }
html, body { height: 100%; }
.stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    background:
        radial-gradient(1200px 600px at 100% 0%, rgba(108,138,93,.10), transparent 60%),
        radial-gradient(900px 500px at 0% 100%, rgba(74,99,64,.08), transparent 55%),
        linear-gradient(180deg, var(--bg-grad-1) 0%, var(--bg-grad-2) 100%) !important;
    color: var(--t1) !important;
}

/* Hide Streamlit chrome */
header[data-testid="stHeader"],
footer,
#MainMenu,
.stDeployButton { display: none !important; }

/* Main block container — full bleed */
.main .block-container {
    padding: 0 !important;
    max-width: 100% !important;
    background: transparent !important;
}

/* ═══════════════════════════════════════════════════════════════
   SIDEBAR
   ═══════════════════════════════════════════════════════════════ */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--sb-grad-1) 0%, var(--sb-grad-2) 100%) !important;
    border-right: 1px solid var(--sb-bdr);
    min-width: 230px !important;
    width: 230px !important;
}
section[data-testid="stSidebar"] > div {
    background: transparent !important;
    padding: 0 !important;
}
section[data-testid="stSidebar"] * {
    color: var(--sb-text) !important;
    font-family: 'Inter', sans-serif !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
    padding: 0 !important;
}
/* Sidebar button: "New Synthesis" — gradient pill */
section[data-testid="stSidebar"] .stButton > button {
    background: linear-gradient(135deg, var(--g2), var(--g3)) !important;
    color: #fff !important;
    border: 1px solid rgba(255,255,255,.14) !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    padding: 10px 14px !important;
    margin: 4px 12px !important;
    width: calc(100% - 24px) !important;
    box-shadow: 0 4px 12px rgba(0,0,0,.25), inset 0 1px 0 rgba(255,255,255,.12) !important;
    transition: transform .15s ease, box-shadow .15s ease, filter .15s ease !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 6px !important;
    letter-spacing: 0.02em !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    transform: translateY(-1px);
    filter: brightness(1.08);
    box-shadow: 0 6px 18px rgba(0,0,0,.30), inset 0 1px 0 rgba(255,255,255,.18) !important;
}
section[data-testid="stSidebar"] .stButton > button:active {
    transform: translateY(0);
}

/* Column padding removal */
[data-testid="column"] { padding: 0 !important; }

/* ═══════════════════════════════════════════════════════════════
   CHAT INPUT
   ═══════════════════════════════════════════════════════════════ */
[data-testid="stChatInput"] {
    background: linear-gradient(135deg, var(--g1), var(--g2)) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 14px !important;
    box-shadow: var(--shd) !important;
    transition: border-color .18s ease, box-shadow .18s ease;
}
[data-testid="stChatInput"]:focus-within {
    border-color: var(--g-accent) !important;
    box-shadow: 0 0 0 4px var(--g-glow), var(--shd) !important;
}
[data-testid="stChatInput"] textarea {
    font-size: 14px !important;
    color: #ffffff !important;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: var(--t3) !important; }
[data-testid="stChatInputSubmitButton"] button {
    background: linear-gradient(135deg, var(--g1), var(--g2)) !important;
    border-radius: 10px !important;
    transition: transform .12s ease, filter .12s ease;
}
[data-testid="stChatInputSubmitButton"] button:hover {
    filter: brightness(1.1);
    transform: translateY(-1px);
}

/* Spinner */
.stSpinner > div > div { border-top-color: var(--g3) !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, var(--bdr), var(--tag-bg));
    border-radius: 6px;
}
::-webkit-scrollbar-thumb:hover { background: var(--t3); }

/* ═══════════════════════════════════════════════════════════════
   SIDEBAR LOGO + NAV
   ═══════════════════════════════════════════════════════════════ */
.sb-logo {
    display:flex; align-items:center; gap:12px;
    padding: 24px 18px 14px;
}
.sb-av {
    width:40px; height:40px;
    background: linear-gradient(135deg, var(--g3), var(--g2));
    border-radius: 11px;
    display:flex; align-items:center; justify-content:center;
    font-weight:800; font-size:17px; color:#fff !important;
    flex-shrink:0;
    box-shadow: 0 4px 12px rgba(0,0,0,.30), inset 0 1px 0 rgba(255,255,255,.18);
    letter-spacing: -.02em;
}
.sb-name {
    font-size:16px; font-weight:700; color:#fff !important;
    line-height:1.15; letter-spacing:.01em;
}
.sb-sub {
    font-size:9px; font-weight:600; color:var(--sb-muted) !important;
    letter-spacing:.16em; text-transform:uppercase; margin-top: 2px;
}

.sb-div { height:1px; background:var(--sb-bdr); margin:10px 14px; }

.sb-nav {
    display:flex; align-items:center; gap:11px;
    padding: 10px 18px;
    margin: 1px 10px;
    border-radius: 8px;
    font-size:13px; font-weight:500;
    color:var(--sb-muted) !important;
    cursor:pointer;
    transition: background .15s ease, color .15s ease, transform .12s ease;
}
.sb-nav:hover {
    background: var(--sb-hover);
    color: var(--sb-text) !important;
    transform: translateX(2px);
}
.sb-nav.on {
    background: var(--sb-active);
    color:#fff !important; font-weight:600;
    box-shadow: inset 3px 0 0 var(--g-accent);
}
.sb-nav:active {
    background: rgba(255,255,255,.20) !important;
    transform: translateX(3px) scale(0.98) !important;
    transition: none;
}
.sb-nav-ico {
    width: 16px; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    opacity: .85;
}
.sb-nav-ico svg { display: block; }

.sb-foot { border-top:1px solid var(--sb-bdr); margin: 20px 14px 12px; padding-top:8px; }

/* ═══════════════════════════════════════════════════════════════
   SESSION HEADER
   ═══════════════════════════════════════════════════════════════ */
.s-hdr {
    padding: 0 0 10px 0;
    border-bottom: 1px solid var(--bdr);
    background: transparent;
    position: sticky; top: 0; z-index: 10;
    text-align: center;
    margin-top: -20px; /* Minimize space from top */
}
.s-lbl {
    font-size:10px; font-weight:700; color:var(--t3);
    text-transform:uppercase; letter-spacing:.14em; margin-bottom:6px;
    justify-content: center;
    display: flex;
}
.s-title {
    font-size: clamp(24px, 3vw, 32px); /* Bigger */
    font-weight:800; color:var(--t1);
    display:flex; align-items:center; justify-content:center; /* Center */
    flex-wrap:wrap; gap:10px;
    letter-spacing: -.01em;
}
.s-badge {
    display:inline-flex; align-items:center; gap:7px;
    background: var(--card);
    border:1px solid var(--bdr);
    border-radius:999px; padding:5px 12px;
    font-size:12px; font-weight:600; color:var(--t2);
    box-shadow: var(--shd-sm);
}
.s-dot {
    display:inline-block;
    width:8px; height:8px; border-radius:50%;
    background:#5fb95f;
    box-shadow: 0 0 0 3px rgba(95,185,95,.22);
    animation: pulse 2.4s ease-in-out infinite;
}
@keyframes pulse {
    0%, 100% { box-shadow: 0 0 0 3px rgba(95,185,95,.22); }
    50%      { box-shadow: 0 0 0 6px rgba(95,185,95,.05); }
}

/* ═══════════════════════════════════════════════════════════════
   EMPTY STATE
   ═══════════════════════════════════════════════════════════════ */
.empty { text-align:center; padding: clamp(48px, 9vw, 90px) 20px; }
.empty-ico {
    font-size: clamp(40px, 6vw, 56px);
    margin-bottom: 18px;
    display:inline-flex; width: 84px; height: 84px;
    align-items:center; justify-content:center;
    border-radius: 22px;
    background: linear-gradient(135deg, var(--card), var(--card-soft));
    border: 1px solid var(--bdr);
    box-shadow: var(--shd);
}
.empty-t {
    font-size: clamp(18px, 2vw, 22px);
    font-weight:700; color:var(--t1); margin-bottom:8px;
    letter-spacing: -.01em;
}
.empty-s {
    font-size: 13px; color:var(--t2); line-height:1.75;
    max-width: 440px; margin: 0 auto;
}

/* Message feed padding */
.feed { padding: clamp(16px, 2.4vw, 26px) clamp(14px, 3vw, 30px) 14px; }

/* ═══════════════════════════════════════════════════════════════
   RESEARCH RESULT CARD
   ═══════════════════════════════════════════════════════════════ */
.rc {
    background: var(--card);
    border-radius: var(--r-lg);
    padding: clamp(16px, 2vw, 22px) clamp(18px, 2.2vw, 24px);
    box-shadow: var(--shd);
    border: 1px solid var(--bdr-soft);
    margin-bottom: 18px;
    animation: fadeUp .35s ease-out both;
    transition: transform .18s ease, box-shadow .18s ease;
}
.rc:hover {
    transform: translateY(-1px);
    box-shadow: var(--shd-lg);
}
@keyframes fadeUp {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
}
.rc-hdr {
    display:flex; align-items:center; justify-content:space-between;
    margin-bottom: 14px; flex-wrap:wrap; gap:10px;
}
.rc-trow { display:flex; align-items:center; gap:12px; min-width: 0; }
.rc-ico {
    width: 36px; height: 36px;
    background: linear-gradient(135deg, var(--conf-bg), #d4e7c8);
    border-radius: 10px;
    display:flex; align-items:center; justify-content:center;
    font-size: 16px; flex-shrink: 0;
    border: 1px solid var(--conf-bd);
}
.rc-title {
    font-size: clamp(15px, 1.4vw, 17px);
    font-weight:700; color:var(--t1);
    letter-spacing: -.01em;
}
.rc-badge-hi, .rc-badge-md {
    display:inline-flex; align-items:center; gap:5px;
    border-radius: 999px; padding:4px 11px;
    font-size:11px; font-weight:700;
    letter-spacing: .01em;
    white-space: nowrap;
}
.rc-badge-hi { background: var(--conf-bg); border:1px solid var(--conf-bd); color: var(--conf-tx); }
.rc-badge-md { background: var(--med-bg);  border:1px solid var(--med-bd);  color: var(--med-tx); }

.rc-body {
    font-size: clamp(13.5px, 1vw, 14.5px);
    line-height: 1.78;
    color: var(--t1);
    margin-bottom: 14px;
    white-space: pre-wrap;
    word-wrap: break-word;
}
.rc-tags { display:flex; flex-wrap:wrap; gap:6px; }
.rc-tag {
    background: var(--tag-bg);
    border-radius: 7px;
    padding: 4px 10px;
    font-size: 11px; font-weight: 600;
    color: var(--tag-tx);
    border: 1px solid var(--bdr-soft);
}

/* ═══════════════════════════════════════════════════════════════
   USER BUBBLE
   ═══════════════════════════════════════════════════════════════ */
.uc {
    background: linear-gradient(135deg, var(--g1), var(--g2));
    border-radius: var(--r-lg);
    padding: 14px 18px;
    margin-left: auto;
    max-width: min(82%, 640px);
    margin-bottom: 18px;
    box-shadow: 0 6px 18px rgba(47,63,41,.25), inset 0 1px 0 rgba(255,255,255,.08);
    animation: fadeUp .3s ease-out both;
}
.uc-text {
    font-size: 14px;
    color: rgba(255,255,255,.96);
    line-height: 1.65;
    word-wrap: break-word;
}

/* ═══════════════════════════════════════════════════════════════
   CLARIFICATION CARD
   ═══════════════════════════════════════════════════════════════ */
.cc {
    background: var(--warn-bg);
    border: 1px solid var(--warn-bd);
    border-left: 4px solid var(--warn-bd2);
    border-radius: var(--r);
    padding: 14px 18px;
    margin-bottom: 18px;
    display:flex; gap:14px;
    animation: fadeUp .3s ease-out both;
}
.cc-ico { font-size: 22px; flex-shrink: 0; line-height: 1.2; }
.cc-title {
    font-size: 13px; font-weight: 700; color: var(--warn-bd2);
    margin-bottom: 4px;
    letter-spacing: .02em; text-transform: uppercase;
}
.cc-body { font-size: 13.5px; color: var(--warn-tx); line-height: 1.65; }

/* Input hint row */
.i-hint {
    font-size: 12px; color: var(--t3);
    display:flex; justify-content:space-between;
    margin-top: 6px; padding: 0 6px;
    flex-wrap: wrap; gap: 6px;
}
.i-link { color: var(--g2); font-weight: 600; cursor: pointer; }
.i-link:hover { color: var(--g1); }

/* ═══════════════════════════════════════════════════════════════
   RIGHT PANEL — Synthesis Metrics
   ═══════════════════════════════════════════════════════════════ */
.rp {
    background: transparent !important;
    border-left: 1px solid var(--bdr);
    padding: clamp(12px, 1.4vw, 18px) clamp(8px, 0.8vw, 12px);
    height: auto !important;
    min-height: auto !important; /* Removes the 100vh stretching bottleneck */
}
.rp-card {
    background: var(--card);
    border-radius: var(--r-lg);
    border: 1px solid var(--bdr-soft);
    box-shadow: var(--shd);
    padding: 18px 16px;
    margin-bottom: 12px;
}
.rp-title {
    font-size: 15px; font-weight: 800; color: var(--t1);
    margin-bottom: 18px;
    letter-spacing: -.01em;
    display:flex; align-items:center; gap:8px;
}
.rp-title::before {
    content: ""; width: 4px; height: 18px;
    background: linear-gradient(180deg, var(--g2), var(--g-accent));
    border-radius: 2px;
}
.rp-lbl {
    font-size: 11.5px; font-weight: 600; color: var(--t2);
    display:flex; justify-content:space-between; align-items:center;
    margin-bottom: 7px;
}
.rp-pct { font-size: 13px; font-weight: 800; color: var(--g2); }
.prog {
    height: 8px;
    background: rgba(0,0,0,.12);
    border-radius: 4px;
    overflow: hidden;
    margin-bottom: 8px;
    border: 1px solid rgba(0,0,0,.07);
}
.prog-fill {
    height: 100%;
    border-radius: 4px;
    background: linear-gradient(90deg, var(--g2), var(--g-accent));
    box-shadow: 0 0 8px var(--g-glow);
    transition: width .6s cubic-bezier(.4,.0,.2,1);
}
.rp-sec {
    font-size: 9.5px; font-weight: 700; color: var(--t3);
    letter-spacing: .14em; text-transform: uppercase;
    margin: 20px 0 10px;
}
.ag {
    display:flex; align-items:center; gap: 11px;
    padding: 10px 12px;
    border-radius: 10px;
    margin-bottom: 6px;
    background: rgba(255,255,255,.65);
    border: 1px solid rgba(0,0,0,.04);
    transition: transform .15s ease, box-shadow .15s ease, background .15s ease;
}
.ag:hover {
    background: rgba(255,255,255,.85);
    transform: translateX(2px);
    box-shadow: var(--shd-sm);
}
.ag-av {
    width: 32px; height: 32px; border-radius: 10px;
    display:flex; align-items:center; justify-content:center;
    font-size: 12px; font-weight: 800;
    flex-shrink: 0;
    letter-spacing: -.02em;
}
.ag-av.complete {
    background: linear-gradient(135deg, var(--conf-bg), #d4e7c8);
    color: var(--g1);
    border: 1px solid var(--conf-bd);
}
.ag-av.idle {
    background: var(--bdr-soft);
    color: var(--t3);
    border: 1px solid var(--bdr);
}
.ag-av.busy {
    background: linear-gradient(135deg, #f7e890, #ecd460);
    color: #6b4f00;
    border: 1px solid #d8b85a;
    animation: pulse-soft 1.4s ease-in-out infinite;
}
@keyframes pulse-soft {
    0%, 100% { opacity: 1; }
    50%      { opacity: .7; }
}
.ag-name { font-size: 12.5px; font-weight: 600; color: var(--t1); }
.ag-sub  { font-size: 10.5px; color: var(--t3); margin-top: 2px; }

/* Validation pill */
.vp-ok, .vp-fail {
    padding: 9px 13px;
    border-radius: 10px;
    font-size: 12px; font-weight: 700;
    margin-top: 14px;
    display:flex; align-items:center; gap:7px;
}
.vp-ok   { background: var(--conf-bg); color: var(--conf-tx); border: 1px solid var(--conf-bd); }
.vp-fail { background: #fde8d4;        color: #8a4000;        border: 1px solid #e8a878; }

/* Right-panel button (Halt) */
[data-testid="column"]:last-child .stButton > button {
    background: transparent !important; /* Removes black color */
    color: #ffffff !important;          /* White text */
    border: 1px solid rgba(255, 255, 255, 0.3) !important;
    border-radius: 10px !important;
    font-size: 13px !important;
    font-weight: 700 !important;
    letter-spacing: 0.02em !important;
    box-shadow: var(--shd-sm) !important;
    transition: all .15s ease !important;
}

[data-testid="column"]:last-child .stButton > button:hover {
    background: rgba(255, 255, 255, 0.1) !important;
    color: #ffffff !important;
    border-color: rgba(255, 255, 255, 0.6) !important;
    transform: translateY(-1px);
}
[data-testid="column"]:last-child .stButton > button:hover {
    background: #fde8d4 !important;
    color: #8a4000 !important;
    border-color: #e8a878 !important;
    transform: translateY(-1px);
}

/* ═══════════════════════════════════════════════════════════════
   RESPONSIVE BREAKPOINTS
   ═══════════════════════════════════════════════════════════════ */

/* Tablet (≤ 1024px) — soften column gap, tighten paddings */
@media (max-width: 1024px) {
    section[data-testid="stSidebar"] {
        min-width: 200px !important;
        width: 200px !important;
    }
    .rp { padding: 18px 14px; }
    .rp-title { font-size: 14px; }
    .ag-name { font-size: 12px; }
    .ag-sub  { font-size: 10px; }
}

/* Mobile-landscape (≤ 820px) — stack columns, sidebar collapses to overlay */
@media (max-width: 820px) {
    /* Streamlit's columns wrap nicely when we force block layout */
    [data-testid="stHorizontalBlock"] {
        flex-direction: column !important;
    }
    [data-testid="column"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 100% !important;
    }
    .rp {
        border-left: none;
        border-top: 1px solid var(--bdr);
        min-height: auto;
        padding: 18px 16px 24px;
    }
    .rp-title { margin-bottom: 14px; }
    /* Sidebar can collapse via Streamlit's own toggle on mobile */
    section[data-testid="stSidebar"] {
        min-width: 240px !important;
        width: 240px !important;
    }
}

/* Mobile (≤ 540px) — compact everything */
@media (max-width: 540px) {
    .s-hdr { padding: 14px 16px 12px; }
    .s-title { font-size: 17px; }
    .s-badge { font-size: 11px; padding: 4px 10px; }
    .feed { padding: 14px 14px 8px; }
    .rc {
        padding: 14px 16px;
        border-radius: 12px;
        margin-bottom: 14px;
    }
    .rc-ico { width: 32px; height: 32px; font-size: 14px; }
    .rc-title { font-size: 14.5px; }
    .rc-body { font-size: 13.5px; line-height: 1.7; }
    .uc {
        max-width: 92%;
        padding: 12px 15px;
        border-radius: 12px;
    }
    .uc-text { font-size: 13.5px; }
    .cc { padding: 12px 14px; gap: 10px; }
    .cc-ico { font-size: 18px; }
    .empty { padding: 48px 16px; }
    .empty-ico { width: 68px; height: 68px; font-size: 38px; }
    .i-hint { font-size: 12px; }
    .rp { padding: 16px 14px 22px; }
    .ag { padding: 9px 10px; }
    .ag-av { width: 28px; height: 28px; font-size: 11px; }
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: .001s !important;
        transition-duration: .001s !important;
    }
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
def _init():
    defs = {
        "thread_id":             str(uuid.uuid4()),
        "is_clarifying":         False,
        "clarification_question": "",
        "display_history":       [],   # list of dicts: role/content/title/confidence/icon/tags
        "session_title":         "Synthesis Workspace",
        "state_values":          {},
    }
    for k, v in defs.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()
config = {"configurable": {"thread_id": st.session_state.thread_id}}

# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────
def _esc(s: str) -> str:
    return html_lib.escape(str(s))

def _truncate(text: str, n: int = 50) -> str:
    return text[:n] + "…" if len(text) > n else text

def _completion(vals: dict) -> int:
    pts = 0
    if vals.get("clarity_status"):       pts += 20
    if vals.get("confidence_score", 0):  pts += 30
    if vals.get("validation_result"):    pts += 20
    if vals.get("final_response"):       pts += 30
    return min(pts, 100)

def _agent_list(vals: dict) -> list[dict]:
    clarity = vals.get("clarity_status", "")
    conf    = vals.get("confidence_score", 0)
    vr      = vals.get("validation_result", "")
    fr      = vals.get("final_response", "")
    return [
        {
            "icon": "Q", "name": "Query Analyzer",
            "sub":  "Clear" if clarity == "clear" else ("Needs clarification" if clarity else "Awaiting query"),
            "status": "complete" if clarity else "idle",
        },
        {
            "icon": "L", "name": "Literature Scraper",
            "sub":  f"Confidence {conf}/10" if conf else "Awaiting query",
            "status": "complete" if conf else "idle",
        },
        {
            "icon": "F", "name": "Fact-Check Validator",
            "sub":  vr.title() if vr else "Awaiting data",
            "status": "complete" if vr else "idle",
        },
        {
            "icon": "D", "name": "Drafting Engine",
            "sub":  "Report ready" if fr else "Idle · Awaiting data",
            "status": "complete" if fr else "idle",
        },
    ]

def _active_count(vals: dict) -> int:
    return sum(1 for a in _agent_list(vals) if a["status"] == "complete")

def _extract_tags(query: str) -> list[str]:
    stop = {"the","and","for","with","that","this","from","are","was","were","have","has","not","but","its"}
    words = [w.strip(".,!?;:\"'").title() for w in query.split() if len(w) > 4 and w.lower() not in stop]
    seen, out = set(), []
    for w in words:
        if w.lower() not in seen:
            seen.add(w.lower()); out.append(w)
        if len(out) == 4:
            break
    return out

# ─────────────────────────────────────────────────────────────────────────────
# HTML COMPONENT BUILDERS
# ─────────────────────────────────────────────────────────────────────────────
def html_user_card(content: str) -> str:
    return f'<div class="uc"><div class="uc-text">{_esc(content)}</div></div>'

def html_result_card(content: str, title: str, icon: str, confidence: int, tags: list[str]) -> str:
    badge = ""
    if confidence >= 7:
        badge = '<span class="rc-badge-hi">✅ High Confidence</span>'
    elif confidence >= 4:
        badge = '<span class="rc-badge-md">⚠️ Medium Confidence</span>'

    tags_html = "".join(f'<span class="rc-tag">{_esc(t)}</span>' for t in tags)
    tags_block = f'<div class="rc-tags">{tags_html}</div>' if tags_html else ""

    return f"""
<div class="rc">
  <div class="rc-hdr">
    <div class="rc-trow">
      <div class="rc-ico">{icon}</div>
      <span class="rc-title">{_esc(title)}</span>
    </div>
    {badge}
  </div>
  <div class="rc-body">{_esc(content)}</div>
  {tags_block}
</div>"""

def html_clarify_card(question: str) -> str:
    return f"""
<div class="cc">
  <div class="cc-ico">🤔</div>
  <div>
    <div class="cc-title">Clarification Needed</div>
    <div class="cc-body">{_esc(question)}</div>
  </div>
</div>"""

def html_empty_state() -> str:
    return """
<div class="empty">
  <div class="empty-ico">🔬</div>
  <div class="empty-t">Aetheris Deep Research Engine</div>
  <div class="empty-s">
    Initialize an advanced synthesis cycle. The multi-agent pipeline orchestrates autonomous models to cross-examine literature streams, audit claim validity, and generate structured insights.
  </div>
  
  <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; max-width: 760px; margin: 36px auto 0; text-align: left;">
    <div style="background: var(--card); border: 1px solid var(--bdr-soft); padding: 16px; border-radius: 12px; box-shadow: var(--shd-sm);">
        <div style="font-weight: 700; font-size: 13.5px; color: var(--g1); margin-bottom: 6px;">📖 Literature Extraction</div>
        <div style="font-size: 12px; color: var(--t2); line-height: 1.6;">Map historical frameworks, contextual vectors, and divergent academic standpoints on any inquiry.</div>
    </div>
    <div style="background: var(--card); border: 1px solid var(--bdr-soft); padding: 16px; border-radius: 12px; box-shadow: var(--shd-sm);">
        <div style="font-weight: 700; font-size: 13.5px; color: var(--g1); margin-bottom: 6px;">🛡️ Fact-Check Validation</div>
        <div style="font-size: 12px; color: var(--t2); line-height: 1.6;">Cross-examine operational assertions against empirical datasets, isolating conflicting points.</div>
    </div>
    <div style="background: var(--card); border: 1px solid var(--bdr-soft); padding: 16px; border-radius: 12px; box-shadow: var(--shd-sm);">
        <div style="font-weight: 700; font-size: 13.5px; color: var(--g1); margin-bottom: 6px;">📊 Auto-Drafting Engine</div>
        <div style="font-size: 12px; color: var(--t2); line-height: 1.6;">Synthesize core trends into publication-ready briefings decorated with categorical tags.</div>
    </div>
  </div>
</div>"""

def html_session_header(title: str, n_active: int) -> str:
    if n_active > 0:
        word = "Agent" if n_active == 1 else "Agents"
        badge = f'<span class="s-badge"><span class="s-dot"></span>{n_active} {word} Complete</span>'
    else:
        badge = ""
    return f"""
<div class="s-hdr">
  <div class="s-lbl">Active Session</div>
  <div class="s-title">{_esc(title)}{badge}</div>
</div>"""

def html_agent_item(icon: str, name: str, sub: str, status: str) -> str:
    return f"""
<div class="ag">
  <div class="ag-av {status}">{icon}</div>
  <div>
    <div class="ag-name">{name}</div>
    <div class="ag-sub">{sub}</div>
  </div>
</div>"""

# ─────────────────────────────────────────────────────────────────────────────
# SVG ICON LIBRARY  —  Lucide-style, 14 × 14, stroke-based
# ─────────────────────────────────────────────────────────────────────────────
_S = 'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"'
_NAV_ICONS = {
    "research":  f'<svg width="14" height="14" viewBox="0 0 24 24" {_S}><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>',
    "synthesis": f'<svg width="14" height="14" viewBox="0 0 24 24" {_S}><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>',
    "pipeline":  f'<svg width="14" height="14" viewBox="0 0 24 24" {_S}><circle cx="12" cy="5" r="2"/><circle cx="5" cy="19" r="2"/><circle cx="19" cy="19" r="2"/><line x1="12" y1="7" x2="5.5" y2="17"/><line x1="12" y1="7" x2="18.5" y2="17"/></svg>',
    "knowledge": f'<svg width="14" height="14" viewBox="0 0 24 24" {_S}><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>',
    "archive":   f'<svg width="14" height="14" viewBox="0 0 24 24" {_S}><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg>',
    "settings":  f'<svg width="14" height="14" viewBox="0 0 24 24" {_S}><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
    "support":   f'<svg width="14" height="14" viewBox="0 0 24 24" {_S}><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
}

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
<div class="sb-logo">
  <div class="sb-av">A</div>
  <div>
    <div class="sb-name">Aetheris</div>
    <div class="sb-sub">Deep Research</div>
  </div>
</div>""", unsafe_allow_html=True)

    if st.button("＋  New Synthesis", key="new_btn", use_container_width=True):
        for k in ("thread_id","is_clarifying","clarification_question",
                  "display_history","session_title","state_values"):
            del st.session_state[k]
        _init()
        st.rerun()

    st.markdown('<div class="sb-div"></div>', unsafe_allow_html=True)

    nav_items = [
        (_NAV_ICONS["research"],  "Research Hub",   True),
        (_NAV_ICONS["synthesis"], "Data Synthesis",  False),
        (_NAV_ICONS["pipeline"],  "Agent Pipeline",  False),
        (_NAV_ICONS["knowledge"], "Knowledge Base",  False),
        (_NAV_ICONS["archive"],   "Archive",         False),
    ]
    nav_html = ""
    for ico, label, active in nav_items:
        cls = "sb-nav on" if active else "sb-nav"
        nav_html += f'<div class="{cls}"><span class="sb-nav-ico">{ico}</span>{label}</div>'
    st.markdown(nav_html, unsafe_allow_html=True)

    st.markdown(f"""
<div class="sb-foot">
  <div class="sb-nav"><span class="sb-nav-ico">{_NAV_ICONS["settings"]}</span>Settings</div>
  <div class="sb-nav"><span class="sb-nav-ico">{_NAV_ICONS["support"]}</span>Support</div>
</div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# MAIN LAYOUT  —  2 columns: main content | right metrics panel
# ─────────────────────────────────────────────────────────────────────────────
vals      = st.session_state.state_values
pct       = _completion(vals)
agents    = _agent_list(vals)
n_active  = _active_count(vals)

col_main, col_right = st.columns([3, 1], gap="small")

# ── RIGHT PANEL ───────────────────────────────────────────────────────────────
with col_right:
    # 1. Build the dynamic conditional HTML blocks
    conf_score = vals.get("confidence_score", 0)
    conf_html = ""
    if conf_score:
        cpct = conf_score * 10
        conf_html = f"""
<div class="rp-lbl" style="margin-top:8px;">Confidence Score<span class="rp-pct">{conf_score}/10</span></div>
<div class="prog"><div class="prog-fill" style="width:{cpct}%"></div></div>
"""

    # Assemble the list of deployed agents
    agents_html = "".join(
        html_agent_item(a["icon"], a["name"], a["sub"], a["status"])
        for a in agents
    )

    # Validation result status banner
    vr = vals.get("validation_result", "")
    vr_html = ""
    if vr:
        cls = "vp-ok" if vr == "sufficient" else "vp-fail"
        label = f"✅ Validation: {vr.title()}" if vr == "sufficient" else f"⚠️ Validation: {vr.title()}"
        vr_html = f'<div class="{cls}" style="margin-top: 12px;">{label}</div>'

    # 2. Render everything inside a SINGLE card with container auto-heights
    st.markdown(f"""
<div class="rp" style="min-height: auto !important; height: auto !important; padding-bottom: 0px !important;">
<div class="rp-card" style="margin-bottom: 10px !important;">
<div class="rp-title">Synthesis Metrics</div>
<div class="rp-lbl">Overall Completion<span class="rp-pct">{pct}%</span></div>
<div class="prog"><div class="prog-fill" style="width:{pct}%"></div></div>
{conf_html}
<div class="rp-sec">Deployed Agents</div>
{agents_html}
{vr_html}
</div>
</div>
""", unsafe_allow_html=True)

    # 3. Place the native Halt button cleanly right beneath the card layout
    if st.button("⏸  Halt Synthesis", key="halt_btn", use_container_width=True):
        keys_to_clear = (
            "thread_id", "is_clarifying", "clarification_question",
            "display_history", "session_title", "state_values"
        )
        for k in keys_to_clear:
            if k in st.session_state:
                del st.session_state[k]
        _init()
        st.rerun()

# ── MAIN COLUMN ───────────────────────────────────────────────────────────────
with col_main:
    # Session header
    st.markdown(
        html_session_header(st.session_state.session_title, n_active),
        unsafe_allow_html=True,
    )

    # Message feed
    st.markdown('<div class="feed">', unsafe_allow_html=True)

    history = st.session_state.display_history
    if not history:
        st.markdown(html_empty_state(), unsafe_allow_html=True)
    else:
        for msg in history:
            role = msg["role"]
            if role == "user":
                st.markdown(html_user_card(msg["content"]), unsafe_allow_html=True)
            elif role == "clarification":
                st.markdown(html_clarify_card(msg["content"]), unsafe_allow_html=True)
            else:
                st.markdown(
                    html_result_card(
                        content=msg["content"],
                        title=msg.get("title", "Synthesis Report"),
                        icon=msg.get("icon", "📋"),
                        confidence=msg.get("confidence", 0),
                        tags=msg.get("tags", []),
                    ),
                    unsafe_allow_html=True,
                )

    st.markdown('</div>', unsafe_allow_html=True)

    # ── End of Main Column ─────────────────────────────────────────────────────

# ── Chat input ────────────────────────────────────────────────────────────
placeholder = (
    "Provide clarification to continue research..."
    if st.session_state.is_clarifying
    else "Instruct agents to pivot research focus or synthesize specific findings..."
)
user_input = st.chat_input(placeholder)

# ── Graph invocation ──────────────────────────────────────────────────────
if user_input:
    # Add user bubble to history
    st.session_state.display_history.append({"role": "user", "content": user_input})

    # Update session title from first query
    if st.session_state.session_title == "Synthesis Workspace":
        st.session_state.session_title = _truncate(user_input, 52)

    with st.spinner("Multi-agent system is processing your query…"):
        try:
            if st.session_state.is_clarifying:
                research_graph.invoke(Command(resume=user_input), config=config)
            else:
                research_graph.invoke(
                    {
                        "query":    user_input,
                        "messages": [HumanMessage(content=user_input)],
                        "attempts": 0,
                    },
                    config=config,
                )

            snapshot = research_graph.get_state(config)
            sv = snapshot.values
            st.session_state.state_values = sv

            # Check for human-feedback interrupt
            if snapshot.next and "human_feedback" in snapshot.next:
                cq = ""
                if snapshot.tasks and snapshot.tasks[0].interrupts:
                    cq = str(snapshot.tasks[0].interrupts[0].value)
                st.session_state.is_clarifying        = True
                st.session_state.clarification_question = cq
                st.session_state.display_history.append(
                    {"role": "clarification", "content": cq}
                )

            else:
                st.session_state.is_clarifying = False
                final = sv.get("final_response", "").strip()

                if final:
                    confidence = sv.get("confidence_score", 0)
                    tags       = _extract_tags(user_input)
                    st.session_state.display_history.append({
                        "role":       "assistant",
                        "content":    final,
                        "title":      "Literature Review Summary",
                        "icon":       "📋",
                        "confidence": confidence,
                        "tags":       tags,
                    })
                else:
                    st.session_state.display_history.append({
                        "role":       "assistant",
                        "content":    "Research pipeline completed, but no final response was generated. Please try a more specific query.",
                        "title":      "System Notice",
                        "icon":       "ℹ️",
                        "confidence": 0,
                        "tags":       [],
                    })

            st.rerun()

        except Exception as exc:
            st.error(f"An error occurred while running the research pipeline: {exc}")
