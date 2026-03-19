"""
Admin endpoint to sync resources from Supabase Storage into the resources table.

POST /api/v1/admin/resources/sync
  - Lists all objects in the Supabase Storage bucket
  - Derives subject names from folder paths (e.g. Grade_9/9-SCIENCE.pdf → "Science")
  - Looks up the matching subject in the DB (grade + subject name)
  - Inserts/skips resource rows (idempotent — won't duplicate on re-run)
  - Returns a summary of what was created / skipped

Folder structure expected in bucket:
  Grade_<N>/<N>-<SUBJECT>.pdf

This endpoint is protected by X-Admin-Api-Key header.
"""
from __future__ import annotations

import logging
import re
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.grade import Grade
from app.models.resource import Resource
from app.models.subject import Subject

logger = logging.getLogger(__name__)
router = APIRouter()


def _require_admin(x_admin_api_key: str = Header(...)):
    if x_admin_api_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid admin API key")


def _list_bucket_objects(supabase_url: str, service_role_key: str, bucket: str) -> list[dict[str, Any]]:
    """Return all objects in a Supabase Storage bucket using the REST API."""
    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Content-Type": "application/json",
    }
    url = f"{supabase_url.rstrip('/')}/storage/v1/object/list/{bucket}"
    # Use recursive listing via prefix search
    all_objects: list[dict[str, Any]] = []

    # First list top-level folders
    resp = httpx.post(url, headers=headers, json={"prefix": "", "limit": 200, "offset": 0}, timeout=30)
    resp.raise_for_status()
    top_level = resp.json()

    for item in top_level:
        name = item.get("name", "")
        # If it's a folder (no metadata/mimetype) recurse into it
        if item.get("metadata") is None:
            folder_prefix = name + "/"
            sub_resp = httpx.post(
                url,
                headers=headers,
                json={"prefix": folder_prefix, "limit": 200, "offset": 0},
                timeout=30,
            )
            sub_resp.raise_for_status()
            for sub_item in sub_resp.json():
                sub_item["_full_path"] = folder_prefix + sub_item.get("name", "")
                all_objects.append(sub_item)
        else:
            item["_full_path"] = name
            all_objects.append(item)

    return all_objects


def _subject_name_from_filename(filename: str) -> str | None:
    """
    Derive a clean subject name from a storage filename.

    Examples:
      9-SCIENCE.pdf  → "Science"
      9-HEALTH.pdf   → "Health"
      9-ICT.pdf      → "ICT"
      9-CIVICS.pdf   → "Civics"
    """
    base = filename.rsplit(".", 1)[0]               # strip extension
    parts = base.split("-", 1)                       # "9-SCIENCE" → ["9", "SCIENCE"]
    if len(parts) < 2:
        return None
    raw = parts[1].strip()                           # "SCIENCE"
    # Title-case but preserve short abbreviations like ICT
    if len(raw) <= 3:
        return raw.upper()
    return raw.title()


def _grade_number_from_folder(folder: str) -> int | None:
    """
    Extract grade number from folder name like 'Grade_9' → 9.
    """
    m = re.search(r"(\d+)", folder)
    return int(m.group(1)) if m else None


@router.post("/admin/resources/sync", tags=["admin-resources"])
def sync_resources_from_storage(
    db: Session = Depends(get_db),
    _: None = Depends(_require_admin),
):
    """
    Sync textbook resources from Supabase Storage into the resources table.
    Safe to run multiple times — will skip already-existing entries.
    """
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(status_code=500, detail="Supabase credentials not configured")

    # ── List bucket objects ──────────────────────────────────────────────────
    try:
        objects = _list_bucket_objects(
            settings.supabase_url,
            settings.supabase_service_role_key,
            settings.supabase_storage_bucket,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to list bucket objects: {exc}")

    created: list[str] = []
    skipped: list[str] = []
    errors: list[str] = []

    for obj in objects:
        full_path: str = obj.get("_full_path", obj.get("name", ""))
        if not full_path.lower().endswith(".pdf"):
            continue

        parts = full_path.split("/", 1)
        if len(parts) != 2:
            errors.append(f"Unexpected path structure: {full_path}")
            continue

        folder, filename = parts[0], parts[1]
        grade_num = _grade_number_from_folder(folder)
        subject_name = _subject_name_from_filename(filename)

        if grade_num is None or subject_name is None:
            errors.append(f"Could not parse: {full_path}")
            continue

        # ── Find grade ───────────────────────────────────────────────────────
        grade: Grade | None = db.scalar(
            select(Grade).where(Grade.name.ilike(f"%{grade_num}%"))
        )
        if not grade:
            errors.append(f"Grade {grade_num} not found in DB for {full_path}")
            continue

        # ── Find subject ─────────────────────────────────────────────────────
        subject: Subject | None = db.scalar(
            select(Subject).where(
                Subject.grade_id == grade.id,
                Subject.name.ilike(f"%{subject_name}%"),
            )
        )
        if not subject:
            errors.append(f"Subject '{subject_name}' (grade {grade_num}) not found in DB for {full_path}")
            continue

        # ── Skip if already exists ───────────────────────────────────────────
        existing = db.scalar(
            select(Resource).where(
                Resource.subject_id == subject.id,
                Resource.storage_path == full_path,
            )
        )
        if existing:
            skipped.append(full_path)
            continue

        # ── Insert new resource ──────────────────────────────────────────────
        title = f"Grade {grade_num} {subject_name} Textbook"
        resource = Resource(
            subject_id=subject.id,
            type="textbook",
            title=title,
            description=f"Official Grade {grade_num} {subject_name} textbook.",
            storage_path=full_path,
            file_url=None,
            is_active=True,
        )
        db.add(resource)
        created.append(full_path)

    db.commit()

    return {
        "status": "ok",
        "created": len(created),
        "skipped": len(skipped),
        "errors": len(errors),
        "created_paths": created,
        "skipped_paths": skipped,
        "error_details": errors,
    }
