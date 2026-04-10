import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

def test_db_schema():
    load_dotenv()
    engine = create_engine(os.getenv("DATABASE_URL"))
    with engine.connect() as conn:
        try:
            # Let's try querying badges to see if image_url exists
            result = conn.execute(text("SELECT id, name, image_url FROM badges LIMIT 1"))
            print("DB Schema looks good, image_url exists.")
        except Exception as e:
            print("DB Schema error:", e)

if __name__ == "__main__":
    test_db_schema()
