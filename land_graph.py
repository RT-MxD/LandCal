"""
Land Calculation LangGraph Workflow
Handles land metric conversions, valuations, party records, and payment conditions.
"""

from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END


class ConditionItem(TypedDict):
    condition: str
    rupees: float


class LandDealState(TypedDict, total=False):
    # Row 1: Location columns
    district: str
    taluka: str
    village: str

    # Row 2: Survey & Area metrics
    old_survey_no: str
    new_survey_no: str
    area: float
    bigha: float          # Formula: area / 16
    sq_mt: float          # Formula: area / 1618.70
    sq_yd: float          # Formula: area / 1930

    # Row 3: Rates
    rupees_per_bigha: float
    rupees_per_sq_yd: float

    # Row 4: Parties
    buyer_name: str
    seller_name: str
    broker: str

    # Row 5: Financials & Dates
    total_payment: float
    payment_received: float
    payment_remaining: float
    buy_date: str
    condition: str
    last_payment_date: str
    sell_date: str

    # Row 6: Conditions beside Rupees list
    conditions_list: List[ConditionItem]

    # Row 7: Land Photos (Survey-Locked)
    land_photos: List[Dict[str, Any]]

    # Payment History (List of payment dates and amounts)
    payment_history: List[Dict[str, Any]]

    # Calculated & Output Fields
    valuation_by_bigha: float
    valuation_by_sqyd: float
    total_condition_rupees: float
    remaining_balance: float
    summary_report: str
    target_report_id: Optional[int]
    saved_report_id: Optional[int]
    db_save_status: Optional[str]
    calculation_log: List[str]


def validate_and_normalize_node(state: LandDealState) -> Dict[str, Any]:
    """Cleans, normalizes, and defaults input variables."""
    log = list(state.get("calculation_log", []))
    log.append("Step 1: Validating and normalizing input fields.")

    def _to_float(val: Any, default: float = 0.0) -> float:
        if val is None or val == "":
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    area = _to_float(state.get("area", 0.0))
    raw_bigha = state.get("bigha")
    raw_sq_mt = state.get("sq_mt")
    raw_sq_yd = state.get("sq_yd")

    total_payment = _to_float(state.get("total_payment", 0.0))
    payment_received = _to_float(state.get("payment_received", 0.0))
    # Payment remaining is directly calculated by Total Payment - Payment Received
    payment_remaining = round(total_payment - payment_received, 2)
    log.append(f"Step 1: Payment Remaining directly calculated as ₹{payment_remaining:,.2f} (Total ₹{total_payment:,.2f} - Received ₹{payment_received:,.2f}).")

    return {
        "district": str(state.get("district", "")).strip(),
        "taluka": str(state.get("taluka", "")).strip(),
        "village": str(state.get("village", "")).strip(),
        "old_survey_no": str(state.get("old_survey_no", "")).strip(),
        "new_survey_no": str(state.get("new_survey_no", "")).strip(),
        "area": area,
        "bigha": _to_float(raw_bigha) if raw_bigha is not None else None,
        "sq_mt": _to_float(raw_sq_mt) if raw_sq_mt is not None else None,
        "sq_yd": _to_float(raw_sq_yd) if raw_sq_yd is not None else None,
        "rupees_per_bigha": _to_float(state.get("rupees_per_bigha", 0.0)),
        "rupees_per_sq_yd": _to_float(state.get("rupees_per_sq_yd", 0.0)),
        "buyer_name": str(state.get("buyer_name", "")).strip(),
        "seller_name": str(state.get("seller_name", "")).strip(),
        "broker": str(state.get("broker", "")).strip(),
        "total_payment": total_payment,
        "payment_received": payment_received,
        "payment_remaining": payment_remaining,
        "buy_date": str(state.get("buy_date", "")).strip(),
        "condition": str(state.get("condition", "")).strip(),
        "last_payment_date": str(state.get("last_payment_date", "")).strip(),
        "sell_date": str(state.get("sell_date", "")).strip(),
        "conditions_list": state.get("conditions_list", []) or [],
        "land_photos": state.get("land_photos", []) or [],
        "payment_history": state.get("payment_history", []) or [],
        "target_report_id": state.get("target_report_id"),
        "calculation_log": log,
    }


