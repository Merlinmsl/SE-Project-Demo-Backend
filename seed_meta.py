"""
seed_meta.py — Seeds all Sri Lanka provinces, districts, and grades (6–11)
into the database. Safe to run multiple times (uses ON CONFLICT DO NOTHING).

Usage:
    python seed_meta.py
"""
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL env variable not set.")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()

# ─── Provinces ────────────────────────────────────────────────────────────────
provinces = [
    (1, "Central"),
    (2, "Eastern"),
    (3, "North Central"),
    (4, "Northern"),
    (5, "North Western"),
    (6, "Sabaragamuwa"),
    (7, "Southern"),
    (8, "Uva"),
    (9, "Western"),
]

# ─── Districts (province_id, district_name) ───────────────────────────────────
districts = [
    # Central
    (1,  1, "Kandy"),
    (2,  1, "Matale"),
    (3,  1, "Nuwara Eliya"),
    # Eastern
    (4,  2, "Ampara"),
    (5,  2, "Batticaloa"),
    (6,  2, "Trincomalee"),
    # North Central
    (7,  3, "Anuradhapura"),
    (8,  3, "Polonnaruwa"),
    # Northern
    (9,  4, "Jaffna"),
    (10, 4, "Kilinochchi"),
    (11, 4, "Mannar"),
    (12, 4, "Mullaitivu"),
    (13, 4, "Vavuniya"),
    # North Western
    (14, 5, "Kurunegala"),
    (15, 5, "Puttalam"),
    # Sabaragamuwa
    (16, 6, "Kegalle"),
    (17, 6, "Ratnapura"),
    # Southern
    (18, 7, "Galle"),
    (19, 7, "Hambantota"),
    (20, 7, "Matara"),
    # Uva
    (21, 8, "Badulla"),
    (22, 8, "Monaragala"),
    # Western
    (23, 9, "Colombo"),
    (24, 9, "Gampaha"),
    (25, 9, "Kalutara"),
]

# ─── Grades ───────────────────────────────────────────────────────────────────
grades = [
    (1, "Grade 6"),
    (2, "Grade 7"),
    (3, "Grade 8"),
    (4, "Grade 9"),
    (5, "Grade 10"),
    (6, "Grade 11"),
]

print("=" * 60)
print("Seeding provinces, districts, and grades...")
print("=" * 60)

try:
    # Provinces
    for pid, name in provinces:
        db.execute(text(
            "INSERT INTO provinces (id, name) VALUES (:id, :name) ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name"
        ), {"id": pid, "name": name})
        print(f"  Province: {name}")

    # Districts
    for did, pid, name in districts:
        db.execute(text(
            "INSERT INTO districts (id, province_id, name) VALUES (:id, :pid, :name) ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, province_id=EXCLUDED.province_id"
        ), {"id": did, "pid": pid, "name": name})
        print(f"  District: {name}")

    # Grades
    for gid, name in grades:
        db.execute(text(
            "INSERT INTO grades (id, name, is_active) VALUES (:id, :name, true) ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, is_active=true"
        ), {"id": gid, "name": name})
        print(f"  Grade: {name}")

    db.commit()
    print("\n✅ All meta data seeded successfully!")
    print(f"   {len(provinces)} provinces, {len(districts)} districts, {len(grades)} grades")

except Exception as e:
    db.rollback()
    print(f"\n❌ Error seeding data: {e}")
    sys.exit(1)
finally:
    db.close()
