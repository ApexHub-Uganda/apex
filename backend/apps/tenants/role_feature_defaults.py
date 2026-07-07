"""Default per-feature permissions for academic portal roles.

School admins can override any value in Permission Settings. When no granular
feature overrides exist for a module, these defaults apply instead of granting
full module read/write to every child feature.
"""
from __future__ import annotations

from typing import Any

from apps.core.constants import UserRole, normalize_role

_PERM = dict[str, bool]


def _rw() -> _PERM:
    return {"can_read": True, "can_write": True}


def _r() -> _PERM:
    return {"can_read": True, "can_write": False}


def _deny() -> _PERM:
    return {"can_read": False, "can_write": False}


_TEACHER_ACADEMICS: dict[str, _PERM] = {
    "teacher_workspace": _rw(),
    "academic_years": _deny(),
    "terms": _r(),
    "classes": _r(),
    "streams": _r(),
    "departments": _deny(),
    "subjects": _r(),
    "subject_assignment": _deny(),
    "grading": _deny(),
    "student_promotion": _deny(),
    "homework": _rw(),
    "assignments": _rw(),
    "timetables": _r(),
    "periods": _r(),
    "classrooms": _r(),
    "class_teacher_tools": _deny(),
    "hod_workspace": _deny(),
    "dos_workspace": _deny(),
    "teacher_assignments": _deny(),
    "class_notices": _deny(),
    "discipline_remarks": _deny(),
}

_TEACHER_EXAMINATIONS: dict[str, _PERM] = {
    "examination_management": _r(),
    "assessment_management": _rw(),
    "marks_entry": _rw(),
    "result_processing": _deny(),
    "report_cards": _r(),
    "grade_calculation": _deny(),
    "marks_approval": _deny(),
    "examination_sessions": _deny(),
    "class_report_cards": _deny(),
}

_TEACHER_ATTENDANCE: dict[str, _PERM] = {
    "student_attendance": _rw(),
    "lesson_attendance": _rw(),
    "staff_attendance": _deny(),
    "attendance_sessions": _deny(),
}

_CLASS_TEACHER_EXTRA: dict[str, _PERM] = {
    "class_teacher_tools": _rw(),
    "class_notices": _rw(),
    "discipline_remarks": _rw(),
    "class_report_cards": _rw(),
}

_HOD_ACADEMICS: dict[str, _PERM] = {
    "hod_workspace": _rw(),
    "teacher_workspace": _deny(),
    "academic_years": _r(),
    "terms": _r(),
    "classes": _r(),
    "streams": _r(),
    "departments": _r(),
    "subjects": _rw(),
    "subject_assignment": _r(),
    "grading": _r(),
    "student_promotion": _deny(),
    "homework": _r(),
    "assignments": _r(),
    "timetables": _r(),
    "periods": _r(),
    "classrooms": _r(),
    "class_teacher_tools": _deny(),
    "dos_workspace": _deny(),
    "teacher_assignments": _r(),
    "class_notices": _r(),
    "discipline_remarks": _rw(),
}

_HOD_EXAMINATIONS: dict[str, _PERM] = {
    "examination_management": _r(),
    "assessment_management": _r(),
    "marks_entry": _r(),
    "result_processing": _r(),
    "report_cards": _r(),
    "grade_calculation": _r(),
    "marks_approval": _rw(),
    "examination_sessions": _r(),
    "class_report_cards": _r(),
}

_HOD_ATTENDANCE: dict[str, _PERM] = {
    "student_attendance": _r(),
    "lesson_attendance": _r(),
    "staff_attendance": _deny(),
    "attendance_sessions": _r(),
}

_DOS_ACADEMICS: dict[str, _PERM] = {
    "dos_workspace": _rw(),
    "teacher_workspace": _deny(),
    "hod_workspace": _deny(),
    "academic_years": _rw(),
    "terms": _rw(),
    "classes": _rw(),
    "streams": _rw(),
    "departments": _rw(),
    "subjects": _rw(),
    "subject_assignment": _rw(),
    "grading": _rw(),
    "student_promotion": _rw(),
    "homework": _rw(),
    "assignments": _rw(),
    "timetables": _rw(),
    "periods": _rw(),
    "classrooms": _rw(),
    "teacher_assignments": _rw(),
    "class_notices": _rw(),
    "discipline_remarks": _rw(),
    "class_teacher_tools": _r(),
}

_DOS_EXAMINATIONS: dict[str, _PERM] = {
    "examination_management": _rw(),
    "assessment_management": _rw(),
    "marks_entry": _rw(),
    "result_processing": _rw(),
    "report_cards": _rw(),
    "grade_calculation": _rw(),
    "marks_approval": _rw(),
    "examination_sessions": _rw(),
    "class_report_cards": _rw(),
}

_DOS_ATTENDANCE: dict[str, _PERM] = {
    "student_attendance": _rw(),
    "lesson_attendance": _rw(),
    "staff_attendance": _r(),
    "attendance_sessions": _rw(),
}

_DOS_ANALYTICS: dict[str, _PERM] = {
    "dashboard_analytics": _rw(),
    "academic_analytics": _rw(),
}

