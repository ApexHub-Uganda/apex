"""Public marketing catalog for the landing page (database-driven)."""
from __future__ import annotations

import random
from typing import Any

from django.db.models import Count

from apps.core.constants import UserRole
from apps.subscriptions.models import FeatureFlag, Plan
from apps.subscriptions.serializers import PlanSerializer


def _format_storage(mb: int) -> str:
    if mb >= 1024:
        gb = mb / 1024
        return f"{gb:.0f} GB" if gb == int(gb) else f"{gb:.1f} GB"
    return f"{mb} MB"


def _format_limit(value: int, *, unlimited_threshold: int = 999_999) -> str:
    if value <= 0 or value >= unlimited_threshold:
        return "Unlimited"
    return f"{value:,}"


TRUSTED_SCHOOLS_LIMIT = 8


def get_trusted_schools(limit: int = TRUSTED_SCHOOLS_LIMIT) -> list[dict[str, str]]:
    """Return a random sample of active school names for the landing page."""
    from apps.tenants.models import Tenant

    school_ids = list(
        Tenant.objects.filter(status="active", is_suspended=False)
        .exclude(name="")
        .values_list("id", flat=True)
    )
    if not school_ids:
        return []

    sample_size = min(limit, len(school_ids))
    picked = random.sample(school_ids, sample_size)
    names_by_id = dict(
        Tenant.objects.filter(id__in=picked).values_list("id", "name")
    )
    return [
        {"id": str(school_id), "name": names_by_id[school_id]}
        for school_id in picked
        if school_id in names_by_id
    ]


def _platform_stats() -> list[dict[str, Any]]:
    from apps.accounts.models import User
    from apps.students.models import Student
    from apps.staff.models import Staff
    from apps.tenants.models import Tenant

    active_schools = Tenant.objects.filter(status="active", is_suspended=False).count()
    total_students = Student.objects.filter(is_deleted=False).count()
    teacher_roles = {UserRole.TEACHER, UserRole.HEAD_TEACHER, UserRole.DEPUTY_HEAD_TEACHER, UserRole.HEAD_OF_DEPARTMENT}
    total_teachers = Staff.objects.filter(is_deleted=False, portal_role__in=teacher_roles).count()
    if total_teachers == 0:
        total_teachers = User.objects.filter(role__in=teacher_roles, is_active=True).count()

    records = total_students + Staff.objects.filter(is_deleted=False).count()
    records_label = f"{records:,}" if records < 1_000_000 else f"{records // 1_000_000}M+"

    return [
        {"value": active_schools, "suffix": "+", "label": "Schools", "decimals": 0},
        {"value": total_students, "suffix": "+", "label": "Students", "decimals": 0},
        {"value": total_teachers, "suffix": "+", "label": "Teachers", "decimals": 0},
        {"value": 99.9, "suffix": "%", "label": "Uptime SLA", "decimals": 1},
        {"value": records, "suffix": "", "label": "Records Managed", "decimals": 0, "display": records_label},
    ]


def _marketing_features() -> list[dict[str, Any]]:
    flags = (
        FeatureFlag.objects.filter(is_active=True)
        .select_related("category")
        .order_by("category__sort_order", "sort_order", "feature_name")
    )
    return [
        {
            "feature_key": f.feature_key,
            "title": f.feature_name,
            "description": f.description or f.feature_name,
            "icon": f.icon or "FiGrid",
            "category": f.category.name if f.category_id else "",
        }
        for f in flags
    ]


def _plan_highlights(plan: Plan, serialized: dict) -> list[str]:
    highlights: list[str] = []
    if plan.description:
        highlights.append(plan.description.strip())
    detail = serialized.get("enabled_features_detail") or []
    names = [item.get("feature_name") for item in detail if item.get("feature_name")]
    for name in names[:6]:
        if name not in highlights:
            highlights.append(name)
    inherited = serialized.get("feature_inheritance_summary")
    if inherited and inherited not in highlights:
        highlights.insert(0, inherited)
    return highlights[:8] or ["Unlimited students, staff, and parents"]


def _comparison_matrix(plans: list[Plan], serialized_plans: list[dict]) -> list[dict[str, Any]]:
    """Compare key capabilities across public plans."""
    compare_keys = [
        ("student_management", "Student Management"),
        ("staff_management", "Staff Management"),
        ("student_billing", "Finance & Billing"),
        ("payroll_runs", "Payroll"),
        ("examination_management", "Examinations"),
        ("library_management", "Library"),
        ("dashboard_analytics", "Analytics"),
        ("multi_campus_support", "Multi-Campus"),
    ]
    plan_features = {
        p["slug"]: set(p.get("features") or [])
        for p in serialized_plans
    }
    rows = []
    for key, label in compare_keys:
        rows.append({
            "feature": label,
            "feature_key": key,
            "plans": {
                slug: key in feats for slug, feats in plan_features.items()
            },
        })
    return rows


def get_marketing_catalog() -> dict[str, Any]:
    plans_qs = (
        Plan.objects.filter(is_active=True, is_public=True)
        .prefetch_related("features")
        .order_by("sort_order", "price_monthly")
    )
    serialized = PlanSerializer(plans_qs, many=True).data

    pricing = []
    recommended_slug = None
    slugs = [p.slug for p in plans_qs]
    if "premium" in slugs:
        recommended_slug = "premium"
    elif slugs:
        recommended_slug = slugs[min(1, len(slugs) - 1)]

    for plan, data in zip(plans_qs, serialized, strict=True):
        pricing.append({
            "id": plan.slug,
            "name": plan.name,
            "slug": plan.slug,
            "description": plan.description,
            "monthly": float(plan.price_monthly),
            "yearly": float(plan.price_yearly),
            "currency": plan.currency,
            "students": "Unlimited",
            "users": "Unlimited",
            "storage": _format_storage(plan.max_storage_mb),
            "sms": _format_limit(plan.max_sms_monthly) + " / mo",
            "email": _format_limit(plan.max_emails_monthly) + " / mo",
            "trial_days": plan.trial_days,
            "features": _plan_highlights(plan, data),
            "feature_count": len(data.get("features") or []),
            "recommended": plan.slug == recommended_slug,
            "cta": "Contact Sales" if plan.slug.endswith("plus") or plan.slug.endswith("enterprise") else "Start Free Trial",
        })

    return {
        "plans": pricing,
        "features": _marketing_features(),
        "stats": _platform_stats(),
        "comparison": _comparison_matrix(list(plans_qs), serialized),
        "platform": {
            "name": "Apex Hub",
            "tagline": "The Easy Way",
            "feature_count": FeatureFlag.objects.filter(is_active=True).count(),
            "plan_count": plans_qs.count(),
        },
    }