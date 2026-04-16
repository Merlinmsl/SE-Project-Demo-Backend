import os
import sys
import datetime
import subprocess
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Use utf-8 for output to avoid Windows console errors
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

def run_integration_test():
    print("STARTING End-to-End Streak Integration Test...")
    
    with engine.connect() as conn:
        # 1. Pick a test student
        student = conn.execute(text("SELECT id, username FROM students LIMIT 1")).fetchone()
        if not student:
            print("ERROR: No students found in database to test with.")
            return
        
        student_id = student[0]
        print(f"Testing with student: {student[1]} (ID: {student_id})")

        # 2. Reset existing streak for clean start
        conn.execute(text("DELETE FROM daily_streaks WHERE user_id = :uid"), {"uid": student_id})
        conn.execute(text("DELETE FROM daily_completions WHERE user_id = :uid"), {"uid": student_id})
        conn.commit()
        print("Cleaned up existing streak data.")

        # 3. Simulate Day 1 Completion
        print("\nSimulating Day 1 Completion...")
        from app.services.streak_service import StreakService
        
        with Session(engine) as session:
            res = StreakService.complete_daily_tasks(session, student_id, {"task": "Integration Test Day 1"})
            print(f"Day 1 Success: Current Streak = {res['current_streak']}")
            if res['current_streak'] != 1:
                print(f"Assertion Failed: Expected 1, got {res['current_streak']}")
                sys.exit(1)

        # 4. Simulate Passing of Time
        print("\nMoving the clock... pretending today's work was actually done YESTERDAY.")
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        conn.execute(
            text("UPDATE daily_streaks SET last_completed_date = :d WHERE user_id = :uid"),
            {"d": yesterday, "uid": student_id}
        )
        conn.execute(
            text("UPDATE daily_completions SET completed_date = :d WHERE user_id = :uid"),
            {"d": yesterday, "uid": student_id}
        )
        conn.commit()

        # 5. Simulate Day 2 Completion
        print("Simulating Day 2 Completion...")
        with Session(engine) as session:
            res = StreakService.complete_daily_tasks(session, student_id, {"task": "Integration Test Day 2"})
            print(f"Day 2 Success: Current Streak = {res['current_streak']}")
            if res['current_streak'] != 2:
                print(f"Assertion Failed: Expected 2, got {res['current_streak']}")
                sys.exit(1)

        # 6. Test the Broken Streak Cron
        print("\nTesting Streak Break...")
        # Move date back to 3 days ago
        three_days_ago = datetime.date.today() - datetime.timedelta(days=3)
        conn.execute(
            text("UPDATE daily_streaks SET last_completed_date = :d WHERE user_id = :uid"),
            {"d": three_days_ago, "uid": student_id}
        )
        conn.commit()
        
        print("Running Cron Job (cron_streak_reset.py)...")
        subprocess.run(["python", "cron_streak_reset.py"], check=True)
        
        # Verify result
        streak = conn.execute(text("SELECT current_streak FROM daily_streaks WHERE user_id = :uid"), {"uid": student_id}).fetchone()
        notif = conn.execute(text("SELECT title FROM notifications WHERE user_id = :uid ORDER BY created_at DESC LIMIT 1"), {"uid": student_id}).fetchone()
        
        print(f"Result: Current Streak = {streak[0]}")
        if notif:
            print(f"Notification Generated: {notif[0]}")
        else:
            print("ERROR: No notification generated.")
            sys.exit(1)
        
        if streak[0] != 0:
            print(f"Assertion Failed: Expected streak 0, got {streak[0]}")
            sys.exit(1)

    print("\nALL INTEGRATION TESTS PASSED!")

if __name__ == "__main__":
    run_integration_test()
