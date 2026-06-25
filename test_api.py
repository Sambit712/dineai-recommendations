"""
test_api.py -- Quick API integration tests (frontend -> backend flow)
Run: python test_api.py
"""
import sys
import io
import urllib.request
import urllib.error
import json

# Fix Windows console encoding for ₹ symbol
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = "http://localhost:8000"
PASS = "[PASS]"
FAIL = "[FAIL]"

def post(path, payload, timeout=90):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        BASE + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        res = urllib.request.urlopen(req, timeout=timeout)
        return res.status, json.loads(res.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

def get(path, timeout=10):
    try:
        res = urllib.request.urlopen(BASE + path, timeout=timeout)
        return res.status, json.loads(res.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


# ── TEST 1: GET /health ──────────────────────────────────────────────────────
print("=" * 60)
print("TEST 1: GET /health")
status, body = get("/health")
ok = status == 200 and body.get("status") == "ok"
print(f"  Status : {status}")
print(f"  Body   : {json.dumps(body)}")
print(f"  Result : {PASS if ok else FAIL}")
print()


# ── TEST 2: POST /recommend — valid full payload ─────────────────────────────
print("=" * 60)
print("TEST 2: POST /recommend  (valid payload — Bangalore / medium / north indian)")
status, body = post("/recommend", {
    "location":   "bangalore",
    "budget":     "medium",
    "cuisine":    "north indian",
    "min_rating": 4.0,
    "extras":     "family-friendly",
})
recs = body.get("recommendations", [])
ok = status == 200 and len(recs) > 0
print(f"  Status        : {status}")
print(f"  total_found   : {body.get('total_found')}")
print(f"  fallback_level: {body.get('fallback_level')}")
print(f"  fallback_msg  : {body.get('fallback_message')}")
print(f"  # recs returned: {len(recs)}")
for r in recs[:3]:
    print(f"    [{r['rank']}] {r['name']} | {r['cuisine']} | rating={r['rating']} | {r['estimated_cost']}")
print(f"  Result : {PASS if ok else FAIL}")
print()


# ── TEST 3: POST /recommend — empty cuisine (frontend edge case) ─────────────
print("=" * 60)
print("TEST 3: POST /recommend  (empty cuisine — frontend sends '' when no chip selected)")
status, body = post("/recommend", {
    "location":   "bangalore",
    "budget":     "low",
    "cuisine":    "",
    "min_rating": 3.5,
    "extras":     "",
})
ok_422 = status == 422   # schema says min_length=1, so 422 is expected
ok_200 = status == 200 and len(body.get("recommendations", [])) > 0
print(f"  Status : {status}")
if status == 422:
    errs = body.get("detail", [])
    print(f"  Validation errors: {len(errs)}")
    for e in errs:
        print(f"    field={e.get('loc')}  msg={e.get('msg')}")
    print(f"  Result : {PASS} (422 expected — cuisine field requires min_length=1)")
    print(f"  NOTE   : Frontend should be fixed to send a valid cuisine or relax schema.")
elif status == 200:
    print(f"  # recs: {len(body.get('recommendations', []))}")
    print(f"  Result : {PASS} (server accepted empty cuisine)")
else:
    print(f"  Body   : {json.dumps(body)[:300]}")
    print(f"  Result : {FAIL} (unexpected status)")
print()


# ── TEST 4: POST /recommend — invalid budget (expect 422) ───────────────────
print("=" * 60)
print("TEST 4: POST /recommend  (invalid budget='ultra' — expect 422)")
status, body = post("/recommend", {
    "location":   "mumbai",
    "budget":     "ultra",
    "cuisine":    "chinese",
    "min_rating": 3.0,
    "extras":     "",
}, timeout=10)
ok = status == 422
print(f"  Status : {status}  ({'expected' if ok else 'UNEXPECTED'})")
if status == 422:
    errs = body.get("detail", [])
    print(f"  Validation errors: {len(errs)}")
    for e in errs:
        print(f"    field={e.get('loc')}  msg={e.get('msg')}")
print(f"  Result : {PASS if ok else FAIL}")
print()


# ── TEST 5: POST /recommend — missing required field (expect 422) ────────────
print("=" * 60)
print("TEST 5: POST /recommend  (missing 'location' field — expect 422)")
status, body = post("/recommend", {
    "budget":     "high",
    "cuisine":    "italian",
    "min_rating": 4.5,
}, timeout=10)
ok = status == 422
print(f"  Status : {status}  ({'expected' if ok else 'UNEXPECTED'})")
print(f"  Result : {PASS if ok else FAIL}")
print()

print("=" * 60)
print("All tests complete.")
