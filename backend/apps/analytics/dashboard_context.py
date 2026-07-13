"""Minimal academic context for the school dashboard header."""
from __future__ import annotations

from typing import Any

from apps.academics.models import Class, Subject
from apps.academics.scoping import get_academic_context
from apps.academics.singleton import get_active_academic_year, get_active_term
from apps.core.constants import UserRole, normalize_role

TEACHER_HEADER_ROLES = frozenset({
    UserRole.TEACHER,
    UserRole.CLASS_TEACHER,
})


def build_dashboard_header_context(*, tenant, user) -> dict[str, Any]:
    """
    Header facts shown on every school dashboard:
    - academic year and current term for all users
    - assigned classes and subject codes (DB ``code`` field) for teachers only
    """
    payload: dict[str, Any] = {
        "academic_year": None,
        "current_term": None,
        "assigned_classes": None,
        "subject_codes": None,
    }

    if not user or not getattr(user, "is_authenticated", False):
        return payload

    year = get_active_academic_year(tenant)
    if year is not None:
        payload["academic_year"] = {"name": year.name}

    term = get_active_term(tenant, academic_year=year)
    if term is not None:
        payload["current_term"] = {
            "name": term.name,
            "term_number": term.term_number,
        }

    role = normalize_role(getattr(user, "role", ""))
    if role not in TEACHER_HEADER_ROLES:
        return payload

    ctx = get_academic_context(user)
    if ctx is None:
        return payload

    class_ids = set(ctx.assigned_class_ids) | set(ctx.class_teacher_class_ids)
    if class_ids:
        payload["assigned_classes"] = list(
            Class.objects.filter(tenant=tenant, id__in=class_ids, is_deleted=False)
            .order_by("name")
            .values_list("name", flat=True),
        )

    if ctx.assigned_subject_ids:
        payload["subject_codes"] = list(
            Subject.objects.filter(
                tenant=tenant,
                id__in=ctx.assigned_subject_ids,
                is_deleted=False,
            )
            .order_by("code")
            .values_list("code", flat=True),
        )

    return payload


# Backwards compatibility for any caller still using the list shape.
def build_dashboard_context_stats(*, tenant, user) -> list[dict[str, Any]]:
    header = build_dashboard_header_context(tenant=tenant, user=user)
    items: list[dict[str, Any]] = []
    if header.get("academic_year"):
        items.append({
            "key": "academic_year",
            "label": "Academic Year",
            "value": header["academic_year"]["name"],
        })
    if header.get("current_term"):
        items.append({
            "key": "current_term",
            "label": "Current Term",
            "value": header["current_term"]["name"],
        })
    if header.get("assigned_classes"):
        items.append({
            "key": "assigned_classes",
            "label": "Class",
            "value": ", ".join(header["assigned_classes"]),
        })
    if header.get("subject_codes"):
        items.append({
            "key": "subject_codes",
            "label": "Subjects",
            "value": ", ".join(header["subject_codes"]),
        })
    return items