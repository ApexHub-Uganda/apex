"""Student promotion engine — bulk promote / hold / graduate with placement history."""
from __future__ import annotations

import re
from datetime import date
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.academics.models import (
    AcademicYear,
    Class,
    PromotionAction,
    PromotionBatch,
    Stream,
    StudentAcademicPlacement,
)
from apps.audit.models import AuditLog
from apps.students.models import Student

# Common terminal class markers (Uganda / Kenya / generic)
_TERMINAL_CODE_RE = re.compile(
    r"(?:^|[^a-z0-9])(p7|p\.?7|primary\s*7|s4|s\.?4|s6|s\.?6|form\s*4|form\s*6|"
    r"grade\s*12|g12|std\s*8|standard\s*8|year\s*13)(?:[^a-z0-9]|$)",
    re.I,
)
_LEVEL_TOKEN_RE = re.compile(
    r"(?:^|[^a-z0-9])(p|s|form|grade|g|std|standard|year|class)\s*\.?(\d{1,2})(?:[^a-z0-9]|$)",
    re.I,
)


class PromotionError(Exception):
    def __init__(self, message: str, *, code: str = "promotion_error"):
        self.message = message
        self.code = code
        super().__init__(message)


def _class_tokens(school_class: Class) -> tuple[str | None, int | None]:
    """Extract (prefix, number) from class code/name e.g. ('P', 6), ('S', 3)."""
    for text in (school_class.code or "", school_class.name or ""):
        m = _LEVEL_TOKEN_RE.search(text.replace("_", " "))
        if m:
            prefix = m.group(1).lower()
            if prefix in {"std", "standard"}:
                prefix = "p"
            if prefix in {"form", "year", "class", "g", "grade"}:
                # map loosely: form/grade numbers often secondary
                prefix = "s" if int(m.group(2)) <= 6 else "g"
            return prefix, int(m.group(2))
    return None, None


def is_terminal_class(school_class: Class) -> bool:
    """Heuristic: top/final class in a pathway (P7, S4, S6, Grade 12, etc.)."""
    blob = f"{school_class.code or ''} {school_class.name or ''}"
    if _TERMINAL_CODE_RE.search(blob):
        return True
    prefix, num = _class_tokens(school_class)
    if prefix == "p" and num == 7:
        return True
    if prefix == "s" and num in {4, 6}:
        return True
    if prefix == "g" and num == 12:
        return True
    return False


def suggest_next_class(
    *,
    tenant,
    source_class: Class,
    target_academic_year: AcademicYear | None = None,
) -> Class | None:
    """
    Suggest the next class after *source_class* for promotion.

    Prefers same level_type and curriculum within the target (or current) year,
    matching incremented level tokens (P5→P6, S2→S3). Returns None for terminal classes.
    """
    if is_terminal_class(source_class):
        return None

    prefix, num = _class_tokens(source_class)
    if prefix is None or num is None:
        return None

    year = target_academic_year or source_class.academic_year
    candidates = Class.objects.filter(
        tenant=tenant,
        academic_year=year,
        is_deleted=False,
    )
    if source_class.level_type:
        same_level = candidates.filter(level_type=source_class.level_type)
        if same_level.exists():
            candidates = same_level
    if source_class.curriculum:
        same_curr = candidates.filter(curriculum=source_class.curriculum)
        if same_curr.exists():
            candidates = same_curr

    next_num = num + 1
    for c in candidates.order_by("name"):
        if c.pk == source_class.pk:
            continue
        c_prefix, c_num = _class_tokens(c)
        if c_prefix == prefix and c_num == next_num:
            return c
    return None


def class_progression_meta(*, tenant, school_class: Class, target_year: AcademicYear | None = None) -> dict[str, Any]:
    """Metadata for promotion UI: terminal flag + suggested next class."""
    terminal = is_terminal_class(school_class)
    nxt = None if terminal else suggest_next_class(
        tenant=tenant, source_class=school_class, target_academic_year=target_year,
    )
    return {
        "is_terminal": terminal,
        "default_action": "graduate" if terminal else "promote",
        "suggested_next_class_id": str(nxt.id) if nxt else None,
        "suggested_next_class_name": nxt.name if nxt else None,
        "suggested_next_class_code": nxt.code if nxt else None,
    }


