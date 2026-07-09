"""Hostel allocation and occupancy workflows."""
from __future__ import annotations

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from apps.hostel.constants import (
    ALLOCATION_ACTIVE,
    ALLOCATION_CHECKED_IN,
    ALLOCATION_CHECKED_OUT,
    ALLOCATION_OCCUPYING_STATUSES,
    ALLOCATION_PENDING,
    ALLOCATION_VACATED,
    MAINTENANCE_COMPLETED,
    MAINTENANCE_IN_PROGRESS,
    MAINTENANCE_OPEN_STATUSES,
    MAINTENANCE_REPORTED,
    VISITOR_CHECKED_IN,
    VISITOR_CHECKED_OUT,
)
from apps.hostel.models import Allocation, HostelMaintenance, HostelVisitor, Room
from apps.tenants.role_permissions import user_can_access_feature, user_is_school_admin


class HostelWorkflowError(Exception):
    def __init__(self, message: str, *, code: str = "hostel_workflow_error"):
        self.message = message
        self.code = code
        super().__init__(message)


def _sync_room_occupancy(room: Room) -> None:
    occupied = Allocation.objects.filter(
        room=room,
        is_deleted=False,
        status__in=ALLOCATION_OCCUPYING_STATUSES,
    ).count()
    room.occupied = occupied
    room.is_available = occupied < room.capacity
    room.save(update_fields=["occupied", "is_available", "updated_at"])


def _require_allocation_write(user, tenant) -> None:
    if user_is_school_admin(user):
        return
    if not user_can_access_feature(tenant, user, "room_allocation", require_write=True):
        raise HostelWorkflowError("Room allocation write permission required.", code="forbidden")


@transaction.atomic
def allocate_room(
    *,
    tenant,
    student,
    room: Room,
    user,
    start_date=None,
    bed_number: str = "",
    notes: str = "",
) -> Allocation:
    _require_allocation_write(user, tenant)
    if room.occupied >= room.capacity:
        raise HostelWorkflowError("Room is at full capacity.", code="room_full")
    active = Allocation.objects.filter(
        tenant=tenant,
        student=student,
        is_deleted=False,
        status__in=ALLOCATION_OCCUPYING_STATUSES,
    ).exists()
    if active:
        raise HostelWorkflowError("Student already has an active hostel allocation.", code="already_allocated")

    allocation = Allocation.objects.create(
        tenant=tenant,
        student=student,
        room=room,
        start_date=start_date or timezone.localdate(),
        status=ALLOCATION_ACTIVE,
        bed_number=(bed_number or "").strip(),
        notes=(notes or "").strip(),
        created_by=user,
        updated_by=user,
    )
    _sync_room_occupancy(room)
    return allocation


@transaction.atomic
def vacate_allocation(*, allocation: Allocation, user, end_date=None) -> Allocation:
    _require_allocation_write(user, allocation.tenant)
    if allocation.status == ALLOCATION_VACATED:
        raise HostelWorkflowError("Allocation is already vacated.", code="already_vacated")
    allocation.status = ALLOCATION_VACATED
    allocation.end_date = end_date or timezone.localdate()
    allocation.updated_by = user
    allocation.save(update_fields=["status", "end_date", "updated_by", "updated_at"])
    _sync_room_occupancy(allocation.room)
    return allocation


@transaction.atomic
def check_in(*, allocation: Allocation, user) -> Allocation:
    _require_allocation_write(user, allocation.tenant)
    if allocation.status not in {ALLOCATION_PENDING, ALLOCATION_ACTIVE}:
        raise HostelWorkflowError("Only pending or active allocations can be checked in.", code="invalid_status")
    allocation.status = ALLOCATION_CHECKED_IN
    allocation.checked_in_at = timezone.now()
    allocation.updated_by = user
    allocation.save(update_fields=["status", "checked_in_at", "updated_by", "updated_at"])
    _sync_room_occupancy(allocation.room)
    return allocation


@transaction.atomic
def check_out(*, allocation: Allocation, user) -> Allocation:
    _require_allocation_write(user, allocation.tenant)
    if allocation.status != ALLOCATION_CHECKED_IN:
        raise HostelWorkflowError("Only checked-in allocations can be checked out.", code="invalid_status")
    allocation.status = ALLOCATION_CHECKED_OUT
    allocation.checked_out_at = timezone.now()
    allocation.updated_by = user
    allocation.save(update_fields=["status", "checked_out_at", "updated_by", "updated_at"])
    _sync_room_occupancy(allocation.room)
    return allocation


def _require_visitor_write(user, tenant) -> None:
    if user_is_school_admin(user):
        return
    if not user_can_access_feature(tenant, user, "hostel_visitors", require_write=True):
        raise HostelWorkflowError("Hostel visitor write permission required.", code="forbidden")


def _require_maintenance_write(user, tenant) -> None:
    if user_is_school_admin(user):
        return
    if not user_can_access_feature(tenant, user, "hostel_maintenance", require_write=True):
        raise HostelWorkflowError("Hostel maintenance write permission required.", code="forbidden")


@transaction.atomic
def resolve_maintenance(*, maintenance: HostelMaintenance, user) -> HostelMaintenance:
    _require_maintenance_write(user, maintenance.tenant)
    if maintenance.status not in MAINTENANCE_OPEN_STATUSES:
        raise HostelWorkflowError("Only open maintenance requests can be resolved.", code="invalid_status")
    maintenance.status = MAINTENANCE_COMPLETED
    maintenance.completed_at = timezone.now()
    maintenance.updated_by = user
    maintenance.save(update_fields=["status", "completed_at", "updated_by", "updated_at"])
    return maintenance


@transaction.atomic
def assign_maintenance(*, maintenance: HostelMaintenance, user, assigned_to) -> HostelMaintenance:
    _require_maintenance_write(user, maintenance.tenant)
    if maintenance.status not in {MAINTENANCE_REPORTED, MAINTENANCE_IN_PROGRESS}:
        raise HostelWorkflowError("Maintenance request cannot be assigned.", code="invalid_status")
    maintenance.status = MAINTENANCE_IN_PROGRESS
    maintenance.assigned_to = assigned_to
    maintenance.updated_by = user
    maintenance.save(update_fields=["status", "assigned_to", "updated_by", "updated_at"])
    return maintenance


@transaction.atomic
def check_out_visitor(*, visitor: HostelVisitor, user) -> HostelVisitor:
    _require_visitor_write(user, visitor.tenant)
    if visitor.status != VISITOR_CHECKED_IN:
        raise HostelWorkflowError("Only checked-in visitors can be checked out.", code="invalid_status")
    visitor.status = VISITOR_CHECKED_OUT
    visitor.check_out_time = timezone.now()
    visitor.updated_by = user
    visitor.save(update_fields=["status", "check_out_time", "updated_by", "updated_at"])
    return visitor