"""
Seed: Top 10 District badge record (Rank 1 logo).

Story : MIN-62  – Badge for Top 10 District Ranking
Commit: 1/11

Inserts (or updates) the Badge row for 'Top 10 District' with:
  • image_url pointing to the Rank-1 district hero badge in Supabase Storage
  • category = 'district'

The script is idempotent – running it multiple times will not create duplicates.

Usage
-----
    python seed_district_badge.py
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in the environment / .env file")

engine = create_engine(DATABASE_URL)

# ── Badge metadata ─────────────────────────────────────────────────────────────

BADGE_NAME = "Top 10 District"
BADGE_DESCRIPTION = (
    "Awarded to students who rank in the Top 10 of their district leaderboard. "
    "Only the most dedicated learners earn this honour!"
)
BADGE_IMAGE_URL = (
    "https://qozmwqaaoyuolfzusefx.supabase.co/storage/v1/object/sign/"
    "mindup-resources/Badges/district_hero_01.png"
    "?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV8zMTdjZDJjZC02NTQ4LTQzYjMtYWZkYy1kOWM1MjI0ODIzZTgiLCJhbGciOiJIUzI1NiJ9"
    ".eyJ1cmwiOiJtaW5kdXAtcmVzb3VyY2VzL0JhZGdlcy9kaXN0cmljdF9oZXJvXzAxLnBuZyIsImlhdCI6MTc3NjAyNzk2MywiZXhwIjoxODA3NTYzOTYzfQ"
    ".n9Od3rErS54_08BmREnvrlI3FUYg01ulvGd6lOqHcR0"
)
BADGE_CATEGORY = "district"


def seed() -> None:
    with engine.begin() as conn:
        # Check if badge already exists
        existing = conn.execute(
            text("SELECT id FROM badges WHERE name = :name"),
            {"name": BADGE_NAME},
        ).fetchone()

        if existing:
            # Update to ensure image_url and category are set correctly
            conn.execute(
                text("""
                    UPDATE badges
                    SET description = :desc,
                        image_url   = :image_url,
                        category    = :category
                    WHERE name = :name
                """),
                {
                    "desc":      BADGE_DESCRIPTION,
                    "image_url": BADGE_IMAGE_URL,
                    "category":  BADGE_CATEGORY,
                    "name":      BADGE_NAME,
                },
            )
            print(f"[SEED] ✓ Updated existing badge: '{BADGE_NAME}' (id={existing[0]})")
        else:
            result = conn.execute(
                text("""
                    INSERT INTO badges (name, description, image_url, category)
                    VALUES (:name, :desc, :image_url, :category)
                    RETURNING id
                """),
                {
                    "name":      BADGE_NAME,
                    "desc":      BADGE_DESCRIPTION,
                    "image_url": BADGE_IMAGE_URL,
                    "category":  BADGE_CATEGORY,
                },
            )
            new_id = result.fetchone()[0]
            print(f"[SEED] ✓ Inserted new badge: '{BADGE_NAME}' (id={new_id})")


if __name__ == "__main__":
    seed()
