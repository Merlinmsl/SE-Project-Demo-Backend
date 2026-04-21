import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

def prepare_db_for_badges():
    load_dotenv()
    engine = create_engine(os.getenv("DATABASE_URL"))
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE badges ADD COLUMN IF NOT EXISTS image_url TEXT;"))
            conn.commit()
            print("Successfully added image_url column to badges table.")
        except Exception as e:
            # Might fail if column already exists (or syntax difference), but usually IF NOT EXISTS handles it.
            print("Alter table note:", e)

    with engine.connect() as conn:
        try:
            # Seed the badge if it's missing
            conn.execute(text("""
                INSERT INTO badges (name, description, image_url) 
                VALUES ('7-Day Streak', 'Awarded for completing quizzes 7 days in a row!', 'https://example.com/streak7.png')
                ON CONFLICT (name) DO UPDATE SET image_url = EXCLUDED.image_url;
            """))
            conn.commit()
            print("Successfully seeded the 7-Day Streak badge.")
        except Exception as e:
            print("Seed error:", e)

if __name__ == "__main__":
    prepare_db_for_badges()
