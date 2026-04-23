from app.rag.chat_service import chat_service
from app.db.session import SessionLocal

# Import all models to ensure they are registered with SQLAlchemy
from app.models.student import Student
from app.models.subject import Subject
from app.models.topic import Topic
from app.models.district import District
from app.models.province import Province
from app.models.ai_chat_log import AiChatLog

def debug_chat():
    question = "What is democracy?"
    subject = "Civics"
    
    print(f"DEBUG: Asking '{question}' for subject: '{subject}'")
    
    db = SessionLocal()
    try:
        response = chat_service.ask(
            question=question,
            subject=subject,
            db=db,
            student_id=1
        )
        # The debug prints I added to chat_service.py will show up in the terminal
    finally:
        db.close()

if __name__ == "__main__":
    debug_chat()
