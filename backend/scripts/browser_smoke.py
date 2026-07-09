"""Browser smoke tests for HR, Library, Hostel, and auth flows."""
from __future__ import annotations

import json
import sys
import time

from playwright.sync_api import sync_playwright

BASE = "http://localhost:5173"
EMAIL = "admin@kampalaroyal.ug"
PASSWORD = "School@2026"

ROUTES = [
    ("/login", "Login"),
    ("/forgot-password", "Forgot password"),
    ("/school-admin/hr/manager", "HR Manager workspace"),
    ("/school-admin/hr/approval", "HR Leave approval"),
    ("/school-admin/hr/analytics", "HR Analytics"),
    ("/school-admin/hr/reports", "HR Reports"),
    ("/school-admin/hr/leave", "HR Leave requests"),
    ("/school-admin/library/librarian", "Librarian workspace"),
    ("/school-admin/library/reports", "Library Reports"),
    ("/school-admin/library/borrowing", "Library Borrowing"),
    ("/school-admin/hostel/manager", "Hostel Manager workspace"),
    ("/school-admin/hostel/reports", "Hostel Reports"),
    ("/school-admin/hostel/allocations", "Hostel Allocations"),
    ("/school-admin/finance/reports", "Finance Reports"),
]


def _login(page) -> None:
    page.goto(f"{BASE}/login", wait_until="networkidle")
    page.fill('input[type="email"], input[name="email"]', EMAIL)
    page.fill('input[type="password"], input[name="password"]', PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_url("**/school-admin**", timeout=30000)


def main() -> int:
    results: list[dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            _login(page)
            results.append({"route": "/login", "label": "Login", "status": "ok"})
        except Exception as exc:
            print(json.dumps({"fatal": f"Login failed: {exc}"}))
            browser.close()
            return 1

        for route, label in ROUTES[1:]:
            entry = {"route": route, "label": label, "status": "ok", "detail": ""}
            try:
                page.goto(f"{BASE}{route}", wait_until="networkidle", timeout=30000)
                time.sleep(0.5)
                body = page.inner_text("body")
                if "Unable to load" in body or "Sign in" in body and route.startswith("/school-admin"):
                    entry["status"] = "warn"
                    entry["detail"] = "Possible auth or load issue"
                if page.locator(".alert-danger").count() > 0:
                    danger = page.locator(".alert-danger").first.inner_text().strip()
                    if danger:
                        entry["status"] = "fail"
                        entry["detail"] = danger[:200]
            except Exception as exc:
                entry["status"] = "fail"
                entry["detail"] = str(exc)[:200]
            results.append(entry)

        browser.close()

    failed = [r for r in results if r["status"] == "fail"]
    print(json.dumps({"results": results, "passed": len(results) - len(failed), "failed": len(failed)}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())