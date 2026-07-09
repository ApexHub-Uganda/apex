"""API smoke tests for HR, Library, Hostel modules."""
from __future__ import annotations

import json
import sys

import requests

BASE = "http://localhost:8000/api/v1"
EMAIL = "admin@kampalaroyal.ug"
PASSWORD = "School@2026"

ENDPOINTS = [
    ("GET", "/hr/workspace/", "HR workspace"),
    ("GET", "/hr/approval-queue/", "HR approval queue"),
    ("GET", "/hr/analytics/", "HR analytics"),
    ("GET", "/hr/reports/?type=summary", "HR reports"),
    ("GET", "/library/workspace/", "Library workspace"),
    ("GET", "/library/reports/?type=inventory", "Library reports"),
    ("GET", "/hostel/workspace/", "Hostel workspace"),
    ("GET", "/hostel/reports/?type=occupancy", "Hostel reports"),
    ("GET", "/finance/reports/?type=collections", "Finance reports"),
]


def main() -> int:
    session = requests.Session()
    login = session.post(f"{BASE}/auth/login/", json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    if login.status_code != 200:
        print(json.dumps({"fatal": f"Login failed: {login.status_code} {login.text[:200]}"}))
        return 1

    token = login.json().get("data", {}).get("access") or login.json().get("access")
    if not token:
        print(json.dumps({"fatal": "No access token in login response"}))
        return 1

    session.headers["Authorization"] = f"Bearer {token}"
    results = []
    for method, path, label in ENDPOINTS:
        resp = session.request(method, f"{BASE}{path}", timeout=30)
        entry = {"label": label, "path": path, "status": resp.status_code}
        if resp.status_code != 200:
            entry["detail"] = resp.text[:200]
            entry["ok"] = False
        else:
            entry["ok"] = True
        results.append(entry)

    failed = [r for r in results if not r["ok"]]
    print(json.dumps({"results": results, "passed": len(results) - len(failed), "failed": len(failed)}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())