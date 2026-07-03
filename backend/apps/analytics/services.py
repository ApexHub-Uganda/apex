"""Analytics computation services."""
from __future__ import annotations

from calendar import month_abbr
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, Optional

from django.db import connection
from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.attendance.models import AttendanceRecord
from apps.finance.models import FeePayment, Invoice
from apps.students.models import Student
from apps.subscriptions.models import PaymentTransaction, Plan, Subscription
from apps.tenants.models import Tenant


def _last_n_month_labels(n: int = 6) -> list[str]:
    """Return short month labels for the last N months (oldest first)."""
    today = timezone.now().date()
    labels: list[str] = []
    year, month = today.year, today.month
    for offset in range(n - 1, -1, -1):
        m = month - offset
        y = year
        while m <= 0:
            m += 12
            y -= 1
        labels.append(month_abbr[m])
    return labels


def _month_range_keys(months: int = 6) -> list[str]:
    today = timezone.now().date()
    keys: list[str] = []
    year, month = today.year, today.month
    for offset in range(months - 1, -1, -1):
        m = month - offset
        y = year
        while m <= 0:
            m += 12
            y -= 1
        keys.append(f"{y}-{m:02d}")
    return keys


def _series_start(months: int = 6) -> datetime:
    today = timezone.now().date()
    start_date = today.replace(day=1) - timedelta(days=months * 31)
    return timezone.make_aware(datetime.combine(start_date, time.min))


def _monthly_count_series(queryset, date_field: str, months: int = 6) -> list[int]:
    """Aggregate queryset counts per month for the last N months."""
    aggregated = (
        queryset.filter(**{f"{date_field}__gte": _series_start(months)})
        .annotate(month=TruncMonth(date_field))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )
    count_by_month = {
        row["month"].strftime("%Y-%m"): row["count"]
        for row in aggregated
        if row["month"]
    }
    return [count_by_month.get(key, 0) for key in _month_range_keys(months)]


def _monthly_sum_series(
    queryset,
    date_field: str,
    sum_field: str,
    months: int = 6,
) -> list[float]:
    """Aggregate queryset sums per month for the last N months."""
    aggregated = (
        queryset.filter(**{f"{date_field}__gte": _series_start(months)})
        .annotate(month=TruncMonth(date_field))
        .values("month")
        .annotate(total=Sum(sum_field))
        .order_by("month")
    )
    sum_by_month = {
        row["month"].strftime("%Y-%m"): float(row["total"] or 0)
        for row in aggregated
        if row["month"]
    }
    return [sum_by_month.get(key, 0.0) for key in _month_range_keys(months)]


def _empty_chart(label: str, months: int = 6) -> dict[str, Any]:
    labels = _last_n_month_labels(months)
    return {
        "labels": labels,
        "datasets": [{"label": label, "data": [0] * len(labels)}],
    }


def _get_system_health(active_sessions: int) -> dict[str, Any]:
    from apps.platform.models import PlatformMetrics, SystemHealthLog

    metrics = PlatformMetrics.get_current()
    recent_logs = SystemHealthLog.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=30),
    )
    log_count = recent_logs.count()
    if log_count:
        healthy_count = recent_logs.filter(status="healthy").count()
        uptime = round(healthy_count / log_count * 100, 2)
        latest = recent_logs.order_by("-created_at").first()
        api_status = latest.status if latest else "healthy"
        database = "connected" if (latest is None or latest.database_ok) else "disconnected"
    else:
        uptime = float(metrics.uptime_percent)
        api_status = "healthy"
        database = "connected"
        try:
            connection.ensure_connection()
        except Exception:
            database = "disconnected"
            api_status = "degraded"

    return {
        "api_status": api_status,
        "database": database,
        "uptime_percent": uptime,
        "storage_used_mb": metrics.storage_used_mb,
        "storage_cap_mb": metrics.storage_cap_mb,
        "active_sessions": active_sessions,
        "failed_jobs": metrics.failed_jobs_24h,
    }


def _get_plan_usage(
    subscription: dict[str, Any] | None,
    total_students: int,
    total_staff: int,
) -> dict[str, Any]:
    if not subscription or subscription.get("limits_enforced") is False:
        return {}
    max_students = subscription.get("max_students") or 0
    max_staff = subscription.get("max_staff") or 0
    if not max_students and not max_staff:
        return {}
    return {
        "students": {
            "used": total_students,
            "limit": max_students,
            "percent": round((total_students / max_students * 100) if max_students else 0.0, 1),
        },
        "staff": {
            "used": total_staff,
            "limit": max_staff,
            "percent": round((total_staff / max_staff * 100) if max_staff else 0.0, 1),
        },
    }


