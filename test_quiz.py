"""Quick test: insert a student and start a quiz via API."""
import os, json
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import requests

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))
db = sessionmaker(bind=engine)()

# Insert a test student
db.execute(text("INSERT INTO students (id, username, full_name, grade_id) VALUES (1, 'test_student', 'Test Student', 1) ON CONFLICT DO NOTHING"))
db.commit()
db.close()
print("Student inserted!")

# Test: start a quiz in TERM mode
print("\n--- TERM MODE TEST ---")
resp = requests.post("http://localhost:8000/api/v1/quiz/start", json={
    "student_id": 1,
    "subject_id": 1,
    "mode": "term"
})
print(f"Status: {resp.status_code}")
data = resp.json()
if resp.status_code == 201:
    print(f"Session ID: {data['session_id']}")
    print(f"Profile: {data['difficulty_profile']}")
    print(f"Total Questions: {data['total_questions']}")
    for q in data["questions"]:
        has_is_correct = any("is_correct" in str(o) for o in q["options"])
        print(f"  Q{q['id']} [{q['difficulty']}]: {q['question_text'][:60]}... ({len(q['options'])} opts, is_correct_exposed={has_is_correct})")
else:
    print(json.dumps(data, indent=2))

# Test: start a quiz in TOPIC mode (Algebra, topic_id=1)
print("\n--- TOPIC MODE TEST ---")
resp2 = requests.post("http://localhost:8000/api/v1/quiz/start", json={
    "student_id": 1,
    "subject_id": 1,
    "mode": "topic",
    "topic_id": 1
})
print(f"Status: {resp2.status_code}")
data2 = resp2.json()
if resp2.status_code == 201:
    print(f"Session ID: {data2['session_id']}")
    print(f"Profile: {data2['difficulty_profile']}")
    print(f"Total Questions: {data2['total_questions']}")
    for q in data2["questions"]:
        print(f"  Q{q['id']} [{q['difficulty']}]: {q['question_text'][:60]}...")
else:
    print(json.dumps(data2, indent=2))
