"""Deliverable email validation — rejects placeholders and dummy addresses."""
from __future__ import annotations

import re
from typing import Optional

# RFC 5322 simplified — practical address check
EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9](?:[a-zA-Z0-9._%+\-]*[a-zA-Z0-9])?"
    r"@"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9\-]*[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9\-]*[a-zA-Z0-9])?)+$"
)

BLOCKED_DOMAINS = frozenset({
    "example.com", "example.org", "example.net", "test.com", "test.org",
    "localhost", "local", "invalid", "domain.com", "email.com",
    "mail.com", "fake.com", "dummy.com", "sample.com", "placeholder.com",
    "yopmail.com", "mailinator.com", "guerrillamail.com", "tempmail.com",
    "10minutemail.com", "throwaway.email", "sharklasers.com",
})

BLOCKED_TLDS = frozenset({"test", "invalid", "localhost", "local"})

DUMMY_LOCAL_PARTS = frozenset({
    "test", "dummy", "fake", "example", "sample", "placeholder", "noreply",
    "no-reply", "donotreply", "do-not-reply", "null", "void", "none",
    "user", "username", "email", "mail", "asdf", "qwerty", "aaa", "bbb",
})

# Obvious non-production host patterns (not broad TLD blocks)
DUMMY_DOMAIN_PATTERNS = re.compile(
    r"^(?:test\.|.*\.test$|localhost|127\.0\.0\.1)$",
    re.IGNORECASE,
)


def normalize_email(value: str) -> str:
    return (value or "").strip()


def validate_deliverable_email(value: str, *, required: bool = True) -> Optional[str]:
    """
    Return an error message if the email is invalid or not deliverable.
    Return None when the address passes validation.
    """
    email = normalize_email(value)
    if not email:
        return "Email is required." if required else None

    if len(email) > 254:
        return "Email address is too long."

    if not EMAIL_PATTERN.match(email):
        return "Enter a valid email address (e.g. name@school.edu)."

    local, _, domain = email.rpartition("@")
    domain_lower = domain.lower()
    local_lower = local.lower()

    if domain_lower in BLOCKED_DOMAINS:
        return f"\"{domain_lower}\" is not allowed. Use a real mailbox you can access."

    tld = domain_lower.rsplit(".", 1)[-1]
    if tld in BLOCKED_TLDS:
        return "Use a real email domain, not a test or placeholder TLD."

    if len(tld) < 2:
        return "Email domain must include a valid top-level domain (e.g. .com, .ug)."

    if local_lower in DUMMY_LOCAL_PARTS and domain_lower in BLOCKED_DOMAINS:
        return "Placeholder email addresses are not allowed."

    if DUMMY_DOMAIN_PATTERNS.search(domain_lower):
        return "Use a real email address, not a demo or placeholder domain."

    if re.fullmatch(r"staff\d*", local_lower) and domain_lower.endswith(".ug"):
        return "Use each staff member's real work email, not generated demo addresses."

    if re.fullmatch(r"parent", local_lower) and len(domain_lower) < 8:
        return "Use the parent's real email address."

    if "." not in domain_lower:
        return "Enter a complete email address with a valid domain."

    return None


def is_deliverable_email(value: str) -> bool:
    return validate_deliverable_email(value, required=bool((value or "").strip())) is None


def filter_deliverable_emails(addresses: list[str]) -> list[str]:
    """Keep only addresses that pass deliverable validation."""
    seen: set[str] = set()
    result: list[str] = []
    for address in addresses:
        email = normalize_email(address)
        if not email or not is_deliverable_email(email):
            continue
        key = email.lower()
        if key not in seen:
            seen.add(key)
            result.append(email)
    return result