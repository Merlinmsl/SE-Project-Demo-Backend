"""
Update / insert Grade 9 textbook resources using the provided signed URLs.

Run from the backend project root:
    venv\\Scripts\\python.exe update_grade9_resources.py
"""
from __future__ import annotations
import os, sys

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

DATABASE_URL = os.environ["DATABASE_URL"].replace(
    "postgresql://", "postgresql+psycopg2://", 1
) if os.environ["DATABASE_URL"].startswith("postgresql://") else os.environ["DATABASE_URL"]

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(__file__))
from app.models.grade   import Grade
from app.models.subject import Subject
from app.models.resource import Resource

# ─── Grade 9 textbooks ──────────────────────────────────────────────────────
GRADE9_BOOKS = [
    {
        "subject": "Civics",
        "storage_path": "Grade_9/9-CIVICS.pdf",
        "file_url": "https://qozmwqaaoyuolfzusefx.supabase.co/storage/v1/object/sign/mindup-resources/Grade_9/9-CIVICS.pdf?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV8zMTdjZDJjZC02NTQ4LTQzYjMtYWZkYy1kOWM1MjI0ODIzZTgiLCJhbGciOiJIUzI1NiJ9.eyJ1cmwiOiJtaW5kdXAtcmVzb3VyY2VzL0dyYWRlXzkvOS1DSVZJQ1MucGRmIiwiaWF0IjoxNzczOTIyNjAyLCJleHAiOjE4MDU0NTg2MDJ9.Vu0wUS7-uiMTYWmxztQ-4Ib4XG6FyleCua2eZMfjKz4",
    },
    {
        "subject": "English",
        "storage_path": "Grade_9/9-ENGLISH.pdf",
        "file_url": "https://qozmwqaaoyuolfzusefx.supabase.co/storage/v1/object/sign/mindup-resources/Grade_9/9-ENGLISH.pdf?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV8zMTdjZDJjZC02NTQ4LTQzYjMtYWZkYy1kOWM1MjI0ODIzZTgiLCJhbGciOiJIUzI1NiJ9.eyJ1cmwiOiJtaW5kdXAtcmVzb3VyY2VzL0dyYWRlXzkvOS1FTkdMSVNILnBkZiIsImlhdCI6MTc3MzkyMjY0MywiZXhwIjoxODA1NDU4NjQzfQ.B4NL8GsTktDZHSK3I1Fuz7KCYyFwof5AAp5swwc3VlI",
    },
    {
        "subject": "Health",
        "storage_path": "Grade_9/9-HEALTH.pdf",
        "file_url": "https://qozmwqaaoyuolfzusefx.supabase.co/storage/v1/object/sign/mindup-resources/Grade_9/9-HEALTH.pdf?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV8zMTdjZDJjZC02NTQ4LTQzYjMtYWZkYy1kOWM1MjI0ODIzZTgiLCJhbGciOiJIUzI1NiJ9.eyJ1cmwiOiJtaW5kdXAtcmVzb3VyY2VzL0dyYWRlXzkvOS1IRUFMVEgucGRmIiwiaWF0IjoxNzczOTIyNjYyLCJleHAiOjE4MDU0NTg2NjJ9.hZiIEAc9pFxfCrlwYOmtGGaId--mFVZfouEMvO0Bwm4",
    },
    {
        "subject": "History",
        "storage_path": "Grade_9/9-HISTORY.pdf",
        "file_url": "https://qozmwqaaoyuolfzusefx.supabase.co/storage/v1/object/sign/mindup-resources/Grade_9/9-HISTORY.pdf?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV8zMTdjZDJjZC02NTQ4LTQzYjMtYWZkYy1kOWM1MjI0ODIzZTgiLCJhbGciOiJIUzI1NiJ9.eyJ1cmwiOiJtaW5kdXAtcmVzb3VyY2VzL0dyYWRlXzkvOS1ISVNUT1JZLnBkZiIsImlhdCI6MTc3MzkyMjY3NCwiZXhwIjoxODA1NDU4Njc0fQ.VkiGlOcSljt3hMjJUIcs4o7rduY5kPoQrLdLWlLk2C8M",
    },
    {
        "subject": "ICT",
        "storage_path": "Grade_9/9-ICT.pdf",
        "file_url": "https://qozmwqaaoyuolfzusefx.supabase.co/storage/v1/object/sign/mindup-resources/Grade_9/9-ICT.pdf?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV8zMTdjZDJjZC02NTQ4LTQzYjMtYWZkYy1kOWM1MjI0ODIzZTgiLCJhbGciOiJIUzI1NiJ9.eyJ1cmwiOiJtaW5kdXAtcmVzb3VyY2VzL0dyYWRlXzkvOS1JQ1QucGRmIiwiaWF0IjoxNzczOTIyNjgzLCJleHAiOjE4MDU0NTg2ODN9.aBstmhu7NKEnolUsa4_0dQLgHLEFlV7jZoElRgq9F4Q",
    },
    {
        "subject": "Science",
        "storage_path": "Grade_9/9-SCIENCE.pdf",
        "file_url": "https://qozmwqaaoyuolfzusefx.supabase.co/storage/v1/object/sign/mindup-resources/Grade_9/9-SCIENCE.pdf?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV8zMTdjZDJjZC02NTQ4LTQzYjMtYWZkYy1kOWM1MjI0ODIzZTgiLCJhbGciOiJIUzI1NiJ9.eyJ1cmwiOiJtaW5kdXAtcmVzb3VyY2VzL0dyYWRlXzkvOS1TQ0lFTkNFLnBkZiIsImlhdCI6MTc3MzkyMjY5OCwiZXhwIjoxODA1NDU4Njk4fQ.3dbH5i02A1e5ZeUQc5Y_rWltDlu3Cj8BhkebxXpSyRM",
    },
]


