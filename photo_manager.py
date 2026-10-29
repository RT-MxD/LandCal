"""
Photo Manager Module for Land Deal Records
Organizes and isolates land photos strictly by Survey Number to prevent mismatches.
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

DEFAULT_PHOTO_DIR = Path(__file__).resolve().parent / "uploads" / "land_photos"
DEFAULT_PHOTO_DIR.mkdir(parents=True, exist_ok=True)


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
    survey_dir.mkdir(parents=True, exist_ok=True)
    return survey_dir


def save_survey_photo(
    survey_no: str,
    file_bytes: bytes,
    original_filename: str,
    base_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Saves an individual photo into the survey's isolated directory.
    Prefixes the filename with the survey number and timestamp to guarantee uniqueness.
    """
    clean_no = sanitize_survey_no(survey_no)
    survey_dir = get_survey_dir(survey_no, base_dir=base_dir)

    # Sanitize original file extension and basename
    ext = Path(original_filename).suffix.lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp", ".bmp"]:
        ext = ".jpg"

    safe_base = re.sub(r'[^a-zA-Z0-9_\-]', '_', Path(original_filename).stem)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
    saved_filename = f"{clean_no}_{timestamp}_{safe_base}{ext}"

    dest_path = survey_dir / saved_filename
    with open(dest_path, "wb") as f:
        f.write(file_bytes)

    return {
        "survey_no": str(survey_no),
        "sanitized_survey": clean_no,
        "filename": saved_filename,
        "original_filename": original_filename,
        "file_path": str(dest_path.resolve()),
        "relative_path": str(dest_path.relative_to(DEFAULT_PHOTO_DIR.parent.parent)),
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

