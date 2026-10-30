"""
Database Module for Land Calculation Workflow
Handles PostgreSQL connection, table migrations, and report persistence.
Uses DATABASE_URL defined in .env.
"""

import csv
import io
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(dotenv_path=env_path, override=False)
except Exception:
    pass

import psycopg2
from psycopg2.extras import RealDictCursor


def get_database_url() -> Optional[str]:
    # 1. Check Streamlit Cloud Secrets first if running inside Streamlit
    try:
        import streamlit as st
        if "DATABASE_URL" in st.secrets:
            val = str(st.secrets["DATABASE_URL"]).strip()
            if val:
                return val
    except Exception:
        pass

    # 2. Check OS environment variable (loaded from .env or Vercel Environment Variables)
    url = os.getenv("DATABASE_URL", "").strip()
    return url if url else None


def get_masked_db_url() -> str:
    """Returns the database URL with the password masked for safe UI display."""
    raw_url = get_database_url()
    if not raw_url:
        return "Not Configured (DATABASE_URL is empty in .env)"
    try:
        parsed = urlparse(raw_url)
        if parsed.password:
            masked_netloc = parsed.netloc.replace(f":{parsed.password}@", ":****@")
            return parsed._replace(netloc=masked_netloc).geturl()
        return raw_url
    except Exception:
        return "postgresql://... [configured]"


def get_connection():
    """Establishes and returns a connection to the PostgreSQL database."""
    db_url = get_database_url()
    if not db_url:
        raise ValueError("DATABASE_URL is not set in .env")
    # Ensure SSL for Supabase / cloud database connections
    if ("supabase.co" in db_url or "pooler.supabase.com" in db_url) and "sslmode" not in db_url:
        sep = "&" if "?" in db_url else "?"
        db_url = f"{db_url}{sep}sslmode=require"
    return psycopg2.connect(db_url)


def check_db_status() -> Dict[str, Any]:
    """Tests the PostgreSQL database connection and returns health status."""
    db_url = get_database_url()
    if not db_url:
        return {
            "connected": False,
            "url_set": False,
            "message": "DATABASE_URL is not configured in .env. Please set your PostgreSQL connection URL.",
            "url_display": "None",
        }

    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
        conn.close()
        return {
            "connected": True,
            "url_set": True,
            "message": "Successfully connected to PostgreSQL database.",
            "url_display": get_masked_db_url(),
        }
    except Exception as e:
        return {
            "connected": False,
            "url_set": True,
            "message": f"Connection failed: {str(e)}",
            "url_display": get_masked_db_url(),
        }


def init_db() -> bool:
    """
    Creates the land_reports table and survey indices if they do not exist.
    """
    db_url = get_database_url()
    if not db_url:
        return False

    create_table_sql = """
    CREATE TABLE IF NOT EXISTS land_reports (
        id SERIAL PRIMARY KEY,
        district VARCHAR(100),
        taluka VARCHAR(100),
        village VARCHAR(100),
        old_survey_no VARCHAR(100),
        new_survey_no VARCHAR(100),
        area DOUBLE PRECISION,
        bigha DOUBLE PRECISION,
        sq_mt DOUBLE PRECISION,
        sq_yd DOUBLE PRECISION,
        rupees_per_bigha DOUBLE PRECISION,
        rupees_per_sq_yd DOUBLE PRECISION,
        buyer_name VARCHAR(255),
        seller_name VARCHAR(255),
        broker VARCHAR(255),
        total_payment DOUBLE PRECISION,
        payment_received DOUBLE PRECISION DEFAULT 0.0,
        payment_remaining DOUBLE PRECISION DEFAULT 0.0,
        buy_date VARCHAR(50),
        condition TEXT,
        last_payment_date VARCHAR(50),
        sell_date VARCHAR(50),
        conditions_list JSONB,
        land_photos JSONB,
        valuation_by_bigha DOUBLE PRECISION,
        valuation_by_sqyd DOUBLE PRECISION,
        total_condition_rupees DOUBLE PRECISION,
        remaining_balance DOUBLE PRECISION,
        summary_report TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_land_reports_new_survey ON land_reports(new_survey_no);
    CREATE INDEX IF NOT EXISTS idx_land_reports_created_at ON land_reports(created_at DESC);
    ALTER TABLE land_reports ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    ALTER TABLE land_reports ADD COLUMN IF NOT EXISTS payment_received DOUBLE PRECISION DEFAULT 0.0;
    ALTER TABLE land_reports ADD COLUMN IF NOT EXISTS payment_remaining DOUBLE PRECISION DEFAULT 0.0;
    ALTER TABLE land_reports ADD COLUMN IF NOT EXISTS payment_history JSONB;
    """
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(create_table_sql)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[db.init_db error] {e}")
        return False