def _get_dashboard_sections(tenant: Tenant) -> dict[str, bool]:
    from apps.subscriptions.services import tenant_has_feature

    return {
        "attendance": tenant_has_feature(tenant, "student_attendance"),
        "finance": tenant_has_feature(tenant, "student_billing"),
        "enrollment": tenant_has_feature(tenant, "admissions"),
        "reports": tenant_has_feature(tenant, "reports"),
        "staff_attendance": tenant_has_feature(tenant, "staff_attendance"),
        "examinations": tenant_has_feature(tenant, "marks_entry"),
        "library": tenant_has_feature(tenant, "library_management"),
        "hostel": tenant_has_feature(tenant, "hostel_management"),
        "transport": tenant_has_feature(tenant, "vehicles"),
        "inventory": tenant_has_feature(tenant, "inventory_items"),
        "hr": tenant_has_feature(tenant, "hr_departments"),
        "payroll": tenant_has_feature(tenant, "payroll_runs"),
        "communication": tenant_has_feature(tenant, "announcements"),
        "classes": tenant_has_feature(tenant, "classes"),
    }


def _get_module_stats(tenant_id: str, sections: dict[str, bool]) -> dict[str, Any]:
    stats: dict[str, Any] = {}

    if sections.get("library"):
        from apps.library.models import Book, BorrowRecord
        stats["library"] = {
            "total_books": Book.objects.filter(tenant_id=tenant_id, is_deleted=False).count(),
            "borrowed": BorrowRecord.objects.filter(
                tenant_id=tenant_id, status__in=["borrowed", "overdue"], is_deleted=False,
            ).count(),
            "overdue": BorrowRecord.objects.filter(
                tenant_id=tenant_id, status="overdue", is_deleted=False,
            ).count(),
        }

    if sections.get("hostel"):
        from apps.hostel.models import Allocation, Hostel, Room
        total_capacity = Room.objects.filter(tenant_id=tenant_id, is_deleted=False).aggregate(
            total=Sum("capacity"),
        )["total"] or 0
        occupied = Allocation.objects.filter(
            tenant_id=tenant_id, status="active", is_deleted=False,
        ).count()
        stats["hostel"] = {
            "hostels": Hostel.objects.filter(tenant_id=tenant_id, is_deleted=False).count(),
            "rooms": Room.objects.filter(tenant_id=tenant_id, is_deleted=False).count(),
            "occupied": occupied,
            "capacity": int(total_capacity),
            "occupancy_rate": round((occupied / total_capacity * 100) if total_capacity else 0.0, 1),
        }

    if sections.get("transport"):
        from apps.transport.models import Route, StudentTransport, Vehicle
        stats["transport"] = {
            "vehicles": Vehicle.objects.filter(tenant_id=tenant_id, is_deleted=False).count(),
            "active_vehicles": Vehicle.objects.filter(
                tenant_id=tenant_id, status="active", is_deleted=False,
            ).count(),
            "routes": Route.objects.filter(tenant_id=tenant_id, is_deleted=False).count(),
            "students_assigned": StudentTransport.objects.filter(
                tenant_id=tenant_id, status="active", is_deleted=False,
            ).count(),
        }

    if sections.get("inventory"):
        from django.db.models import F
        from apps.inventory.models import Item
        stats["inventory"] = {
            "items": Item.objects.filter(tenant_id=tenant_id, is_deleted=False).count(),
            "low_stock": Item.objects.filter(
                tenant_id=tenant_id, is_deleted=False, quantity__lte=F("reorder_level"),
            ).count(),
        }

    if sections.get("hr"):
        from apps.hr.models import Leave
        stats["hr"] = {
            "pending_leave": Leave.objects.filter(
                tenant_id=tenant_id, status="pending", is_deleted=False,
            ).count(),
            "approved_leave": Leave.objects.filter(
                tenant_id=tenant_id, status="approved", is_deleted=False,
            ).count(),
        }

    if sections.get("payroll"):
        from apps.payroll.models import PayrollRun
        stats["payroll"] = {
            "runs_this_year": PayrollRun.objects.filter(
                tenant_id=tenant_id,
                is_deleted=False,
                created_at__year=timezone.now().year,
            ).count(),
            "pending_runs": PayrollRun.objects.filter(
                tenant_id=tenant_id, status="draft", is_deleted=False,
            ).count(),
        }

    if sections.get("communication"):
        from apps.communication.models import Announcement
        stats["communication"] = {
            "announcements": Announcement.objects.filter(tenant_id=tenant_id, is_deleted=False).count(),
            "published": Announcement.objects.filter(
                tenant_id=tenant_id, is_published=True, is_deleted=False,
            ).count(),
        }

    return stats


