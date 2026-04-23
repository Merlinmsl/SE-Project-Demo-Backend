from app.rag.chat_service import chat_service
from app.db.session import SessionLocal

# Import all models to ensure they are registered with SQLAlchemy
from app.models.student import Student
from app.models.subject import Subject
from app.models.topic import Topic
from app.models.district import District
from app.models.province import Province
from app.models.ai_chat_log import AiChatLog

def test_chat():
    question = "What is democracy?"
    # Test with "Civics" which should trigger the fallback to "9" in ChromaDB
    subject = "Civics" 
    
    print(f"Asking: '{question}' for subject: '{subject}'")
    
    # We pass None for DB to skip logging if we just want to test RAG
    # Or we can create one if needed for the full flow
    db = SessionLocal()
    try:
        response = chat_service.ask(
            question=question,
            subject=subject,
            db=db,
            student_id=1 # Just a dummy ID for testing
        )
        
        print("\n--- RESPONSE ---")
        print(f"Answer: {response['answer']}")
        print(f"Confidence: {response['confidence']}")
        print(f"Matched: {response['matched']}")
        print(f"Cited Pages: {response['cited_pages']}")
        print("\n--- SOURCES ---")
        for i, s in enumerate(response['sources']):
            print(f"[{i}] {s['citation']} (dist: {s['distance']})")
            
    finally:
        db.close()

if __name__ == "__main__":
    test_chat()