def save_deal_report(state: Dict[str, Any]) -> Tuple[bool, Optional[int], str]:
    """
    Saves a generated land deal state and summary report to PostgreSQL.
    Returns (success, record_id, status_message).
    """
    db_url = get_database_url()
    if not db_url:
        return False, None, "DATABASE_URL is not set in .env. Skipping database save."

    try:
        init_db()
        conn = get_connection()

        conditions_json = json.dumps(state.get("conditions_list", []) or [])
        photos_json = json.dumps(state.get("land_photos", []) or [])
        payment_history_json = json.dumps(state.get("payment_history", []) or [])

        insert_sql = """
        INSERT INTO land_reports (
            district, taluka, village, old_survey_no, new_survey_no,
            area, bigha, sq_mt, sq_yd, rupees_per_bigha, rupees_per_sq_yd,
            buyer_name, seller_name, broker, total_payment, payment_received, payment_remaining, buy_date,
            condition, last_payment_date, sell_date,
            conditions_list, land_photos, payment_history,
            valuation_by_bigha, valuation_by_sqyd,
            total_condition_rupees, remaining_balance,
            summary_report
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s,
            %s, %s,
            %s
        ) RETURNING id;
        """

        params = (
            str(state.get("district", "")).strip(),
            str(state.get("taluka", "")).strip(),
            str(state.get("village", "")).strip(),
            str(state.get("old_survey_no", "")).strip(),
            str(state.get("new_survey_no", "")).strip(),
            float(state.get("area", 0.0) or 0.0),
            float(state.get("bigha", 0.0) or 0.0),
            float(state.get("sq_mt", 0.0) or 0.0),
            float(state.get("sq_yd", 0.0) or 0.0),
            float(state.get("rupees_per_bigha", 0.0) or 0.0),
            float(state.get("rupees_per_sq_yd", 0.0) or 0.0),
            str(state.get("buyer_name", "")).strip(),
            str(state.get("seller_name", "")).strip(),
            str(state.get("broker", "")).strip(),
            float(state.get("total_payment", 0.0) or 0.0),
            float(state.get("payment_received", 0.0) or 0.0),
            float(state.get("payment_remaining", 0.0) or 0.0),
            str(state.get("buy_date", "")).strip(),
            str(state.get("condition", "")).strip(),
            str(state.get("last_payment_date", "")).strip(),
            str(state.get("sell_date", "")).strip(),
            conditions_json,
            photos_json,
            payment_history_json,
            float(state.get("valuation_by_bigha", 0.0) or 0.0),
            float(state.get("valuation_by_sqyd", 0.0) or 0.0),
            float(state.get("total_condition_rupees", 0.0) or 0.0),
            float(state.get("remaining_balance", 0.0) or 0.0),
            str(state.get("summary_report", "")).strip(),
        )

        with conn.cursor() as cur:
            cur.execute(insert_sql, params)
            new_id = cur.fetchone()[0]
        conn.commit()
        conn.close()

        return True, new_id, f"Report successfully saved to PostgreSQL (Record ID: #{new_id})"
    except Exception as e:
        return False, None, f"Failed to save report to PostgreSQL: {str(e)}"


