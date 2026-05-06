"""Streamlit theme — CSS injection for a modern, calm UI.

Streamlit's default theme is fine but a bit utilitarian. We add an Inter
font, a subtle gradient backdrop, soft cards, refined buttons and tighter
typography. Everything stays compatible with the dark base set in
``.streamlit/config.toml``.
"""

from __future__ import annotations

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --w-bg: #0b0d12;
    --w-bg-alt: #11141b;
    --w-border: rgba(255,255,255,0.07);
    --w-fg: #ECEFF4;
    --w-fg-dim: #9aa3b2;
    --w-accent: #7c3aed;
    --w-accent-2: #06b6d4;
    --w-good: #22c55e;
    --w-warn: #f59e0b;
    --w-danger: #ef4444;
}

html, body, [class*="css"], .main, .block-container {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    color: var(--w-fg);
    letter-spacing: -0.005em;
}

.block-container {
    padding-top: 1.6rem !important;
    padding-bottom: 4rem !important;
    max-width: 1200px !important;
}

/* Header */
h1, h2, h3, h4 {
    font-weight: 700 !important;
    letter-spacing: -0.02em;
}

h1 {
    font-size: 2rem !important;
    background: linear-gradient(90deg, #fff 0%, #c4b5fd 60%, #a5f3fc 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.25rem !important;
}

p, li, label, .stMarkdown {
    color: var(--w-fg) !important;
    line-height: 1.55;
}

.muted, .caption-soft {
    color: var(--w-fg-dim) !important;
    font-size: 0.875rem;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    border-bottom: 1px solid var(--w-border);
    padding-bottom: 4px;
}
.stTabs [data-baseweb="tab"] {
    height: 42px;
    padding: 0 16px;
    border-radius: 12px;
    background: transparent;
    color: var(--w-fg-dim);
    font-weight: 500;
    transition: all 0.15s ease;
}
.stTabs [data-baseweb="tab"]:hover {
    color: var(--w-fg);
    background: rgba(255,255,255,0.04);
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, rgba(124,58,237,0.16), rgba(6,182,212,0.10));
    color: var(--w-fg) !important;
    border: 1px solid rgba(124,58,237,0.35);
}

/* Buttons */
.stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    border: 1px solid var(--w-border) !important;
    transition: all 0.15s ease;
    padding: 0.55rem 1.1rem !important;
}
.stButton > button:hover {
    border-color: rgba(124,58,237,0.5) !important;
    transform: translateY(-1px);
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #7c3aed 0%, #06b6d4 100%) !important;
    border: none !important;
    color: white !important;
    box-shadow: 0 6px 16px rgba(124,58,237,0.25);
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 8px 22px rgba(124,58,237,0.35);
}

/* Inputs */
.stTextInput input, .stTextArea textarea, .stSelectbox > div > div {
    background: var(--w-bg-alt) !important;
    border: 1px solid var(--w-border) !important;
    border-radius: 10px !important;
    color: var(--w-fg) !important;
    font-size: 0.95rem !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: rgba(124,58,237,0.55) !important;
    box-shadow: 0 0 0 3px rgba(124,58,237,0.18) !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: var(--w-bg-alt) !important;
    border-right: 1px solid var(--w-border);
}

/* Status containers */
.w-card {
    background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));
    border: 1px solid var(--w-border);
    border-radius: 14px;
    padding: 18px 20px;
    margin: 8px 0 14px;
}
.w-card h3 { margin-top: 0 !important; font-size: 1.05rem !important; }

.w-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(124,58,237,0.10);
    color: #c4b5fd;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 500;
    margin-right: 6px;
    border: 1px solid rgba(124,58,237,0.25);
}
.w-pill.good { background: rgba(34,197,94,0.10); color: #86efac; border-color: rgba(34,197,94,0.25); }
.w-pill.warn { background: rgba(245,158,11,0.10); color: #fcd34d; border-color: rgba(245,158,11,0.25); }
.w-pill.muted { background: rgba(255,255,255,0.04); color: var(--w-fg-dim); border-color: var(--w-border); }

.w-translation {
    background: var(--w-bg-alt);
    border: 1px solid var(--w-border);
    border-left: 3px solid var(--w-accent);
    border-radius: 12px;
    padding: 18px 20px;
    font-size: 1.05rem;
    line-height: 1.55;
    white-space: pre-wrap;
}

.w-empty {
    text-align: center;
    color: var(--w-fg-dim);
    padding: 40px 20px;
    border: 1px dashed var(--w-border);
    border-radius: 14px;
}

code, kbd, pre, .stCodeBlock {
    font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, monospace !important;
}

/* Hide Streamlit chrome we don't need */
header[data-testid="stHeader"] { background: transparent; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }

/* Dataframe polish */
[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid var(--w-border);
}
</style>
"""


def inject(st_module) -> None:
    """Inject the CSS into the current Streamlit page."""
    st_module.markdown(CSS, unsafe_allow_html=True)


__all__ = ["CSS", "inject"]
