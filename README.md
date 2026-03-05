# Sprint1BackendTest_ready_v3 (FastAPI + SQLAlchemy + psycopg2)

This is a **local backend test workspace** for your Sprint-1 user stories **MIN-13 → MIN-18**:
- MIN-13 Complete profile after first login
- MIN-14 Province-first dropdown + validate district belongs to province (province auto-derivable from district)
- MIN-15 Edit student profile
- MIN-16 Mandatory profile completion before using dashboard/resources
- MIN-17 Admin view student count (Sprint-1: API key protected)
- MIN-18 Select subjects + access subject resources (PDF view links)

> ✅ DB schema is **NOT changed**.  
> ✅ Gender is stored in **Clerk public metadata** (no DB column required).  
> ✅ Resources use **Supabase Storage private bucket** (signed URLs), with a **mock mode** so you can test now.

---

## 1) Profile completion rule (your final decision: **every field**)

`profile_completed=true` ONLY when ALL are present:

**DB fields**
- email (from Clerk)
- full_name
- username (student-entered, unique)
- grade_id
- district_id (province derived)
- avatar_id
- >= 1 selected subject

**Clerk metadata**
- `public_metadata.gender` (mandatory)

This is enforced by:
- `POST /api/v1/me/onboarding` (sets everything in one go)
- recalculation in `GET /api/v1/me/profile` and after updates

---

## 2) Province-first dropdown flow (MIN-14)
Use:
- `GET /api/v1/meta/provinces`
- `GET /api/v1/meta/districts?province_id=<id>`

Onboarding requires **both** `province_id` and `district_id` and validates:
`district.province_id == province_id`.

---

## 3) Resources in Supabase Storage private bucket (MIN-18)

This backend returns a **signed view URL** in `view_url` for each resource with `storage_path`.

To let you test even without real PDFs uploaded:
- set `STORAGE_MODE=mock` → returns fake signed URLs (still exercises the endpoint behavior)
- later switch to `STORAGE_MODE=supabase` and provide Supabase credentials

---

## 4) Clerk verification redirect (frontend)
You said: **Force redirect after sign-up to `/dashboard`**.

In your React app, set Clerk force redirect URLs (examples):
- `CLERK_SIGN_UP_FORCE_REDIRECT_URL=/dashboard`
- `CLERK_SIGN_IN_FORCE_REDIRECT_URL=/dashboard`

Then in `/dashboard`:
- call `GET /api/v1/me/profile`
- if `profile_completed=false` → show glass overlay onboarding form.

---

## 5) Run locally (NO Docker)

### Prerequisites
- Python 3.10+ installed
- A local Postgres server running (you can use pgAdmin4 to manage it)
- Your database already loaded with **db1.sql** (you said you've done this)

### Configure
Create `.env`:

```bash
cp .env.example .env
```

Edit `.env` and set `DATABASE_URL` to your local Postgres connection string, for example:

```env
DATABASE_URL=postgresql+psycopg2://postgres:<YOUR_PASSWORD>@localhost:5432/mindup
```

For your current “no Clerk frontend yet / no PDFs uploaded yet” testing, keep:
```env
AUTH_MODE=dev
CLERK_MODE=mock
STORAGE_MODE=mock
```

### Install + run
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Swagger:
- http://localhost:8000/docs

---

## 6) Switching to Supabase hosted DB later (after merge)

When you move this code into the real repo and want to use Supabase Postgres, update:

```env
DATABASE_URL=postgresql+psycopg2://postgres:<DB_PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres?sslmode=require
```

> Use your Supabase project's “Connection string” and ensure **sslmode=require**.

---

## 7) Switching Storage to real Supabase signed URLs (later)

When PDFs are uploaded to a **private** Supabase Storage bucket:

```env
STORAGE_MODE=supabase
SUPABASE_URL=https://<PROJECT_REF>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<SERVICE_ROLE_KEY>
SUPABASE_STORAGE_BUCKET=<YOUR_BUCKET_NAME>
SUPABASE_SIGNED_URL_EXPIRES_IN=3600
```

Then the resources endpoint will return real `view_url` signed links.

---

## 8) Testing

Use:
- `README_TESTING.md` for the full Swagger/Postman step-by-step flow
- `postman/MindUp_Sprint1.postman_collection.json` (import into Postman)

