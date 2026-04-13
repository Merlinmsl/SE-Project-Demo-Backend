"""
Seed: Top 10 District badge records (Rank 1 & Rank 2 logos).

Story : MIN-62  – Badge for Top 10 District Ranking
Commit: 2/11  (rank-2 URL added)

Inserts (or updates) the Badge row for 'Top 10 District' with:
  • image_url pointing to the badge asset in Supabase Storage
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

# ── Badge definitions ──────────────────────────────────────────────────────────

DISTRICT_BADGES = [
    {
        "name": "Top 10 District",
        "description": (
            "Awarded to students who rank in the Top 10 of their district leaderboard. "
            "Only the most dedicated learners earn this honour!"
        ),
        "image_url": (
            "https://qozmwqaaoyuolfzusefx.supabase.co/storage/v1/object/sign/"
            "mindup-resources/Badges/district_hero_01.png"
            "?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV8zMTdjZDJjZC02NTQ4LTQzYjMtYWZkYy1kOWM1MjI0ODIzZTgiLCJhbGciOiJIUzI1NiJ9"
            ".eyJ1cmwiOiJtaW5kdXAtcmVzb3VyY2VzL0JhZGdlcy9kaXN0cmljdF9oZXJvXzAxLnBuZyIsImlhdCI6MTc3NjAyNzk2MywiZXhwIjoxODA3NTYzOTYzfQ"
            ".n9Od3rErS54_08BmREnvrlI3FUYg01ulvGd6lOqHcR0"
        ),
        "category": "district",
    },
    {
        "name": "Top 10 District – Runner Up",
        "description": (
            "Awarded to students who hold the 2nd position in their district leaderboard. "
            "An outstanding achievement that shows true commitment!"
        ),
        "image_url": (
            "https://qozmwqaaoyuolfzusefx.supabase.co/storage/v1/object/sign/"
            "mindup-resources/Badges/district_hero_02.png"
            "?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV8zMTdjZDJjZC02NTQ4LTQzYjMtYWZkYy1kOWM1MjI0ODIzZTgiLCJhbGciOiJIUzI1NiJ9"
            ".eyJ1cmwiOiJtaW5kdXAtcmVzb3VyY2VzL0JhZGdlcy9kaXN0cmljdF9oZXJvXzAyLnBuZyIsImlhdCI6MTc3NjAzMDIxNiwiZXhwIjoxODA3NTY2MjE2fQ"
            ".GBynxdZ5W_E9m7V31BlhJLtznNv-tAQEdJ4EYv0WL8w"
        ),
        "category": "district",
    },
    {
        "name": "Top 10 District – Rank 3",
        "description": (
            "Awarded to students who hold the 3rd position in their district leaderboard. "
            "A spectacular achievement proving continuous effort!"
        ),
        "image_url": (
            "https://qozmwqaaoyuolfzusefx.supabase.co/storage/v1/object/sign/"
            "mindup-resources/Badges/district_hero_03.png"
            "?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV8zMTdjZDJjZC02NTQ4LTQzYjMtYWZkYy1kOWM1MjI0ODIzZTgiLCJhbGciOiJIUzI1NiJ9"
            ".eyJ1cmwiOiJtaW5kdXAtcmVzb3VyY2VzL0JhZGdlcy9kaXN0cmljdF9oZXJvXzAzLnBuZyIsImlhdCI6MTc3NjA5NDI0MywiZXhwIjoxODA3NjMwMjQzfQ"
            ".kHRZ84pTvBbVkSy5BI1gORkOUU7ZIEukW2lDZGwjEGw"
        ),
        "category": "district",
    },
    {
        "name": "Top 10 District – Rank 4",
        "description": (
            "Awarded to students who hold the 4th position in their district leaderboard. "
            "A superb rank indicating immense dedication and skill!"
        ),
        "image_url": (
            "https://qozmwqaaoyuolfzusefx.supabase.co/storage/v1/object/sign/"
            "mindup-resources/Badges/district_hero_04.png"
            "?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV8zMTdjZDJjZC02NTQ4LTQzYjMtYWZkYy1kOWM1MjI0ODIzZTgiLCJhbGciOiJIUzI1NiJ9"
            ".eyJ1cmwiOiJtaW5kdXAtcmVzb3VyY2VzL0JhZGdlcy9kaXN0cmljdF9oZXJvXzA0LnBuZyIsImlhdCI6MTc3NjEwMzY1MCwiZXhwIjoxODA3NjM5NjUwfQ"
            ".uuaGQfRXwBpGgcZnZumaZb_PN3IgrqXcuwkA3WuYCZg"
        ),
        "category": "district",
    },
    {
        "name": "Top 10 District – Rank 5",
        "description": (
            "Awarded to students who hold the 5th position in their district leaderboard. "
            "A fantastic display of perseverance!"
        ),
        "image_url": (
            "https://qozmwqaaoyuolfzusefx.supabase.co/storage/v1/object/sign/"
            "mindup-resources/Badges/district_hero_05.png"
            "?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV8zMTdjZDJjZC02NTQ4LTQzYjMtYWZkYy1kOWM1MjI0ODIzZTgiLCJhbGciOiJIUzI1NiJ9"
            ".eyJ1cmwiOiJtaW5kdXAtcmVzb3VyY2VzL0JhZGdlcy9kaXN0cmljdF9oZXJvXzA1LnBuZyIsImlhdCI6MTc3NjEwNDkwMCwiZXhwIjoxODA3NjQwOTAwfQ"
            ".OMrouq07aEW652sznWqycRQ7kd0O4z8bvGE_CeTsIWA"
        ),
        "category": "district",
    },
    {
        "name": "Top 10 District – Rank 6",
        "description": (
            "Awarded to students who hold the 6th position in their district leaderboard. "
            "An incredible milestone reflecting real progress!"
        ),
        "image_url": (
            "https://qozmwqaaoyuolfzusefx.supabase.co/storage/v1/object/sign/"
            "mindup-resources/Badges/district_hero_06.png"
            "?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV8zMTdjZDJjZC02NTQ4LTQzYjMtYWZkYy1kOWM1MjI0ODIzZTgiLCJhbGciOiJIUzI1NiJ9"
            ".eyJ1cmwiOiJtaW5kdXAtcmVzb3VyY2VzL0JhZGdlcy9kaXN0cmljdF9oZXJvXzA2LnBuZyIsImlhdCI6MTc3NjEwNjQxMSwiZXhwIjoxODA3NjQyNDExfQ"
            ".ahnw7mTwbQlK76ODs__aAlAxPJgOlQyZtHBq2xyCDR8"
        ),
        "category": "district",
    },
]


def seed() -> None:
    with engine.begin() as conn:
        for badge in DISTRICT_BADGES:
            existing = conn.execute(
                text("SELECT id FROM badges WHERE name = :name"),
                {"name": badge["name"]},
            ).fetchone()

            if existing:
                conn.execute(
                    text("""
                        UPDATE badges
                        SET description = :desc,
                            image_url   = :image_url,
                            category    = :category
                        WHERE name = :name
                    """),
                    {
                        "desc":      badge["description"],
                        "image_url": badge["image_url"],
                        "category":  badge["category"],
                        "name":      badge["name"],
                    },
                )
                print(f"[SEED] ✓ Updated badge: '{badge['name']}' (id={existing[0]})")
            else:
                result = conn.execute(
                    text("""
                        INSERT INTO badges (name, description, image_url, category)
                        VALUES (:name, :desc, :image_url, :category)
                        RETURNING id
                    """),
                    {
                        "name":      badge["name"],
                        "desc":      badge["description"],
                        "image_url": badge["image_url"],
                        "category":  badge["category"],
                    },
                )
                new_id = result.fetchone()[0]
                print(f"[SEED] ✓ Inserted badge: '{badge['name']}' (id={new_id})")


if __name__ == "__main__":
    seed()
