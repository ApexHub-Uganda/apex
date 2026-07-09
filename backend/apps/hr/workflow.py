"""HR approval and review workflows."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.hr.constants import (
    LEAVE_APPROVED,
    LEAVE_PENDING,
    LEAVE_REJECTED,
    REVIEW_DRAFT,
    REVIEW_SUBMITTED,
)
from apps.hr.models import Leave, PerformanceReview
from apps.hr.scoping import user_can_manage_leave_requests, user_can_manage_performance_reviews


class HRWorkflowError(Exception):
    def __init__(self, message: str, *, code: str = "hr_workflow_error"):
        self.message = message
        self.code = code
        super().__init__(message)


@transaction.atomic
def approve_leave(*, leave: Leave, user) -> Leave:
    if not user_can_manage_leave_requests(user, leave.tenant):
        raise HRWorkflowError("Leave request write permission required.", code="forbidden_approve")
    if leave.status != LEAVE_PENDING:
        raise HRWorkflowError("Only pending leave requests can be approved.", code="invalid_status")
    leave.status = LEAVE_APPROVED
    leave.approved_by = user
    leave.approval_date = timezone.localdate()
    leave.rejection_reason = ""
    leave.updated_by = user
    leave.save(update_fields=[
        "status", "approved_by", "approval_date", "rejection_reason", "updated_by", "updated_at",
    ])
    return leave


@transaction.atomic
def reject_leave(*, leave: Leave, user, reason: str = "") -> Leave:
    if not user_can_manage_leave_requests(user, leave.tenant):
        raise HRWorkflowError("Leave request write permission required.", code="forbidden_reject")
    if leave.status != LEAVE_PENDING:
        raise HRWorkflowError("Only pending leave requests can be rejected.", code="invalid_status")
    leave.status = LEAVE_REJECTED
    leave.approved_by = user
    leave.approval_date = timezone.localdate()
    leave.rejection_reason = (reason or "").strip()
    leave.updated_by = user
    leave.save(update_fields=[
        "status", "approved_by", "approval_date", "rejection_reason", "updated_by", "updated_at",
    ])
    return leave


@transaction.atomic
def bulk_leave_action(*, tenant, user, action: str, leave_ids: list) -> dict:
    if action not in {"approve", "reject"}:
        raise HRWorkflowError("Invalid bulk action.", code="invalid_action")
    if not user_can_manage_leave_requests(user, tenant):
        raise HRWorkflowError("Leave request write permission required.", code="forbidden")

    leaves = list(
        Leave.objects.filter(
            tenant=tenant,
            is_deleted=False,
            id__in=leave_ids,
            status=LEAVE_PENDING,
        )
    )
    if not leaves:
        raise HRWorkflowError("No pending leave requests found.", code="not_found")

    processed = []
    for leave in leaves:
        if action == "approve":
            approve_leave(leave=leave, user=user)
        else:
            reject_leave(leave=leave, user=user, reason="Bulk rejection")
        processed.append(str(leave.id))

    return {"processed": processed, "count": len(processed)}


@transaction.atomic
def submit_performance_review(*, review: PerformanceReview, user) -> PerformanceReview:
    if not user_can_manage_performance_reviews(user, review.tenant):
        raise HRWorkflowError("Performance review write permission required.", code="forbidden_submit")
    if review.status != REVIEW_DRAFT:
        raise HRWorkflowError("Only draft reviews can be submitted.", code="invalid_status")
    review.status = REVIEW_SUBMITTED
    review.submitted_at = timezone.now()
    review.updated_by = user
    review.save(update_fields=["status", "submitted_at", "updated_by", "updated_at"])
    return review