def calculate_area_metrics_node(state: LandDealState) -> Dict[str, Any]:
    """
    Automatically calculates area metrics based on user's exact formulas:
    - Bigha = area / 16
    - Sq.mt = area / 1618.70
    - Sq.yd = area / 1930
    """
    log = list(state.get("calculation_log", []))
    area = state.get("area", 0.0)

    # Formulas automatically calculated from input area
    calc_bigha = round(area / 16.0, 4) if area > 0 else 0.0
    calc_sq_mt = round(area / 1618.70, 4) if area > 0 else 0.0
    calc_sq_yd = round(area / 1930.0, 4) if area > 0 else 0.0

    log.append(f"Step 2: Area conversions automatically calculated (Area={area}): "
               f"Bigha={calc_bigha} [area/16], Sq.mt={calc_sq_mt} [area/1618.70], Sq.yd={calc_sq_yd} [area/1930].")

    return {
        "bigha": calc_bigha,
        "sq_mt": calc_sq_mt,
        "sq_yd": calc_sq_yd,
        "calculation_log": log,
    }


def calculate_valuations_node(state: LandDealState) -> Dict[str, Any]:
    """Calculates land valuation by rate per bigha and rate per sq.yd."""
    log = list(state.get("calculation_log", []))
    bigha = state.get("bigha", 0.0)
    sq_yd = state.get("sq_yd", 0.0)
    rupees_per_bigha = state.get("rupees_per_bigha", 0.0)
    rupees_per_sq_yd = state.get("rupees_per_sq_yd", 0.0)

    val_bigha = round(bigha * rupees_per_bigha, 2)
    val_sqyd = round(sq_yd * rupees_per_sq_yd, 2)

    log.append(f"Step 3: Valuations calculated: By Bigha = ₹{val_bigha:,.2f}, By Sq.yd = ₹{val_sqyd:,.2f}.")

    return {
        "valuation_by_bigha": val_bigha,
        "valuation_by_sqyd": val_sqyd,
        "calculation_log": log,
    }


def process_conditions_and_balance_node(state: LandDealState) -> Dict[str, Any]:
    """Tallies payments across condition rows and determines remaining balance against total payment."""
    log = list(state.get("calculation_log", []))
    total_payment = state.get("total_payment", 0.0)
    conditions = state.get("conditions_list", [])

    total_condition_rupees = 0.0
    for idx, item in enumerate(conditions):
        try:
            amt = float(item.get("rupees", 0.0))
        except (ValueError, TypeError):
            amt = 0.0
        total_condition_rupees += amt

    total_condition_rupees = round(total_condition_rupees, 2)
    remaining_balance = round(total_payment - total_condition_rupees, 2)

    log.append(f"Step 4: Conditions processed. Total Condition Allocated = ₹{total_condition_rupees:,.2f}, "
               f"Total Payment = ₹{total_payment:,.2f}, Remaining Balance = ₹{remaining_balance:,.2f}.")

    return {
        "total_condition_rupees": total_condition_rupees,
        "remaining_balance": remaining_balance,
        "calculation_log": log,
    }


