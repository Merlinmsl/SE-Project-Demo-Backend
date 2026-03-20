import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv('DATABASE_URL')
print("Testing DB Connection:", db_url)

try:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        print("Connection successful.")
except Exception as e:
    print("Connection failed:", e)
