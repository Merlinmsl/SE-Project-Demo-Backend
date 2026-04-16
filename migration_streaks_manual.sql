-- ============================================================
-- MindUp — Daily Streak Tracking (MIN-63 / MIN-291)
-- Manual SQL Migration — run this in the Supabase SQL Editor
-- Dashboard → SQL Editor → paste and press Run
-- ============================================================

-- ------------------------------------------------------------
-- 1. daily_streaks
--    One row per student. Holds the live streak state.
-- ------------------------------------------------------------
-- Add missing timestamp columns if the table was created previously without them
ALTER TABLE daily_streaks ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE daily_streaks ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE TABLE IF NOT EXISTS daily_streaks (
    id               BIGSERIAL PRIMARY KEY,
    user_id          BIGINT NOT NULL
                         UNIQUE
                         REFERENCES students(id) ON DELETE CASCADE,
    current_streak   INTEGER NOT NULL DEFAULT 0,
    longest_streak   INTEGER NOT NULL DEFAULT 0,
    last_completed_date DATE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for fast look-ups inside the streak service
CREATE INDEX IF NOT EXISTS ix_daily_streaks_user_id
    ON daily_streaks(user_id);

CREATE INDEX IF NOT EXISTS ix_daily_streaks_last_completed_date
    ON daily_streaks(last_completed_date);

-- ------------------------------------------------------------
-- 2. daily_completions
--    Append-only audit log — one row per completion event.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS daily_completions (
    id               BIGSERIAL PRIMARY KEY,
    user_id          BIGINT NOT NULL
                         REFERENCES students(id) ON DELETE CASCADE,
    completed_date   DATE NOT NULL,
    tasks_completed  JSONB         -- flexible audit payload (nullable)
);

CREATE INDEX IF NOT EXISTS ix_daily_completions_user_id
    ON daily_completions(user_id);

CREATE INDEX IF NOT EXISTS ix_daily_completions_completed_date
    ON daily_completions(completed_date);

-- ------------------------------------------------------------
-- 3. notifications
--    In-app notification store — used by cron_streak_reset.py
--    to alert students when their streak is broken.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL
                    REFERENCES students(id) ON DELETE CASCADE,
    title       VARCHAR(255) NOT NULL,
    message     TEXT NOT NULL,
    is_read     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_notifications_user_id
    ON notifications(user_id);

-- ------------------------------------------------------------
-- 4. Seed — one sample row so backend tests can run immediately.
--    Uses the first student in the table; safe to re-run (ON CONFLICT).
-- ------------------------------------------------------------
DO $$
DECLARE
    v_student_id BIGINT;
BEGIN
    SELECT id INTO v_student_id FROM students LIMIT 1;

    IF v_student_id IS NOT NULL THEN
        INSERT INTO daily_streaks
            (user_id, current_streak, longest_streak, last_completed_date)
        VALUES
            (v_student_id, 3, 5, CURRENT_DATE - INTERVAL '1 day')
        ON CONFLICT (user_id) DO NOTHING;

        INSERT INTO daily_completions
            (user_id, completed_date, tasks_completed)
        VALUES
            (v_student_id, CURRENT_DATE - INTERVAL '1 day', '{"tasks": 2}')
        ON CONFLICT DO NOTHING;

        RAISE NOTICE 'Seed data inserted for student id=%', v_student_id;
    ELSE
        RAISE NOTICE 'No students found — skipping seed.';
    END IF;
END;
$$;

-- ============================================================
-- Verification — run after the script above to confirm success
-- ============================================================
SELECT 'daily_streaks'    AS table_name, COUNT(*) AS rows FROM daily_streaks
UNION ALL
SELECT 'daily_completions',              COUNT(*)          FROM daily_completions
UNION ALL
SELECT 'notifications',                  COUNT(*)          FROM notifications;