def generate_deal_report_node(state: LandDealState) -> Dict[str, Any]:
    """Generates an executive land deal summary and audit report."""
    log = list(state.get("calculation_log", []))
    log.append("Step 5: Generating comprehensive land deal summary report.")

    district = state.get("district") or "N/A"
    taluka = state.get("taluka") or "N/A"
    village = state.get("village") or "N/A"
    old_survey = state.get("old_survey_no") or "N/A"
    new_survey = state.get("new_survey_no") or "N/A"
    area = state.get("area", 0.0)
    bigha = state.get("bigha", 0.0)
    sq_mt = state.get("sq_mt", 0.0)
    sq_yd = state.get("sq_yd", 0.0)
    rate_bigha = state.get("rupees_per_bigha", 0.0)
    rate_sqyd = state.get("rupees_per_sq_yd", 0.0)
    buyer = state.get("buyer_name") or "N/A"
    seller = state.get("seller_name") or "N/A"
    broker = state.get("broker") or "N/A"
    total_pay = state.get("total_payment", 0.0)
    pay_received = state.get("payment_received", 0.0)
    pay_remaining = state.get("payment_remaining", 0.0)
    buy_date = state.get("buy_date") or "N/A"
    condition_note = state.get("condition") or "N/A"
    last_payment_date = state.get("last_payment_date") or "N/A"
    sell_date = state.get("sell_date") or "N/A"

    val_bigha = state.get("valuation_by_bigha", 0.0)
    val_sqyd = state.get("valuation_by_sqyd", 0.0)
    cond_total = state.get("total_condition_rupees", 0.0)
    rem_balance = state.get("remaining_balance", 0.0)
    conditions = state.get("conditions_list", [])

    condition_rows_md = ""
    if conditions:
        condition_rows_md += "| # | Condition / Milestone | Amount (₹) |\n|---|---|---:|\n"
        for i, c in enumerate(conditions, 1):
            desc = c.get("condition", f"Condition {i}")
            amt = float(c.get("rupees", 0.0))
            condition_rows_md += f"| {i} | {desc} | ₹{amt:,.2f} |\n"
        condition_rows_md += f"| **Total** | **All Conditions Total** | **₹{cond_total:,.2f}** |\n"
    else:
        condition_rows_md = "_No condition payments specified._\n"

    # Format attached photos
    photos = state.get("land_photos", [])
    photos_md = ""
    if photos:
        photos_md += "| # | Photo Filename | Upload Timestamp | Size (KB) |\n|---|---|---|---:|\n"
        for i, p in enumerate(photos, 1):
            fn = p.get("filename", f"photo_{i}")
            ts = p.get("modified_at") or p.get("uploaded_at") or "N/A"
            sz = round(float(p.get("size_bytes", 0)) / 1024.0, 1)
            photos_md += f"| {i} | `{fn}` | {ts} | {sz} KB |\n"
    else:
        photos_md = "_No inspection photos attached to this survey plot._\n"

    # Format payment history table
    payment_hist = state.get("payment_history", []) or []
    payment_dates_md = ""
    if payment_hist:
        payment_dates_md += "\n### 📅 Payment Installments & Date Log\n"
        payment_dates_md += "| # | Payment Received Date | Amount (₹) |\n|---|---|---:|\n"
        for i, item in enumerate(payment_hist, 1):
            p_date = item.get("date", "N/A")
            try:
                p_amt = float(item.get("amount", 0.0))
            except Exception:
                p_amt = 0.0
            payment_dates_md += f"| {i} | {p_date} | ₹{p_amt:,.2f} |\n"
        payment_dates_md += f"| **Total** | **All Payments Done** | **₹{pay_received:,.2f}** |\n"

    report = f"""# 🌾 Land Deal Calculation Report

## 1. Location Details
- **District:** {district}
- **Taluka:** {taluka}
- **Village:** {village}

## 2. Land Survey & Area Measurements
- **Old Survey No:** {old_survey}
- **New Survey No:** {new_survey}
- **Area (Input):** {area:,.4f}
- **Bigha [Formula: area / 16]:** {bigha:,.4f}
- **Sq.mt [Formula: area / 1618.70]:** {sq_mt:,.4f}
- **Sq.yd [Formula: area / 1930]:** {sq_yd:,.4f}

## 3. Rate & Valuations
- **Rate per Bigha:** ₹{rate_bigha:,.2f}  
  ↳ **Total Valuation (by Bigha):** ₹{val_bigha:,.2f}
- **Rate per Sq.yd:** ₹{rate_sqyd:,.2f}  
  ↳ **Total Valuation (by Sq.yd):** ₹{val_sqyd:,.2f}

## 4. Parties Involved
- **Buyer Name:** {buyer}
- **Seller Name:** {seller}
- **Broker:** {broker}

## 5. Transaction & Payment Schedule
- **Agreed Total Payment:** ₹{total_pay:,.2f}
- **Total Payment Received (Done by Buyer):** ₹{pay_received:,.2f}
- **Payment Remaining (Directly Calculated: Total - Received):** ₹{pay_remaining:,.2f}
- **Last Payment Date:** {last_payment_date}
- **Buy Date:** {buy_date}
- **Primary Condition:** {condition_note}
- **Sell Date:** {sell_date}
{payment_dates_md}

## 6. Conditions & Milestone Breakdown
{condition_rows_md}

## 7. Land Inspection Photos & Attachments
{photos_md}

---
### 💰 Financial Settlement Status
- **Total Payment Committed:** ₹{total_pay:,.2f}
- **Payment Done by Buyer (Received):** ₹{pay_received:,.2f}
- **Payment Remaining to Collect (Total - Received):** ₹{pay_remaining:,.2f}
- **Total Allocated by Conditions:** ₹{cond_total:,.2f}
- **Remaining Balance Due:** ₹{rem_balance:,.2f}
"""
    return {
        "summary_report": report,
        "calculation_log": log,
    }


