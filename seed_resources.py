"""
Seed script: reads PDFs from Supabase Storage and inserts resource rows in DB.
Run from the backend project root:
    venv\Scripts\python.exe seed_resources.py
"""
from __future__ import annotations
import os, re, sys

# Load .env
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

SUPABASE_URL     = os.environ["SUPABASE_URL"].rstrip("/")
SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
BUCKET           = os.environ.get("SUPABASE_STORAGE_BUCKET", "mindup-resources")
DATABASE_URL     = os.environ["DATABASE_URL"].replace(
    "postgresql://", "postgresql+psycopg2://", 1
) if os.environ["DATABASE_URL"].startswith("postgresql://") else os.environ["DATABASE_URL"]

import httpx
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(__file__))
from app.models.grade    import Grade
from app.models.resource import Resource
from app.models.subject  import Subject


def list_pdfs() -> list[str]:
    """List all PDF storage_paths from the bucket."""
    hdrs = {
        "apikey": SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }
    url = f"{SUPABASE_URL}/storage/v1/object/list/{BUCKET}"
    paths: list[str] = []

    resp = httpx.post(url, headers=hdrs, json={"prefix": "", "limit": 200, "offset": 0}, timeout=30)
    resp.raise_for_status()
    top = resp.json()
    print(f"Top-level items: {[i.get('name') for i in top]}")

    for item in top:
        name = item.get("name", "")
        if item.get("metadata") is None:          # it's a folder
            prefix = name + "/"
            r = httpx.post(url, headers=hdrs, json={"prefix": prefix, "limit": 200, "offset": 0}, timeout=30)
            r.raise_for_status()
            for sub in r.json():
                fp = prefix + sub.get("name", "")
                if fp.lower().endswith(".pdf"):
                    paths.append(fp)
        else:
            if name.lower().endswith(".pdf"):
                paths.append(name)

    return paths


def parse_path(full_path: str):
    """Return (grade_num, subject_name) or (None, None)."""
    parts = full_path.split("/", 1)
    if len(parts) != 2:
        return None, None
    folder, filename = parts
    m = re.search(r"(\d+)", folder)
    grade_num = int(m.group(1)) if m else None
    base = filename.rsplit(".", 1)[0]
    seg = base.split("-", 1)
    if len(seg) < 2:
        return grade_num, None
    raw = seg[1].strip()
    subject_name = raw.upper() if len(raw) <= 3 else raw.title()
    return grade_num, subject_name


def main():
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

    # Quick connectivity check
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("DB connection OK.\n")

    print("Listing Supabase Storage bucket…")
    try:
        pdfs = list_pdfs()
    except Exception as e:
        print(f"ERROR: {e}"); sys.exit(1)

    print(f"\nFound {len(pdfs)} PDF(s):")
    for p in pdfs:
        print(f"  {p}")

    created, skipped, errors = [], [], []

    with Session(engine) as db:
        for fp in pdfs:
            grade_num, subject_name = parse_path(fp)
            if not grade_num or not subject_name:
                errors.append(f"Cannot parse: {fp}"); continue

            grade = db.scalar(select(Grade).where(Grade.name.ilike(f"%{grade_num}%")))
            if not grade:
                errors.append(f"Grade {grade_num} not in DB — {fp}"); continue

            subject = db.scalar(
                select(Subject).where(
                    Subject.grade_id == grade.id,
                    Subject.name.ilike(f"%{subject_name}%"),
                )
            )
            if not subject:
                errors.append(f"Subject '{subject_name}' not in DB for grade {grade_num} — {fp}"); continue

            exists = db.scalar(
                select(Resource).where(
                    Resource.subject_id == subject.id,
                    Resource.storage_path == fp,
                )
            )
            if exists:
                skipped.append(fp)
                print(f"  SKIP  {fp}")
                continue

            db.add(Resource(
                subject_id=subject.id,
                type="textbook",
                title=f"Grade {grade_num} {subject_name} Textbook",
                description=f"Official Grade {grade_num} {subject_name} textbook.",
                storage_path=fp,
                file_url=None,
                is_active=True,
            ))
            created.append(fp)
            print(f"  ADD   {fp}  →  {subject.name} (id={subject.id})")

        db.commit()

    print(f"\n{'─'*50}")
    print(f"  Created : {len(created)}")
    print(f"  Skipped : {len(skipped)}")
    print(f"  Errors  : {len(errors)}")
    for e in errors:
        print(f"  ✗ {e}")


if __name__ == "__main__":
    main()
