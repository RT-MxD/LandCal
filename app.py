"""
Streamlit Web Application for Land Calculation LangGraph Workflow
Features:
1. Land Calculation Workflow Dashboard:
   - Saved Report Option Box (Select previous report to review, edit, and update)
   - 6-Row Layout (Location, Survey Metrics, Rates, Parties, Timeline, Conditions)
   - Land Photos Uploader (Survey-Locked)
   - In-place PostgreSQL Update or New Record Save
2. Saved Reports Explorer:
   - Search & Filter by New Survey No
   - Full metrics, Markdown reports, and quick loading into the calculation workflow
"""

import json
import os
from datetime import date, datetime
import streamlit as st

from land_graph import run_land_calculation
from photo_manager import (
    sanitize_survey_no,
    save_survey_photo,
    list_survey_photos,
    delete_survey_photo,
    get_all_survey_photos,
    photo_already_saved,
)
from db import (
    check_db_status,
    get_saved_reports,
    get_report_by_id,
    delete_report_by_id,
    get_masked_db_url,
    export_reports_to_csv,
)

# Page Configuration
st.set_page_config(
    page_title="LandCal — Land Calculation & Reports",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1b4332;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #40916c;
        margin-bottom: 1.2rem;
    }
    .row-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 14px;
        border-left: 4px solid #2d6a4f;
    }
    .row-title {
        font-size: 1.05rem;
        font-weight: 600;
        color: #2d6a4f;
        margin-bottom: 8px;
    }
    .metric-box {
        background: linear-gradient(135deg, #d8f3dc, #b7e4c7);
        border-radius: 8px;
        padding: 15px;
        text-align: center;
        border: 1px solid #74c69d;
    }
    .stButton>button {
        border-radius: 6px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">🌾 LandCal — Land Calculation Workflow & Reports</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Multi-variable land calculation, automated metric conversions, and PostgreSQL report management powered by LangGraph.</div>', unsafe_allow_html=True)


def _parse_date(val, default_date: date) -> date:
    """Safely converts string or date object into a date object."""
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


# Check database health
db_health = check_db_status()

# Sidebar Controls
with st.sidebar:
    st.header("⚙️ Workflow Controls")

    if st.button("📋 Load Sample Gujarat Deal", use_container_width=True):
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

    if st.button("🔄 Clear All Fields / Reset", use_container_width=True):
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


# Top-Level Section Tabs
tab_workflow, tab_saved_reports = st.tabs([
    "🧮 1. Land Calculation Workflow",
    "📋 2. Saved Reports (Search via New Survey No)"
])


# =============================================================================
# SECTION 1: Land Calculation Workflow Dashboard
# =============================================================================
with tab_workflow:
    form_ver = st.session_state.get("form_version", 0)

    # -------------------------------------------------------------------------
    # Saved Report Option Box (Select, Edit & Update)
    # -------------------------------------------------------------------------
    st.markdown('<div class="row-card"><div class="row-title">📂 Saved Report Option Box (Select Previous Report to Edit)</div>', unsafe_allow_html=True)

    saved_reports_all = get_saved_reports() if db_health["connected"] else []

    option_box_choices = {"-- 🆕 New Land Calculation (Default / Blank) --": None}
    for r in saved_reports_all:
        up_ts = r.get("updated_at") or r.get("created_at")
        ts_str = up_ts.strftime('%Y-%m-%d %H:%M') if hasattr(up_ts, 'strftime') else str(up_ts)[:16]
        label = f"Report #{r['id']} — Survey: {r['new_survey_no'] or 'N/A'} (Old: {r['old_survey_no'] or 'N/A'}) | {r['village'] or 'N/A'}, {r['district'] or 'N/A'} | ₹{r['total_payment']:,.2f} | {ts_str}"
        option_box_choices[label] = r["id"]

    # Current index calculation
    current_active_id = st.session_state.get("active_report_id", None)
    current_index = 0
    if current_active_id is not None:
        for idx, (lbl, rid) in enumerate(option_box_choices.items()):
            if rid == current_active_id:
                current_index = idx
                break

    col_opt, col_clr = st.columns([5, 1])
    with col_opt:
        selected_option = st.selectbox(
            "Select previous saved report to review, edit, or update:",
            options=list(option_box_choices.keys()),
            index=current_index,
            key=f"workflow_saved_report_selector_{form_ver}",
            help="Select any previously saved report. All variables will be loaded into the rows below so you can edit and update the report."
        )
    with col_clr:
        st.write("")
        st.write("")
        if st.button("🔄 Refresh", key=f"btn_refresh_options_{form_ver}", use_container_width=True):
            st.rerun()

    new_selected_id = option_box_choices.get(selected_option)

    # If the user changed the dropdown selection, load that report or switch to new
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

    # Active editing mode banner
    if st.session_state.get("active_report_id"):
        e_col1, e_col2 = st.columns([5, 1])
        with e_col1:
            st.info(f"✏️ **Editing Mode Active:** Loaded **Report #{st.session_state.active_report_id}** (Survey No: **`{st.session_state.get('new_survey_no') or 'N/A'}`**). Any changes below can be updated directly to this report.")
        with e_col2:
            st.write("")
            if st.button("✕ Switch to New", key=f"btn_switch_new_{form_ver}", use_container_width=True, help="Stop editing this report and start a new calculation"):
                st.session_state.active_report_id = None
                st.session_state.form_version += 1
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # -------------------------------------------------------------
    # Row 1: District, Taluka, Village
    # -------------------------------------------------------------
    st.markdown('<div class="row-card"><div class="row-title">Row 1: Location Variables</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        district_input = st.text_input("District", value=st.session_state.get("district", "Ahmedabad"), key=f"district_{form_ver}", placeholder="e.g. Ahmedabad")
    with c2:
        taluka_input = st.text_input("Taluka", value=st.session_state.get("taluka", "Sanand"), key=f"taluka_{form_ver}", placeholder="e.g. Sanand")
    with c3:
        village_input = st.text_input("Village", value=st.session_state.get("village", "Shela"), key=f"village_{form_ver}", placeholder="e.g. Shela")
    st.markdown('</div>', unsafe_allow_html=True)

    # -------------------------------------------------------------
    # Row 2: Land Survey & Metrics (Area input by user, Bigha, Sq.mt, Sq.yd auto-calculated)
    # -------------------------------------------------------------
    st.markdown('<div class="row-card"><div class="row-title">Row 2: Land Survey & Metrics</div>', unsafe_allow_html=True)
    r2_c1, r2_c2, r2_c3 = st.columns(3)
    with r2_c1:
        old_survey_input = st.text_input("Old Survey No", value=st.session_state.get("old_survey_no", "104/A"), key=f"old_survey_{form_ver}")
    with r2_c2:
        new_survey_input = st.text_input("New Survey No", value=st.session_state.get("new_survey_no", "112"), key=f"new_survey_{form_ver}")
    with r2_c3:
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
            help="Input land area in base units. Bigha, Sq.mt, and Sq.yd will be calculated automatically during the workflow."
        )
    st.caption("ℹ️ *Bigha [area / 1618.74], Sq.mt [area * 1618.74], and Sq.yd [area * 1936] will be automatically calculated during the workflow.*")
    st.markdown('</div>', unsafe_allow_html=True)

    # -------------------------------------------------------------
    # -------------------------------------------------------------
    # Row 3: Valuation per bigha, Valuation per sq.yd
    # -------------------------------------------------------------
    st.markdown('<div class="row-card"><div class="row-title">Row 3: Rate & Valuations</div>', unsafe_allow_html=True)
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
    st.markdown('</div>', unsafe_allow_html=True)

    # -------------------------------------------------------------
    # Row 4: Buyer name, Seller name, Broker
    # -------------------------------------------------------------
    st.markdown('<div class="row-card"><div class="row-title">Row 4: Parties Involved</div>', unsafe_allow_html=True)
    r4_c1, r4_c2, r4_c3 = st.columns(3)
    with r4_c1:
        buyer_name_input = st.text_input("Buyer Name", value=st.session_state.get("buyer_name", "Ramesh Patel"), key=f"buyer_name_{form_ver}")
    with r4_c2:
        seller_name_input = st.text_input("Seller Name", value=st.session_state.get("seller_name", "Kishore Shah"), key=f"seller_name_{form_ver}")
    with r4_c3:
        broker_input = st.text_input("Broker", value=st.session_state.get("broker", "Mahesh Desai"), key=f"broker_{form_ver}")
    st.markdown('</div>', unsafe_allow_html=True)

    # -------------------------------------------------------------
    # Row 5: Total payment, Payment Received, Payment Remaining, Buy date, Condition, Last payment date, Sell date
    # -------------------------------------------------------------
    st.markdown('<div class="row-card"><div class="row-title">Row 5: Transaction & Timeline Terms</div>', unsafe_allow_html=True)
    
    # 1. Buyer Payment Status (Total Payment, New Payment Received, Last Payment Date, Total Received, Remaining)
    st.markdown("##### 💳 Buyer Payment Status")
    
    # Pre-calculate current values from session state / widget cache
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

    # 3 Inputs: Total Payment (Auto-Calculated), New Payment Received, and Last Payment Date
    r5_p1, r5_p2, r5_p3 = st.columns(3)
    with r5_p1:
        total_payment_input = st.number_input(
            "Total Agreed Payment (₹) [Auto-Calculated]",
            value=curr_total,
            format="%.2f",
            disabled=True,
            help="Automatically calculated: (Bigha × Valuation/Bigha) or (Sq.yd × Valuation/Sq.yd)"
        )
    with r5_p2:
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
            help="Enter any payment received from buyer. It will automatically count with existing payments into Total Payment Received and Payment Remaining."
        )
    with r5_p3:
        default_last_d = _parse_date(st.session_state.get("last_payment_date_val"), date.today())
        last_payment_date_input = st.date_input(
            "Last Payment Date",
            value=default_last_d,
            key=f"last_payment_date_{form_ver}",
            help="Date on which payment was received."
        )

    # Directly calculated output boxes (Read-only / Disabled)
    r5_s1, r5_s2 = st.columns(2)
    with r5_s1:
        st.number_input(
            "Total Payment Received (Done by Buyer) (₹)",
            value=float(curr_cum_received),
            format="%.2f",
            disabled=True,
            help="Directly calculated: Previously Received + New Payment Received"
        )
    with r5_s2:
        st.number_input(
            "Payment Remaining (Buyer Balance) (₹)",
            value=float(curr_remaining),
            format="%.2f",
            disabled=True,
            help="Directly calculated: Total Payment - Total Payment Received"
        )

    # Dynamic calculation status indicator
    stat_icon = "🟢" if curr_remaining <= 0 else "🟠"
    calc_breakdown = f" *(Previously Received: ₹{curr_exist:,.2f} + New: ₹{curr_new:,.2f})*" if curr_exist > 0 and curr_new > 0 else (f" *(Previously Received: ₹{curr_exist:,.2f})*" if curr_exist > 0 else "")
    st.caption(
        f"{stat_icon} **Status:** Total Agreed: **₹{curr_total:,.2f}** | "
        f"**Total Received:** **₹{curr_cum_received:,.2f}**{calc_breakdown} | "
        f"**Payment Remaining:** **₹{curr_remaining:,.2f}** | "
        f"**Last Payment Date:** **{last_payment_date_input}**"
    )

    # Payment Dates & Installments History
    pay_history_list = list(st.session_state.get("payment_history", []) or [])
    if pay_history_list or curr_new > 0:
        with st.expander(f"📜 Payment Dates & History ({len(pay_history_list) + (1 if curr_new > 0 else 0)} payment(s) recorded)", expanded=False):
            hist_display = []
            for i, h in enumerate(pay_history_list, 1):
                hist_display.append({"#": i, "Payment Received Date": str(h.get("date", "N/A")), "Amount (₹)": f"₹{float(h.get('amount', 0.0)):,.2f}"})
            if curr_new > 0:
                hist_display.append({"#": len(pay_history_list) + 1, "Payment Received Date": f"{last_payment_date_input} (New Installment)", "Amount (₹)": f"+₹{curr_new:,.2f}"})
            st.table(hist_display)

    payment_received_input = curr_cum_received
    payment_remaining_input = curr_remaining

    # 2. Timeline & Conditions (Last Payment Date moved to Buyer Payment Status)
    st.markdown("##### 📅 Timeline & Conditions")
    r5_c1, r5_c2, r5_c3 = st.columns(3)
    with r5_c1:
        default_buy_d = _parse_date(st.session_state.get("buy_date_val"), date(2026, 3, 1))
        buy_date_input = st.date_input("Buy Date", value=default_buy_d, key=f"buy_date_{form_ver}")
    with r5_c2:
        condition_input = st.text_input("Condition", value=st.session_state.get("condition_main", "Title Clearance & Boundary Marking"), key=f"condition_{form_ver}")
    with r5_c3:
        default_sell_d = _parse_date(st.session_state.get("sell_date_val"), date(2026, 7, 15))
        sell_date_input = st.date_input("Sell Date", value=default_sell_d, key=f"sell_date_{form_ver}")
    st.markdown('</div>', unsafe_allow_html=True)

    # -------------------------------------------------------------
    # Row 6: Conditions box beside Rupees box
    # -------------------------------------------------------------
    st.markdown('<div class="row-card"><div class="row-title">Row 6: Conditions Beside Rupees</div>', unsafe_allow_html=True)
    updated_conditions = []
    for idx, item in enumerate(st.session_state.conditions_list):
        col_cond, col_rs, col_del = st.columns([6, 4, 1])
        with col_cond:
            c_text = st.text_input(
                f"Condition #{idx+1}",
                value=item["condition"],
                key=f"cond_text_{idx}_{form_ver}",
                placeholder=f"e.g. Milestone {idx+1} / Payment Condition"
            )
        with col_rs:
            raw_cond_rs = item.get("rupees")
            val_cond_rs = float(raw_cond_rs) if raw_cond_rs is not None and float(raw_cond_rs) > 0 else None
            c_rs = st.number_input(
                f"Rupees (₹) #{idx+1}",
                min_value=0.0,
                value=val_cond_rs,
                placeholder="0",
                step=50000.0,
                format="%.2f",
                key=f"cond_rs_{idx}_{form_ver}"
            )
        with col_del:
            st.write("")
            st.write("")
            if st.button("🗑️", key=f"del_cond_{idx}_{form_ver}", help="Remove this condition"):
                st.session_state.conditions_list.pop(idx)
                st.session_state.form_version += 1
                st.rerun()

        updated_conditions.append({"condition": c_text, "rupees": float(c_rs or 0.0)})

    st.session_state.conditions_list = updated_conditions

    col_add, _ = st.columns([2, 8])
    with col_add:
        if st.button("➕ Add Condition Row", key=f"btn_add_cond_{form_ver}", use_container_width=True):
            st.session_state.conditions_list.append({"condition": "", "rupees": 0.0})
            st.session_state.form_version += 1
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # -------------------------------------------------------------
    # Row 7: Land Photos Uploader (Survey-Locked)
    # -------------------------------------------------------------
    st.markdown('<div class="row-card"><div class="row-title">Row 7: Land Photos (Survey-Locked)</div>', unsafe_allow_html=True)
    active_survey_for_photos = (new_survey_input or old_survey_input or "").strip()
    clean_survey = sanitize_survey_no(active_survey_for_photos) if active_survey_for_photos else None

    if not clean_survey or clean_survey == "unspecified_survey":
        st.warning("⚠️ Please provide a **Survey Number** in Row 2 above to upload photos.")
    else:
        st.caption(f"Target Survey: **{active_survey_for_photos}** (Folder: `survey_{clean_survey}/`)")
        uploaded_photos = st.file_uploader(
            f"Select photos for Survey {active_survey_for_photos}",
            type=["jpg", "jpeg", "png", "webp", "bmp"],
            accept_multiple_files=True,
            key=f"app_photos_{clean_survey}_{form_ver}",
            help="Select land inspection photos. They will be auto-saved and attached to this survey plot immediately."
        )

        # Auto-save any newly uploaded photos immediately so users never lose them
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
                st.success(f"✅ Successfully uploaded & attached {newly_saved_count} photo(s) to Survey {active_survey_for_photos}!")

        # Photos Gallery for current survey (searches both new and old survey folders)
        current_survey_photos = get_all_survey_photos(new_survey_input, old_survey_input)
        active_rep_p = st.session_state.get("active_report_photos", []) or []
        seen_fp = {p["file_path"] for p in current_survey_photos}
        for p in active_rep_p:
            if p.get("file_path") and p["file_path"] not in seen_fp and os.path.exists(p["file_path"]):
                current_survey_photos.append(p)
                seen_fp.add(p["file_path"])

        if current_survey_photos:
            st.write(f"**Attached Inspection Photos for Survey {active_survey_for_photos} ({len(current_survey_photos)} photo(s)):**")
            thumb_cols = st.columns(min(max(len(current_survey_photos), 1), 4))
            for idx, photo in enumerate(current_survey_photos):
                with thumb_cols[idx % len(thumb_cols)]:
                    p_path = photo.get("file_path", "")
                    if os.path.exists(p_path):
                        st.image(p_path, use_container_width=True)
                        st.caption(f"`{photo['filename']}`")
                        if st.button("🗑️ Remove", key=f"del_app_{photo['filename']}_{idx}_{form_ver}"):
                            delete_survey_photo(p_path, survey_no=photo.get("survey_no") or active_survey_for_photos)
                            st.rerun()
                    else:
                        st.caption(f"📄 `{photo.get('filename')}`")
        else:
            st.info(f"No inspection photos attached yet for Survey {active_survey_for_photos}. Select photos above to attach them.")
    st.markdown('</div>', unsafe_allow_html=True)

    # -------------------------------------------------------------
    # Execution Button & LangGraph Workflow Run
    # -------------------------------------------------------------
    st.markdown("---")
    
    is_editing = st.session_state.get("active_report_id") is not None
    target_id_for_execution = None
    trigger_execution = False

    if is_editing:
        active_id = st.session_state.active_report_id
        btn_u_col, btn_n_col = st.columns([5, 5])
        with btn_u_col:
            if st.button(
                f"💾 Update Saved Report #{active_id} (Survey {new_survey_input or old_survey_input})",
                type="primary",
                use_container_width=True,
                help=f"Updates Report #{active_id} in PostgreSQL with your edited values."
            ):
                target_id_for_execution = active_id
                trigger_execution = True

        with btn_n_col:
            if st.button(
                "➕ Save as New Separate Report",
                type="secondary",
                use_container_width=True,
                help="Preserves Report #{active_id} untouched and creates a brand new report."
            ):
                target_id_for_execution = None
                trigger_execution = True
    else:
        btn_col1, _ = st.columns([4, 6])
        with btn_col1:
            if st.button("🚀 Run LangGraph Calculation Workflow", type="primary", use_container_width=True):
                target_id_for_execution = None
                trigger_execution = True

    if trigger_execution:
        with st.spinner("Executing LangGraph StateGraph nodes..."):
            # Auto-save any pending uploaded photos before execution
            if active_survey_for_photos and 'uploaded_photos' in locals() and uploaded_photos:
                for f in uploaded_photos:
                    if not photo_already_saved(active_survey_for_photos, f.name, f.size):
                        save_survey_photo(active_survey_for_photos, f.getvalue(), f.name)

            survey_photos_payload = get_all_survey_photos(new_survey_input, old_survey_input)
            active_rep_p = st.session_state.get("active_report_photos", []) or []
            existing_paths = {p["file_path"] for p in survey_photos_payload if p.get("file_path")}
            for p in active_rep_p:
                if p.get("file_path") and p["file_path"] not in existing_paths and os.path.exists(p["file_path"]):
                    survey_photos_payload.append(p)
                    existing_paths.add(p["file_path"])
            st.session_state.active_report_photos = survey_photos_payload

            # If new payment received was entered, log into payment_history with current payment date
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
            # Consolidate cumulative payment received into existing base, update history, and reset new payment received
            st.session_state.existing_payment_received = float(result.get("payment_received", payment_received_input))
            st.session_state.new_payment_received = 0.0
            st.session_state.payment_received = float(result.get("payment_received", payment_received_input))
            st.session_state.payment_remaining = float(result.get("payment_remaining", payment_remaining_input))
            st.session_state.payment_history = current_history
            st.session_state.last_payment_date_val = last_payment_date_input
            if result.get("saved_report_id"):
                st.session_state.active_report_id = result.get("saved_report_id")

    # Display results if available in session state
    if "latest_result" in st.session_state:
        result = st.session_state["latest_result"]

        st.success("✅ LangGraph Workflow Executed Successfully!")

        # PostgreSQL Database Save Status Banner
        saved_id = result.get("saved_report_id")
        save_stat = result.get("db_save_status", "")
        if saved_id:
            if "updated" in str(save_stat).lower():
                st.success(f"💾 **Report #{saved_id} for Survey '{result.get('new_survey_no') or 'N/A'}' was successfully updated in PostgreSQL Database!**")
            else:
                st.success(f"💾 **Report successfully saved to PostgreSQL Database!** (Record ID: **#{saved_id}** — Survey: **{result.get('new_survey_no') or 'N/A'}**)")
        else:
            st.info(f"ℹ️ **PostgreSQL Status:** {save_stat}")
            if "not set" in save_stat.lower():
                st.caption("👉 Add `DATABASE_URL=postgresql://...` to your `.env` file to enable database saving.")

        # Summary Metrics Cards
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Total Land (Bigha)", f"{result.get('bigha', 0.0):,.4f}")
        with m2:
            st.metric("Total Agreed Payment", f"₹{result.get('total_payment', 0.0):,.2f}")
        with m3:
            st.metric("Payment Received (Done)", f"₹{result.get('payment_received', 0.0):,.2f}")
        with m4:
            rem = result.get('payment_remaining', 0.0)
            st.metric("Payment Remaining", f"₹{rem:,.2f}", delta=f"-₹{rem:,.2f}" if rem > 0 else "Fully Settled")

        # Display Execution Trace and Logs
        with st.expander("🔍 View LangGraph Execution Trace", expanded=False):
            for log_step in result.get("calculation_log", []):
                st.write(f"• {log_step}")

        # Full Deal Report
        st.markdown("### 📄 Generated Land Deal Report")
        st.markdown(result.get("summary_report", ""))

        # Visual Gallery for Attached Land Inspection Photos
        deal_photos = result.get("land_photos") or []
        if deal_photos:
            st.markdown("#### 📸 Attached Land Inspection Photos")
            photo_cols = st.columns(min(max(len(deal_photos), 1), 4))
            for idx, p in enumerate(deal_photos):
                col_idx = idx % len(photo_cols)
                f_path = p.get("file_path")
                if f_path and os.path.exists(f_path):
                    with photo_cols[col_idx]:
                        st.image(f_path, caption=p.get("filename", f"Photo #{idx+1}"), use_container_width=True)

        # Action Buttons below report
        d_col1, d_col2 = st.columns([3, 7])
        with d_col1:
            st.download_button(
                label="📥 Download Deal Summary (Markdown)",
                data=result.get("summary_report", ""),
                file_name=f"land_deal_{new_survey_input or 'survey'}.md",
                mime="text/markdown",
                use_container_width=True,
            )


# =============================================================================
# SECTION 2: Saved Reports (Search via New Survey No)
# =============================================================================
with tab_saved_reports:
    st.markdown('<div class="row-card"><div class="row-title">📂 Saved Land Calculation Reports</div>', unsafe_allow_html=True)
    st.markdown("Search and inspect reports saved in your local PostgreSQL database. Filter specifically by **New Survey No**.")
    st.markdown('</div>', unsafe_allow_html=True)

    # Database connection status header
    if not db_health["connected"]:
        st.warning("⚠️ **PostgreSQL Database is not connected.**")
        st.markdown("""
        To view and search saved reports, please ensure:
        1. Your local PostgreSQL service is running.
        2. Your connection string is configured in `.env` under `DATABASE_URL=`, for example:
           ```env
           DATABASE_URL=postgresql://postgres:password@localhost:5432/landcal
           ```
        """)
    else:
        st.success(f"🟢 Connected to PostgreSQL: `{db_health['url_display']}`")

        # -------------------------------------------------------------
        # CSV Backup Section: Download All Reports before DB expiration
        # -------------------------------------------------------------
        all_reports_for_backup = get_saved_reports(limit=10000)
        csv_backup_data = export_reports_to_csv(all_reports_for_backup) if all_reports_for_backup else ""

        bk_card_col, bk_btn_col = st.columns([7, 3])
        with bk_card_col:
            st.markdown(
                f"💾 **Monthly Database Expiration Backup:** Download all **{len(all_reports_for_backup)}** saved report(s) as a CSV file to safeguard your records before monthly database reset."
            )
        with bk_btn_col:
            st.download_button(
                label=f"📥 Download All Reports (CSV)",
                data=csv_backup_data,
                file_name=f"all_land_reports_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                disabled=(len(all_reports_for_backup) == 0),
                type="primary",
                use_container_width=True,
                help="Download all saved land calculation reports as a CSV spreadsheet before database expiration."
            )
        st.markdown("---")

    # Search by New Survey No
    col_search, col_ref = st.columns([5, 1])
    with col_search:
        survey_filter = st.text_input(
            "🔍 Search Saved Reports by New Survey No:",
            value=st.session_state.get("search_survey_query", ""),
            placeholder="e.g. 112, 48/2, etc. (Leave blank to show all)",
            help="Filters saved database reports matching the New Survey Number.",
        )
    with col_ref:
        st.write("")
        st.write("")
        if st.button("🔄 Refresh List", key="btn_refresh_tab2", use_container_width=True):
            st.rerun()

    # Query reports
    if db_health["connected"]:
        saved_records = get_saved_reports(new_survey_no=survey_filter)

        if not saved_records:
            if survey_filter.strip():
                st.info(f"No saved reports found for New Survey No matching: **'{survey_filter.strip()}'**.")
            else:
                st.info("No saved reports found in the database yet. Run a calculation in Section 1 to generate and save reports.")
        else:
            st.write(f"Found **{len(saved_records)}** saved report(s)" + (f" matching New Survey No **'{survey_filter}'**" if survey_filter.strip() else "") + ":")

            record_options = {}
            for r in saved_records:
                up_ts = r.get("updated_at") or r.get("created_at")
                ts_str = up_ts.strftime('%Y-%m-%d %H:%M') if hasattr(up_ts, 'strftime') else str(up_ts)[:16]
                label = f"#{r['id']} | New Survey No: {r['new_survey_no'] or 'N/A'} (Old: {r['old_survey_no'] or 'N/A'}) | {r['village'] or 'N/A'}, {r['district'] or 'N/A'} | ₹{r['total_payment']:,.2f} | {ts_str}"
                record_options[label] = r['id']

            selected_label = st.selectbox(
                "Select a report to view details:",
                options=list(record_options.keys()),
                key="selected_report_dropdown"
            )

            selected_id = record_options[selected_label]
            selected_report = next((r for r in saved_records if r["id"] == selected_id), None)

            if selected_report:
                st.markdown("---")
                h_col1, h_col2 = st.columns([7, 3])
                with h_col1:
                    st.markdown(f"### 📋 Report #{selected_report['id']} — Survey: `{selected_report['new_survey_no'] or 'N/A'}`")
                    st.caption(f"Location: {selected_report['village']}, {selected_report['taluka']}, {selected_report['district']} | Old Survey No: {selected_report['old_survey_no'] or 'N/A'}")
                with h_col2:
                    st.caption(f"Created: {selected_report.get('created_at')} | Updated: {selected_report.get('updated_at')}")

                # Metric Cards for selected report
                sm1, sm2, sm3, sm4 = st.columns(4)
                with sm1:
                    st.metric("Total Land (Bigha)", f"{selected_report.get('bigha', 0.0):,.4f}")
                with sm2:
                    st.metric("Total Agreed Payment", f"₹{selected_report.get('total_payment', 0.0):,.2f}")
                with sm3:
                    st.metric("Payment Received (Done)", f"₹{selected_report.get('payment_received', 0.0):,.2f}")
                with sm4:
                    s_rem = selected_report.get('payment_remaining', 0.0)
                    st.metric("Payment Remaining", f"₹{s_rem:,.2f}", delta=f"-₹{s_rem:,.2f}" if s_rem > 0 else "Fully Settled")

                # Action Buttons
                act_col1, act_col2, act_col3 = st.columns([3, 3, 2])
                with act_col1:
                    if st.button("🔄 Load into Workflow Dashboard to Edit", use_container_width=True, help="Load this report into Tab 1 to modify and update it"):
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
                        st.success(f"✅ Loaded Report #{selected_report['id']} (Survey {selected_report['new_survey_no']}) into Tab 1 for editing!")
                        st.rerun()

                with act_col2:
                    st.download_button(
                        label="📥 Download Deal Report (MD)",
                        data=selected_report.get("summary_report", ""),
                        file_name=f"saved_report_{selected_report.get('new_survey_no') or 'deal'}_{selected_report['id']}.md",
                        mime="text/markdown",
                        use_container_width=True,
                    )

                with act_col3:
                    if st.button("🗑️ Delete Report", type="secondary", use_container_width=True, help="Permanently delete this report from PostgreSQL"):
                        ok, msg = delete_report_by_id(selected_id)
                        if ok:
                            if st.session_state.get("active_report_id") == selected_id:
                                st.session_state.active_report_id = None
                            st.success(f"Report #{selected_id} deleted.")
                            st.rerun()
                        else:
                            st.error(msg)

                # Rendered Deal Markdown Report
                st.markdown("#### 📄 Full Saved Report Document")
                st.markdown(selected_report.get("summary_report", "_No report document stored._"))

                saved_photos = selected_report.get("land_photos") or []
                if saved_photos:
                    st.markdown("#### 📸 Saved Land Inspection Photos")
                    s_photo_cols = st.columns(min(max(len(saved_photos), 1), 4))
                    for s_idx, sp in enumerate(saved_photos):
                        s_col_idx = s_idx % len(s_photo_cols)
                        s_fpath = sp.get("file_path")
                        if s_fpath and os.path.exists(s_fpath):
                            with s_photo_cols[s_col_idx]:
                                st.image(s_fpath, caption=sp.get("filename", f"Photo #{s_idx+1}"), use_container_width=True)
    else:
        st.info("Please set your `DATABASE_URL` in `.env` and ensure PostgreSQL is running to explore saved reports.")
