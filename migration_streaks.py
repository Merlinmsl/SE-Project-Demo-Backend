import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from app.db.base import Base
from app.models.student import Student # Need to import to resolve FKs
from app.models.daily_streak import DailyStreak
from app.models.daily_completion import DailyCompletion
import datetime

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("Error: DATABASE_URL not found in environment.")
    sys.exit(1)

engine = create_engine(DATABASE_URL)

def up():
    print("Running UP migration: Creating streak tables...")
    Base.metadata.create_all(bind=engine, tables=[DailyStreak.__table__, DailyCompletion.__table__])
    print("Tables created.")
    
    # Adding indexes
    print("Indexes on user_id and last_completed_date are defined in models.")
    
    # Seed sample data
    print("Seeding sample data for testing...")
    with engine.connect() as conn:
        student_check = conn.execute(text("SELECT id FROM students LIMIT 1")).fetchone()
        if student_check:
            student_id = student_check[0]
            # Seed daily_streaks
            conn.execute(
                text("""
                INSERT INTO daily_streaks (user_id, current_streak, longest_streak, last_completed_date)
                VALUES (:user_id, 3, 5, :last_date)
                ON CONFLICT DO NOTHING
                """),
                {"user_id": student_id, "last_date": datetime.date.today() - datetime.timedelta(days=1)}
            )
            # Seed daily_completions
            conn.execute(
                text("""
                INSERT INTO daily_completions (user_id, completed_date, tasks_completed)
                VALUES (:user_id, :last_date, '{"tasks": 2}')
                """),
                {"user_id": student_id, "last_date": datetime.date.today() - datetime.timedelta(days=1)}
            )
            conn.commit()
            print(f"Sample data seeded for student ID={student_id}.")
        else:
            print("No student found. Skipping seed.")
            
def down():
    print("Running DOWN migration: Dropping streak tables...")
    Base.metadata.drop_all(bind=engine, tables=[DailyStreak.__table__, DailyCompletion.__table__])
    print("Tables dropped.")

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else 'up'
    if action == 'down':
        down()
    else:
        up()