def _log(*, tenant, user, action: str, resource_type: str, resource_id: str, description: str, changes=None, request=None):
    ip = None
    path = ""
    method = ""
    ua = ""
    if request is not None:
        ip = (request.META.get("HTTP_X_FORWARDED_FOR", "") or "").split(",")[0].strip() or request.META.get("REMOTE_ADDR")
        path = (request.path or "")[:500]
        method = request.method or ""
        ua = (request.META.get("HTTP_USER_AGENT") or "")[:500]
    AuditLog.objects.create(
        tenant=tenant,
        user=user if getattr(user, "is_authenticated", False) else None,
        action=action[:50],
        resource_type=resource_type[:100],
        resource_id=str(resource_id)[:100],
        description=description,
        changes=changes or {},
        ip_address=ip or None,
        user_agent=ua,
        request_method=method[:10],
        request_path=path,
        status_code=200,
    )


def ensure_placement_for_student(*, tenant, student, academic_year=None) -> StudentAcademicPlacement | None:
    """Ensure a current placement row exists for the student's current class."""
    if not student.school_class_id:
        return None
    year = academic_year or student.school_class.academic_year
    placement, created = StudentAcademicPlacement.objects.get_or_create(
        tenant=tenant,
        student=student,
        academic_year=year,
        school_class_id=student.school_class_id,
        stream_id=student.stream_id,
        defaults={
            "status": StudentAcademicPlacement.STATUS_ACTIVE,
            "is_current": True,
            "enrolled_on": student.enrollment_date or timezone.localdate(),
        },
    )
    if not created and not placement.is_current:
        StudentAcademicPlacement.objects.filter(
            tenant=tenant, student=student, is_current=True, is_deleted=False,
        ).exclude(pk=placement.pk).update(is_current=False)
        placement.is_current = True
        placement.status = StudentAcademicPlacement.STATUS_ACTIVE
        placement.save(update_fields=["is_current", "status", "updated_at"])
    return placement


def _students_for_source(*, tenant, source_class, source_stream=None):
    qs = Student.objects.filter(
        tenant=tenant,
        school_class=source_class,
        is_deleted=False,
        status="active",
    ).select_related("school_class", "stream").order_by("last_name", "first_name")
    if source_stream is not None:
        qs = qs.filter(stream=source_stream)
    return list(qs)


