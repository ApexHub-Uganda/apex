"""Tenant utility helpers."""
from __future__ import annotations

import re

from apps.tenants.models import Tenant


def generate_school_code(name: str) -> str:
    """Derive a unique short school code from the school name."""
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", name).upper().split()
    if len(cleaned) >= 2:
        base = f"{cleaned[0][:3]}{cleaned[1][:3]}"
    elif cleaned:
        base = cleaned[0][:6]
    else:
        base = "SCH"

    base = base[:6].ljust(3, "X")[:6]
    code = base
    counter = 1
    while Tenant.objects.filter(code__iexact=code).exists():
        suffix = str(counter)
        code = f"{base[: max(3, 6 - len(suffix))]}{suffix}"[:6]
        counter += 1
    return code