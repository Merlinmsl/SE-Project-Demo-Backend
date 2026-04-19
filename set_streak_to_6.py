import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from app.models.study_streak import StudyStreak
from app.models.student import Student
from app.models.district import District
from app.models.province import Province
from app.models.grade import Grade
from datetime import date, timedelta

def override_streaks():
    load_dotenv()
    engine = create_engine(os.getenv("DATABASE_URL"))
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    yesterday = date.today() - timedelta(days=1)
    students = db.query(Student).all()
    count = 0
    
    for student in students:
        streak = db.query(StudyStreak).filter(StudyStreak.student_id == student.id).first()
        if not streak:
            streak = StudyStreak(student_id=student.id)
            db.add(streak)
        
        # Set streak to 6, and pretend the user was last active yesterday
        streak.current_streak = 6
        streak.last_activity_date = yesterday
        
        # ALSO: if they already have the badge, delete it so we can test the award logic fresh!
        from app.models.badge import StudentBadge
        db.query(StudentBadge).filter(StudentBadge.student_id == student.id).delete()
        
        count += 1
        
    db.commit()
    db.close()
    print(f"✅ Success! Set {count} students' streak to 6 days (last active: yesterday).")
    print("✅ Cleared any existing 7-day badges for a fresh test.")
    print("\n👉 Go to the frontend and COMPLETE A QUIZ to trigger the 7-day streak badge!")

if __name__ == "__main__":
    override_streaks()