def update_deal_report(report_id: int, state: Dict[str, Any]) -> Tuple[bool, Optional[int], str]:
    """
    Updates an existing land deal report in PostgreSQL by report_id.
    Returns (success, report_id, status_message).
    """
    db_url = get_database_url()
    if not db_url:
        return False, None, "DATABASE_URL is not set in .env. Skipping database update."

    try:
        init_db()
        conn = get_connection()

        conditions_json = json.dumps(state.get("conditions_list", []) or [])
        photos_json = json.dumps(state.get("land_photos", []) or [])
        payment_history_json = json.dumps(state.get("payment_history", []) or [])

        update_sql = """
        UPDATE land_reports SET
            district = %s,
            taluka = %s,
            village = %s,
            old_survey_no = %s,
            new_survey_no = %s,
            area = %s,
            bigha = %s,
            sq_mt = %s,
            sq_yd = %s,
            rupees_per_bigha = %s,
            rupees_per_sq_yd = %s,
            buyer_name = %s,
            seller_name = %s,
            broker = %s,
            total_payment = %s,
            payment_received = %s,
            payment_remaining = %s,
            buy_date = %s,
            condition = %s,
            last_payment_date = %s,
            sell_date = %s,
            conditions_list = %s,
            land_photos = %s,
            payment_history = %s,
            valuation_by_bigha = %s,
            valuation_by_sqyd = %s,
            total_condition_rupees = %s,
            remaining_balance = %s,
            summary_report = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        RETURNING id;
        """

        params = (
            str(state.get("district", "")).strip(),
            str(state.get("taluka", "")).strip(),
            str(state.get("village", "")).strip(),
            str(state.get("old_survey_no", "")).strip(),
            str(state.get("new_survey_no", "")).strip(),
            float(state.get("area", 0.0) or 0.0),
            float(state.get("bigha", 0.0) or 0.0),
            float(state.get("sq_mt", 0.0) or 0.0),
            float(state.get("sq_yd", 0.0) or 0.0),
            float(state.get("rupees_per_bigha", 0.0) or 0.0),
            float(state.get("rupees_per_sq_yd", 0.0) or 0.0),
            str(state.get("buyer_name", "")).strip(),
            str(state.get("seller_name", "")).strip(),
            str(state.get("broker", "")).strip(),
            float(state.get("total_payment", 0.0) or 0.0),
            float(state.get("payment_received", 0.0) or 0.0),
            float(state.get("payment_remaining", 0.0) or 0.0),
            str(state.get("buy_date", "")).strip(),
            str(state.get("condition", "")).strip(),
            str(state.get("last_payment_date", "")).strip(),
            str(state.get("sell_date", "")).strip(),
            conditions_json,
            photos_json,
            payment_history_json,
            float(state.get("valuation_by_bigha", 0.0) or 0.0),
            float(state.get("valuation_by_sqyd", 0.0) or 0.0),
            float(state.get("total_condition_rupees", 0.0) or 0.0),
            float(state.get("remaining_balance", 0.0) or 0.0),
            str(state.get("summary_report", "")).strip(),
            report_id,
        )

        with conn.cursor() as cur:
            cur.execute(update_sql, params)
            row = cur.fetchone()
            if not row:
                conn.close()
                return False, None, f"Report #{report_id} not found in database to update."
            updated_id = row[0]
        conn.commit()
        conn.close()

        survey_label = state.get("new_survey_no") or state.get("old_survey_no") or ""
        return True, updated_id, f"Report #{updated_id} (Survey {survey_label}) successfully updated in PostgreSQL."
    except Exception as e:
        return False, None, f"Failed to update report #{report_id} in PostgreSQL: {str(e)}"


