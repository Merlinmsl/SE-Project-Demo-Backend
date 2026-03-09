"""
All-in-one seed: inserts prerequisites via DB + questions via API.
No manual SQL needed.
"""
import json
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import requests

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
API_URL = "http://localhost:8000/api/v1/admin/questions/"

# --- Step 1: Insert prerequisites directly into DB ---
print("=" * 60)
print("Step 1: Inserting prerequisite data into DB...")
print("=" * 60)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()

prereq_sql = [
    "INSERT INTO provinces (id, name) VALUES (1, 'Western') ON CONFLICT DO NOTHING;",
    "INSERT INTO districts (id, province_id, name) VALUES (1, 1, 'Colombo') ON CONFLICT DO NOTHING;",
    "INSERT INTO admins (id, username, password, display_name) VALUES (1, 'admin1', 'hashed_password', 'Admin One') ON CONFLICT DO NOTHING;",
    "INSERT INTO grades (id, name) VALUES (1, 'Grade 10') ON CONFLICT DO NOTHING;",
    "INSERT INTO subjects (id, grade_id, name) VALUES (1, 1, 'Mathematics') ON CONFLICT DO NOTHING;",
    "INSERT INTO topics (id, subject_id, name) VALUES (1, 1, 'Algebra') ON CONFLICT DO NOTHING;",
    "INSERT INTO topics (id, subject_id, name) VALUES (2, 1, 'Geometry') ON CONFLICT DO NOTHING;",
    "INSERT INTO topics (id, subject_id, name) VALUES (3, 1, 'Number Theory') ON CONFLICT DO NOTHING;",
]

try:
    for sql in prereq_sql:
        db.execute(text(sql))
        print(f"  OK: {sql[:60]}...")
    db.commit()
    print("Prerequisites inserted successfully!\n")
except Exception as e:
    db.rollback()
    print(f"Error inserting prerequisites: {e}")
    sys.exit(1)
finally:
    db.close()

# --- Step 2: Insert questions via API ---
print("=" * 60)
print("Step 2: Inserting questions via API...")
print("=" * 60)

with open("seed_questions.json", "r", encoding="utf-8") as f:
    data = json.load(f)

questions = data["questions"]
success = 0
failed = 0

for i, q in enumerate(questions, 1):
    try:
        resp = requests.post(API_URL, json=q, timeout=10)
        if resp.status_code == 201:
            result = resp.json()
            print(f"  [{i}/{len(questions)}] Created: {result['question_text'][:50]}... (id={result['id']}, xp={result['xp_value']})")
            success += 1
        else:
            print(f"  [{i}/{len(questions)}] FAILED: {q['question_text'][:50]}...")
            print(f"     Status: {resp.status_code}, Error: {resp.text[:200]}")
            failed += 1
    except requests.exceptions.ConnectionError:
        print(f"\nERROR: Cannot connect to API at {API_URL}")
        print("Make sure the server is running: python -m uvicorn app.main:app --reload --port 8000")
        sys.exit(1)

print(f"\n{'=' * 60}")
print(f"Done! {success} created, {failed} failed, {len(questions)} total")
print(f"{'=' * 60}")
