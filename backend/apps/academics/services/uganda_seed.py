"""Uganda-first presets: assessment schemes, combinations, optional term templates."""
from __future__ import annotations

from datetime import date
from typing import Any

from apps.academics.models import AssessmentScheme, SubjectCombination
from apps.examinations.models import GradingScheme, GradingSchemeBand


UGANDA_ASSESSMENT_PRESETS = [
    {
        "name": "BOT / MOT / EOT (30/70)",
        "description": "Uganda secondary continuous assessment: BOT+MOT continuous, EOT weighted 70%.",
        "is_default": True,
        "components": [
            {"key": "bot", "label": "BOT", "weight_percent": 15, "exam_type_hint": "continuous"},
            {"key": "mot", "label": "MOT", "weight_percent": 15, "exam_type_hint": "midterm"},
            {"key": "eot", "label": "EOT", "weight_percent": 70, "exam_type_hint": "final"},
        ],
        "paper_aggregation": "average",
        "use_division_bands": True,
        "division_bands": [
            {"min_aggregate": 4, "max_aggregate": 12, "division": "I", "remarks": "Distinction"},
            {"min_aggregate": 13, "max_aggregate": 24, "division": "II", "remarks": "Credit"},
            {"min_aggregate": 25, "max_aggregate": 32, "division": "III", "remarks": "Pass"},
            {"min_aggregate": 33, "max_aggregate": 36, "division": "IV", "remarks": "Pass"},
            {"min_aggregate": 37, "max_aggregate": 99, "division": "U", "remarks": "Ungraded"},
        ],
    },
    {
        "name": "CA1 / CA2 / CA3 + EOT",
        "description": "Three continuous assessments + end-of-term exam.",
        "is_default": False,
        "components": [
            {"key": "ca1", "label": "CA1", "weight_percent": 10, "exam_type_hint": "continuous"},
            {"key": "ca2", "label": "CA2", "weight_percent": 10, "exam_type_hint": "continuous"},
            {"key": "ca3", "label": "CA3", "weight_percent": 10, "exam_type_hint": "midterm"},
            {"key": "eot", "label": "EOT", "weight_percent": 70, "exam_type_hint": "final"},
        ],
        "paper_aggregation": "average",
        "use_division_bands": False,
        "division_bands": [],
    },
]

# Combination codes map to subject codes schools may create — stored as code refs only.
UGANDA_COMBINATIONS = [
    {"code": "PCM", "name": "Physics, Chemistry, Mathematics", "level": "a_level",
     "subjects": [{"code": "PHY", "is_core": True}, {"code": "CHE", "is_core": True}, {"code": "MATH", "is_core": True}],
     "description": "Common A-level science combination."},
    {"code": "PCB", "name": "Physics, Chemistry, Biology", "level": "a_level",
     "subjects": [{"code": "PHY", "is_core": True}, {"code": "CHE", "is_core": True}, {"code": "BIO", "is_core": True}],
     "description": "A-level science (PCB)."},
    {"code": "HEL", "name": "History, Economics, Literature", "level": "a_level",
     "subjects": [{"code": "HIST", "is_core": True}, {"code": "ECON", "is_core": True}, {"code": "LIT", "is_core": True}],
     "description": "A-level arts combination."},
    {"code": "MEG", "name": "Mathematics, Economics, Geography", "level": "a_level",
     "subjects": [{"code": "MATH", "is_core": True}, {"code": "ECON", "is_core": True}, {"code": "GEO", "is_core": True}],
     "description": "A-level MEG."},
    {"code": "O_CORE", "name": "O-Level Core Set", "level": "o_level",
     "subjects": [
         {"code": "ENG", "is_core": True}, {"code": "MATH", "is_core": True},
         {"code": "BIO", "is_core": False}, {"code": "CHE", "is_core": False},
         {"code": "PHY", "is_core": False}, {"code": "HIST", "is_core": False},
         {"code": "GEO", "is_core": False},
     ],
     "description": "Typical O-level core + electives (school customises)."},
]

