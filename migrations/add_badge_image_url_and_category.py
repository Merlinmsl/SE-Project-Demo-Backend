"""
Migration: add image_url and category columns to badges table.

Story : MIN-62  – Badge for Top 10 District Ranking
Commit: 1/11

UP   – adds image_url (TEXT) and category (VARCHAR 100) to `badges`.
DOWN – drops those two columns (reversible).

Usage
-----
    # apply
    python migrations/add_badge_image_url_and_category.py up

    # rollback
    python migrations/add_badge_image_url_and_category.py down
"""

import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in the environment / .env file")

engine = create_engine(DATABASE_URL)


def up() -> None:
    """Apply migration: add image_url and category to badges."""
    with engine.begin() as conn:
        # Add image_url column (idempotent: skip if already exists)
        conn.execute(text("""
            ALTER TABLE badges
            ADD COLUMN IF NOT EXISTS image_url TEXT;
        """))

        # Add category column (idempotent: skip if already exists)
        conn.execute(text("""
            ALTER TABLE badges
            ADD COLUMN IF NOT EXISTS category VARCHAR(100);
        """))

    print("[UP] ✓ Added image_url and category columns to badges table.")


def down() -> None:
    """Rollback migration: drop image_url and category from badges."""
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE badges DROP COLUMN IF EXISTS image_url;"))
        conn.execute(text("ALTER TABLE badges DROP COLUMN IF EXISTS category;"))

    print("[DOWN] ✓ Dropped image_url and category columns from badges table.")


if __name__ == "__main__":
    direction = sys.argv[1] if len(sys.argv) > 1 else "up"
    if direction == "up":
        up()
    elif direction == "down":
        down()
    else:
        print(f"Unknown direction '{direction}'. Use 'up' or 'down'.")
        sys.exit(1)
