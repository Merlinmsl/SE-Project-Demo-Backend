# Daily Streak Tracking (MIN-63) - Backend API Documentation

This module tracks daily activity and rewards consistent learning.

## Models
- **DailyStreak**: Tracks `current_streak`, `longest_streak`, and `last_completed_date`.
- **DailyCompletion**: Audit log of daily task completions.
- **Notification**: System used to alert users when streaks are broken.

## API Endpoints (`/api/v1/streaks`)

### 1. Get Current Streak
`GET /api/v1/streaks/current`
- **Response**: `StreakResponse`
- **Fields**: `current_streak` (int), `longest_streak` (int), `last_completed_date` (ISO date)

### 2. Complete Daily Task
`POST /api/v1/streaks/complete`
- **Request**: Optional JSON body `{ "tasks": { ... } }`
- **Response**: `StreakCompleteResponse`
- **Note**: This endpoint is idempotent. Calling it multiple times on the same day will only increment the streak once.

### 3. Streak History
`GET /api/v1/streaks/history`
- **Response**: List of `StreakHistoryItem`
- **Purpose**: Used for the calendar view to show which days the student was active.

## Notification Endpoints (`/api/v1/notifications`)
These endpoints manage alerts for broken streaks which are triggered by the Cron Job.

### 1. View Notifications
`GET /api/v1/notifications?unread_only=false`
- **Response**: List of `NotificationResponse`
- **Note**: Supports query parameter `unread_only` to filter read messages.

### 2. Mark Notification as Read
`POST /api/v1/notifications/{id}/read`
- **Response**: `MarkReadResponse` showing state success.

### 3. Mark All Notifications as Read
`POST /api/v1/notifications/read-all`
- **Response**: `MarkReadResponse` updating all user notifications.

## Cron Job: Streak Reset
To handle streaks that the student forgot to maintain, a cron job must be scheduled to run daily at 00:01 UTC.

**Script:** `cron_streak_reset.py`

**Deployment (Linux/Ubuntu):**
```bash
# Edit crontab
crontab -e

# Add this line to run every day at midnight UTC
0 0 * * * /path/to/venv/bin/python /path/to/project/cron_streak_reset.py >> /var/log/mindup_cron.log 2>&1
```

## Maintenance & Troubleshooting
- **Resetting a User:** Delete rows from `daily_streaks` and `daily_completions` for that `user_id`.
- **Concurrency:** The backend uses `FOR UPDATE` row-level locking to prevent race conditions during simultaneous completion requests.