@transaction.atomic
def preview_promotion(
    *,
    tenant,
    user,
    source_class_id,
    source_stream_id=None,
    target_class_id=None,
    target_stream_id=None,
    target_academic_year_id=None,
    actions: list[dict] | None = None,
    notes: str = "",
    request=None,
) -> dict[str, Any]:
    source_class = Class.objects.filter(tenant=tenant, pk=source_class_id, is_deleted=False).first()
    if not source_class:
        raise PromotionError("Source class not found.", code="class_not_found")
    source_stream = None
    if source_stream_id:
        source_stream = Stream.objects.filter(tenant=tenant, pk=source_stream_id, school_class=source_class).first()

    target_class = None
    if target_class_id:
        target_class = Class.objects.filter(tenant=tenant, pk=target_class_id, is_deleted=False).first()
        if not target_class:
            raise PromotionError("Target class not found.", code="target_not_found")

    target_stream = None
    if target_stream_id and target_class:
        target_stream = Stream.objects.filter(tenant=tenant, pk=target_stream_id, school_class=target_class).first()

    target_year = None
    if target_academic_year_id:
        target_year = AcademicYear.objects.filter(tenant=tenant, pk=target_academic_year_id, is_deleted=False).first()
    if target_year is None and target_class is not None:
        target_year = target_class.academic_year

    # Auto-map next class when not provided
    if target_class is None:
        target_class = suggest_next_class(
            tenant=tenant,
            source_class=source_class,
            target_academic_year=target_year,
        )
        if target_class is not None and target_year is None:
            target_year = target_class.academic_year

    progression = class_progression_meta(
        tenant=tenant, school_class=source_class, target_year=target_year,
    )
    default_action = (
        PromotionAction.ACTION_GRADUATE
        if progression["is_terminal"]
        else PromotionAction.ACTION_PROMOTE
    )

    students = _students_for_source(tenant=tenant, source_class=source_class, source_stream=source_stream)
    action_map = {str(a.get("student_id") or a.get("student")): a for a in (actions or []) if a}

    rows = []
    for st in students:
        override = action_map.get(str(st.id), {})
        action = override.get("action") or default_action
        if action not in {
            PromotionAction.ACTION_PROMOTE,
            PromotionAction.ACTION_HOLD,
            PromotionAction.ACTION_GRADUATE,
            PromotionAction.ACTION_SKIP,
        }:
            action = default_action

        to_class_id = override.get("to_class") or (str(target_class.id) if target_class else None)
        to_stream_id = override.get("to_stream") or (str(target_stream.id) if target_stream else None)
        if action == PromotionAction.ACTION_HOLD:
            to_class_id = str(source_class.id)
            to_stream_id = str(source_stream.id) if source_stream else (str(st.stream_id) if st.stream_id else None)
        if action == PromotionAction.ACTION_GRADUATE:
            to_class_id = None
            to_stream_id = None
        if action == PromotionAction.ACTION_PROMOTE and not to_class_id:
            raise PromotionError(
                f"Target class required to promote {st.admission_number}. "
                "Select a target class, or mark terminal classes as Graduate.",
                code="target_required",
            )

        rows.append({
            "student_id": str(st.id),
            "admission_number": st.admission_number,
            "full_name": st.full_name,
            "action": action,
            "from_class_id": str(source_class.id),
            "from_class_name": source_class.name,
            "from_stream_id": str(st.stream_id) if st.stream_id else None,
            "from_stream_name": st.stream.name if st.stream_id else None,
            "to_class_id": to_class_id,
            "to_stream_id": to_stream_id,
            "reason": override.get("reason") or "",
        })

    batch = PromotionBatch.objects.create(
        tenant=tenant,
        academic_year=source_class.academic_year,
        target_academic_year=target_year,
        source_class=source_class,
        source_stream=source_stream,
        default_target_class=target_class,
        default_target_stream=target_stream,
        status=PromotionBatch.STATUS_PREVIEWED,
        mapping={"rows": rows},
        preview={
            "count": len(rows),
            "promote": sum(1 for r in rows if r["action"] == "promote"),
            "hold": sum(1 for r in rows if r["action"] == "hold"),
            "graduate": sum(1 for r in rows if r["action"] == "graduate"),
            "skip": sum(1 for r in rows if r["action"] == "skip"),
        },
        notes=notes or "",
        created_by=user,
        updated_by=user,
    )

    for r in rows:
        PromotionAction.objects.create(
            tenant=tenant,
            batch=batch,
            student_id=r["student_id"],
            action=r["action"],
            from_class_id=r["from_class_id"],
            from_stream_id=r["from_stream_id"],
            to_class_id=r["to_class_id"],
            to_stream_id=r["to_stream_id"],
            reason=r["reason"],
            created_by=user,
            updated_by=user,
        )

    _log(
        tenant=tenant, user=user, action="promotion_preview",
        resource_type="PromotionBatch", resource_id=str(batch.id),
        description=f"Preview promotion from {source_class.name}: {len(rows)} students",
        changes=batch.preview, request=request,
    )
    return {
        "batch_id": str(batch.id),
        "status": batch.status,
        "preview": batch.preview,
        "rows": rows,
        "source_class": {"id": str(source_class.id), "name": source_class.name},
        "target_class": {"id": str(target_class.id), "name": target_class.name} if target_class else None,
        "target_academic_year": {"id": str(target_year.id), "name": target_year.name} if target_year else None,
        "progression": progression,
    }