_CLASS_TEACHER_ROLE_ACADEMICS: dict[str, _PERM] = {
    **_TEACHER_ACADEMICS,
    **_CLASS_TEACHER_EXTRA,
    "teacher_workspace": _r(),
    "hod_workspace": _deny(),
    "dos_workspace": _deny(),
}

_ASSISTANT_BURSAR_FINANCE: dict[str, _PERM] = {
    "assistant_bursar_workspace": _rw(),
    "bursar_workspace": _deny(),
    "fee_structures": _r(),
    "fee_categories": _r(),
    "discounts": _rw(),
    "student_billing": _rw(),
    "invoice_generation": _rw(),
    "payment_recording": _rw(),
    "misc_income": _rw(),
    "expenses": _rw(),
    "refunds": _rw(),
    "debtor_management": _rw(),
    "finance_notes": _rw(),
    "financial_reports": _r(),
    "finance_analytics": _r(),
    "transaction_approval": _deny(),
    "budget_management": _deny(),
    "financial_accounts": _deny(),
    "accounting_periods": _deny(),
    "salary_structures": _deny(),
    "payroll_runs": _deny(),
    "payslips": _deny(),
}

_BURSAR_FINANCE: dict[str, _PERM] = {
    "bursar_workspace": _rw(),
    "assistant_bursar_workspace": _r(),
    "fee_structures": _rw(),
    "fee_categories": _rw(),
    "discounts": _rw(),
    "student_billing": _rw(),
    "invoice_generation": _rw(),
    "payment_recording": _rw(),
    "misc_income": _rw(),
    "expenses": _rw(),
    "refunds": _rw(),
    "debtor_management": _rw(),
    "finance_notes": _rw(),
    "financial_reports": _rw(),
    "finance_analytics": _rw(),
    "transaction_approval": _rw(),
    "budget_management": _rw(),
    "financial_accounts": _rw(),
    "accounting_periods": _rw(),
    "salary_structures": _rw(),
    "payroll_runs": _r(),
    "payslips": _r(),
}

DEFAULT_ROLE_FEATURE_PERMISSIONS: dict[str, dict[str, _PERM]] = {
    UserRole.TEACHER: {
        **_TEACHER_ACADEMICS,
        **_TEACHER_EXAMINATIONS,
        **_TEACHER_ATTENDANCE,
    },
    UserRole.CLASS_TEACHER: {
        **_CLASS_TEACHER_ROLE_ACADEMICS,
        **_TEACHER_EXAMINATIONS,
        **_TEACHER_ATTENDANCE,
    },
    UserRole.HEAD_OF_DEPARTMENT: {
        **_HOD_ACADEMICS,
        **_HOD_EXAMINATIONS,
        **_HOD_ATTENDANCE,
    },
    UserRole.DIRECTOR_OF_STUDIES: {
        **_DOS_ACADEMICS,
        **_DOS_EXAMINATIONS,
        **_DOS_ATTENDANCE,
        **_DOS_ANALYTICS,
    },
    UserRole.DEPUTY_HEAD_TEACHER: {
        **_HOD_ACADEMICS,
        **_HOD_EXAMINATIONS,
        **_HOD_ATTENDANCE,
        "dashboard_analytics": _r(),
    },
    UserRole.HEAD_TEACHER: {
        **_DOS_ACADEMICS,
        **_DOS_EXAMINATIONS,
        **_DOS_ATTENDANCE,
        "dashboard_analytics": _r(),
    },
    UserRole.ASSISTANT_BURSAR: {
        **_ASSISTANT_BURSAR_FINANCE,
        "dashboard_analytics": _r(),
    },
    UserRole.BURSAR: {
        **_BURSAR_FINANCE,
        "dashboard_analytics": _rw(),
    },
    UserRole.PARENT: {
        "parent_fee_statements": _r(),
        "student_billing": _deny(),
        "payment_recording": _deny(),
        "finance_analytics": _deny(),
        "financial_reports": _deny(),
        "bursar_workspace": _deny(),
        "assistant_bursar_workspace": _deny(),
        "transaction_approval": _deny(),
    },
}


def get_default_feature_permission(role: str, feature_key: str) -> dict[str, bool] | None:
    """Return default read/write for a role/feature, or None to inherit module level."""
    canonical = normalize_role(role)
    perms = DEFAULT_ROLE_FEATURE_PERMISSIONS.get(canonical, {}).get(feature_key)
    if perms is None:
        return None
    return perms.copy()


def merge_class_teacher_feature_permissions(
    base: dict[str, dict[str, bool]],
    *,
    is_class_teacher: bool,
) -> dict[str, dict[str, bool]]:
    """Elevate class-teacher feature flags when the user is assigned to a class."""
    if not is_class_teacher:
        return base
    merged = {key: value.copy() for key, value in base.items()}
    for feature_key, perms in _CLASS_TEACHER_EXTRA.items():
        existing = merged.get(feature_key, {"can_read": False, "can_write": False})
        merged[feature_key] = {
            "can_read": existing.get("can_read") or perms["can_read"],
            "can_write": existing.get("can_write") or perms["can_write"],
        }
    return merged