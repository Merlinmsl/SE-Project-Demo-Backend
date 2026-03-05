"""
MindUp API Test Script (Production mode — Clerk JWT)
=====================================================

HOW TO GET A CLERK JWT FOR TESTING
-----------------------------------
Option A — From your frontend app:
  1. Sign in to the app as a student
  2. Open browser DevTools → Network tab
  3. Find any API request → copy the value after "Authorization: Bearer "

Option B — From the Clerk dashboard:
  1. Go to https://dashboard.clerk.com → Users
  2. Click a user → "Impersonate user" to get a session
  3. In the browser console run:  await window.Clerk.session.getToken()

Option C — From your frontend code (temporary debug):
  const token = await clerk.session.getToken();
  console.log(token);

Paste the token below, then run:
  python test_endpoints.py
"""

import urllib.request, json

# ── Paste your Clerk JWT here ──────────────────────────────────────────────────
CLERK_TOKEN = ""   # e.g.  "eyJhbGciOiJSUzI1NiIsInR5c..."
# ──────────────────────────────────────────────────────────────────────────────

BASE = "http://localhost:8000/api/v1"
ADMIN_KEY = "change-me"   # must match ADMIN_API_KEY in .env

if not CLERK_TOKEN:
    print("⚠  CLERK_TOKEN is empty — student endpoint tests will return 401.")
    print("   See the instructions at the top of this file to get one.\n")

student_auth = {"Authorization": f"Bearer {CLERK_TOKEN}"}
admin_auth   = {"X-Admin-Api-Key": ADMIN_KEY}


def test(label, url, headers=None, method="GET", body=None, expect_status=200):
    h = dict(headers or {})
    if body:
        h["Content-Type"] = "application/json"
        body_enc = json.dumps(body).encode()
    else:
        body_enc = None
    req = urllib.request.Request(url, headers=h, method=method, data=body_enc)
    try:
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())
            ok = r.status == expect_status
            print(f"[{'PASS' if ok else 'FAIL'}] [{r.status}] {label}")
            print("   ", json.dumps(data)[:250])
            return r.status, data
    except urllib.error.HTTPError as e:
        data = e.read().decode()
        ok = e.code == expect_status
        print(f"[{'PASS' if ok else 'FAIL'}] [{e.code}] {label}")
        print("   ", data[:200])
        return e.code, data


# ── 1. Public / meta endpoints (no auth required) ─────────────────────────────
print("=== META ENDPOINTS (no auth) ===")
test("GET /meta/provinces",              f"{BASE}/meta/provinces")
test("GET /meta/districts?province_id=1",f"{BASE}/meta/districts?province_id=1")
test("GET /meta/grades",                 f"{BASE}/meta/grades")
test("GET /meta/avatars",                f"{BASE}/meta/avatars")

# ── 2. Student profile flow (requires valid Clerk JWT) ─────────────────────────
print("\n=== STUDENT PROFILE FLOW (requires Clerk JWT) ===")
status, data = test("GET /me/profile",  f"{BASE}/me/profile", headers=student_auth)
if status == 200:
    print(f"   id={data['id']}, profile_completed={data['profile_completed']}")

test("POST /me/onboarding", f"{BASE}/me/onboarding", headers=student_auth, method="POST", body={
    "full_name":    "Test Student",
    "username":     "test_student_prod1",
    "grade_id":     1,
    "province_id":  1,
    "district_id":  1,
    "avatar_key":   "avatar_1",
    "subject_ids":  [1],
})

status, data = test("GET /me/profile (after onboarding)", f"{BASE}/me/profile", headers=student_auth)
if status == 200:
    print(f"   profile_completed={data['profile_completed']}, avatar={data['avatar_key']!r}")

test("PUT /me/profile (update name)",     f"{BASE}/me/profile", headers=student_auth, method="PUT",
     body={"full_name": "Updated Name"})
test("PUT /me/profile (update avatar)",   f"{BASE}/me/profile", headers=student_auth, method="PUT",
     body={"avatar_key": "avatar_3"})
test("PUT /me/profile (update username)", f"{BASE}/me/profile", headers=student_auth, method="PUT",
     body={"username": "test_student_prod2"})

# ── 3. Subjects ────────────────────────────────────────────────────────────────
print("\n=== SUBJECTS ===")
test("GET /subjects/available?grade_id=1", f"{BASE}/subjects/available?grade_id=1", headers=student_auth)
test("GET /me/subjects",                   f"{BASE}/me/subjects",  headers=student_auth)
test("PUT /me/subjects",                   f"{BASE}/me/subjects",  headers=student_auth, method="PUT",
     body={"subject_ids": [1, 2]})
test("GET /me/subjects (after update)",    f"{BASE}/me/subjects",  headers=student_auth)

# ── 4. Resources ───────────────────────────────────────────────────────────────
print("\n=== RESOURCES ===")
test("GET /resources?subject_id=1", f"{BASE}/resources?subject_id=1", headers=student_auth)

# ── 5. Admin (X-Admin-Api-Key, unchanged) ─────────────────────────────────────
print("\n=== ADMIN ===")
test("GET /admin/stats/student-count", f"{BASE}/admin/stats/student-count", headers=admin_auth)

# ── 6. Auth edge cases ────────────────────────────────────────────────────────
print("\n=== AUTH EDGE CASES ===")
test("GET /me/profile  (no token → 401)",      f"{BASE}/me/profile",   expect_status=401)
test("GET /me/profile  (bad token → 401)",     f"{BASE}/me/profile",
     headers={"Authorization": "Bearer not_a_real_token"}, expect_status=401)

# ── 7. Onboarding edge cases ──────────────────────────────────────────────────
print("\n=== ONBOARDING EDGE CASES ===")
test("POST /me/onboarding bad district (→ 400)", f"{BASE}/me/onboarding", headers=student_auth, method="POST",
     body={"full_name": "Test", "username": "bad_test99", "grade_id": 1,
           "province_id": 1, "district_id": 999, "avatar_key": "avatar_2", "subject_ids": [1]},
     expect_status=400)
