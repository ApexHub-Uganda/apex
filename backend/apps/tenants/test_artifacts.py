"""Detect and remove test or junk schools that leaked into operational databases."""
from __future__ import annotations

from typing import Any

from django.db import transaction

from apps.core.management.commands.seed_platform import UGANDAN_SCHOOLS
from apps.tenants.models import Tenant
from apps.tenants.school_validation import (
    SEED_SCHOOL_CODES,
    is_probable_test_or_junk_school,
)


def get_probable_test_schools(*, include_seeded: bool = False) -> list[Tenant]:
    rows = list(Tenant.objects.order_by("name", "code"))
    results: list[Tenant] = []
    for tenant in rows:
        if not include_seeded and tenant.code.upper() in SEED_SCHOOL_CODES:
            continue
        if is_probable_test_or_junk_school(
            name=tenant.name,
            code=tenant.code,
            email=tenant.email,
        ):
            results.append(tenant)
    return results


@transaction.atomic
def prune_test_schools(*, dry_run: bool = False) -> dict[str, Any]:
    """Permanently delete junk/test schools using the tenant deletion service."""
    from apps.tenants.services import delete_tenant_permanently

    candidates = get_probable_test_schools()
    deleted: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []

    for tenant in candidates:
        row = {
            "id": str(tenant.id),
            "name": tenant.name,
            "code": tenant.code,
            "email": tenant.email,
        }
        if dry_run:
            deleted.append(row)
            continue

        delete_tenant_permanently(
            tenant,
            confirmation_name=tenant.name,
            actor=None,
        )
        deleted.append(row)

    return {
        "deleted": deleted,
        "skipped": skipped,
        "dry_run": dry_run,
        "seed_school_codes": sorted(SEED_SCHOOL_CODES),
        "seed_school_count": len(UGANDAN_SCHOOLS),
    }