def save_to_database_node(state: LandDealState) -> Dict[str, Any]:
    """
    Saves the generated land deal report into the PostgreSQL database if configured.
    """
    log = list(state.get("calculation_log", []))
    try:
        from db import save_deal_report, update_deal_report, get_database_url
        if not get_database_url():
            log.append("Step 6: DATABASE_URL not set in .env; report not saved to database.")
            return {
                "saved_report_id": None,
                "db_save_status": "DATABASE_URL not set in .env",
                "calculation_log": log,
            }

        target_id = state.get("target_report_id")
        if target_id:
            success, report_id, message = update_deal_report(target_id, state)
            if success:
                log.append(f"Step 6: Existing Report #{target_id} successfully updated in PostgreSQL database.")
                return {
                    "saved_report_id": report_id,
                    "db_save_status": f"Updated (ID: #{report_id})",
                    "calculation_log": log,
                }
            else:
                log.append(f"Step 6: Database update failed ({message}).")
                return {
                    "saved_report_id": None,
                    "db_save_status": f"Failed: {message}",
                    "calculation_log": log,
                }
        else:
            success, report_id, message = save_deal_report(state)
            if success:
                log.append(f"Step 6: Report successfully saved to PostgreSQL database (ID: #{report_id}).")
                return {
                    "saved_report_id": report_id,
                    "db_save_status": f"Saved (ID: #{report_id})",
                    "calculation_log": log,
                }
            else:
                log.append(f"Step 6: Database save skipped or failed ({message}).")
                return {
                    "saved_report_id": None,
                    "db_save_status": f"Failed: {message}",
                    "calculation_log": log,
                }
    except Exception as e:
        log.append(f"Step 6: Database operation encountered an exception: {e}")
        return {
            "saved_report_id": None,
            "db_save_status": f"Error: {str(e)}",
            "calculation_log": log,
        }


def create_land_calculation_graph() -> StateGraph:
    """Builds and compiles the Land Calculation StateGraph."""
    graph = StateGraph(LandDealState)

    # Add workflow nodes
    graph.add_node("validate_and_normalize", validate_and_normalize_node)
    graph.add_node("calculate_area_metrics", calculate_area_metrics_node)
    graph.add_node("calculate_valuations", calculate_valuations_node)
    graph.add_node("process_conditions_and_balance", process_conditions_and_balance_node)
    graph.add_node("generate_deal_report", generate_deal_report_node)
    graph.add_node("save_to_database", save_to_database_node)

    # Add edges defining sequential flow
    graph.add_edge(START, "validate_and_normalize")
    graph.add_edge("validate_and_normalize", "calculate_area_metrics")
    graph.add_edge("calculate_area_metrics", "calculate_valuations")
    graph.add_edge("calculate_valuations", "process_conditions_and_balance")
    graph.add_edge("process_conditions_and_balance", "generate_deal_report")
    graph.add_edge("generate_deal_report", "save_to_database")
    graph.add_edge("save_to_database", END)

    return graph


# Pre-compiled executable graph
land_graph_app = create_land_calculation_graph().compile()


def run_land_calculation(state_inputs: Dict[str, Any]) -> LandDealState:
    """Convenience helper to invoke the compiled LangGraph workflow."""
    return land_graph_app.invoke(state_inputs)


if __name__ == "__main__":
    import sys
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    sample_deal = {
        "district": "Ahmedabad",
        "taluka": "Sanand",
        "village": "Shela",
        "old_survey_no": "104/A",
        "new_survey_no": "112",
        "area": 3200.0,
        "rupees_per_bigha": 2500000.0,
        "rupees_per_sq_yd": 12000.0,
        "buyer_name": "Ramesh Patel",
        "seller_name": "Kishore Shah",
        "broker": "Mahesh Desai",
        "total_payment": 5000000.0,
        "buy_date": "2026-03-01",
        "condition": "Title Clearance and Boundary Marking",
        "last_payment_date": "2026-06-30",
        "sell_date": "2026-07-15",
        "conditions_list": [
            {"condition": "Token Advance", "rupees": 500000.0},
            {"condition": "Banakhat / Agreement", "rupees": 1500000.0},
            {"condition": "Title Clearance Certificate", "rupees": 1000000.0},
            {"condition": "Dastavej (Final Registry)", "rupees": 2000000.0},
        ],
    }

    result = run_land_calculation(sample_deal)
    print("Execution Logs:")
    for step in result.get("calculation_log", []):
        print(" -", step)
    print("\n" + result.get("summary_report", ""))
