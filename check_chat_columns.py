from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()
result = db.execute(text(
    "SELECT column_name, data_type FROM information_schema.columns "
    "WHERE table_name = 'ai_chat_logs' ORDER BY ordinal_position"
))
for row in result:
    print(row[0], "-", row[1])
db.close()
