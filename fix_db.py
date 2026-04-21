import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
db_url = os.getenv("DATABASE_URI") or os.getenv("DATABASE_URL")

engine = create_engine(db_url, connect_args={"connect_timeout": 15})

with engine.begin() as conn:
    print("Adding created_at...")
    conn.execute(text("ALTER TABLE daily_streaks ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"))
    
    print("Adding updated_at...")
    conn.execute(text("ALTER TABLE daily_streaks ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"))

print("Database fixed successfully!")