@transaction.atomic
def commit_promotion(
    *,
    tenant,
    user,
    batch_id,
    request=None,
    issue_certificates: bool = False,
) -> dict[str, Any]:
    batch = (
        PromotionBatch.objects.select_for_update()
        .filter(tenant=tenant, pk=batch_id, is_deleted=False)
        .select_related("source_class", "target_academic_year")
        .first()
    )
    if not batch:
        raise PromotionError("Promotion batch not found.", code="batch_not_found")
    if batch.status == PromotionBatch.STATUS_COMMITTED:
        raise PromotionError("Batch already committed.", code="already_committed")
    if batch.status == PromotionBatch.STATUS_UNDONE:
        raise PromotionError("Batch was undone; create a new preview.", code="batch_undone")

    today = timezone.localdate()
    applied = 0
    actions = list(
        PromotionAction.objects.filter(tenant=tenant, batch=batch, is_deleted=False)
        .select_related("student", "from_class", "to_class", "to_stream")
    )
    for act in actions:
        student = act.student
        # Close current placements
        StudentAcademicPlacement.objects.filter(
            tenant=tenant, student=student, is_current=True, is_deleted=False,
        ).update(is_current=False, ended_on=today, status=StudentAcademicPlacement.STATUS_PROMOTED
                 if act.action == PromotionAction.ACTION_PROMOTE
                 else StudentAcademicPlacement.STATUS_REPEATED
                 if act.action == PromotionAction.ACTION_HOLD
                 else StudentAcademicPlacement.STATUS_GRADUATED
                 if act.action == PromotionAction.ACTION_GRADUATE
                 else StudentAcademicPlacement.STATUS_ACTIVE)

        if act.action == PromotionAction.ACTION_SKIP:
            act.applied = True
            act.save(update_fields=["applied", "updated_at"])
            continue

        if act.action == PromotionAction.ACTION_GRADUATE:
            student.status = "graduated"
            student.school_class = None
            student.stream = None
            student.save(update_fields=["status", "school_class", "stream", "updated_at"])
            placement = StudentAcademicPlacement.objects.create(
                tenant=tenant,
                student=student,
                academic_year=batch.academic_year,
                school_class=act.from_class or batch.source_class,
                stream=act.from_stream,
                status=StudentAcademicPlacement.STATUS_GRADUATED,
                is_current=False,
                enrolled_on=None,
                ended_on=today,
                notes=act.reason or "Graduated",
                created_by=user,
                updated_by=user,
            )
            act.placement = placement
            act.applied = True
            act.save(update_fields=["placement", "applied", "updated_at"])
            applied += 1
            continue

        if act.action == PromotionAction.ACTION_HOLD:
            # Stay in same class/stream; record repeated placement for same or next year
            year = batch.target_academic_year or batch.academic_year
            student.school_class = act.from_class or batch.source_class
            student.stream = act.from_stream
            student.status = "active"
            student.save(update_fields=["school_class", "stream", "status", "updated_at"])
            placement = StudentAcademicPlacement.objects.create(
                tenant=tenant,
                student=student,
                academic_year=year,
                school_class=student.school_class,
                stream=student.stream,
                status=StudentAcademicPlacement.STATUS_REPEATED,
                is_current=True,
                enrolled_on=today,
                notes=act.reason or "Held back",
                created_by=user,
                updated_by=user,
            )
            act.placement = placement
            act.applied = True
            act.save(update_fields=["placement", "applied", "updated_at"])
            applied += 1
            continue

        # PROMOTE
        to_class = act.to_class
        if to_class is None:
            raise PromotionError(f"Missing target class for {student.admission_number}.", code="target_required")
        student.school_class = to_class
        student.stream = act.to_stream
        student.status = "active"
        student.save(update_fields=["school_class", "stream", "status", "updated_at"])
        year = batch.target_academic_year or to_class.academic_year
        placement = StudentAcademicPlacement.objects.create(
            tenant=tenant,
            student=student,
            academic_year=year,
            school_class=to_class,
            stream=act.to_stream,
            status=StudentAcademicPlacement.STATUS_ACTIVE,
            is_current=True,
            enrolled_on=today,
            notes=act.reason or "Promoted",
            created_by=user,
            updated_by=user,
        )
        act.placement = placement
        act.applied = True
        act.save(update_fields=["placement", "applied", "updated_at"])
        applied += 1

    batch.status = PromotionBatch.STATUS_COMMITTED
    batch.committed_at = timezone.now()
    batch.committed_by = user
    batch.updated_by = user
    batch.save(update_fields=["status", "committed_at", "committed_by", "updated_by", "updated_at"])

    graduated_student_ids: list[str] = []
    for act in actions:
        if act.action == PromotionAction.ACTION_GRADUATE and act.applied:
            graduated_student_ids.append(str(act.student_id))

    certificates: list[dict[str, Any]] = []
    if issue_certificates and graduated_student_ids:
        # Certificates are issued on demand via PDF endpoints; return IDs for the UI to download.
        for sid in graduated_student_ids:
            certificates.append({
                "student_id": sid,
                "types": ["completion", "leaving", "transcript"],
            })

    _log(
        tenant=tenant, user=user, action="promotion_commit",
        resource_type="PromotionBatch", resource_id=str(batch.id),
        description=f"Committed promotion: {applied} student(s)",
        changes={"applied": applied, "graduated": len(graduated_student_ids)},
        request=request,
    )
    return {
        "batch_id": str(batch.id),
        "status": batch.status,
        "applied": applied,
        "graduated": len(graduated_student_ids),
        "graduated_student_ids": graduated_student_ids,
        "certificates": certificates,
        "issue_certificates": issue_certificates,
        "committed_at": batch.committed_at.isoformat(),
    }