def _get_upgrade_suggestions(tenant: Tenant) -> list[dict[str, Any]]:
    from apps.subscriptions.models import FeatureFlag
    from apps.subscriptions.services import get_enabled_feature_keys

    enabled = set(get_enabled_feature_keys(tenant))
    suggestions: list[dict[str, Any]] = []
    for feature in FeatureFlag.objects.filter(is_active=True, show_in_nav=True).order_by("sort_order"):
        if feature.feature_key in enabled:
            continue
        suggestions.append({
            "feature_key": feature.feature_key,
            "label": feature.feature_name.split(" - ")[0] if " - " in feature.feature_name else feature.feature_name,
            "nav_key": feature.nav_key,
            "icon": feature.icon or "FiGrid",
            "path": feature.route_path or f"/school-admin/{feature.nav_key}",
        })
        if len(suggestions) >= 6:
            break
    return suggestions


def get_school_dashboard(tenant_id: str) -> dict[str, Any]:
    """School admin dashboard statistics — plan-aware sections and module stats."""
    from apps.academics.models import Class
    from apps.audit.models import AuditLog
    from apps.staff.models import Staff
    from apps.subscriptions.services import get_tenant_dashboard_widgets

    from apps.subscriptions.services import get_subscription_summary

    tenant = Tenant.objects.select_related().get(pk=tenant_id)
    subscription = get_subscription_summary(tenant)
    sections = _get_dashboard_sections(tenant)

    today = timezone.now().date()
    month_start = today.replace(day=1)
    month_labels = _last_n_month_labels(6)

    students = Student.objects.filter(tenant_id=tenant_id, is_deleted=False)
    total_students = students.count()
    total_staff = Staff.objects.filter(tenant_id=tenant_id, is_deleted=False).count()
    active_classes = Class.objects.filter(tenant_id=tenant_id, is_deleted=False).count()

    attendance_today = AttendanceRecord.objects.filter(
        tenant_id=tenant_id, date=today, attendee_type="student", is_deleted=False,
    )
    present_today = attendance_today.filter(status="present").count()
    attendance_total_today = attendance_today.count()
    attendance_rate = round(
        (present_today / attendance_total_today * 100) if attendance_total_today else 0.0,
        1,
    )

    fee_payments = FeePayment.objects.filter(
        tenant_id=tenant_id, status="completed", is_deleted=False,
    )
    collected_mtd = fee_payments.filter(payment_date__gte=month_start).aggregate(
        total=Sum("amount_paid"),
    )["total"] or Decimal("0")

    invoices = Invoice.objects.filter(tenant_id=tenant_id, is_deleted=False)
    total_billed = invoices.aggregate(total=Sum("total_amount"))["total"] or Decimal("0")
    total_paid = invoices.aggregate(total=Sum("amount_paid"))["total"] or Decimal("0")
    pending_fees = float((total_billed - total_paid) if total_billed > total_paid else Decimal("0"))
    fee_collection = round(
        float(total_paid / total_billed * 100) if total_billed else 0.0,
        1,
    )

    total_capacity = Class.objects.filter(tenant_id=tenant_id, is_deleted=False).aggregate(
        total=Sum("capacity"),
    )["total"] or 0
    class_capacity = round(
        (total_students / total_capacity * 100) if total_capacity else 0.0,
        1,
    )

    weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    present_data: list[int] = []
    absent_data: list[int] = []
    for offset in range(4, -1, -1):
        day = today - timedelta(days=offset)
        if day.weekday() >= 5:
            present_data.append(0)
            absent_data.append(0)
            continue
        day_records = AttendanceRecord.objects.filter(
            tenant_id=tenant_id,
            date=day,
            attendee_type="student",
            is_deleted=False,
        )
        present_data.append(day_records.filter(status="present").count())
        absent_data.append(day_records.filter(status="absent").count())

    finance_data = _monthly_sum_series(
        fee_payments,
        "payment_date",
        "amount_paid",
        6,
    )

    recent_activities = []
    for log in AuditLog.objects.filter(tenant_id=tenant_id).select_related("user").order_by("-created_at")[:8]:
        recent_activities.append({
            "id": str(log.id),
            "type": log.action,
            "message": log.description or f"{log.action} on {log.resource_type}",
            "time": log.created_at.isoformat(),
        })

    enrollment_chart = None
    if sections.get("enrollment"):
        enrollment_data = _monthly_count_series(
            students,
            "created_at",
            6,
        )
        enrollment_chart = {
            "labels": month_labels,
            "datasets": [{"label": "New Students", "data": enrollment_data}],
        }

    class_chart = None
    if sections.get("classes"):
        by_class = list(
            students.filter(school_class__isnull=False)
            .values("school_class__name")
            .annotate(count=Count("id"))
            .order_by("-count")[:8]
        )
        class_chart = {
            "labels": [row["school_class__name"] or "Unassigned" for row in by_class],
            "datasets": [{"label": "Students", "data": [row["count"] for row in by_class]}],
        }

    payload: dict[str, Any] = {
        "subscription": subscription,
        "plan_usage": _get_plan_usage(subscription, total_students, total_staff),
        "sections": sections,
        "widgets": get_tenant_dashboard_widgets(tenant),
        "module_stats": _get_module_stats(tenant_id, sections),
        "upgrade_suggestions": _get_upgrade_suggestions(tenant),
        "stats": {
            "total_students": total_students,
            "total_staff": total_staff,
            "attendance_rate": attendance_rate,
            "fee_collection": fee_collection,
            "active_classes": active_classes,
            "pending_fees": pending_fees,
            "class_capacity": class_capacity,
            "fee_collected_mtd": float(collected_mtd),
        },
        "recent_activities": recent_activities,
        "generated_at": timezone.now().isoformat(),
    }

    if sections.get("attendance"):
        payload["attendance_chart"] = {
            "labels": weekday_labels,
            "datasets": [
                {"label": "Present", "data": present_data},
                {"label": "Absent", "data": absent_data},
            ],
        }

    if sections.get("finance"):
        payload["finance_chart"] = {
            "labels": month_labels,
            "datasets": [{"label": "Collected", "data": finance_data}],
        }

    if enrollment_chart:
        payload["enrollment_chart"] = enrollment_chart

    if class_chart and class_chart["labels"]:
        payload["class_chart"] = class_chart

    return payload


