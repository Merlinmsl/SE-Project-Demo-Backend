import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
db_url = os.getenv("DATABASE_URI") or os.getenv("DATABASE_URL")
engine = create_engine(db_url, connect_args={"connect_timeout": 15})

with engine.begin() as conn:
    print(conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'daily_streaks'")).fetchall())
