"""HR analytics and report builders."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from django.db.models import Count
from django.utils import timezone

from apps.academics.models import Department
from apps.hr.constants import CONTRACT_ACTIVE, LEAVE_PENDING, REVIEW_DRAFT, REVIEW_SUBMITTED
from apps.hr.models import Leave, PerformanceReview, StaffContract, StaffDiscipline
from apps.staff.models import Staff


def build_hr_analytics(*, tenant) -> dict[str, Any]:
    staff_qs = Staff.objects.filter(tenant=tenant, is_deleted=False)
    leave_qs = Leave.objects.filter(tenant=tenant, is_deleted=False)
    review_qs = PerformanceReview.objects.filter(tenant=tenant, is_deleted=False)
    contract_qs = StaffContract.objects.filter(tenant=tenant, is_deleted=False)
    discipline_qs = StaffDiscipline.objects.filter(tenant=tenant, is_deleted=False)

    return {
        "generated_at": timezone.now().isoformat(),
        "summary": {
            "staff_total": staff_qs.count(),
            "staff_active": staff_qs.filter(status="active").count(),
            "departments": Department.objects.filter(tenant=tenant, is_deleted=False).count(),
            "pending_leaves": leave_qs.filter(status=LEAVE_PENDING).count(),
            "approved_leaves": leave_qs.filter(status="approved").count(),
            "draft_reviews": review_qs.filter(status=REVIEW_DRAFT).count(),
            "submitted_reviews": review_qs.filter(status=REVIEW_SUBMITTED).count(),
            "active_contracts": contract_qs.filter(status=CONTRACT_ACTIVE).count(),
            "open_discipline_cases": discipline_qs.filter(status="open").count(),
        },
        "leave_by_type": [
            {"leave_type": row["leave_type"], "count": row["count"]}
            for row in leave_qs.values("leave_type").annotate(count=Count("id")).order_by("-count")
        ],
        "staff_by_status": [
            {"status": row["status"], "count": row["count"]}
            for row in staff_qs.values("status").annotate(count=Count("id")).order_by("-count")
        ],
    }


def build_hr_reports(
    *,
    tenant,
    report_type: str = "summary",
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    today = timezone.localdate()
    start = start_date or (today - timedelta(days=30))
    end = end_date or today

    payload: dict[str, Any] = {
        "report_type": report_type,
        "period": {"start": str(start), "end": str(end)},
        "generated_at": timezone.now().isoformat(),
        "rows": [],
        "totals": {},
        "summary": {},
    }

    staff_qs = Staff.objects.filter(tenant=tenant, is_deleted=False)
    leave_qs = Leave.objects.filter(tenant=tenant, is_deleted=False)
    review_qs = PerformanceReview.objects.filter(tenant=tenant, is_deleted=False)
    contract_qs = StaffContract.objects.filter(tenant=tenant, is_deleted=False)
    discipline_qs = StaffDiscipline.objects.filter(tenant=tenant, is_deleted=False)

    if report_type == "summary":
        payload["summary"] = {
            "staff_total": staff_qs.count(),
            "staff_active": staff_qs.filter(status="active").count(),
            "pending_leaves": leave_qs.filter(status=LEAVE_PENDING).count(),
            "approved_leaves": leave_qs.filter(status="approved").count(),
            "draft_reviews": review_qs.filter(status=REVIEW_DRAFT).count(),
            "submitted_reviews": review_qs.filter(status=REVIEW_SUBMITTED).count(),
            "active_contracts": contract_qs.filter(status=CONTRACT_ACTIVE).count(),
            "open_discipline_cases": discipline_qs.filter(status="open").count(),
        }
        return payload

    if report_type == "leaves":
        records = leave_qs.filter(
            start_date__gte=start,
            start_date__lte=end,
        ).select_related("staff", "approved_by").order_by("-start_date")
        payload["rows"] = [
            {
                "staff": leave.staff.full_name if leave.staff_id else "",
                "leave_type": leave.leave_type,
                "start_date": str(leave.start_date),
                "end_date": str(leave.end_date),
                "days": leave.days,
                "status": leave.status,
                "approved_by": leave.approved_by.get_full_name() if leave.approved_by_id else "",
            }
            for leave in records
        ]
        payload["totals"] = {
            "count": records.count(),
            "pending": records.filter(status=LEAVE_PENDING).count(),
            "approved": records.filter(status="approved").count(),
        }

    elif report_type == "reviews":
        records = review_qs.filter(
            review_period_start__gte=start,
            review_period_start__lte=end,
        ).select_related("staff", "reviewer").order_by("-review_period_start")
        payload["rows"] = [
            {
                "staff": review.staff.full_name if review.staff_id else "",
                "period_start": str(review.review_period_start),
                "period_end": str(review.review_period_end),
                "overall_rating": review.overall_rating,
                "status": review.status,
                "reviewer": review.reviewer.get_full_name() if review.reviewer_id else "",
            }
            for review in records
        ]
        payload["totals"] = {"count": records.count()}

    elif report_type == "contracts":
        records = contract_qs.filter(
            start_date__gte=start,
            start_date__lte=end,
        ).select_related("staff", "position").order_by("-start_date")
        payload["rows"] = [
            {
                "staff": contract.staff.full_name if contract.staff_id else "",
                "position": contract.position.title if contract.position_id else "",
                "contract_type": contract.contract_type,
                "start_date": str(contract.start_date),
                "end_date": str(contract.end_date) if contract.end_date else "",
                "status": contract.status,
            }
            for contract in records
        ]
        payload["totals"] = {
            "count": records.count(),
            "active": records.filter(status=CONTRACT_ACTIVE).count(),
        }

    elif report_type == "discipline":
        records = discipline_qs.filter(
            incident_date__gte=start,
            incident_date__lte=end,
        ).select_related("staff").order_by("-incident_date")
        payload["rows"] = [
            {
                "staff": case.staff.full_name if case.staff_id else "",
                "incident_date": str(case.incident_date),
                "severity": case.severity,
                "status": case.status,
                "description": (case.description or "")[:120],
            }
            for case in records
        ]
        payload["totals"] = {
            "count": records.count(),
            "open": records.filter(status="open").count(),
        }

    return payload