@transaction.atomic
def undo_promotion(*, tenant, user, batch_id, request=None) -> dict[str, Any]:
    """Undo a committed batch only if no grades exist for students in their new class after commit."""
    batch = (
        PromotionBatch.objects.select_for_update()
        .filter(tenant=tenant, pk=batch_id, is_deleted=False)
        .first()
    )
    if not batch:
        raise PromotionError("Promotion batch not found.", code="batch_not_found")
    if batch.status != PromotionBatch.STATUS_COMMITTED:
        raise PromotionError("Only committed batches can be undone.", code="invalid_status")

    from apps.examinations.models import Grade

    actions = list(
        PromotionAction.objects.filter(tenant=tenant, batch=batch, applied=True, is_deleted=False)
        .select_related("student", "from_class", "from_stream", "to_class")
    )
    # Block undo if any student has grades entered after promotion in new class
    for act in actions:
        if act.action == PromotionAction.ACTION_PROMOTE and act.to_class_id:
            if Grade.objects.filter(
                tenant=tenant,
                student=act.student,
                is_deleted=False,
                exam__school_class_id=act.to_class_id,
                created_at__gte=batch.committed_at,
            ).exists():
                raise PromotionError(
                    f"Cannot undo: {act.student.admission_number} already has marks in the new class.",
                    code="marks_exist",
                )

    today = timezone.localdate()
    restored = 0
    for act in actions:
        student = act.student
        # Mark post-promotion placements not current
        StudentAcademicPlacement.objects.filter(
            tenant=tenant, student=student, is_current=True, is_deleted=False,
        ).update(is_current=False, ended_on=today)

        if act.action == PromotionAction.ACTION_GRADUATE:
            student.status = "active"
        student.school_class = act.from_class
        student.stream = act.from_stream
        student.status = "active"
        student.save(update_fields=["school_class", "stream", "status", "updated_at"])
        if act.from_class_id:
            StudentAcademicPlacement.objects.create(
                tenant=tenant,
                student=student,
                academic_year=batch.academic_year,
                school_class=act.from_class,
                stream=act.from_stream,
                status=StudentAcademicPlacement.STATUS_ACTIVE,
                is_current=True,
                enrolled_on=today,
                notes="Restored by promotion undo",
                created_by=user,
                updated_by=user,
            )
        restored += 1

    batch.status = PromotionBatch.STATUS_UNDONE
    batch.undone_at = timezone.now()
    batch.undone_by = user
    batch.updated_by = user
    batch.save(update_fields=["status", "undone_at", "undone_by", "updated_by", "updated_at"])

    _log(
        tenant=tenant, user=user, action="promotion_undo",
        resource_type="PromotionBatch", resource_id=str(batch.id),
        description=f"Undid promotion for {restored} student(s)",
        changes={"restored": restored}, request=request,
    )
    return {"batch_id": str(batch.id), "status": batch.status, "restored": restored}
