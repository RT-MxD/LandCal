"""
Photo Manager Module for Land Deal Records
Organizes and isolates land photos strictly by Survey Number to prevent mismatches.
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


# Detect serverless environment (Vercel / AWS Lambda) where root filesystem is read-only
IS_SERVERLESS = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
if IS_SERVERLESS:
    DEFAULT_PHOTO_DIR = Path("/tmp") / "uploads" / "land_photos"
else:
    DEFAULT_PHOTO_DIR = Path(__file__).resolve().parent / "uploads" / "land_photos"

try:
    DEFAULT_PHOTO_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    DEFAULT_PHOTO_DIR = Path("/tmp") / "uploads" / "land_photos"
    try:
        DEFAULT_PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass


def get_supabase_project_ref() -> Optional[str]:
    """
    Extracts the Supabase project reference ID directly from DATABASE_URL.
    Keeps DATABASE_URL intact as the sole database connection configuration.
    """
    ref = os.getenv("SUPABASE_PROJECT_REF")
    if ref and ref.strip():
        return ref.strip()
    try:
        from db import get_database_url
        db_url = get_database_url() or ""
        m = re.search(r"(?:postgres\.([a-z0-9]{15,30})|db\.([a-z0-9]{15,30})\.supabase\.co)", db_url)
        if m:
            return m.group(1) or m.group(2)
    except Exception:
        pass
    return None


def upload_to_supabase_storage(
    survey_no: str,
    file_bytes: bytes,
    saved_filename: str,
    bucket_name: str = "land_photos"
) -> Optional[str]:
    """
    Uploads photo bytes to Supabase Storage bucket and returns the permanent public URL.
    Returns None if Supabase credentials or network are unavailable (enabling local fallback).
    """
    try:
        project_ref = get_supabase_project_ref()
        if not project_ref:
            return None

        # Check for Supabase key in OS env or Streamlit secrets
        supabase_key = (
            os.getenv("SUPABASE_KEY")
            or os.getenv("SUPABASE_ANON_KEY")
            or os.getenv("SUPABASE_SERVICE_KEY")
            or ""
        ).strip()
        if not supabase_key:
            try:
                import streamlit as st
                supabase_key = str(
                    st.secrets.get("SUPABASE_KEY")
                    or st.secrets.get("SUPABASE_ANON_KEY")
                    or st.secrets.get("SUPABASE_SERVICE_KEY")
                    or ""
                ).strip()
            except Exception:
                pass

        clean_no = sanitize_survey_no(survey_no)
        object_path = f"survey_{clean_no}/{saved_filename}"
        upload_url = f"https://{project_ref}.supabase.co/storage/v1/object/{bucket_name}/{object_path}"
        public_url = f"https://{project_ref}.supabase.co/storage/v1/object/public/{bucket_name}/{object_path}"

        ext = Path(saved_filename).suffix.lower()
        content_type = "image/jpeg"
        if ext == ".png":
            content_type = "image/png"
        elif ext == ".webp":
            content_type = "image/webp"

        headers = {
            "Content-Type": content_type,
            "x-upsert": "true",
        }
        if supabase_key:
            headers["Authorization"] = f"Bearer {supabase_key}"
            headers["apikey"] = supabase_key

        import urllib.request
        req = urllib.request.Request(upload_url, data=file_bytes, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status in (200, 201):
                return public_url
    except Exception:
        pass
    return None


def get_photo_display_url(photo_item: Any) -> Optional[str]:
    """
    Resolves a photo entry (dict or string path/URL) into a displayable target for st.image.
    Supports:
    1. Cloud / Supabase URLs (http:// or https://)
    2. Local file paths (absolute, relative, or cross-platform fallback)
    3. Returns None if unresolvable.
    """
    if not photo_item:
        return None

    raw_path = ""
    filename = ""
    if isinstance(photo_item, dict):
        raw_path = (
            photo_item.get("file_path")
            or photo_item.get("public_url")
            or photo_item.get("url")
            or photo_item.get("image_url")
            or ""
        ).strip()
        filename = photo_item.get("filename", "")
    elif isinstance(photo_item, str):
        raw_path = photo_item.strip()

    if not raw_path:
        return None

    # 1. Cloud / Web URL
    if raw_path.startswith("http://") or raw_path.startswith("https://") or raw_path.startswith("data:image"):
        return raw_path

    # 2. Local file path exists directly
    if os.path.exists(raw_path):
        return raw_path

    # 3. Resolve relative to project root or uploads folder
    p = Path(raw_path)
    candidates = [
        Path(__file__).resolve().parent / raw_path,
        DEFAULT_PHOTO_DIR / p.name,
    ]
    if isinstance(photo_item, dict) and photo_item.get("survey_no"):
        clean_no = sanitize_survey_no(photo_item["survey_no"])
        candidates.append(DEFAULT_PHOTO_DIR / f"survey_{clean_no}" / p.name)
        if filename:
            candidates.append(DEFAULT_PHOTO_DIR / f"survey_{clean_no}" / filename)

    for cand in candidates:
        if cand.exists():
            return str(cand.resolve())

    return None


def sanitize_survey_no(survey_no: Optional[str]) -> str:
    """
    Sanitizes survey numbers into filesystem-safe strings.
    E.g. '104/A' -> '104_A', '45/paiki 1' -> '45_paiki_1'
    """
    if not survey_no or not str(survey_no).strip():
        return "unspecified_survey"
    s = str(survey_no).strip()
    # Replace slashes, backslashes, colons, spaces, and illegal characters with underscores
    s = re.sub(r'[\\/*?:"<>|\s]+', '_', s)
    # Remove consecutive underscores
    s = re.sub(r'_+', '_', s).strip('._')
    return s if s else "unspecified_survey"


def get_survey_dir(survey_no: str, base_dir: Optional[Path] = None) -> Path:
    """Returns the dedicated directory for a given survey number, creating it if needed."""
    root = Path(base_dir) if base_dir else DEFAULT_PHOTO_DIR
    clean_no = sanitize_survey_no(survey_no)
    survey_dir = root / f"survey_{clean_no}"
    try:
        survey_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        survey_dir = Path("/tmp") / "uploads" / "land_photos" / f"survey_{clean_no}"
        try:
            survey_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
    return survey_dir


def save_survey_photo(
    survey_no: str,
    file_bytes: bytes,
    original_filename: str,
    base_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Saves an individual photo into cloud storage (Supabase Storage) or survey-isolated directory.
    Prefixes the filename with the survey number and timestamp to guarantee uniqueness.
    """
    clean_no = sanitize_survey_no(survey_no)

    # Sanitize original file extension and basename
    ext = Path(original_filename).suffix.lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp", ".bmp"]:
        ext = ".jpg"

    safe_base = re.sub(r'[^a-zA-Z0-9_\-]', '_', Path(original_filename).stem)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
    saved_filename = f"{clean_no}_{timestamp}_{safe_base}{ext}"

    # 1. Attempt Supabase Storage Upload
    public_url = upload_to_supabase_storage(survey_no, file_bytes, saved_filename)
    if public_url:
        return {
            "survey_no": str(survey_no),
            "sanitized_survey": clean_no,
            "filename": saved_filename,
            "original_filename": original_filename,
            "file_path": public_url,
            "public_url": public_url,
            "storage_type": "supabase",
            "size_bytes": len(file_bytes),
            "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    # 2. Local / Serverless Disk Fallback
    survey_dir = get_survey_dir(survey_no, base_dir=base_dir)
    dest_path = survey_dir / saved_filename
    try:
        with open(dest_path, "wb") as f:
            f.write(file_bytes)
    except OSError:
        survey_dir = Path("/tmp") / "uploads" / "land_photos" / f"survey_{clean_no}"
        try:
            survey_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        dest_path = survey_dir / saved_filename
        with open(dest_path, "wb") as f:
            f.write(file_bytes)

    try:
        rel_path = str(dest_path.relative_to(DEFAULT_PHOTO_DIR.parent.parent))
    except Exception:
        rel_path = str(dest_path)

    return {
        "survey_no": str(survey_no),
        "sanitized_survey": clean_no,
        "filename": saved_filename,
        "original_filename": original_filename,
        "file_path": str(dest_path.resolve()),
        "relative_path": rel_path,
        "storage_type": "local",
        "size_bytes": len(file_bytes),
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def list_survey_photos(survey_no: str, base_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Lists all photos belonging to a specific survey number."""
    clean_no = sanitize_survey_no(survey_no)
    root = Path(base_dir) if base_dir else DEFAULT_PHOTO_DIR
    survey_dir = root / f"survey_{clean_no}"

    if not survey_dir.exists() or not survey_dir.is_dir():
        return []

    photos = []
    valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    for f in sorted(survey_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if f.is_file() and f.suffix.lower() in valid_exts:
            photos.append({
                "survey_no": str(survey_no),
                "sanitized_survey": clean_no,
                "filename": f.name,
                "file_path": str(f.resolve()),
                "size_bytes": f.stat().st_size,
                "modified_at": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            })
    return photos


def delete_survey_photo(photo_path: str, survey_no: Optional[str] = None) -> bool:
    """Deletes a specific photo. If survey_no is provided, verifies that photo belongs to that survey."""
    if not photo_path:
        return False

    # For cloud-stored photos, allow removing the reference
    if photo_path.startswith("http://") or photo_path.startswith("https://"):
        return True

    path = Path(photo_path)
    if not path.exists() or not path.is_file():
        return False

    if survey_no:
        clean_no = sanitize_survey_no(survey_no)
        # Ensure the file is actually inside the survey's folder
        if path.parent.name != f"survey_{clean_no}":
            return False

    try:
        path.unlink()
        return True
    except OSError:
        return False


def photo_already_saved(
    survey_no: str,
    original_filename: str,
    file_size: int,
    base_dir: Optional[Path] = None
) -> bool:
    """
    Checks if a photo with the same original basename and size already exists in the survey folder.
    Prevents duplicate auto-saving when Streamlit reruns.
    """
    clean_no = sanitize_survey_no(survey_no)
    root = Path(base_dir) if base_dir else DEFAULT_PHOTO_DIR
    survey_dir = root / f"survey_{clean_no}"
    if not survey_dir.exists() or not survey_dir.is_dir():
        return False

    safe_base = re.sub(r'[^a-zA-Z0-9_\-]', '_', Path(original_filename).stem)
    ext = Path(original_filename).suffix.lower()
    for f in survey_dir.iterdir():
        if f.is_file() and f.stat().st_size == file_size:
            if safe_base in f.name and f.suffix.lower() == ext:
                return True
    return False


def get_all_survey_photos(
    new_survey_no: Optional[str] = None,
    old_survey_no: Optional[str] = None,
    base_dir: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """
    Lists all photos across both new and old survey numbers without duplicates.
    Guarantees photos are found whether searched by new or old survey number.
    """
    seen_paths = set()
    combined = []
    candidates = []
    if new_survey_no and str(new_survey_no).strip():
        candidates.append(str(new_survey_no).strip())
    if old_survey_no and str(old_survey_no).strip():
        candidates.append(str(old_survey_no).strip())

    for s_no in candidates:
        for p in list_survey_photos(s_no, base_dir=base_dir):
            if p["file_path"] not in seen_paths:
                seen_paths.add(p["file_path"])
                combined.append(p)
    return combined
