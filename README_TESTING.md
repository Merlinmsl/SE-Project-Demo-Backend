# Testing Guide (Swagger + Postman)

This guide lets you test **each endpoint** in this backend workspace even if:
- you don't have your teammate's Clerk frontend code yet
- you don't have PDFs uploaded to Supabase Storage yet

---

## A) Start the server

1) Create `.env`:
```bash
cp .env.example .env
```

2) Set these values in `.env` for now:
- `AUTH_MODE=dev`
- `CLERK_MODE=mock`
- `STORAGE_MODE=mock`

3) Make sure your local Postgres is running and `.env` points to it via `DATABASE_URL`.

If you need a fresh DB quickly, you can run the minimal schema+seed scripts in `sql/` (optional):
```bash
# example (psql)
psql -U postgres -d mindup -f sql/schema_min.sql
psql -U postgres -d mindup -f sql/seed_provinces_districts.sql
psql -U postgres -d mindup -f sql/seed_demo_grade_subjects_avatars.sql
```

4) Install + run:
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open Swagger:
- http://localhost:8000/docs

---

## B) Common headers for Swagger tests

For **student endpoints** (most endpoints):
- `X-Clerk-User-Id: user_123`
- `X-Email: student@example.com`

> Why X-Email? In production, email comes from Clerk token.
> In `AUTH_MODE=dev` we simulate that via `X-Email`.

For **admin endpoint**:
- `X-Admin-Api-Key: change-me`

---

## C) Test flow in order (recommended)

### 1) Meta endpoints (province-first dropdown)
1. `GET /api/v1/meta/provinces`
   - Expect: list of provinces

2. Pick a province id (example: `1`), then:
   `GET /api/v1/meta/districts?province_id=1`
   - Expect: only districts from that province

3. `GET /api/v1/meta/grades`
4. `GET /api/v1/meta/avatars`

---

### 2) First login behavior (MIN-13)
Call:
- `GET /api/v1/me/profile`

Expected:
- A student row is created if missing
- `username` will be like `pending_xxxxxxxx`
- `profile_completed=false`

---

### 3) Complete onboarding (MIN-13 + MIN-14 + MIN-16)
Call:
- `POST /api/v1/me/onboarding`

Example body:
```json
{
  "full_name": "Test Student",
  "username": "test_student_01",
  "gender": "Male",
  "grade_id": 1,
  "province_id": 1,
  "district_id": 1,
  "avatar_id": 1,
  "subject_ids": [1, 2]
}
```

Expected:
- `profile_completed=true`
- `gender` appears in response (from Clerk metadata mock store)
- Province/district mismatch gives 400

> Mock Clerk metadata is saved in `.mock_clerk_store.json` so it survives uvicorn restarts.

---

### 4) Confirm dashboard-unlock condition (MIN-16)
Call again:
- `GET /api/v1/me/profile`

Expected:
- `profile_completed=true`
- This is what your React dashboard checks to remove the glass overlay.

---

### 5) Subjects (MIN-18)
1. `GET /api/v1/subjects/available`
   - uses student's grade if grade_id query not passed

2. `PUT /api/v1/me/subjects`
```json
{"subject_ids":[1,2]}
```

3. `GET /api/v1/me/subjects`

Expected:
- selected subjects returned

---

### 6) Resources (MIN-18)

#### If your DB already contains resources
Call:
- `GET /api/v1/resources?subject_id=1&type=textbook`

Expected:
- 403 if subject_id not selected by student
- 403 if profile not completed
- if `storage_path` exists, you get `view_url` (signed or mock)

#### If you DON'T have any resources rows yet
Insert one row manually in pgAdmin (example):
```sql
insert into resources (subject_id, type, title, description, storage_path, is_active)
values (1, 'textbook', 'Grade 9 English Textbook', 'Sample', 'english/grade9/textbook1.pdf', true);
```

Then call the same endpoint again.

---

### 7) Admin student count (MIN-17)
Call:
- `GET /api/v1/admin/stats/student-count`
Header:
- `X-Admin-Api-Key: change-me`

Expected:
- `{ "count": <number> }`

---

## D) Switching to real Supabase signed URLs later

When you have a private bucket and uploaded PDFs:
1) Set in `.env`:
- `STORAGE_MODE=supabase`
- `SUPABASE_URL=https://<project>.supabase.co`
- `SUPABASE_SERVICE_ROLE_KEY=<service role key>`
- `SUPABASE_STORAGE_BUCKET=<your bucket name>`

2) Ensure each resource row has:
- `storage_path` like: `english/grade9/textbook1.pdf`

Now `/api/v1/resources` will return real signed links.

---

## E) Switching to real Clerk metadata later

When you get Clerk secret key:
1) Set:
- `CLERK_MODE=live`
- `CLERK_SECRET_KEY=sk_live_...`

Now onboarding/update will write `public_metadata.gender` into Clerk for real.
