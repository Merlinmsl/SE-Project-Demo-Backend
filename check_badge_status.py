import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from app.models.student import Student
from app.models.badge import StudentBadge
from app.models.district import District
from app.models.province import Province
from app.models.grade import Grade

def check_medi():
    load_dotenv()
    engine = create_engine(os.getenv("DATABASE_URL"))
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    students = db.query(Student).all()
    for student in students:
        badge_count = db.query(StudentBadge).filter(StudentBadge.student_id == student.id).count()
        print(f"Student: username='{student.username}', full_name='{student.full_name}', has_badges={badge_count}")
        
    db.close()

if __name__ == "__main__":
    check_medi()
