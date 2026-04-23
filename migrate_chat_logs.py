"""
Migration: Add missing columns to ai_chat_logs table.
Run once: python migrate_chat_logs.py
"""
from app.db.session import SessionLocal
from sqlalchemy import text

MIGRATION_SQL = """
ALTER TABLE ai_chat_logs
    ADD COLUMN IF NOT EXISTS topic_id INTEGER REFERENCES topics(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS session_id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS matched INTEGER DEFAULT 1;
"""

db = SessionLocal()
try:
    db.execute(text(MIGRATION_SQL))
    db.commit()
    print("Migration applied successfully.")
    
    # Verify
    result = db.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'ai_chat_logs' ORDER BY ordinal_position"
    ))
    print("Current columns:", [row[0] for row in result])
except Exception as e:
    db.rollback()
    print("Migration failed:", e)
finally:
    db.close()
