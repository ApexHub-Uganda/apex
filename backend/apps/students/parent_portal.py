"""Parent/sponsor portal: child-scoped finance + academics with fee-gated results."""
from __future__ import annotations

from typing import Any

from django.db.models import Avg, Count  # Count used for attendance summary

from apps.academics.models import Homework, Timetable
from apps.attendance.models import AttendanceRecord
from apps.core.constants import UserRole, normalize_role
from apps.examinations.models import Grade, ReportCard
from apps.finance.reports import build_parent_fee_statement
from apps.finance.results_access import compute_student_fee_clearance
from apps.tenants.role_permissions import get_user_feature_permissions, user_can_access_feature


def get_parent_profile(user):
    return getattr(user, "parent_profile", None)


def get_parent_children(user, tenant):
    parent = get_parent_profile(user)
    if parent is None or tenant is None:
        return []
    return list(
        parent.children.filter(tenant=tenant, is_deleted=False)
        .select_related("school_class", "stream")
        .order_by("last_name", "first_name")
    )


def parent_can_read_feature(tenant, user, feature_key: str) -> bool:
    if normalize_role(getattr(user, "role", "")) != UserRole.PARENT:
        return False
    return user_can_access_feature(tenant, user, feature_key, require_write=False)


def build_parent_portal_overview(*, tenant, user) -> dict[str, Any]:
    children = get_parent_children(user, tenant)
    perms = get_user_feature_permissions(tenant, user) if tenant else {}
    finance_features = [
        "parent_fee_statements", "student_billing", "fee_structures", "debtor_management",
    ]
    academic_features = [
        "report_cards", "terms", "timetables", "homework", "classes",
        "student_attendance", "examination_management",
    ]
    enabled_finance = [k for k in finance_features if parent_can_read_feature(tenant, user, k)]
    enabled_academic = [k for k in academic_features if parent_can_read_feature(tenant, user, k)]

    child_rows = []
    for child in children:
        clearance = compute_student_fee_clearance(tenant=tenant, student=child)
        child_rows.append({
            "id": str(child.id),
            "full_name": child.full_name,
            "admission_number": child.admission_number,
            "class_name": child.school_class.name if child.school_class_id else None,
            "class_id": str(child.school_class_id) if child.school_class_id else None,
            "stream_name": child.stream.name if getattr(child, "stream_id", None) else None,
            "fee_clearance": clearance,
            "results_allowed": clearance["results_allowed"],
        })

    return {
        "role": "parent",
        "children": child_rows,
        "modules": {
            "finance": {
                "can_read": bool(enabled_finance) or parent_can_read_feature(tenant, user, "parent_fee_statements"),
                "features": enabled_finance,
                "path": "/school-admin/finance/statements",
            },
            "academics": {
                "can_read": bool(enabled_academic),
                "features": enabled_academic,
                "path": "/school-admin/parent/academics",
            },
            "results": {
                "can_read": parent_can_read_feature(tenant, user, "report_cards")
                or parent_can_read_feature(tenant, user, "examination_management"),
                "path": "/school-admin/parent/results",
                "fee_gated": True,
            },
        },
        "permissions": perms,
    }


def build_parent_finance_bundle(*, tenant, user, student_id: str | None = None) -> dict[str, Any]:
    if not (
        parent_can_read_feature(tenant, user, "parent_fee_statements")
        or parent_can_read_feature(tenant, user, "student_billing")
    ):
        return {"children": [], "denied": True, "message": "Finance access is not enabled for your role."}

    children = get_parent_children(user, tenant)
    if student_id:
        children = [c for c in children if str(c.id) == str(student_id)]

    statements = []
    for child in children:
        stmt = build_parent_fee_statement(tenant=tenant, student=child)
        stmt["fee_clearance"] = compute_student_fee_clearance(tenant=tenant, student=child)
        statements.append(stmt)

    return {
        "children": statements,
        "count": len(statements),
        "view": "parent_finance",
        "denied": False,
    }