def main():
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("DB connection OK.\n")

    created, updated, errors = [], [], []

    with Session(engine) as db:
        # Find Grade 9
        grade = db.scalar(select(Grade).where(Grade.name.ilike("%9%")))
        if not grade:
            print("ERROR: Grade 9 not found in DB. Aborting.")
            sys.exit(1)
        print(f"Found grade: id={grade.id}  name='{grade.name}'\n")

        for book in GRADE9_BOOKS:
            subj_name = book["subject"]
            storage_path = book["storage_path"]
            file_url = book["file_url"]

            # Find subject (case-insensitive partial match)
            subject = db.scalar(
                select(Subject).where(
                    Subject.grade_id == grade.id,
                    Subject.name.ilike(f"%{subj_name}%"),
                )
            )
            if not subject:
                errors.append(f"Subject '{subj_name}' not found for Grade 9")
                print(f"  ✗ Subject '{subj_name}' not found — skipping")
                continue

            # Check if resource already exists (by storage_path OR subject+type)
            existing = db.scalar(
                select(Resource).where(
                    Resource.subject_id == subject.id,
                    Resource.type == "textbook",
                )
            )

            if existing:
                # Update both storage_path and file_url
                existing.storage_path = storage_path
                existing.file_url = file_url
                existing.is_active = True
                updated.append(subj_name)
                print(f"  UPDATE  {subj_name} (id={existing.id}) → {storage_path}")
            else:
                # Insert new record
                db.add(Resource(
                    subject_id=subject.id,
                    type="textbook",
                    title=f"Grade 9 {subj_name} Textbook",
                    description=f"Official Grade 9 {subj_name} textbook.",
                    storage_path=storage_path,
                    file_url=file_url,
                    is_active=True,
                ))
                created.append(subj_name)
                print(f"  CREATE  {subj_name} (subject_id={subject.id}) → {storage_path}")

        db.commit()

    print(f"\n{'─'*55}")
    print(f"  Created : {len(created)}  → {created}")
    print(f"  Updated : {len(updated)}  → {updated}")
    print(f"  Errors  : {len(errors)}")
    for e in errors:
        print(f"  ✗ {e}")


if __name__ == "__main__":
    main()