UGANDA_GRADING_D1_F9 = [
    (80, 100, "D1", 1, "Distinction"),
    (75, 79.99, "D2", 2, "Distinction"),
    (70, 74.99, "C3", 3, "Credit"),
    (65, 69.99, "C4", 4, "Credit"),
    (60, 64.99, "C5", 5, "Credit"),
    (55, 59.99, "C6", 6, "Credit"),
    (50, 54.99, "P7", 7, "Pass"),
    (45, 49.99, "P8", 8, "Pass"),
    (0, 44.99, "F9", 9, "Fail"),
]


def seed_uganda_presets(*, tenant, user=None) -> dict[str, Any]:
    created = {"assessment_schemes": 0, "combinations": 0, "grading_schemes": 0}

    for preset in UGANDA_ASSESSMENT_PRESETS:
        obj, was_created = AssessmentScheme.objects.get_or_create(
            tenant=tenant,
            name=preset["name"],
            defaults={
                "description": preset["description"],
                "is_default": preset["is_default"],
                "components": preset["components"],
                "paper_aggregation": preset["paper_aggregation"],
                "use_division_bands": preset["use_division_bands"],
                "division_bands": preset["division_bands"],
                "created_by": user,
                "updated_by": user,
            },
        )
        if was_created:
            created["assessment_schemes"] += 1
        elif preset["is_default"] and not obj.is_default:
            AssessmentScheme.objects.filter(tenant=tenant, is_default=True).exclude(pk=obj.pk).update(is_default=False)
            obj.is_default = True
            obj.save(update_fields=["is_default", "updated_at"])

    for comb in UGANDA_COMBINATIONS:
        _, was_created = SubjectCombination.objects.get_or_create(
            tenant=tenant,
            code=comb["code"],
            defaults={
                "name": comb["name"],
                "level": comb["level"],
                "subjects": comb["subjects"],
                "description": comb["description"],
                "is_active": True,
                "created_by": user,
                "updated_by": user,
            },
        )
        if was_created:
            created["combinations"] += 1

    scheme, was_created = GradingScheme.objects.get_or_create(
        tenant=tenant,
        name="UNEB D1–F9",
        defaults={
            "description": "Uganda secondary 1–9 grade points (informal school use; not official UNEB scale).",
            "is_default": True,
            "created_by": user,
            "updated_by": user,
        },
    )
    if was_created:
        created["grading_schemes"] += 1
        for lo, hi, grade, gp, remark in UGANDA_GRADING_D1_F9:
            GradingSchemeBand.objects.create(
                tenant=tenant,
                scheme=scheme,
                min_score=lo,
                max_score=hi,
                grade=grade,
                grade_point=gp,
                remarks=remark,
                created_by=user,
                updated_by=user,
            )
        GradingScheme.objects.filter(tenant=tenant, is_default=True).exclude(pk=scheme.pk).update(is_default=False)

    return created


def uganda_term_templates(year: int = 2026) -> list[dict[str, Any]]:
    """Suggested term date templates for Ugandan calendar (schools may edit)."""
    return [
        {
            "name": "Term 1",
            "term_number": 1,
            "start_date": date(year, 2, 3),
            "end_date": date(year, 5, 2),
            "mid_term_break_start": date(year, 3, 17),
            "mid_term_break_end": date(year, 3, 28),
            "reporting_date": date(year, 2, 3),
            "closing_date": date(year, 5, 2),
        },
        {
            "name": "Term 2",
            "term_number": 2,
            "start_date": date(year, 5, 26),
            "end_date": date(year, 8, 22),
            "mid_term_break_start": date(year, 7, 7),
            "mid_term_break_end": date(year, 7, 18),
            "reporting_date": date(year, 5, 26),
            "closing_date": date(year, 8, 22),
        },
        {
            "name": "Term 3",
            "term_number": 3,
            "start_date": date(year, 9, 15),
            "end_date": date(year, 12, 5),
            "mid_term_break_start": date(year, 10, 20),
            "mid_term_break_end": date(year, 10, 27),
            "reporting_date": date(year, 9, 15),
            "closing_date": date(year, 12, 5),
        },
    ]