def get_school_detail(tenant_id: str) -> dict[str, Any]:
    """School profile and platform-level summary for super-admin detail view."""
    from apps.academics.models import Class
    from apps.accounts.models import User
    from apps.core.constants import UserRole
    from apps.staff.models import Staff

    tenant = Tenant.objects.select_related().get(pk=tenant_id)

    total_students = Student.objects.filter(tenant_id=tenant_id, is_deleted=False).count()
    total_staff = Staff.objects.filter(tenant_id=tenant_id, is_deleted=False).count()
    active_classes = Class.objects.filter(tenant_id=tenant_id, is_deleted=False).count()

    sub = tenant.active_subscription
    plan = sub.plan if sub else None
    enabled_features = tenant.get_enabled_features()

    admin_user = User.objects.filter(tenant=tenant, role=UserRole.SCHOOL_ADMIN).first()

    return {
        "school": {
            "id": str(tenant.id),
            "name": tenant.name,
            "code": tenant.code,
            "email": tenant.email,
            "phone": tenant.phone,
            "address": tenant.address,
            "city": tenant.city,
            "country": tenant.country,
            "timezone": tenant.timezone,
            "status": tenant.status,
            "is_verified": tenant.is_verified,
            "is_suspended": tenant.is_suspended,
            "tagline": tenant.tagline,
            "website": tenant.website,
            "registration_number": tenant.registration_number,
            "created_at": tenant.created_at.isoformat(),
            "admin_email": admin_user.email if admin_user else None,
            "registration_type": tenant.registration_type,
            "payment_attempted": tenant.payment_attempted,
            "enabled_feature_count": len(enabled_features),
        },
        "subscription": {
            "id": str(sub.id) if sub else None,
            "plan": plan.name if plan else None,
            "plan_slug": plan.slug if plan else None,
            "plan_id": str(plan.id) if plan else None,
            "status": sub.status if sub else None,
            "billing_cycle": sub.billing_cycle if sub else None,
            "monthly_amount": float(plan.price_monthly) if plan else 0.0,
            "yearly_amount": float(plan.price_yearly) if plan else 0.0,
            "current_period_end": sub.current_period_end.isoformat() if sub and sub.current_period_end else None,
            "trial_ends_at": sub.trial_ends_at.isoformat() if sub and sub.trial_ends_at else None,
            "feature_count": plan.features.filter(is_active=True).count() if plan else 0,
            "limits_enforced": False,
            "max_students": None,
            "max_staff": None,
            "max_parents": None,
            "max_branches": None,
        },
        "stats": {
            "total_students": total_students,
            "total_staff": total_staff,
            "active_classes": active_classes,
        },
        "generated_at": timezone.now().isoformat(),
    }


