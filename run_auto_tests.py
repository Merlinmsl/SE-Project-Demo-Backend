import urllib.request, json

BASE = "http://localhost:8000/api/v1"
RESULTS = []

def test(label, url, headers=None, method="GET", body=None, expect_status=200):
    h = dict(headers or {})
    if body is not None:
        h["Content-Type"] = "application/json"
        body_enc = json.dumps(body).encode()
    else:
        body_enc = None
    req = urllib.request.Request(url, headers=h, method=method, data=body_enc)
    try:
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())
            ok = r.status == expect_status
            tag = "PASS" if ok else "FAIL"
            line = f"[{tag}] [{r.status}] {label}"
            detail = json.dumps(data)[:180]
    except urllib.error.HTTPError as e:
        data = e.read().decode()
        ok = e.code == expect_status
        tag = "PASS" if ok else "FAIL"
        line = f"[{tag}] [{e.code}] {label}"
        detail = data[:180]
    RESULTS.append(ok)
    print(line)
    print("   ", detail)
    return ok

print("=" * 55)
print("  MindUp Sprint-1 — Automated Tests (Local DB)")
print("=" * 55)

print("\n--- Meta endpoints (public, no auth) ---")
test("GET /meta/provinces",               f"{BASE}/meta/provinces")
test("GET /meta/districts?province_id=1", f"{BASE}/meta/districts?province_id=1")
test("GET /meta/grades",                  f"{BASE}/meta/grades")
test("GET /meta/avatars",                 f"{BASE}/meta/avatars")

print("\n--- Admin endpoint ---")
test("GET /admin/stats/student-count (valid key)",  f"{BASE}/admin/stats/student-count", headers={"X-Admin-Api-Key": "change-me"})
test("GET /admin/stats/student-count (no key→403)", f"{BASE}/admin/stats/student-count", expect_status=403)

print("\n--- Auth protection: no token → 401 ---")
test("GET  /me/profile   (no token→401)",  f"{BASE}/me/profile",               expect_status=401)
test("GET  /me/subjects  (no token→401)",  f"{BASE}/me/subjects",              expect_status=401)
test("GET  /resources    (no token→401)",  f"{BASE}/resources?subject_id=1",   expect_status=401)
test("POST /me/onboarding(no token→401)",  f"{BASE}/me/onboarding", method="POST", body={}, expect_status=401)
test("PUT  /me/profile   (no token→401)",  f"{BASE}/me/profile", method="PUT", body={}, expect_status=401)
test("PUT  /me/subjects  (no token→401)",  f"{BASE}/me/subjects", method="PUT", body={}, expect_status=401)

print("\n--- Auth protection: bad token → 401 ---")
bad = {"Authorization": "Bearer this.is.fake"}
test("GET /me/profile (bad token→401)", f"{BASE}/me/profile", headers=bad, expect_status=401)

total = len(RESULTS)
passed = sum(RESULTS)
print("\n" + "=" * 55)
print(f"  Result: {passed}/{total} passed {'✓' if passed == total else '✗'}")
print("=" * 55)
if passed < total:
    print("  NOTE: Student-auth endpoints (POST/PUT /me/*) require")
    print("  a valid Clerk JWT to test. Use get_clerk_token.html")
    print("  in a browser to obtain one, then paste into Postman.")
