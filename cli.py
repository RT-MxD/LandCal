"""
Command-line interface for the Land Calculation LangGraph workflow.
Allows running calculations directly or interactively from the terminal.
"""

import argparse
import json
import sys

# Configure UTF-8 for console output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from land_graph import run_land_calculation


def main():
    parser = argparse.ArgumentParser(description="Land Calculation LangGraph CLI")
    parser.add_argument("--district", default="Ahmedabad", help="District name")
    parser.add_argument("--taluka", default="Sanand", help="Taluka name")
    parser.add_argument("--village", default="Shela", help="Village name")
    parser.add_argument("--old-survey", default="104/A", help="Old Survey Number")
    parser.add_argument("--new-survey", default="112", help="New Survey Number")
    parser.add_argument("--area", type=float, default=3200.0, help="Area (input)")
    parser.add_argument("--bigha", type=float, default=None, help="Bigha (manual override, default area/16)")
    parser.add_argument("--sq-mt", type=float, default=None, help="Sq.mt (manual override, default area/1618.70)")
    parser.add_argument("--sq-yd", type=float, default=None, help="Sq.yd (manual override, default area/1930)")
    parser.add_argument("--rate-bigha", type=float, default=2500000.0, help="Rupees per Bigha")
    parser.add_argument("--rate-sqyd", type=float, default=12000.0, help="Rupees per Sq.yd")
    parser.add_argument("--buyer", default="Ramesh Patel", help="Buyer Name")
    parser.add_argument("--seller", default="Kishore Shah", help="Seller Name")
    parser.add_argument("--broker", default="Mahesh Desai", help="Broker Name")
    parser.add_argument("--total-payment", type=float, default=5000000.0, help="Agreed Total Payment")
    parser.add_argument("--payment-received", type=float, default=0.0, help="Payment Received from Buyer")
    parser.add_argument("--payment-remaining", type=float, default=None, help="Payment Remaining (Buyer Balance)")
    parser.add_argument("--buy-date", default="2026-03-01", help="Buy Date (YYYY-MM-DD)")
    parser.add_argument("--condition", default="Title Clearance", help="Condition Note")
    parser.add_argument("--last-payment-date", default="2026-06-30", help="Last Payment Date (YYYY-MM-DD)")
    parser.add_argument("--sell-date", default="2026-07-15", help="Sell Date (YYYY-MM-DD)")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    payload = {
        "district": args.district,
        "taluka": args.taluka,
        "village": args.village,
        "old_survey_no": args.old_survey,
        "new_survey_no": args.new_survey,
        "area": args.area,
        "bigha": args.bigha,
        "sq_mt": args.sq_mt,
        "sq_yd": args.sq_yd,
        "rupees_per_bigha": args.rate_bigha,
        "rupees_per_sq_yd": args.rate_sqyd,
        "buyer_name": args.buyer,
        "seller_name": args.seller,
        "broker": args.broker,
        "total_payment": args.total_payment,
        "payment_received": args.payment_received,
        "payment_remaining": args.payment_remaining,
        "buy_date": args.buy_date,
        "condition": args.condition,
        "last_payment_date": args.last_payment_date,
        "sell_date": args.sell_date,
        "conditions_list": [
            {"condition": "Token Advance", "rupees": 500000.0},
            {"condition": "Banakhat / Agreement", "rupees": 1500000.0},
            {"condition": "Title Clearance Certificate", "rupees": 1000000.0},
            {"condition": "Dastavej (Final Registry)", "rupees": 2000000.0},
        ],
    }

    result = run_land_calculation(payload)

    if args.json:
        # Filter non-serializable elements if any
        clean_result = {k: v for k, v in result.items() if k != "calculation_log"}
        print(json.dumps(clean_result, indent=2))
    else:
        print("\n=== LangGraph Execution Trace ===")
        for step in result.get("calculation_log", []):
            print(f" -> {step}")
        print("\n" + result.get("summary_report", ""))


if __name__ == "__main__":
    main()
