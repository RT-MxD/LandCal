"""
Streamlit Web Application for Land Calculation & Reports
"""

import os
from datetime import date, datetime
import streamlit as st

from land_graph import run_land_calculation
from photo_manager import (
    sanitize_survey_no,
    save_survey_photo,
    delete_survey_photo,
    get_all_survey_photos,
    photo_already_saved,
    get_photo_display_url,
)
from db import (
    check_db_status,
    get_saved_reports,
    delete_report_by_id,
    export_reports_to_csv,
)

# Page Configuration
st.set_page_config(
    page_title="LandCal — Land Valuation & Registry",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "ui_theme" not in st.session_state:
    st.session_state.ui_theme = "Dark"

is_dark = st.session_state.ui_theme == "Dark"

# Explicit High-Contrast Palettes for Dark & Light Modes
if is_dark:
    bg_app = "#0b0f19"
    bg_sidebar = "#111827"
    bg_card = "#1e293b"
    bg_input = "#0f172a"
    bg_disabled = "#334155"
    text_primary = "#f8fafc"
    text_secondary = "#cbd5e1"
    text_muted = "#94a3b8"
    border_color = "#334155"
    border_focus = "#14b8a6"
    accent_color = "#14b8a6"
    accent_hover = "#0d9488"
    btn_sec_bg = "#1e293b"
    btn_sec_text = "#f8fafc"
    shadow_val = "0 4px 12px rgba(0, 0, 0, 0.4)"
else:
    bg_app = "#f1f5f9"
    bg_sidebar = "#ffffff"
    bg_card = "#ffffff"
    bg_input = "#f8fafc"
    bg_disabled = "#e2e8f0"
    text_primary = "#0f172a"
    text_secondary = "#334155"
    text_muted = "#64748b"
    border_color = "#cbd5e1"
    border_focus = "#0f766e"
    accent_color = "#0f766e"
    accent_hover = "#0d9488"
    btn_sec_bg = "#f8fafc"
    btn_sec_text = "#0f172a"
    shadow_val = "0 1px 3px rgba(15, 23, 42, 0.06)"

# Production-Grade Explicit Theme Styling
st.markdown(f"""
<style>
    :root {{
        --bg-app: {bg_app};
        --bg-sidebar: {bg_sidebar};
        --bg-card: {bg_card};
        --bg-input: {bg_input};
        --bg-disabled: {bg_disabled};
        --text-primary: {text_primary};
        --text-secondary: {text_secondary};
        --text-muted: {text_muted};
        --border-color: {border_color};
        --border-focus: {border_focus};
        --accent-color: {accent_color};
        --accent-hover: {accent_hover};
        --btn-sec-bg: {btn_sec_bg};
        --btn-sec-text: {btn_sec_text};
        --shadow-card: {shadow_val};
    }}

    /* App Background & Base Typography */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
        background-color: var(--bg-app) !important;
        color: var(--text-primary) !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }}

    .block-container {{
        padding-top: 1.5rem !important;
        padding-bottom: 3rem !important;
        max-width: 1380px;
    }}

    /* Force Universal Text Contrast Across All Markdown, Labels, Tables & Captions */
    h1, h2, h3, h4, h5, h6, p, span, div, label, li, td, th {{
        color: var(--text-primary);
    }}
    .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {{
        color: var(--text-primary) !important;
    }}
    .stCaption, [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {{
        color: var(--text-secondary) !important;
        opacity: 1 !important;
    }}

    /* Top Bar Header */
    .app-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 1px solid var(--border-color);
        padding-bottom: 0.85rem;
        margin-bottom: 1.25rem;
    }}
    .app-title {{
        font-size: 1.6rem;
        font-weight: 700;
        color: var(--text-primary) !important;
        letter-spacing: -0.02em;
        margin: 0;
    }}
    .app-subtitle {{
        font-size: 0.875rem;
        color: var(--text-secondary) !important;
        font-weight: 500;
    }}

    /* Section Headers inside Cards */
    .section-label {{
        font-size: 0.76rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        color: var(--accent-color) !important;
        margin-bottom: 0.85rem;
        display: flex;
        align-items: center;
        gap: 6px;
    }}

    /* Bordered Card Containers */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: var(--bg-card) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 10px !important;
        padding: 1.2rem !important;
        box-shadow: var(--shadow-card);
        margin-bottom: 0.9rem;
    }}

    /* Input Labels */
    [data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] p,
    .stTextInput label, .stNumberInput label, .stDateInput label, .stSelectbox label, .stFileUploader label {{
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        color: var(--text-primary) !important;
        opacity: 1 !important;
    }}

    /* All Input Boxes & Selectboxes */
    .stTextInput input, .stNumberInput input, .stDateInput input {{
        background-color: var(--bg-input) !important;
        color: var(--text-primary) !important;
        -webkit-text-fill-color: var(--text-primary) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 6px !important;
        font-size: 0.92rem !important;
        caret-color: var(--accent-color) !important;
    }}
    .stTextInput input::placeholder, .stNumberInput input::placeholder {{
        color: var(--text-muted) !important;
        -webkit-text-fill-color: var(--text-muted) !important;
        opacity: 1 !important;
    }}
    .stTextInput input:focus, .stNumberInput input:focus, .stDateInput input:focus {{
        border-color: var(--border-focus) !important;
        box-shadow: 0 0 0 2px rgba(20, 184, 166, 0.25) !important;
    }}

    /* Number Input Step Buttons (+/-) */
    .stNumberInput button {{
        background-color: var(--bg-input) !important;
        color: var(--text-primary) !important;
        border-color: var(--border-color) !important;
    }}
    .stNumberInput button svg {{
        fill: var(--text-primary) !important;
    }}

    /* Selectbox & Dropdown Menus */
    div[data-baseweb="select"] > div {{
        background-color: var(--bg-input) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 6px !important;
    }}
    div[data-baseweb="select"] span, div[data-baseweb="select"] div {{
        color: var(--text-primary) !important;
    }}
    div[data-baseweb="select"] svg {{
        fill: var(--text-primary) !important;
    }}
    div[data-baseweb="popover"], ul[role="listbox"], li[role="option"] {{
        background-color: var(--bg-card) !important;
        color: var(--text-primary) !important;
    }}
    li[role="option"]:hover, li[role="option"][aria-selected="true"] {{
        background-color: var(--bg-disabled) !important;
        color: var(--accent-color) !important;
    }}

    /* Disabled / Read-Only Computed Inputs */
    .stTextInput input[disabled], .stNumberInput input[disabled],
    div[data-baseweb="input"]:has(input:disabled) {{
        background-color: var(--bg-disabled) !important;
        color: var(--text-primary) !important;
        -webkit-text-fill-color: var(--text-primary) !important;
        font-weight: 700 !important;
        border: 1px solid var(--border-color) !important;
        opacity: 1 !important;
    }}

    /* File Uploader Dropzone */
    [data-testid="stFileUploaderDropzone"] {{
        background-color: var(--bg-input) !important;
        border: 1px dashed var(--border-color) !important;
        color: var(--text-primary) !important;
    }}
    [data-testid="stFileUploaderDropzone"] div,
    [data-testid="stFileUploaderDropzone"] span,
    [data-testid="stFileUploaderDropzone"] small {{
        color: var(--text-secondary) !important;
    }}
    [data-testid="stFileUploaderDropzone"] button {{
        background-color: var(--bg-card) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-color) !important;
    }}

    /* Metric Containers */
    div[data-testid="stMetric"] {{
        background-color: var(--bg-card) !important;
        border: 1px solid var(--border-color) !important;
        border-left: 4px solid var(--accent-color) !important;
        border-radius: 8px;
        padding: 0.9rem 1.1rem;
        box-shadow: var(--shadow-card);
    }}
    div[data-testid="stMetricLabel"] p, div[data-testid="stMetricLabel"] {{
        font-size: 0.78rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        color: var(--text-secondary) !important;
    }}
    div[data-testid="stMetricValue"] div, div[data-testid="stMetricValue"] {{
        font-size: 1.35rem !important;
        font-weight: 700 !important;
        color: var(--text-primary) !important;
    }}

    /* Buttons */
    .stButton > button, .stDownloadButton > button {{
        border-radius: 6px !important;
        font-weight: 600 !important;
        font-size: 0.875rem !important;
        padding: 0.48rem 1rem !important;
        transition: all 0.15s ease !important;
        background-color: var(--btn-sec-bg) !important;
        border: 1px solid var(--border-color) !important;
        color: var(--btn-sec-text) !important;
    }}
    .stButton > button p, .stDownloadButton > button p,
    .stButton > button span, .stDownloadButton > button span {{
        color: inherit !important;
    }}
    .stButton > button:hover, .stDownloadButton > button:hover {{
        border-color: var(--accent-color) !important;
        color: var(--accent-color) !important;
    }}
    .stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {{
        background-color: var(--accent-color) !important;
        border-color: var(--accent-color) !important;
        color: #ffffff !important;
    }}
    .stButton > button[kind="primary"] p, .stDownloadButton > button[kind="primary"] p,
    .stButton > button[kind="primary"] span, .stDownloadButton > button[kind="primary"] span {{
        color: #ffffff !important;
    }}
    .stButton > button[kind="primary"]:hover, .stDownloadButton > button[kind="primary"]:hover {{
        background-color: var(--accent-hover) !important;
        border-color: var(--accent-hover) !important;
        color: #ffffff !important;
    }}

    /* Tabs */
    div[data-baseweb="tab-list"] {{
        border-bottom: 1px solid var(--border-color) !important;
        gap: 8px;
    }}
    button[data-baseweb="tab"] {{
        font-size: 0.92rem !important;
        font-weight: 600 !important;
        color: var(--text-secondary) !important;
        background-color: transparent !important;
        padding: 0.65rem 1.2rem !important;
    }}
    button[data-baseweb="tab"] p {{
        color: var(--text-secondary) !important;
        font-weight: 600 !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: var(--accent-color) !important;
        border-bottom: 2px solid var(--accent-color) !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] p {{
        color: var(--accent-color) !important;
    }}

    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background-color: var(--bg-sidebar) !important;
        border-right: 1px solid var(--border-color) !important;
    }}
    section[data-testid="stSidebar"] * {{
        color: var(--text-primary);
    }}

    .status-badge {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 12px;
        border-radius: 6px;
        font-size: 0.78rem;
        font-weight: 600;
        background-color: var(--bg-input);
        border: 1px solid var(--border-color);
        color: var(--text-primary) !important;
        margin-top: 6px;
        width: 100%;
    }}

    /* Expanders & Tables */
    div[data-testid="stExpander"] {{
        border: 1px solid var(--border-color) !important;
        border-radius: 8px !important;
        background-color: var(--bg-input) !important;
    }}
    div[data-testid="stExpander"] summary, div[data-testid="stExpander"] summary p {{
        color: var(--text-primary) !important;
        font-weight: 600 !important;
    }}
    div[data-testid="stTable"] table, .stMarkdown table {{
        width: 100%;
        border-collapse: collapse;
        background-color: var(--bg-card) !important;
        color: var(--text-primary) !important;
    }}
    div[data-testid="stTable"] th, .stMarkdown th {{
        background-color: var(--bg-input) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-color) !important;
        padding: 8px 12px !important;
        font-weight: 600 !important;
    }}
    div[data-testid="stTable"] td, .stMarkdown td {{
        background-color: var(--bg-card) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-color) !important;
        padding: 8px 12px !important;
    }}

    /* Alerts / Info / Success Banners */
    div[data-testid="stAlert"] {{
        background-color: var(--bg-input) !important;
        border: 1px solid var(--border-color) !important;
        color: var(--text-primary) !important;
    }}
    div[data-testid="stAlert"] p {{
        color: var(--text-primary) !important;
    }}

    hr {{
        border-color: var(--border-color) !important;
    }}
</style>
""", unsafe_allow_html=True)


def _parse_date(val, default_date: date) -> date:
    if isinstance(val, date):
        return val
    if isinstance(val, str) and val.strip():
        try:
            return date.fromisoformat(val.strip()[:10])
        except Exception:
            pass
    return default_date


# Initialize Session State
if "form_version" not in st.session_state:
    st.session_state.form_version = 0

if "active_report_id" not in st.session_state:
    st.session_state.active_report_id = None

if "conditions_list" not in st.session_state:
    st.session_state.conditions_list = [
        {"condition": "Token Advance", "rupees": 500000.0},
        {"condition": "Banakhat (Agreement)", "rupees": 1500000.0},
        {"condition": "Title Clearance Certificate", "rupees": 1000000.0},
        {"condition": "Dastavej (Final Registry)", "rupees": 2000000.0},
    ]

if "area_val" not in st.session_state:
    st.session_state.area_val = 3200.0

if "rate_bigha" not in st.session_state:
    st.session_state.rate_bigha = 2500000.0

if "rate_sqyd" not in st.session_state:
    st.session_state.rate_sqyd = 12000.0

if "bigha_val" not in st.session_state:
    st.session_state.bigha_val = round(3200.0 / 1618.74, 4)

if "sqmt_val" not in st.session_state:
    st.session_state.sqmt_val = round(3200.0 * 1618.74, 4)

if "sqyd_val" not in st.session_state:
    st.session_state.sqyd_val = round(3200.0 * 1936.0, 4)

if "total_payment" not in st.session_state:
    st.session_state.total_payment = round(st.session_state.bigha_val * st.session_state.rate_bigha, 2)

if "existing_payment_received" not in st.session_state:
    st.session_state.existing_payment_received = 2000000.0

if "new_payment_received" not in st.session_state:
    st.session_state.new_payment_received = 0.0

if "payment_received" not in st.session_state:
    st.session_state.payment_received = 2000000.0

if "payment_remaining" not in st.session_state:
    st.session_state.payment_remaining = round(st.session_state.total_payment - 2000000.0, 2)

if "last_payment_date_val" not in st.session_state:
    st.session_state.last_payment_date_val = date(2026, 3, 1)

if "payment_history" not in st.session_state:
    st.session_state.payment_history = [
        {"date": "2026-03-01", "amount": 2000000.0}
    ]


def calculate_auto_totals(area: float, rate_bigha: float, rate_sqyd: float):
    """Calculates bigha, sq.mt, sq.yd and total agreed payment based on formulas."""
    bigha = round(area / 1618.74, 4) if area > 0 else 0.0
    sq_mt = round(area * 1618.74, 4) if area > 0 else 0.0
    sq_yd = round(area * 1936.0, 4) if area > 0 else 0.0
    if rate_bigha > 0:
        total_pay = round(bigha * rate_bigha, 2)
    elif rate_sqyd > 0:
        total_pay = round(sq_yd * rate_sqyd, 2)
    else:
        total_pay = 0.0
    return bigha, sq_mt, sq_yd, total_pay


def on_area_change():
    """Auto-computes Bigha, Sq.mt, Sq.yd, and Total Agreed Payment when Area changes using specified formulas."""
    form_ver = st.session_state.get("form_version", 0)
    curr_area = float(st.session_state.get(f"input_area_{form_ver}") or 0.0)
    rate_b = float(st.session_state.get(f"rate_bigha_{form_ver}") or 0.0)
    rate_s = float(st.session_state.get(f"rate_sqyd_{form_ver}") or 0.0)

    bigha, sqmt, sqyd, tot_pay = calculate_auto_totals(curr_area, rate_b, rate_s)
    st.session_state.bigha_val = bigha
    st.session_state.sqmt_val = sqmt
    st.session_state.sqyd_val = sqyd
    st.session_state.input_area = curr_area
    st.session_state.total_payment = tot_pay
    exist = float(st.session_state.get("existing_payment_received") or 0.0)
    new_rec = float(st.session_state.get(f"new_payment_{form_ver}") or 0.0)
    cum_rec = round(exist + new_rec, 2)
    st.session_state.payment_remaining = round(tot_pay - cum_rec, 2)


def on_rate_change():
    """Auto-computes Total Agreed Payment when Valuation per Bigha or Sq.yd changes."""
    form_ver = st.session_state.get("form_version", 0)
    curr_area = float(st.session_state.get(f"input_area_{form_ver}") or 0.0)
    rate_b = float(st.session_state.get(f"rate_bigha_{form_ver}") or 0.0)
    rate_s = float(st.session_state.get(f"rate_sqyd_{form_ver}") or 0.0)

    bigha, sqmt, sqyd, tot_pay = calculate_auto_totals(curr_area, rate_b, rate_s)
    st.session_state.rate_bigha = rate_b
    st.session_state.rate_sqyd = rate_s
    st.session_state.total_payment = tot_pay
    exist = float(st.session_state.get("existing_payment_received") or 0.0)
    new_rec = float(st.session_state.get(f"new_payment_{form_ver}") or 0.0)
    cum_rec = round(exist + new_rec, 2)
    st.session_state.payment_remaining = round(tot_pay - cum_rec, 2)


def on_payment_change():
    """Auto-computes Total Payment Received and Payment Remaining when New Payment changes."""
    form_ver = st.session_state.get("form_version", 0)
    tot = float(st.session_state.get(f"total_payment_{form_ver}") or st.session_state.get("total_payment") or 0.0)
    exist = float(st.session_state.get("existing_payment_received") or 0.0)
    new_rec = float(st.session_state.get(f"new_payment_{form_ver}") or 0.0)
    cum_rec = round(exist + new_rec, 2)
    rem = round(tot - cum_rec, 2)
    st.session_state.new_payment_received = new_rec
    st.session_state.payment_received = cum_rec
    st.session_state.payment_remaining = rem


db_health = check_db_status()

# Sidebar
with st.sidebar:
    st.markdown("### LandCal Workspace")

    # Theme Mode Switcher
    theme_choice = st.radio(
        "Appearance",
        options=["Dark", "Light"],
        index=0 if st.session_state.ui_theme == "Dark" else 1,
        horizontal=True,
    )
    if theme_choice != st.session_state.ui_theme:
        st.session_state.ui_theme = theme_choice
        st.rerun()

    st.markdown("---")
    st.caption("Quick Actions")

    if st.button("Load Sample Data", use_container_width=True):
        st.session_state.active_report_id = None
        st.session_state.district = "Ahmedabad"
        st.session_state.taluka = "Sanand"
        st.session_state.village = "Shela"
        st.session_state.old_survey_no = "104/A"
        st.session_state.new_survey_no = "112"
        st.session_state.input_area = 3200.0
        sample_bigha = round(3200.0 / 1618.74, 4)
        sample_sqmt = round(3200.0 * 1618.74, 4)
        sample_sqyd = round(3200.0 * 1936.0, 4)
        st.session_state.bigha_val = sample_bigha
        st.session_state.sqmt_val = sample_sqmt
        st.session_state.sqyd_val = sample_sqyd
        st.session_state.rate_bigha = 2500000.0
        st.session_state.rate_sqyd = 12000.0
        st.session_state.buyer_name = "Ramesh Patel"
        st.session_state.seller_name = "Kishore Shah"
        st.session_state.broker = "Mahesh Desai"
        sample_tot_pay = round(sample_bigha * 2500000.0, 2)
        st.session_state.total_payment = sample_tot_pay
        st.session_state.existing_payment_received = 2000000.0
        st.session_state.new_payment_received = 0.0
        st.session_state.payment_received = 2000000.0
        st.session_state.payment_remaining = round(sample_tot_pay - 2000000.0, 2)
        st.session_state.buy_date_val = date(2026, 3, 1)
        st.session_state.last_payment_date_val = date(2026, 3, 1)
        st.session_state.payment_history = [
            {"date": "2026-03-01", "amount": 2000000.0}
        ]
        st.session_state.sell_date_val = date(2026, 7, 15)
        st.session_state.condition_main = "Title Clearance and Boundary Marking"
        st.session_state.conditions_list = [
            {"condition": "Token Advance", "rupees": 500000.0},
            {"condition": "Banakhat (Agreement)", "rupees": 1500000.0},
            {"condition": "Title Clearance Certificate", "rupees": 1000000.0},
            {"condition": "Dastavej (Final Registry)", "rupees": 2000000.0},
        ]
        st.session_state.form_version += 1
        st.rerun()

    if st.button("Reset Form", use_container_width=True):
        st.session_state.active_report_id = None
        st.session_state.district = ""
        st.session_state.taluka = ""
        st.session_state.village = ""
        st.session_state.old_survey_no = ""
        st.session_state.new_survey_no = ""
        st.session_state.input_area = 0.0
        st.session_state.bigha_val = 0.0
        st.session_state.sqmt_val = 0.0
        st.session_state.sqyd_val = 0.0
        st.session_state.rate_bigha = 0.0
        st.session_state.rate_sqyd = 0.0
        st.session_state.buyer_name = ""
        st.session_state.seller_name = ""
        st.session_state.broker = ""
        st.session_state.total_payment = 0.0
        st.session_state.existing_payment_received = 0.0
        st.session_state.new_payment_received = 0.0
        st.session_state.payment_received = 0.0
        st.session_state.payment_remaining = 0.0
        st.session_state.buy_date_val = date(2026, 1, 1)
        st.session_state.last_payment_date_val = date.today()
        st.session_state.payment_history = []
        st.session_state.sell_date_val = date(2026, 12, 1)
        st.session_state.condition_main = ""
        st.session_state.conditions_list = [{"condition": "", "rupees": 0.0}]
        st.session_state.form_version += 1
        st.rerun()

    st.markdown("---")
    st.caption("System Status")
    if db_health["connected"]:
        st.markdown('<div class="status-badge">🟢 Database Online</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-badge">⚪ Offline Mode</div>', unsafe_allow_html=True)


# Top Header
st.markdown("""
<div class="app-header">
    <h1 class="app-title">LandCal</h1>
    <span class="app-subtitle">Land Valuation & Survey Registry</span>
</div>
""", unsafe_allow_html=True)

tab_workflow, tab_saved_reports = st.tabs([
    "Calculator & Deal Entry",
    "Saved Records"
])


# =============================================================================
# TAB 1: Calculator & Deal Entry
# =============================================================================
with tab_workflow:
    form_ver = st.session_state.get("form_version", 0)

    # Record Selector Bar
    with st.container(border=True):
        saved_reports_all = get_saved_reports() if db_health["connected"] else []

        option_box_choices = {"New Calculation Record": None}
        for r in saved_reports_all:
            up_ts = r.get("updated_at") or r.get("created_at")
            ts_str = up_ts.strftime('%Y-%m-%d %H:%M') if hasattr(up_ts, 'strftime') else str(up_ts)[:16]
            label = f"#{r['id']} • Survey {r['new_survey_no'] or 'N/A'} ({r['village'] or 'N/A'}) — ₹{r['total_payment']:,.0f} [{ts_str}]"
            option_box_choices[label] = r["id"]

        current_active_id = st.session_state.get("active_report_id", None)
        current_index = 0
        if current_active_id is not None:
            for idx, (lbl, rid) in enumerate(option_box_choices.items()):
                if rid == current_active_id:
                    current_index = idx
                    break

        col_opt, col_clr = st.columns([6, 1])
        with col_opt:
            selected_option = st.selectbox(
                "Active Record",
                options=list(option_box_choices.keys()),
                index=current_index,
                key=f"workflow_saved_report_selector_{form_ver}",
            )
        with col_clr:
            st.write("")
            if st.button("Refresh", key=f"btn_refresh_options_{form_ver}", use_container_width=True):
                st.rerun()

        new_selected_id = option_box_choices.get(selected_option)

        if new_selected_id != current_active_id:
            if new_selected_id is not None:
                rep = next((r for r in saved_reports_all if r["id"] == new_selected_id), None)
                if rep:
                    st.session_state.active_report_id = rep["id"]
                    st.session_state.district = rep.get("district", "")
                    st.session_state.taluka = rep.get("taluka", "")
                    st.session_state.village = rep.get("village", "")
                    st.session_state.old_survey_no = rep.get("old_survey_no", "")
                    st.session_state.new_survey_no = rep.get("new_survey_no", "")
                    st.session_state.input_area = float(rep.get("area", 0.0) or 0.0)
                    st.session_state.bigha_val = float(rep.get("bigha", 0.0) or 0.0)
                    st.session_state.sqmt_val = float(rep.get("sq_mt", 0.0) or 0.0)
                    st.session_state.sqyd_val = float(rep.get("sq_yd", 0.0) or 0.0)
                    st.session_state.rate_bigha = float(rep.get("rupees_per_bigha", 0.0) or 0.0)
                    st.session_state.rate_sqyd = float(rep.get("rupees_per_sq_yd", 0.0) or 0.0)
                    st.session_state.buyer_name = rep.get("buyer_name", "")
                    tot_val = float(rep.get("total_payment", 0.0) or 0.0)
                    rec_val = float(rep.get("payment_received", 0.0) or 0.0)
                    rem_val = round(tot_val - rec_val, 2)
                    st.session_state.total_payment = tot_val
                    st.session_state.existing_payment_received = rec_val
                    st.session_state.new_payment_received = 0.0
                    st.session_state.payment_received = rec_val
                    st.session_state.payment_remaining = rem_val
                    st.session_state.last_payment_date_val = _parse_date(rep.get("last_payment_date"), date.today())
                    st.session_state.payment_history = rep.get("payment_history") or (
                        [{"date": str(rep.get("last_payment_date") or date.today()), "amount": rec_val}] if rec_val > 0 else []
                    )
                    st.session_state.condition_main = rep.get("condition", "")
                    st.session_state.buy_date_val = _parse_date(rep.get("buy_date"), date(2026, 3, 1))
                    st.session_state.conditions_list = rep.get("conditions_list") or [{"condition": "", "rupees": 0.0}]
                    st.session_state.active_report_photos = rep.get("land_photos") or []
                    st.session_state.form_version += 1
                    st.rerun()
            else:
                st.session_state.active_report_id = None
                st.session_state.form_version += 1
                st.rerun()

        if st.session_state.get("active_report_id"):
            e_col1, e_col2 = st.columns([6, 1])
            with e_col1:
                st.info(f"Editing Record #{st.session_state.active_report_id} (Survey No: {st.session_state.get('new_survey_no') or 'N/A'})")
            with e_col2:
                if st.button("New Record", key=f"btn_switch_new_{form_ver}", use_container_width=True):
                    st.session_state.active_report_id = None
                    st.session_state.form_version += 1
                    st.rerun()

    # Section 1: Location & Survey Details
    with st.container(border=True):
        st.markdown('<div class="section-label">1. Location & Survey Details</div>', unsafe_allow_html=True)
        c1, c2, c3, c4, c5, c6 = st.columns([1.2, 1.2, 1.2, 1, 1, 1.2])
        with c1:
            district_input = st.text_input("District", value=st.session_state.get("district", "Ahmedabad"), key=f"district_{form_ver}")
        with c2:
            taluka_input = st.text_input("Taluka", value=st.session_state.get("taluka", "Sanand"), key=f"taluka_{form_ver}")
        with c3:
            village_input = st.text_input("Village", value=st.session_state.get("village", "Shela"), key=f"village_{form_ver}")
        with c4:
            old_survey_input = st.text_input("Old Survey No", value=st.session_state.get("old_survey_no", "104/A"), key=f"old_survey_{form_ver}")
        with c5:
            new_survey_input = st.text_input("New Survey No", value=st.session_state.get("new_survey_no", "112"), key=f"new_survey_{form_ver}")
        with c6:
            raw_area = st.session_state.get("input_area")
            val_area = float(raw_area) if raw_area is not None and float(raw_area) > 0 else None
            area_input = st.number_input(
                "Area",
                min_value=0.0,
                value=val_area,
                placeholder="0",
                step=10.0,
                key=f"input_area_{form_ver}",
                on_change=on_area_change,
            )
            area_num = float(area_input or 0.0)

        # Live converted preview
        bigha_preview = round(area_num / 1618.74, 4) if area_num > 0 else 0.0
        sqmt_preview = round(area_num * 1618.74, 4) if area_num > 0 else 0.0
        sqyd_preview = round(area_num * 1936.0, 4) if area_num > 0 else 0.0
        st.caption(f"Converted Metrics — **Bigha:** `{bigha_preview:,.4f}` [area / 1618.74]  |  **Sq.mt:** `{sqmt_preview:,.4f}` [area * 1618.74]  |  **Sq.yd:** `{sqyd_preview:,.4f}` [area * 1936]")

    # Section 2: Rates & Parties Involved
    col_rates, col_parties = st.columns([2, 3])
    with col_rates:
        with st.container(border=True):
            st.markdown('<div class="section-label">2. Rate & Valuations</div>', unsafe_allow_html=True)
            r3_c1, r3_c2 = st.columns(2)
            with r3_c1:
                raw_rate_b = st.session_state.get("rate_bigha")
                val_rate_b = float(raw_rate_b) if raw_rate_b is not None and float(raw_rate_b) > 0 else None
                rate_bigha_input = st.number_input(
                    "Valuation per Bigha (₹)",
                    min_value=0.0,
                    value=val_rate_b,
                    placeholder="0",
                    step=50000.0,
                    format="%.2f",
                    key=f"rate_bigha_{form_ver}",
                    on_change=on_rate_change,
                    help="Manually enter the valuation per Bigha in ₹."
                )
            with r3_c2:
                raw_rate_s = st.session_state.get("rate_sqyd")
                val_rate_s = float(raw_rate_s) if raw_rate_s is not None and float(raw_rate_s) > 0 else None
                rate_sqyd_input = st.number_input(
                    "Valuation per Sq.yd (₹)",
                    min_value=0.0,
                    value=val_rate_s,
                    placeholder="0",
                    step=500.0,
                    format="%.2f",
                    key=f"rate_sqyd_{form_ver}",
                    on_change=on_rate_change,
                    help="Manually enter the valuation per Sq.yd in ₹."
                )

    with col_parties:
        with st.container(border=True):
            st.markdown('<div class="section-label">3. Parties Involved</div>', unsafe_allow_html=True)
            r4_c1, r4_c2, r4_c3 = st.columns(3)
            with r4_c1:
                buyer_name_input = st.text_input("Buyer Name", value=st.session_state.get("buyer_name", "Ramesh Patel"), key=f"buyer_name_{form_ver}")
            with r4_c2:
                seller_name_input = st.text_input("Seller Name", value=st.session_state.get("seller_name", "Kishore Shah"), key=f"seller_name_{form_ver}")
            with r4_c3:
                broker_input = st.text_input("Broker Name", value=st.session_state.get("broker", "Mahesh Desai"), key=f"broker_{form_ver}")

    # Section 4: Payment & Timeline
    with st.container(border=True):
        st.markdown('<div class="section-label">4. Payment Ledger & Timeline</div>', unsafe_allow_html=True)

        # Formula for Total Agreed Payment: bigha * valuation per bigha or sq.yd * valuation per sq.yd
        area_num = float(area_input or 0.0)
        rate_b_num = float(rate_bigha_input or 0.0)
        rate_s_num = float(rate_sqyd_input or 0.0)

        calc_bigha = round(area_num / 1618.74, 4) if area_num > 0 else 0.0
        calc_sqyd = round(area_num * 1936.0, 4) if area_num > 0 else 0.0
        if rate_b_num > 0:
            curr_total = round(calc_bigha * rate_b_num, 2)
        elif rate_s_num > 0:
            curr_total = round(calc_sqyd * rate_s_num, 2)
        else:
            curr_total = float(st.session_state.get("total_payment", 0.0))

        curr_exist = float(st.session_state.get("existing_payment_received", 0.0))
        raw_new = st.session_state.get(f"new_payment_{form_ver}", st.session_state.get("new_payment_received", 0.0))
        curr_new = float(raw_new or 0.0)
        curr_cum_received = round(curr_exist + curr_new, 2)
        curr_remaining = round(curr_total - curr_cum_received, 2)
        st.session_state.total_payment = curr_total
        st.session_state.new_payment_received = curr_new
        st.session_state.payment_received = curr_cum_received
        st.session_state.payment_remaining = curr_remaining

        p1, p2, p3, p4, p5 = st.columns(5)
        with p1:
            total_payment_input = st.number_input(
                "Total Agreed Payment (₹) [Auto-Calculated]",
                value=curr_total,
                format="%.2f",
                disabled=True,
                help="Automatically calculated: (Bigha × Valuation/Bigha) or (Sq.yd × Valuation/Sq.yd)"
            )
        with p2:
            val_new_p = curr_new if curr_new > 0 else None
            new_payment_input = st.number_input(
                "New Payment Received (+₹)",
                min_value=0.0,
                value=val_new_p,
                placeholder="0",
                step=50000.0,
                format="%.2f",
                key=f"new_payment_{form_ver}",
                on_change=on_payment_change,
            )
        with p3:
            default_last_d = _parse_date(st.session_state.get("last_payment_date_val"), date.today())
            last_payment_date_input = st.date_input(
                "Payment Date",
                value=default_last_d,
                key=f"last_payment_date_{form_ver}",
            )
        with p4:
            st.number_input(
                "Total Received (₹)",
                value=float(curr_cum_received),
                format="%.2f",
                disabled=True,
            )
        with p5:
            st.number_input(
                "Balance Remaining (₹)",
                value=float(curr_remaining),
                format="%.2f",
                disabled=True,
            )

        t1, t2, t3 = st.columns([1, 1, 2])
        with t1:
            default_buy_d = _parse_date(st.session_state.get("buy_date_val"), date(2026, 3, 1))
            buy_date_input = st.date_input("Buy Date", value=default_buy_d, key=f"buy_date_{form_ver}")
        with t2:
            default_sell_d = _parse_date(st.session_state.get("sell_date_val"), date(2026, 7, 15))
            sell_date_input = st.date_input("Sell Date", value=default_sell_d, key=f"sell_date_{form_ver}")
        with t3:
            condition_input = st.text_input("Primary Deal Condition", value=st.session_state.get("condition_main", "Title Clearance & Boundary Marking"), key=f"condition_{form_ver}")

        pay_history_list = list(st.session_state.get("payment_history", []) or [])
        if pay_history_list or curr_new > 0:
            with st.expander(f"Payment Installment History ({len(pay_history_list) + (1 if curr_new > 0 else 0)})", expanded=False):
                hist_display = []
                for i, h in enumerate(pay_history_list, 1):
                    hist_display.append({"#": i, "Date": str(h.get("date", "N/A")), "Amount (₹)": f"₹{float(h.get('amount', 0.0)):,.2f}"})
                if curr_new > 0:
                    hist_display.append({"#": len(pay_history_list) + 1, "Date": f"{last_payment_date_input} (Pending Save)", "Amount (₹)": f"+₹{curr_new:,.2f}"})
                st.table(hist_display)

        payment_received_input = curr_cum_received
        payment_remaining_input = curr_remaining

    # Section 5 & 6: Milestones & Photos side-by-side
    col_milestones, col_photos = st.columns([3, 2])

    with col_milestones:
        with st.container(border=True):
            st.markdown('<div class="section-label">5. Payment Milestones & Conditions</div>', unsafe_allow_html=True)
            updated_conditions = []
            for idx, item in enumerate(st.session_state.conditions_list):
                col_cond, col_rs, col_del = st.columns([5, 3, 1])
                with col_cond:
                    c_text = st.text_input(
                        f"Milestone #{idx+1}",
                        value=item["condition"],
                        key=f"cond_text_{idx}_{form_ver}",
                        label_visibility="collapsed" if idx > 0 else "visible",
                        placeholder="Condition description"
                    )
                with col_rs:
                    raw_cond_rs = item.get("rupees")
                    val_cond_rs = float(raw_cond_rs) if raw_cond_rs is not None and float(raw_cond_rs) > 0 else None
                    c_rs = st.number_input(
                        f"Amount (₹) #{idx+1}",
                        min_value=0.0,
                        value=val_cond_rs,
                        placeholder="0",
                        step=50000.0,
                        format="%.2f",
                        key=f"cond_rs_{idx}_{form_ver}",
                        label_visibility="collapsed" if idx > 0 else "visible",
                    )
                with col_del:
                    if idx == 0:
                        st.write("")
                    if st.button("✕", key=f"del_cond_{idx}_{form_ver}"):
                        st.session_state.conditions_list.pop(idx)
                        st.session_state.form_version += 1
                        st.rerun()

                updated_conditions.append({"condition": c_text, "rupees": float(c_rs or 0.0)})

            st.session_state.conditions_list = updated_conditions

            if st.button("+ Add Milestone", key=f"btn_add_cond_{form_ver}"):
                st.session_state.conditions_list.append({"condition": "", "rupees": 0.0})
                st.session_state.form_version += 1
                st.rerun()

    with col_photos:
        with st.container(border=True):
            st.markdown('<div class="section-label">6. Survey Photos</div>', unsafe_allow_html=True)
            active_survey_for_photos = (new_survey_input or old_survey_input or "").strip()
            clean_survey = sanitize_survey_no(active_survey_for_photos) if active_survey_for_photos else None

            if not clean_survey or clean_survey == "unspecified_survey":
                st.caption("Enter a Survey Number to enable photo uploads.")
            else:
                uploaded_photos = st.file_uploader(
                    f"Upload Photos (Survey {active_survey_for_photos})",
                    type=["jpg", "jpeg", "png", "webp", "bmp"],
                    accept_multiple_files=True,
                    key=f"app_photos_{clean_survey}_{form_ver}",
                )

                if uploaded_photos:
                    saved_keys = st.session_state.setdefault("saved_photo_keys", set())
                    newly_saved_count = 0
                    for f in uploaded_photos:
                        f_key = f"{clean_survey}_{f.name}_{f.size}"
                        if f_key not in saved_keys and not photo_already_saved(active_survey_for_photos, f.name, f.size):
                            save_survey_photo(active_survey_for_photos, f.getvalue(), f.name)
                            saved_keys.add(f_key)
                            newly_saved_count += 1
                    if newly_saved_count > 0:
                        st.toast(f"Saved {newly_saved_count} photo(s) to Survey {active_survey_for_photos}")

                current_survey_photos = get_all_survey_photos(new_survey_input, old_survey_input)
                active_rep_p = st.session_state.get("active_report_photos", []) or []
                seen_fp = {p["file_path"] for p in current_survey_photos if p.get("file_path")}
                for p in active_rep_p:
                    p_disp = get_photo_display_url(p)
                    if p.get("file_path") and p["file_path"] not in seen_fp and p_disp:
                        current_survey_photos.append(p)
                        seen_fp.add(p["file_path"])

                if current_survey_photos:
                    thumb_cols = st.columns(2)
                    for idx, photo in enumerate(current_survey_photos):
                        with thumb_cols[idx % 2]:
                            p_path = photo.get("file_path", "")
                            disp_target = get_photo_display_url(photo)
                            if disp_target:
                                st.image(disp_target, use_container_width=True)
                                photo_id_label = photo.get('filename') or f"photo_{idx}"
                                if st.button("Remove", key=f"del_app_{photo_id_label}_{idx}_{form_ver}", use_container_width=True):
                                    delete_survey_photo(p_path, survey_no=photo.get("survey_no") or active_survey_for_photos)
                                    # Also remove from active report session photos
                                    st.session_state.active_report_photos = [
                                        rp for rp in st.session_state.get("active_report_photos", [])
                                        if rp.get("file_path") != p_path
                                    ]
                                    st.rerun()

    # Action Bar
    is_editing = st.session_state.get("active_report_id") is not None
    target_id_for_execution = None
    trigger_execution = False

    if is_editing:
        active_id = st.session_state.active_report_id
        btn_u_col, btn_n_col, _ = st.columns([3, 3, 4])
        with btn_u_col:
            if st.button(f"Update Record #{active_id}", type="primary", use_container_width=True):
                target_id_for_execution = active_id
                trigger_execution = True
        with btn_n_col:
            if st.button("Save as New Record", type="secondary", use_container_width=True):
                target_id_for_execution = None
                trigger_execution = True
    else:
        btn_col1, _ = st.columns([3, 7])
        with btn_col1:
            if st.button("Calculate & Save Report", type="primary", use_container_width=True):
                target_id_for_execution = None
                trigger_execution = True

    if trigger_execution:
        with st.spinner("Processing calculation..."):
            if active_survey_for_photos and 'uploaded_photos' in locals() and uploaded_photos:
                for f in uploaded_photos:
                    if not photo_already_saved(active_survey_for_photos, f.name, f.size):
                        save_survey_photo(active_survey_for_photos, f.getvalue(), f.name)

            survey_photos_payload = get_all_survey_photos(new_survey_input, old_survey_input)
            active_rep_p = st.session_state.get("active_report_photos", []) or []
            existing_paths = {p["file_path"] for p in survey_photos_payload if p.get("file_path")}
            for p in active_rep_p:
                if p.get("file_path") and p["file_path"] not in existing_paths and get_photo_display_url(p):
                    survey_photos_payload.append(p)
                    existing_paths.add(p["file_path"])
            st.session_state.active_report_photos = survey_photos_payload

            current_history = list(st.session_state.get("payment_history", []) or [])
            if curr_new > 0:
                current_history.append({"date": str(last_payment_date_input), "amount": float(curr_new)})

            workflow_payload = {
                "district": district_input,
                "taluka": taluka_input,
                "village": village_input,
                "old_survey_no": old_survey_input,
                "new_survey_no": new_survey_input,
                "area": float(area_input or 0.0),
                "rupees_per_bigha": float(rate_bigha_input or 0.0),
                "rupees_per_sq_yd": float(rate_sqyd_input or 0.0),
                "buyer_name": buyer_name_input,
                "seller_name": seller_name_input,
                "total_payment": float(total_payment_input or 0.0),
                "payment_received": float(payment_received_input or 0.0),
                "payment_remaining": float(payment_remaining_input or 0.0),
                "buy_date": str(buy_date_input),
                "condition": condition_input,
                "last_payment_date": str(last_payment_date_input),
                "sell_date": str(sell_date_input),
                "conditions_list": updated_conditions,
                "land_photos": survey_photos_payload,
                "payment_history": current_history,
                "target_report_id": target_id_for_execution,
            }

            result = run_land_calculation(workflow_payload)
            st.session_state["latest_result"] = result
            st.session_state.existing_payment_received = float(result.get("payment_received", payment_received_input))
            st.session_state.new_payment_received = 0.0
            st.session_state.payment_received = float(result.get("payment_received", payment_received_input))
            st.session_state.payment_remaining = float(result.get("payment_remaining", payment_remaining_input))
            st.session_state.payment_history = current_history
            st.session_state.last_payment_date_val = last_payment_date_input
            if result.get("saved_report_id"):
                st.session_state.active_report_id = result.get("saved_report_id")

    # Output Section
    if "latest_result" in st.session_state:
        result = st.session_state["latest_result"]
        st.markdown("---")

        saved_id = result.get("saved_report_id")
        if saved_id:
            st.success(f"Record #{saved_id} saved (Survey {result.get('new_survey_no') or 'N/A'}).")

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Total Land (Bigha)", f"{result.get('bigha', 0.0):,.4f}")
        with m2:
            st.metric("Total Payment", f"₹{result.get('total_payment', 0.0):,.2f}")
        with m3:
            st.metric("Total Received", f"₹{result.get('payment_received', 0.0):,.2f}")
        with m4:
            rem = result.get('payment_remaining', 0.0)
            st.metric("Balance Remaining", f"₹{rem:,.2f}")

        with st.container(border=True):
            hdr_c1, hdr_c2 = st.columns([7, 3])
            with hdr_c1:
                st.markdown('<div class="section-label">Generated Valuation Report</div>', unsafe_allow_html=True)
            with hdr_c2:
                st.download_button(
                    label="Download Report (.md)",
                    data=result.get("summary_report", ""),
                    file_name=f"land_deal_{new_survey_input or 'survey'}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )

            st.markdown(result.get("summary_report", ""))

            deal_photos = result.get("land_photos") or []
            if deal_photos:
                st.markdown("---")
                st.markdown('<div class="section-label">Attached Survey Photos</div>', unsafe_allow_html=True)
                photo_cols = st.columns(min(max(len(deal_photos), 1), 4))
                for idx, p in enumerate(deal_photos):
                    disp_src = get_photo_display_url(p)
                    if disp_src:
                        with photo_cols[idx % len(photo_cols)]:
                            st.image(disp_src, caption=p.get("filename", f"Photo #{idx+1}"), use_container_width=True)


# =============================================================================
# TAB 2: Saved Records
# =============================================================================
with tab_saved_reports:
    if not db_health["connected"]:
        st.warning("PostgreSQL database is not connected. Configure `DATABASE_URL` in `.env` to view saved records.")
    else:
        all_reports_for_backup = get_saved_reports(limit=10000)
        csv_backup_data = export_reports_to_csv(all_reports_for_backup) if all_reports_for_backup else ""

        with st.container(border=True):
            col_search, col_ref, col_exp = st.columns([5, 1.5, 2.5])
            with col_search:
                survey_filter = st.text_input(
                    "Filter by New Survey No",
                    value=st.session_state.get("search_survey_query", ""),
                    placeholder="Enter survey number...",
                )
            with col_ref:
                st.write("")
                if st.button("Refresh", key="btn_refresh_tab2", use_container_width=True):
                    st.rerun()
            with col_exp:
                st.write("")
                st.download_button(
                    label=f"Export CSV ({len(all_reports_for_backup)})",
                    data=csv_backup_data,
                    file_name=f"landcal_backup_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    disabled=(len(all_reports_for_backup) == 0),
                    type="primary",
                    use_container_width=True,
                )

        saved_records = get_saved_reports(new_survey_no=survey_filter)

        if not saved_records:
            st.info("No matching records found.")
        else:
            record_options = {}
            for r in saved_records:
                up_ts = r.get("updated_at") or r.get("created_at")
                ts_str = up_ts.strftime('%Y-%m-%d %H:%M') if hasattr(up_ts, 'strftime') else str(up_ts)[:16]
                label = f"#{r['id']} • Survey {r['new_survey_no'] or 'N/A'} (Old: {r['old_survey_no'] or 'N/A'}) | {r['village'] or 'N/A'}, {r['district'] or 'N/A'} | ₹{r['total_payment']:,.2f} [{ts_str}]"
                record_options[label] = r['id']

            selected_label = st.selectbox(
                f"Select Record ({len(saved_records)} found)",
                options=list(record_options.keys()),
                key="selected_report_dropdown"
            )

            selected_id = record_options[selected_label]
            selected_report = next((r for r in saved_records if r["id"] == selected_id), None)

            if selected_report:
                sm1, sm2, sm3, sm4 = st.columns(4)
                with sm1:
                    st.metric("Total Land (Bigha)", f"{selected_report.get('bigha', 0.0):,.4f}")
                with sm2:
                    st.metric("Total Payment", f"₹{selected_report.get('total_payment', 0.0):,.2f}")
                with sm3:
                    st.metric("Total Received", f"₹{selected_report.get('payment_received', 0.0):,.2f}")
                with sm4:
                    s_rem = selected_report.get('payment_remaining', 0.0)
                    st.metric("Balance Remaining", f"₹{s_rem:,.2f}")

                with st.container(border=True):
                    act_col1, act_col2, act_col3, _ = st.columns([2.5, 2.5, 2, 3])
                    with act_col1:
                        if st.button("Load in Calculator", type="primary", use_container_width=True):
                            st.session_state.active_report_id = selected_report["id"]
                            st.session_state.district = selected_report.get("district", "")
                            st.session_state.taluka = selected_report.get("taluka", "")
                            st.session_state.village = selected_report.get("village", "")
                            st.session_state.old_survey_no = selected_report.get("old_survey_no", "")
                            st.session_state.new_survey_no = selected_report.get("new_survey_no", "")
                            st.session_state.input_area = float(selected_report.get("area", 0.0) or 0.0)
                            st.session_state.bigha_val = float(selected_report.get("bigha", 0.0) or 0.0)
                            st.session_state.sqmt_val = float(selected_report.get("sq_mt", 0.0) or 0.0)
                            st.session_state.sqyd_val = float(selected_report.get("sq_yd", 0.0) or 0.0)
                            st.session_state.rate_bigha = float(selected_report.get("rupees_per_bigha", 0.0) or 0.0)
                            st.session_state.rate_sqyd = float(selected_report.get("rupees_per_sq_yd", 0.0) or 0.0)
                            st.session_state.buyer_name = selected_report.get("buyer_name", "")
                            st.session_state.seller_name = selected_report.get("seller_name", "")
                            st.session_state.broker = selected_report.get("broker", "")
                            tot_p = float(selected_report.get("total_payment", 0.0) or 0.0)
                            rec_p = float(selected_report.get("payment_received", 0.0) or 0.0)
                            rem_p = round(tot_p - rec_p, 2)
                            st.session_state.total_payment = tot_p
                            st.session_state.existing_payment_received = rec_p
                            st.session_state.new_payment_received = 0.0
                            st.session_state.payment_received = rec_p
                            st.session_state.payment_remaining = rem_p
                            st.session_state.condition_main = selected_report.get("condition", "")
                            st.session_state.buy_date_val = _parse_date(selected_report.get("buy_date"), date(2026, 3, 1))
                            st.session_state.last_payment_date_val = _parse_date(selected_report.get("last_payment_date"), date.today())
                            st.session_state.payment_history = selected_report.get("payment_history") or (
                                [{"date": str(selected_report.get("last_payment_date") or date.today()), "amount": rec_p}] if rec_p > 0 else []
                            )
                            st.session_state.sell_date_val = _parse_date(selected_report.get("sell_date"), date(2026, 7, 15))

                            conds = selected_report.get("conditions_list") or []
                            if isinstance(conds, list) and len(conds) > 0:
                                st.session_state.conditions_list = conds

                            st.session_state.active_report_photos = selected_report.get("land_photos") or []
                            st.session_state.form_version += 1
                            st.toast(f"Loaded Record #{selected_report['id']} into Calculator")
                            st.rerun()

                    with act_col2:
                        st.download_button(
                            label="Download Markdown",
                            data=selected_report.get("summary_report", ""),
                            file_name=f"report_{selected_report.get('new_survey_no') or 'deal'}_{selected_report['id']}.md",
                            mime="text/markdown",
                            use_container_width=True,
                        )

                    with act_col3:
                        if st.button("Delete Record", type="secondary", use_container_width=True):
                            ok, msg = delete_report_by_id(selected_id)
                            if ok:
                                if st.session_state.get("active_report_id") == selected_id:
                                    st.session_state.active_report_id = None
                                st.rerun()
                            else:
                                st.error(msg)

                    st.markdown("---")
                    st.markdown(selected_report.get("summary_report", "_No report content available._"))

                    saved_photos = selected_report.get("land_photos") or []
                    if saved_photos:
                        st.markdown("---")
                        st.markdown('<div class="section-label">Survey Photos</div>', unsafe_allow_html=True)
                        s_photo_cols = st.columns(min(max(len(saved_photos), 1), 4))
                        for s_idx, sp in enumerate(saved_photos):
                            s_disp = get_photo_display_url(sp)
                            if s_disp:
                                with s_photo_cols[s_idx % len(s_photo_cols)]:
                                    st.image(s_disp, caption=sp.get("filename", f"Photo #{s_idx+1}"), use_container_width=True)