def get_saved_reports(new_survey_no: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Retrieves saved reports from PostgreSQL.
    Optionally filters by New Survey No (case-insensitive partial match).
    """
    db_url = get_database_url()
    if not db_url:
        return []

    try:
        conn = get_connection()
        query = """
        SELECT
            id, district, taluka, village, old_survey_no, new_survey_no,
            area, bigha, sq_mt, sq_yd, rupees_per_bigha, rupees_per_sq_yd,
            buyer_name, seller_name, broker, total_payment, payment_received, payment_remaining, buy_date,
            condition, last_payment_date, sell_date,
            conditions_list, land_photos, payment_history,
            valuation_by_bigha, valuation_by_sqyd,
            total_condition_rupees, remaining_balance,
            summary_report, created_at, updated_at
        FROM land_reports
        """
        params = []
        if new_survey_no and str(new_survey_no).strip():
            query += " WHERE new_survey_no ILIKE %s"
            params.append(f"%{str(new_survey_no).strip()}%")

        query += " ORDER BY COALESCE(updated_at, created_at) DESC LIMIT %s;"
        params.append(limit)

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
        conn.close()

        # Parse JSON fields if returned as string
        results = []
        for r in rows:
            row_dict = dict(r)
            if isinstance(row_dict.get("conditions_list"), str):
                try:
                    row_dict["conditions_list"] = json.loads(row_dict["conditions_list"])
                except Exception:
                    pass
            if isinstance(row_dict.get("land_photos"), str):
                try:
                    row_dict["land_photos"] = json.loads(row_dict["land_photos"])
                except Exception:
                    pass
            if isinstance(row_dict.get("payment_history"), str):
                try:
                    row_dict["payment_history"] = json.loads(row_dict["payment_history"])
                except Exception:
                    pass
            results.append(row_dict)
        return results
    except Exception as e:
        print(f"[db.get_saved_reports error] {e}")
        return []


def get_report_by_id(report_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves a single report by its ID."""
    db_url = get_database_url()
    if not db_url:
        return None

    try:
        conn = get_connection()
        query = "SELECT * FROM land_reports WHERE id = %s;"
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (report_id,))
            row = cur.fetchone()
        conn.close()

        if not row:
            return None

        result = dict(row)
        if isinstance(result.get("conditions_list"), str):
            try:
                result["conditions_list"] = json.loads(result["conditions_list"])
            except Exception:
                pass
        if isinstance(result.get("land_photos"), str):
            try:
                result["land_photos"] = json.loads(result["land_photos"])
            except Exception:
                pass
        if isinstance(result.get("payment_history"), str):
            try:
                result["payment_history"] = json.loads(result["payment_history"])
            except Exception:
                pass
        return result
    except Exception as e:
        print(f"[db.get_report_by_id error] {e}")
        return None


def delete_report_by_id(report_id: int) -> Tuple[bool, str]:
    """Deletes a report by its ID."""
    db_url = get_database_url()
    if not db_url:
        return False, "DATABASE_URL is not configured."

    try:
        conn = get_connection()
        query = "DELETE FROM land_reports WHERE id = %s;"
        with conn.cursor() as cur:
            cur.execute(query, (report_id,))
        conn.commit()
        conn.close()
        return True, f"Report #{report_id} successfully deleted."
    except Exception as e:
        return False, f"Failed to delete report #{report_id}: {str(e)}"


def export_reports_to_csv(reports: Optional[List[Dict[str, Any]]] = None) -> str:
    """
    Exports saved land reports into a clean, comprehensive CSV format.
    If reports is None, fetches all available reports from PostgreSQL.
    Useful for creating complete backups before database expiration.
    """
    if reports is None:
        reports = get_saved_reports(limit=10000)

    if not reports:
        return ""

    fieldnames = [
        "id", "district", "taluka", "village",
        "old_survey_no", "new_survey_no", "area", "bigha", "sq_mt", "sq_yd",
        "rupees_per_bigha", "rupees_per_sq_yd",
        "buyer_name", "seller_name", "broker",
        "total_payment", "payment_received", "payment_remaining",
        "buy_date", "condition", "last_payment_date", "sell_date",
        "valuation_by_bigha", "valuation_by_sqyd",
        "total_condition_rupees", "remaining_balance",
        "conditions_list", "payment_history", "land_photos_count",
        "created_at", "updated_at"
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()

    for r in reports:
        row = dict(r)

        # Serialize list/dict structures into clean JSON
        if isinstance(row.get("conditions_list"), (list, dict)):
            row["conditions_list"] = json.dumps(row["conditions_list"])
        if isinstance(row.get("payment_history"), (list, dict)):
            row["payment_history"] = json.dumps(row["payment_history"])

        photos = row.get("land_photos")
        row["land_photos_count"] = len(photos) if isinstance(photos, list) else 0

        # Format datetime objects into strings
        for ts_col in ["created_at", "updated_at"]:
            val = row.get(ts_col)
            if val and hasattr(val, "strftime"):
                row[ts_col] = val.strftime("%Y-%m-%d %H:%M:%S")

        writer.writerow(row)

    return output.getvalue()