def build_parent_academics_bundle(*, tenant, user, student_id: str | None = None) -> dict[str, Any]:
    children = get_parent_children(user, tenant)
    if student_id:
        children = [c for c in children if str(c.id) == str(student_id)]

    can_timetable = parent_can_read_feature(tenant, user, "timetables")
    can_homework = parent_can_read_feature(tenant, user, "homework")
    can_attendance = parent_can_read_feature(tenant, user, "student_attendance")
    can_results = (
        parent_can_read_feature(tenant, user, "report_cards")
        or parent_can_read_feature(tenant, user, "examination_management")
    )

    if not any([can_timetable, can_homework, can_attendance, can_results]):
        return {
            "children": [],
            "denied": True,
            "message": "Academic access is not enabled for your role. Contact the school admin.",
        }

    rows = []
    for child in children:
        clearance = compute_student_fee_clearance(tenant=tenant, student=child)
        class_id = child.school_class_id
        bundle: dict[str, Any] = {
            "student": {
                "id": str(child.id),
                "full_name": child.full_name,
                "admission_number": child.admission_number,
                "class_name": child.school_class.name if class_id else None,
            },
            "fee_clearance": clearance,
            "sections": {},
        }

        if can_timetable and class_id:
            slots = Timetable.objects.filter(
                tenant=tenant, school_class_id=class_id, is_deleted=False,
            ).select_related("subject", "teacher__staff", "period").order_by("day_of_week", "start_time")[:40]
            bundle["sections"]["timetable"] = [
                {
                    "day_of_week": s.day_of_week,
                    "start_time": s.start_time.strftime("%H:%M") if s.start_time else "",
                    "end_time": s.end_time.strftime("%H:%M") if s.end_time else "",
                    "subject": s.subject.name if s.subject_id else "",
                    "teacher": (
                        s.teacher.staff.full_name
                        if s.teacher_id and getattr(s.teacher, "staff_id", None)
                        else ""
                    ),
                    "room": s.room or "",
                }
                for s in slots
            ]

        if can_homework and class_id:
            hw = Homework.objects.filter(
                tenant=tenant, school_class_id=class_id, is_deleted=False, is_published=True,
            ).select_related("subject").order_by("-assigned_date")[:20]
            bundle["sections"]["homework"] = [
                {
                    "title": h.title,
                    "subject": h.subject.name if h.subject_id else "",
                    "assigned_date": str(h.assigned_date),
                    "due_date": str(h.due_date),
                }
                for h in hw
            ]

        if can_attendance:
            recent = AttendanceRecord.objects.filter(
                tenant=tenant, student=child, is_deleted=False, attendee_type="student",
            ).order_by("-date")[:30]
            summary = recent.values("status").annotate(count=Count("id"))
            bundle["sections"]["attendance"] = {
                "recent": [
                    {"date": str(r.date), "status": r.status, "remarks": r.remarks or ""}
                    for r in recent[:15]
                ],
                "summary": {row["status"]: row["count"] for row in summary},
            }

        if can_results:
            if clearance["results_allowed"]:
                cards = ReportCard.objects.filter(
                    tenant=tenant, student=child, is_deleted=False, is_published=True, is_latest=True,
                ).select_related("term", "school_class", "stream").prefetch_related("subject_lines").order_by("-term__start_date")[:10]
                grades = Grade.objects.filter(
                    tenant=tenant, student=child, is_deleted=False,
                    exam__lifecycle_status="published",
                    exam__is_deleted=False,
                ).select_related("exam", "exam__subject", "exam__term").order_by("-exam__exam_date")[:40]
                bundle["sections"]["results"] = {
                    "locked": False,
                    "report_cards": [
                        {
                            "id": str(c.id),
                            "term": c.term.name if c.term_id else "",
                            "class_name": c.school_class.name if c.school_class_id else "",
                            "stream_name": c.stream.name if getattr(c, "stream_id", None) else "",
                            "average_score": str(c.average_score),
                            "total_score": str(c.total_score),
                            "rank": c.rank,
                            "stream_rank": getattr(c, "stream_rank", None),
                            "days_present": getattr(c, "days_present", 0),
                            "days_absent": getattr(c, "days_absent", 0),
                            "teacher_remarks": c.teacher_remarks,
                            "principal_remarks": c.principal_remarks,
                            "dos_remarks": getattr(c, "dos_remarks", "") or "",
                            "subjects": [
                                {
                                    "name": ln.subject_name,
                                    "total": str(ln.total_score),
                                    "grade": ln.grade,
                                    "ca": str(ln.ca_score) if ln.ca_score is not None else None,
                                    "exam": str(ln.exam_score) if ln.exam_score is not None else None,
                                }
                                for ln in c.subject_lines.filter(is_deleted=False).order_by("sort_order")
                            ],
                        }
                        for c in cards
                    ],
                    "recent_grades": [
                        {
                            "exam": g.exam.name if g.exam_id else "",
                            "subject": g.exam.subject.name if g.exam_id and g.exam.subject_id else "",
                            "score": str(g.score),
                            "grade": g.grade,
                            "exam_date": str(g.exam.exam_date) if g.exam_id else "",
                        }
                        for g in grades
                    ],
                    "average": str(
                        grades.aggregate(avg=Avg("score"))["avg"] or 0
                    ),
                }
            else:
                bundle["sections"]["results"] = {
                    "locked": True,
                    "message": clearance["message"],
                    "fee_clearance": clearance,
                    "report_cards": [],
                    "recent_grades": [],
                }

        rows.append(bundle)

    return {"children": rows, "count": len(rows), "view": "parent_academics", "denied": False}

