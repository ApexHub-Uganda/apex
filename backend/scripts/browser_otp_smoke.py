"""Browser smoke test: copy OTP from password reset email and paste on reset page."""
from __future__ import annotations

import json
import os
import re
import sys
import time

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apex_hub.settings")
django.setup()

from datetime import timedelta  # noqa: E402

from django.core.cache import cache  # noqa: E402
from django.utils import timezone  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

from apps.accounts.models import User  # noqa: E402
from apps.accounts.password_reset import (  # noqa: E402
    _cooldown_cache_key,
    _hash_otp,
)
from apps.core.email_templates import build_password_reset_email  # noqa: E402

BASE = "http://localhost:5173"
EMAIL = "admin@kampalaroyal.ug"
ORIGINAL_PASSWORD = "School@2026"
TEST_PASSWORD = "SmokeOtp@2026"
TEST_OTP = "847291"


def _seed_otp_for_user() -> None:
    user = User.objects.get(email__iexact=EMAIL, is_active=True)
    user.password_reset_token = _hash_otp(user_id=str(user.id), otp=TEST_OTP)
    user.password_reset_expires = timezone.now() + timedelta(minutes=10)
    user.save(update_fields=["password_reset_token", "password_reset_expires", "updated_at"])
    cache.delete(_cooldown_cache_key(str(user.id)))


def _restore_password() -> None:
    user = User.objects.get(email__iexact=EMAIL, is_active=True)
    user.set_password(ORIGINAL_PASSWORD)
    user.password_reset_token = ""
    user.password_reset_expires = None
    user.save(update_fields=["password", "password_reset_token", "password_reset_expires", "updated_at"])


def _email_plain_otp() -> str:
    branded = build_password_reset_email(
        first_name="Admin",
        email=EMAIL,
        otp=TEST_OTP,
        expires_minutes=10,
    )
    match = re.search(r"Your Apex Hub verification code is: (\d{6})", branded.text_body)
    if not match:
        match = re.search(r"\n(\d{6})\n", branded.text_body)
    if not match:
        raise RuntimeError("Plain-text OTP not found in email template")
    return match.group(1)


def _navigate_reset_page(page, email: str) -> None:
    """Reach reset page via forgot-password UI without issuing a new OTP."""
    page.route(
        "**/api/v1/auth/password-reset/",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "success": True,
                "message": f"A 6-digit verification code has been sent to {email}.",
                "data": {"expires_in_minutes": 10, "resend_cooldown_seconds": 60},
            }),
        ),
    )
    page.goto(f"{BASE}/forgot-password", wait_until="networkidle")
    page.fill("#reset-email", email)
    page.click('button[type="submit"]')
    page.wait_for_selector("text=Enter verification code", timeout=15000)


def main() -> int:
    results: list[dict] = []
    try:
        _seed_otp_for_user()
        plain_otp = _email_plain_otp()
        assert plain_otp == TEST_OTP

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            context.grant_permissions(["clipboard-read", "clipboard-write"])
            page = context.new_page()

            # --- Test 1: paste plain-text OTP from email ---
            _navigate_reset_page(page, EMAIL)
            first_otp = page.locator('input[aria-label="Digit 1"]')
            first_otp.click()
            page.evaluate(
                """async (code) => {
                  await navigator.clipboard.writeText(code);
                }""",
                plain_otp,
            )
            page.keyboard.press("Control+v")
            time.sleep(0.3)
            digits = [page.locator(f'input[aria-label="Digit {i}"]').input_value() for i in range(1, 7)]
            pasted = "".join(digits)
            results.append({
                "test": "paste_plain_text_otp",
                "expected": TEST_OTP,
                "actual": pasted,
                "ok": pasted == TEST_OTP,
            })

            # --- Test 2: paste spaced OTP (old email styling artifact) ---
            _navigate_reset_page(page, EMAIL)
            first_otp = page.locator('input[aria-label="Digit 1"]')
            first_otp.click()
            spaced = " ".join(TEST_OTP)
            page.evaluate(
                """async (code) => {
                  await navigator.clipboard.writeText(code);
                }""",
                spaced,
            )
            page.keyboard.press("Control+v")
            time.sleep(0.3)
            digits = [page.locator(f'input[aria-label="Digit {i}"]').input_value() for i in range(1, 7)]
            pasted_spaced = "".join(digits)
            results.append({
                "test": "paste_spaced_otp_strips_non_digits",
                "expected": TEST_OTP,
                "actual": pasted_spaced,
                "ok": pasted_spaced == TEST_OTP,
            })

            # --- Test 3: full reset submit with pasted OTP ---
            _navigate_reset_page(page, EMAIL)
            first_otp = page.locator('input[aria-label="Digit 1"]')
            first_otp.click()
            page.evaluate(
                """async (code) => {
                  await navigator.clipboard.writeText(code);
                }""",
                plain_otp,
            )
            page.keyboard.press("Control+v")
            page.fill('input[autocomplete="new-password"]', TEST_PASSWORD)
            page.locator('input[autocomplete="new-password"]').nth(1).fill(TEST_PASSWORD)
            page.click('button[type="submit"]')
            page.wait_for_url("**/login**", timeout=30000)
            results.append({
                "test": "submit_reset_redirects_to_login",
                "ok": "/login" in page.url,
            })

            # --- Test 4: login with new password ---
            page.fill('input[type="email"]', EMAIL)
            page.fill('input[type="password"]', TEST_PASSWORD)
            page.click('button[type="submit"]')
            page.wait_for_url("**/school-admin**", timeout=30000)
            results.append({
                "test": "login_with_reset_password",
                "ok": "/school-admin" in page.url,
            })

            browser.close()

    except Exception as exc:
        print(json.dumps({"fatal": str(exc), "results": results}, indent=2))
        _restore_password()
        return 1
    finally:
        _restore_password()

    failed = [r for r in results if not r.get("ok")]
    print(json.dumps({
        "results": results,
        "passed": len(results) - len(failed),
        "failed": len(failed),
        "email_plain_otp": plain_otp if "plain_otp" in locals() else "",
    }, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())