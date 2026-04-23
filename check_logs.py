from app.db.session import SessionLocal
from app.models.ai_chat_log import AiChatLog
from app.models.student import Student
from app.models.subject import Subject
from app.models.topic import Topic
from app.models.district import District
from app.models.province import Province

db = SessionLocal()
try:
    logs = db.query(AiChatLog).order_by(AiChatLog.created_at.desc()).limit(5).all()
    for log in logs:
        print(f"--- LOG ID: {log.id} ---")
        print(f"QUESTION: {log.question}")
        print(f"RESPONSE:\n{log.response}")
        print(f"SESSION: {log.session_id}")
        print("-" * 20)
finally:
    db.close()