def get_platform_dashboard() -> dict[str, Any]:
    """Super admin platform statistics with charts and operational KPIs."""
    from apps.accounts.models import LoginHistory, User, UserSession
    from apps.audit.models import AuditLog
    from apps.staff.models import Staff

    now = timezone.now()
    today = now.date()
    month_start = today.replace(day=1)
    thirty_days_ago = now - timedelta(days=30)
    month_labels = _last_n_month_labels(6)

    tenants = Tenant.objects.all()
    total_schools = tenants.count()
    active_schools = tenants.filter(status="active", is_suspended=False).count()
    suspended_schools = tenants.filter(is_suspended=True).count()
    pending_schools = tenants.filter(status="pending").count()
    unverified_schools = tenants.filter(is_verified=False, is_suspended=False).count()

    subscriptions = Subscription.objects.select_related("plan")
    active_subs_qs = subscriptions.filter(status__in=["trial", "active", "grace_period"])
    trial_count = active_subs_qs.filter(status="trial").count()
    active_sub_count = active_subs_qs.filter(status="active").count()
    grace_count = active_subs_qs.filter(status="grace_period").count()
    expired_subs = subscriptions.filter(status="expired").count()

    mrr = subscriptions.filter(status="active").aggregate(
        total=Sum("plan__price_monthly"),
    )["total"] or Decimal("0")

    completed_payments = PaymentTransaction.objects.filter(status="completed")
    revenue_total = completed_payments.aggregate(total=Sum("amount"))["total"] or Decimal("0")

    revenue_mtd = completed_payments.filter(created_at__gte=month_start).aggregate(
        total=Sum("amount"),
    )["total"] or Decimal("0")

    failed_payments_30d = PaymentTransaction.objects.filter(
        status="failed", created_at__gte=thirty_days_ago,
    ).count()

    total_students = Student.objects.filter(is_deleted=False).count()
    total_staff = Staff.objects.filter(is_deleted=False).count()
    active_users_24h = User.objects.filter(last_login_at__gte=now - timedelta(hours=24)).count()
    active_sessions = UserSession.objects.filter(is_active=True, expires_at__gt=now).count()

    schools_prev_month = tenants.filter(
        created_at__lt=month_start,
        created_at__gte=month_start - timedelta(days=31),
    ).count()
    schools_this_month = tenants.filter(created_at__gte=month_start).count()
    growth_rate = round(
        ((schools_this_month - schools_prev_month) / schools_prev_month * 100)
        if schools_prev_month else (100.0 if schools_this_month else 0.0),
        1,
    )

    converted = subscriptions.filter(status="active").count()
    expired_trials = subscriptions.filter(status__in=["expired", "cancelled"]).count()
    churn_rate = round(
        (expired_subs / subscriptions.count() * 100) if subscriptions.count() else 0.0,
        1,
    )
    conversion_rate = round(
        (converted / (converted + expired_trials) * 100) if (converted + expired_trials) else 0.0,
        1,
    )

    avg_revenue_per_school = round(
        float(revenue_total) / total_schools if total_schools else 0.0,
        2,
    )

    revenue_by_month = _monthly_sum_series(completed_payments, "created_at", "amount", 6)
    schools_by_month = _monthly_count_series(tenants, "created_at", 6)
    enrollment_by_month = _monthly_count_series(
        Student.objects.filter(is_deleted=False),
        "created_at",
        6,
    )

    plan_distribution = list(
        subscriptions.filter(status__in=["trial", "active", "grace_period"])
        .values("plan__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    country_distribution = list(
        tenants.values("country")
        .annotate(count=Count("id"))
        .order_by("-count")[:6]
    )

    recent_schools = []
    for tenant in tenants.order_by("-created_at")[:8]:
        sub = tenant.active_subscription
        student_count = Student.objects.filter(tenant=tenant, is_deleted=False).count()
        recent_schools.append({
            "id": str(tenant.id),
            "name": tenant.name,
            "plan": sub.plan.name if sub and sub.plan else "—",
            "plan_slug": sub.plan.slug if sub and sub.plan else None,
            "status": tenant.status,
            "students": student_count,
            "country": tenant.country or "",
            "created_at": tenant.created_at.isoformat(),
        })

    top_schools = []
    for tenant in tenants:
        student_count = Student.objects.filter(tenant=tenant, is_deleted=False).count()
        sub = tenant.active_subscription
        top_schools.append({
            "id": str(tenant.id),
            "name": tenant.name,
            "plan_slug": sub.plan.slug if sub and sub.plan else None,
            "students": student_count,
            "country": tenant.country or "",
        })
    top_schools.sort(key=lambda x: x["students"], reverse=True)
    top_schools = top_schools[:5]

    recent_activity = []
    for log in AuditLog.objects.select_related("user", "tenant").order_by("-created_at")[:8]:
        recent_activity.append({
            "id": str(log.id),
            "action": log.action,
            "description": log.description or f"{log.action} on {log.resource_type}",
            "user": log.user.email if log.user else "System",
            "tenant": log.tenant.name if log.tenant else "Platform",
            "time": log.created_at.isoformat(),
        })

    if not recent_activity:
        for entry in LoginHistory.objects.filter(success=True).select_related("user").order_by("-created_at")[:5]:
            recent_activity.append({
                "id": str(entry.id),
                "action": "login",
                "description": f"Successful login from {entry.ip_address or 'unknown IP'}",
                "user": entry.email,
                "tenant": "Platform",
                "time": entry.created_at.isoformat(),
            })

    plan_labels = [p["plan__name"] or "Unknown" for p in plan_distribution]
    plan_counts = [p["count"] for p in plan_distribution]
    country_labels = [c["country"] or "Unknown" for c in country_distribution]
    country_counts = [c["count"] for c in country_distribution]
    active_sub_count_total = active_subs_qs.count()

    return {
        "stats": {
            "total_schools": total_schools,
            "active_schools": active_schools,
            "pending_schools": pending_schools,
            "suspended_schools": suspended_schools,
            "unverified_schools": unverified_schools,
            "active_subscriptions": active_sub_count,
            "trial_subscriptions": trial_count,
            "grace_period_subscriptions": grace_count,
            "monthly_revenue": float(mrr),
            "revenue_mtd": float(revenue_mtd),
            "total_revenue": float(revenue_total),
            "arr": float(mrr * 12),
            "total_students": total_students,
            "total_staff": total_staff,
            "active_users_24h": active_users_24h,
            "active_sessions": active_sessions,
            "growth_rate": growth_rate,
            "churn_rate": churn_rate,
            "conversion_rate": conversion_rate,
            "avg_revenue_per_school": avg_revenue_per_school,
            "failed_payments_30d": failed_payments_30d,
        },
        "revenue_chart": {
            "labels": month_labels,
            "datasets": [{"label": "Revenue ($)", "data": revenue_by_month}],
        },
        "schools_chart": {
            "labels": month_labels,
            "datasets": [{"label": "New Schools", "data": schools_by_month}],
        },
        "enrollment_chart": {
            "labels": month_labels,
            "datasets": [{"label": "New Enrollments", "data": enrollment_by_month}],
        },
        "subscription_chart": {
            "labels": plan_labels,
            "datasets": [{"label": "Subscriptions", "data": plan_counts}],
        },
        "country_chart": {
            "labels": country_labels,
            "datasets": [{"label": "Schools", "data": country_counts}],
        },
        "plan_breakdown": [
            {
                "plan": p["plan__name"] or "Unknown",
                "count": p["count"],
                "percent": round(p["count"] / active_sub_count_total * 100, 1) if active_sub_count_total else 0.0,
            }
            for p in plan_distribution
        ],
        "system_health": _get_system_health(active_sessions),
        "recent_schools": recent_schools,
        "top_schools": top_schools,
        "recent_activity": recent_activity,
        "generated_at": now.isoformat(),
    }


def get_plans_subscriptions_hub() -> dict[str, Any]:
    """Overview data for merged Plans & Subscriptions super-admin page."""
    now = timezone.now()
    today = now.date()
    week_ahead = now + timedelta(days=7)

    plans = Plan.objects.all()
    subscriptions = Subscription.objects.select_related("plan", "tenant")

    active_subs = subscriptions.filter(status="active")
    mrr = active_subs.aggregate(total=Sum("plan__price_monthly"))["total"] or Decimal("0")

    plan_distribution = list(
        subscriptions.filter(status__in=["trial", "active", "grace_period"])
        .values("plan__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    status_breakdown = {
        row["status"]: row["count"]
        for row in subscriptions.values("status").annotate(count=Count("id"))
    }

    expiring_soon = []
    for sub in subscriptions.filter(
        status__in=["active", "trial", "grace_period"],
    ).filter(
        Q(current_period_end__lte=week_ahead) | Q(trial_ends_at__lte=week_ahead),
    ).order_by("current_period_end", "trial_ends_at")[:8]:
        expiring_soon.append({
            "id": str(sub.id),
            "school": sub.tenant.name,
            "plan": sub.plan.name if sub.plan else "—",
            "status": sub.status,
            "ends_at": (sub.current_period_end or sub.trial_ends_at).isoformat()
            if (sub.current_period_end or sub.trial_ends_at) else None,
        })

    plan_cards = []
    for plan in plans.prefetch_related("features").order_by("sort_order", "price_monthly"):
        features = list(
            plan.features.filter(is_active=True)
            .order_by("category__sort_order", "sort_order")
            .values_list("feature_name", flat=True)[:6]
        )
        sub_count = subscriptions.filter(plan=plan, status__in=["trial", "active", "grace_period"]).count()
        plan_cards.append({
            "id": str(plan.id),
            "name": plan.name,
            "slug": plan.slug,
            "price_monthly": float(plan.price_monthly),
            "price_yearly": float(plan.price_yearly),
            "max_students": plan.max_students,
            "max_staff": plan.max_staff,
            "max_parents": plan.max_parents,
            "max_branches": plan.max_branches,
            "trial_days": plan.trial_days,
            "grace_period_days": plan.grace_period_days,
            "is_active": plan.is_active,
            "subscriber_count": sub_count,
            "feature_count": plan.features.filter(is_active=True).count(),
            "features": features,
        })

    return {
        "stats": {
            "total_plans": plans.count(),
            "active_plans": plans.filter(is_active=True).count(),
            "total_subscriptions": subscriptions.count(),
            "active_subscriptions": active_subs.count(),
            "trial_subscriptions": subscriptions.filter(status="trial").count(),
            "grace_period_subscriptions": subscriptions.filter(status="grace_period").count(),
            "expired_subscriptions": subscriptions.filter(status="expired").count(),
            "mrr": float(mrr),
            "arr": float(mrr * 12),
        },
        "plan_distribution": {
            "labels": [p["plan__name"] or "Unknown" for p in plan_distribution],
            "datasets": [{"label": "Subscriptions", "data": [p["count"] for p in plan_distribution]}],
        },
        "status_breakdown": status_breakdown,
        "expiring_soon": expiring_soon,
        "plan_cards": plan_cards,
        "generated_at": now.isoformat(),
    }


def get_billing_operations() -> dict[str, Any]:
    """Billing & payments command center for super-admin."""
    from apps.subscriptions.models import PaymentProvider

    now = timezone.now()
    today = now.date()
    month_start = today.replace(day=1)
    thirty_days_ago = now - timedelta(days=30)
    month_labels = _last_n_month_labels(6)

    transactions = PaymentTransaction.objects.select_related("tenant", "provider")
    completed = transactions.filter(status="completed")
    failed = transactions.filter(status="failed")
    pending = transactions.filter(status="pending")

    revenue_total = completed.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    revenue_mtd = completed.filter(created_at__gte=month_start).aggregate(
        total=Sum("amount"),
    )["total"] or Decimal("0")
    failed_amount_30d = failed.filter(created_at__gte=thirty_days_ago).aggregate(
        total=Sum("amount"),
    )["total"] or Decimal("0")

    total_txn_30d = transactions.filter(created_at__gte=thirty_days_ago).count()
    failed_count_30d = failed.filter(created_at__gte=thirty_days_ago).count()
    success_rate = round(
        ((total_txn_30d - failed_count_30d) / total_txn_30d * 100) if total_txn_30d else 100.0,
        1,
    )

    revenue_chart = _monthly_sum_series(completed, "created_at", "amount", 6)
    failed_by_month = _monthly_count_series(failed, "created_at", 6)

    providers = list(PaymentProvider.objects.values(
        "id", "name", "slug", "method_type", "is_active", "is_sandbox",
    ))

    failed_queue = []
    for txn in failed.filter(created_at__gte=thirty_days_ago).order_by("-created_at")[:10]:
        failed_queue.append({
            "id": str(txn.id),
            "school": txn.tenant.name,
            "amount": float(txn.amount),
            "currency": txn.currency,
            "reference": txn.reference,
            "provider": txn.provider.name if txn.provider else "—",
            "created_at": txn.created_at.isoformat(),
        })

    recent_transactions = []
    for txn in transactions.order_by("-created_at")[:12]:
        recent_transactions.append({
            "id": str(txn.id),
            "school": txn.tenant.name,
            "amount": float(txn.amount),
            "currency": txn.currency,
            "status": txn.status,
            "reference": txn.reference,
            "provider": txn.provider.name if txn.provider else "—",
            "created_at": txn.created_at.isoformat(),
        })

    return {
        "stats": {
            "revenue_total": float(revenue_total),
            "revenue_mtd": float(revenue_mtd),
            "failed_count_30d": failed_count_30d,
            "failed_amount_30d": float(failed_amount_30d),
            "pending_count": pending.count(),
            "success_rate": success_rate,
            "active_providers": PaymentProvider.objects.filter(is_active=True).count(),
        },
        "revenue_chart": {
            "labels": month_labels,
            "datasets": [{"label": "Collected ($)", "data": revenue_chart}],
        },
        "failed_chart": {
            "labels": month_labels,
            "datasets": [{"label": "Failed Payments", "data": failed_by_month}],
        },
        "status_breakdown": {
            "completed": completed.count(),
            "failed": failed.count(),
            "pending": pending.count(),
            "refunded": transactions.filter(status="refunded").count(),
        },
        "providers": providers,
        "failed_queue": failed_queue,
        "recent_transactions": recent_transactions,
        "generated_at": now.isoformat(),
    }


def get_platform_analytics() -> dict[str, Any]:
    """Dedicated analytics page data for super-admin."""
    from apps.platform.models import PlatformMetrics

    now = timezone.now()
    today = now.date()
    year = today.year
    month_labels = _last_n_month_labels(6)

    subscriptions = Subscription.objects.select_related("plan")
    mrr_by_month: list[float] = []
    year_cursor, month_cursor = today.year, today.month
    for _ in range(6):
        period_end = date(year_cursor, month_cursor, 1)
        if month_cursor == 12:
            next_month = date(year_cursor + 1, 1, 1)
        else:
            next_month = date(year_cursor, month_cursor + 1, 1)
        mrr = subscriptions.filter(
            status="active",
            current_period_start__lt=next_month,
        ).aggregate(total=Sum("plan__price_monthly"))["total"] or Decimal("0")
        mrr_by_month.insert(0, float(mrr))
        month_cursor -= 1
        if month_cursor <= 0:
            month_cursor = 12
            year_cursor -= 1

    plan_distribution = list(
        subscriptions.filter(status__in=["trial", "active", "grace_period"])
        .values("plan__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    plan_labels = [p["plan__name"] or "Unknown" for p in plan_distribution]
    plan_counts = [p["count"] for p in plan_distribution]

    quarterly_labels: list[str] = []
    quarterly_data: list[int] = []
    for q in range(1, 5):
        q_start = date(year, (q - 1) * 3 + 1, 1)
        if q < 4:
            q_end = date(year, q * 3 + 1, 1)
        else:
            q_end = date(year + 1, 1, 1)
        count = Tenant.objects.filter(created_at__gte=q_start, created_at__lt=q_end).count()
        quarterly_labels.append(f"Q{q}")
        quarterly_data.append(count)

    metrics = PlatformMetrics.get_current()
    health = _get_system_health(0)

    completed_payments = PaymentTransaction.objects.filter(status="completed")
    revenue_by_month = _monthly_sum_series(completed_payments, "created_at", "amount", 6)
    schools_by_month = _monthly_count_series(Tenant.objects.all(), "created_at", 6)
    enrollment_by_month = _monthly_count_series(
        Student.objects.filter(is_deleted=False),
        "created_at",
        6,
    )

    return {
        "revenue_chart": {
            "labels": month_labels,
            "datasets": [{"label": "MRR ($)", "data": mrr_by_month}],
        },
        "payment_revenue_chart": {
            "labels": month_labels,
            "datasets": [{"label": "Payments ($)", "data": revenue_by_month}],
        },
        "plan_distribution": {
            "labels": plan_labels,
            "datasets": [{"label": "Subscriptions", "data": plan_counts}],
        },
        "school_growth_chart": {
            "labels": quarterly_labels,
            "datasets": [{"label": "New Schools", "data": quarterly_data}],
        },
        "schools_chart": {
            "labels": month_labels,
            "datasets": [{"label": "New Schools", "data": schools_by_month}],
        },
        "enrollment_chart": {
            "labels": month_labels,
            "datasets": [{"label": "New Enrollments", "data": enrollment_by_month}],
        },
        "platform_health": {
            "uptime": float(health["uptime_percent"]),
            "customer_satisfaction": float(metrics.customer_satisfaction_percent),
            "feature_adoption": float(metrics.feature_adoption_percent),
            "support_resolution": float(metrics.support_resolution_percent),
        },
        "summary": {
            "total_schools": Tenant.objects.count(),
            "active_subscriptions": subscriptions.filter(status="active").count(),
            "total_students": Student.objects.filter(is_deleted=False).count(),
            "mrr": float(
                subscriptions.filter(status="active").aggregate(total=Sum("plan__price_monthly"))["total"] or 0,
            ),
        },
        "generated_at": now.isoformat(),
    }


def get_enrollment_analytics(tenant_id: Optional[str] = None) -> dict[str, Any]:
    qs = Student.objects.filter(is_deleted=False)
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    by_status = dict(qs.values_list("status").annotate(c=Count("id")).values_list("status", "c"))
    by_class = list(
        qs.filter(school_class__isnull=False)
        .values("school_class__name")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    return {"by_status": by_status, "by_class": by_class}


def get_attendance_analytics(tenant_id: str, days: int = 30) -> dict[str, Any]:
    start = timezone.now().date() - timedelta(days=days)
    records = AttendanceRecord.objects.filter(
        tenant_id=tenant_id, date__gte=start, attendee_type="student", is_deleted=False,
    )
    total = records.count()
    present = records.filter(status="present").count()
    absent = records.filter(status="absent").count()
    late = records.filter(status="late").count()
    return {
        "period_days": days,
        "total_records": total,
        "present": present,
        "absent": absent,
        "late": late,
        "rate": round((present / total * 100) if total else 0, 1),
    }


def get_revenue_analytics(tenant_id: Optional[str] = None) -> dict[str, Any]:
    qs = FeePayment.objects.filter(status="completed", is_deleted=False)
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    by_method = list(qs.values("payment_method").annotate(total=Sum("amount_paid"), count=Count("id")))
    month_start = timezone.now().date().replace(day=1)
    this_month = qs.filter(payment_date__gte=month_start).aggregate(total=Sum("amount_paid"))["total"] or 0
    return {"by_method": by_method, "this_month": str(this_month)}