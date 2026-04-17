import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

def break_streak():
    load_dotenv()
    db_url = os.getenv("DATABASE_URI") or os.getenv("DATABASE_URL")
    if not db_url:
        print("Required DATABASE_URL. Exiting.")
        return

    engine = create_engine(db_url, connect_args={"connect_timeout": 15})
    
    with engine.begin() as conn:
        two_days_ago = (datetime.now(timezone.utc) - timedelta(days=2)).date()
        
        # Shift the completed date backwards to simulate the user missing a day
        conn.execute(
            text("UPDATE daily_streaks SET last_completed_date = :date WHERE current_streak > 0"), 
            {"date": two_days_ago}
        )
        print(f"Time traveled! Set last_completed_date to {two_days_ago}")

if __name__ == "__main__":
    break_streak()
