"""
LandCal FastAPI Application
REST API for Land Calculation, Metric Conversions, PostgreSQL Report Persistence,
and Survey-Locked Inspection Photo Management.
"""

import io
import os
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, Query, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

# Core LandCal modules
from db import (
    check_db_status,
    delete_report_by_id,
    export_reports_to_csv,
    get_report_by_id,
    get_saved_reports,
    init_db,
)
from land_graph import run_land_calculation
from photo_manager import (
    DEFAULT_PHOTO_DIR,
    delete_survey_photo,
    get_all_survey_photos,
    list_survey_photos,
    photo_already_saved,
    sanitize_survey_no,
    save_survey_photo,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management."""
    # Ensure storage directory exists (safe against read-only serverless filesystems)
    try:
        DEFAULT_PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    # Attempt to initialize database tables if DATABASE_URL is configured
    try:
        init_db()
    except Exception:
        pass
    yield


app = FastAPI(
    title="LandCal REST API",
    description=(
        "Production-ready FastAPI backend for Land Calculation workflows powered by LangGraph, "
        "PostgreSQL persistence, and survey-locked inspection photo management."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Enable CORS for web and mobile frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# PYDANTIC DATA SCHEMAS
# =============================================================================

class ConditionItemModel(BaseModel):
    condition: str = Field(..., description="Description of condition or milestone")
    rupees: float = Field(0.0, description="Payment amount in ₹ assigned to this condition")


class PaymentRecordModel(BaseModel):
    date: str = Field(..., description="Payment date formatted as YYYY-MM-DD")
    amount: float = Field(..., description="Amount received in ₹")


class AreaConversionRequest(BaseModel):
    area: float = Field(..., description="Input area value to convert", gt=0)


class AreaConversionResponse(BaseModel):
    area: float
    bigha: float = Field(..., description="Bigha = area / 1618.74")
    sq_mt: float = Field(..., description="Sq.mt = area * 1618.74")
    sq_yd: float = Field(..., description="Sq.yd = area * 1936")


class LandCalculationRequest(BaseModel):
    # Location
    district: str = Field("", description="District name")
    taluka: str = Field("", description="Taluka name")
    village: str = Field("", description="Village name")

    # Survey & Area
    old_survey_no: str = Field("", description="Old survey number (e.g. 104/A)")
    new_survey_no: str = Field("", description="New survey number (e.g. 112)")
    area: float = Field(0.0, description="Area measurement in base units")

    # Rates & Valuations (manually entered by user)
    rupees_per_bigha: float = Field(0.0, description="Valuation per Bigha in ₹ (manually entered)")
    rupees_per_sq_yd: float = Field(0.0, description="Valuation per Sq.yd in ₹ (manually entered)")

    # Parties
    buyer_name: str = Field("", description="Name of buyer")
    seller_name: str = Field("", description="Name of seller")
    broker: str = Field("", description="Broker name or agency")

    # Financials & Dates
    total_payment: float = Field(0.0, description="Total agreed payment in ₹")
    payment_received: float = Field(0.0, description="Base/previous payment received in ₹")
    new_payment_received: float = Field(0.0, description="Incremental new payment received in ₹")
    buy_date: str = Field("", description="Buy date (YYYY-MM-DD)")
    condition: str = Field("", description="Primary deal condition note")
    last_payment_date: str = Field("", description="Date of last payment (YYYY-MM-DD)")
    sell_date: str = Field("", description="Target sell/closing date (YYYY-MM-DD)")

    # Milestones & History
    conditions_list: List[ConditionItemModel] = Field(default_factory=list, description="Conditions beside rupees")
    payment_history: List[PaymentRecordModel] = Field(default_factory=list, description="List of payment date logs")

    # Workflow Options
    target_report_id: Optional[int] = Field(None, description="If updating an existing report, specify its ID")
    save_to_db: bool = Field(True, description="Whether to persist the result in PostgreSQL")


class LandCalculationResponse(BaseModel):
    district: str
    taluka: str
    village: str
    old_survey_no: str
    new_survey_no: str
    area: float
    bigha: float
    sq_mt: float
    sq_yd: float
    rupees_per_bigha: float
    rupees_per_sq_yd: float
    valuation_by_bigha: float
    valuation_by_sqyd: float
    buyer_name: str
    seller_name: str
    broker: str
    total_payment: float
    payment_received: float
    payment_remaining: float
    buy_date: str
    condition: str
    last_payment_date: str
    sell_date: str
    conditions_list: List[Dict[str, Any]]
    total_condition_rupees: float
    remaining_balance: float
    payment_history: List[Dict[str, Any]]
    land_photos: List[Dict[str, Any]]
    summary_report: str
    calculation_log: List[str]
    saved_report_id: Optional[int] = None
    db_save_status: Optional[str] = None


class BaseResponse(BaseModel):
    success: bool
    message: str


# =============================================================================
# ROOT & HEALTH CHECK ENDPOINTS
# =============================================================================

@app.get("/", tags=["System"])
def root_endpoint():
    """Welcome endpoint with API metadata and documentation links."""
    return {
        "app": "LandCal REST API",
        "version": "1.0.0",
        "status": "online",
        "docs": "/docs",
        "redoc": "/redoc",
        "description": "FastAPI service for Land Calculation workflows, reports, and inspection photos."
    }


@app.get("/api/health", tags=["System"])
def health_check():
    """Tests PostgreSQL database connectivity and returns health status."""
    db_health = check_db_status()
    return {
        "status": "healthy" if db_health.get("connected") else "database_disconnected",
        "database": db_health,
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# AREA CONVERSION & METRIC CALCULATOR ENDPOINTS
# =============================================================================

@app.post("/api/convert-metrics", response_model=AreaConversionResponse, tags=["Calculations"])
def convert_metrics(req: AreaConversionRequest):
    """
    Utility endpoint for instant area conversions based on formulas:
    - Bigha = area / 1618.74
    - Sq.mt = area * 1618.74
    - Sq.yd = area * 1936
    """
    area = req.area
    return AreaConversionResponse(
        area=round(area, 4),
        bigha=round(area / 1618.74, 4) if area > 0 else 0.0,
        sq_mt=round(area * 1618.74, 4) if area > 0 else 0.0,
        sq_yd=round(area * 1936.0, 4) if area > 0 else 0.0,
    )


# =============================================================================
# LANGGRAPH WORKFLOW EXECUTION ENDPOINTS
# =============================================================================

@app.post("/api/calculate", response_model=LandCalculationResponse, tags=["Calculations"])
def calculate_land_deal(req: LandCalculationRequest):
    """
    Executes the full LangGraph state graph for a land deal:
    1. Validates inputs and normalizes financials.
    2. Calculates area metrics (Bigha, Sq.mt, Sq.yd).
    3. Calculates land valuations by Bigha and Sq.yd.
    4. Tallies condition milestones and determines remaining balances.
    5. Discovers survey-locked inspection photos across new and old survey numbers.
    6. Generates full Markdown Deal Report.
    7. Persists or updates record in PostgreSQL (if DATABASE_URL is configured and save_to_db is True).
    """
    # Auto-calculate total agreed payment: bigha * rate_bigha or sq.yd * rate_sqyd
    calc_bigha = round(req.area / 1618.74, 4) if req.area > 0 else 0.0
    calc_sqyd = round(req.area * 1936.0, 4) if req.area > 0 else 0.0
    if req.rupees_per_bigha > 0:
        tot_payment = round(calc_bigha * req.rupees_per_bigha, 2)
    elif req.rupees_per_sq_yd > 0:
        tot_payment = round(calc_sqyd * req.rupees_per_sq_yd, 2)
    else:
        tot_payment = float(req.total_payment or 0.0)

    # Consolidate payment amounts and history
    base_received = float(req.payment_received or 0.0)
    curr_new = float(req.new_payment_received or 0.0)
    total_received = round(base_received + curr_new, 2)
    pay_remaining = round(tot_payment - total_received, 2)

    payment_date = req.last_payment_date or str(date.today())
    current_history = [p.model_dump() for p in req.payment_history]
    if curr_new > 0:
        current_history.append({"date": payment_date, "amount": curr_new})

    # Retrieve all photos attached to the new and/or old survey numbers
    survey_photos = get_all_survey_photos(req.new_survey_no, req.old_survey_no)

    conditions_data = [c.model_dump() for c in req.conditions_list]

    workflow_payload: Dict[str, Any] = {
        "district": req.district,
        "taluka": req.taluka,
        "village": req.village,
        "old_survey_no": req.old_survey_no,
        "new_survey_no": req.new_survey_no,
        "area": req.area,
        "rupees_per_bigha": req.rupees_per_bigha,
        "rupees_per_sq_yd": req.rupees_per_sq_yd,
        "buyer_name": req.buyer_name,
        "seller_name": req.seller_name,
        "broker": req.broker,
        "total_payment": tot_payment,
        "payment_received": total_received,
        "payment_remaining": pay_remaining,
        "buy_date": req.buy_date,
        "condition": req.condition,
        "last_payment_date": payment_date,
        "sell_date": req.sell_date,
        "conditions_list": conditions_data,
        "land_photos": survey_photos,
        "payment_history": current_history,
        "target_report_id": req.target_report_id if req.save_to_db else None,
    }

    try:
        result = run_land_calculation(workflow_payload)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LangGraph execution error: {str(e)}"
        )

    return LandCalculationResponse(
        district=result.get("district", ""),
        taluka=result.get("taluka", ""),
        village=result.get("village", ""),
        old_survey_no=result.get("old_survey_no", ""),
        new_survey_no=result.get("new_survey_no", ""),
        area=float(result.get("area", 0.0)),
        bigha=float(result.get("bigha", 0.0)),
        sq_mt=float(result.get("sq_mt", 0.0)),
        sq_yd=float(result.get("sq_yd", 0.0)),
        rupees_per_bigha=float(result.get("rupees_per_bigha", 0.0)),
        rupees_per_sq_yd=float(result.get("rupees_per_sq_yd", 0.0)),
        valuation_by_bigha=float(result.get("valuation_by_bigha", 0.0)),
        valuation_by_sqyd=float(result.get("valuation_by_sqyd", 0.0)),
        buyer_name=result.get("buyer_name", ""),
        seller_name=result.get("seller_name", ""),
        broker=result.get("broker", ""),
        total_payment=float(result.get("total_payment", 0.0)),
        payment_received=float(result.get("payment_received", 0.0)),
        payment_remaining=float(result.get("payment_remaining", 0.0)),
        buy_date=result.get("buy_date", ""),
        condition=result.get("condition", ""),
        last_payment_date=result.get("last_payment_date", ""),
        sell_date=result.get("sell_date", ""),
        conditions_list=result.get("conditions_list", []),
        total_condition_rupees=float(result.get("total_condition_rupees", 0.0)),
        remaining_balance=float(result.get("remaining_balance", 0.0)),
        payment_history=result.get("payment_history", []),
        land_photos=result.get("land_photos", []),
        summary_report=result.get("summary_report", ""),
        calculation_log=result.get("calculation_log", []),
        saved_report_id=result.get("saved_report_id"),
        db_save_status=result.get("db_save_status"),
    )


# =============================================================================
# SAVED REPORTS MANAGEMENT (POSTGRESQL CRUD)
# =============================================================================

@app.get("/api/reports", tags=["Reports"])
def list_reports(
    new_survey_no: Optional[str] = Query(None, description="Filter reports by New Survey Number"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of reports to return"),
):
    """Retrieves saved reports from PostgreSQL database with optional New Survey No filter."""
    try:
        records = get_saved_reports(new_survey_no=new_survey_no, limit=limit)
        return {
            "count": len(records),
            "filter_survey": new_survey_no,
            "reports": records,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query reports from database: {str(e)}"
        )


@app.get("/api/reports/{report_id}", tags=["Reports"])
def get_report(report_id: int):
    """Retrieves a single saved land calculation report by its record ID."""
    report = get_report_by_id(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report #{report_id} was not found."
        )
    return report


@app.put("/api/reports/{report_id}", response_model=LandCalculationResponse, tags=["Reports"])
def update_report(report_id: int, req: LandCalculationRequest):
    """
    Updates an existing report by ID with new calculations, milestones, and payment entries.
    """
    # Force target_report_id to report_id
    req.target_report_id = report_id
    req.save_to_db = True
    return calculate_land_deal(req)


@app.delete("/api/reports/{report_id}", response_model=BaseResponse, tags=["Reports"])
def delete_report(report_id: int):
    """Permanently deletes a report from the PostgreSQL database."""
    success, message = delete_report_by_id(report_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    return BaseResponse(success=True, message=message)


@app.get("/api/reports/{report_id}/markdown", tags=["Reports"])
def download_report_markdown(report_id: int):
    """Downloads the full Markdown deal summary report for a given report ID."""
    report = get_report_by_id(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report #{report_id} was not found."
        )
    summary_md = report.get("summary_report", "")
    survey_tag = report.get("new_survey_no") or report.get("old_survey_no") or "deal"
    filename = f"land_deal_{survey_tag}_{report_id}.md"

    return Response(
        content=summary_md,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.get("/api/reports/export/csv", tags=["Reports"])
def export_reports_csv():
    """Exports and downloads all database reports as a CSV backup spreadsheet."""
    all_reports = get_saved_reports(limit=10000)
    if not all_reports:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No reports found in the database to export."
        )
    csv_content = export_reports_to_csv(all_reports)
    filename = f"all_land_reports_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# =============================================================================
# LAND INSPECTION PHOTOS MANAGEMENT
# =============================================================================

@app.post("/api/photos/upload", tags=["Photos"])
async def upload_photos(
    survey_no: str = Form(..., description="Survey Number to isolate and lock photos to"),
    files: List[UploadFile] = File(..., description="One or more image files to attach"),
):
    """
    Uploads inspection photos isolated and locked to the specified survey number.
    Supports JPG, JPEG, PNG, WEBP, and BMP formats.
    """
    clean_no = sanitize_survey_no(survey_no)
    if not clean_no or clean_no == "unspecified_survey":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid Survey Number is required to upload inspection photos."
        )

    saved_photos = []
    allowed_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

    for f in files:
        ext = Path(f.filename).suffix.lower()
        if ext not in allowed_exts:
            continue

        file_bytes = await f.read()
        if len(file_bytes) == 0:
            continue

        # Prevent duplicate uploads of identical files
        if not photo_already_saved(survey_no, f.filename, len(file_bytes)):
            photo_info = save_survey_photo(survey_no, file_bytes, f.filename)
            saved_photos.append(photo_info)

    return {
        "success": True,
        "count": len(saved_photos),
        "survey_no": survey_no,
        "uploaded_photos": saved_photos,
        "message": f"Successfully uploaded {len(saved_photos)} photo(s) for Survey {survey_no}."
    }


@app.get("/api/photos", tags=["Photos"])
def get_photos(
    survey_no: Optional[str] = Query(None, description="Primary survey number"),
    old_survey_no: Optional[str] = Query(None, description="Optional old survey number to combine"),
):
    """
    Lists all attached land inspection photos for a survey number (or across both old and new survey numbers).
    """
    if old_survey_no or survey_no:
        photos = get_all_survey_photos(survey_no, old_survey_no)
    else:
        photos = []

    return {
        "count": len(photos),
        "survey_no": survey_no,
        "old_survey_no": old_survey_no,
        "photos": photos,
    }


@app.get("/api/photos/file/{survey_no}/{filename}", tags=["Photos"])
def serve_photo(survey_no: str, filename: str):
    """Streams and serves an attached inspection photo file directly."""
    clean_no = sanitize_survey_no(survey_no)
    photo_path = DEFAULT_PHOTO_DIR / f"survey_{clean_no}" / filename

    if not photo_path.exists() or not photo_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Photo '{filename}' not found for Survey '{survey_no}'."
        )

    # Determine media type
    ext = photo_path.suffix.lower()
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }
    media_type = media_types.get(ext, "application/octet-stream")

    return FileResponse(path=str(photo_path), media_type=media_type, filename=filename)


@app.delete("/api/photos", response_model=BaseResponse, tags=["Photos"])
def delete_photo(
    file_path: Optional[str] = Query(None, description="Absolute file path of the photo to delete"),
    survey_no: Optional[str] = Query(None, description="Survey number if deleting by filename"),
    filename: Optional[str] = Query(None, description="Filename if deleting by survey number"),
):
    """Deletes an inspection photo by its file path or survey number and filename."""
    target_path = None
    if file_path:
        target_path = file_path
    elif survey_no and filename:
        clean_no = sanitize_survey_no(survey_no)
        target_path = str(DEFAULT_PHOTO_DIR / f"survey_{clean_no}" / filename)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'file_path' or both 'survey_no' and 'filename' must be provided."
        )

    success, message = delete_survey_photo(target_path, survey_no=survey_no)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message
        )

    return BaseResponse(success=True, message=message)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
