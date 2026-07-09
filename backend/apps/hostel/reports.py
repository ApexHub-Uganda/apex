"""Hostel summary and typed reports."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from django.db.models import Sum
from django.utils import timezone

from apps.hostel.constants import ALLOCATION_OCCUPYING_STATUSES, MAINTENANCE_OPEN_STATUSES
from apps.hostel.models import Allocation, Hostel, HostelFee, HostelMaintenance, HostelVisitor, Room


def build_hostel_reports(
    *,
    tenant,
    hostel_ids: list | None = None,
    report_type: str = "occupancy",
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    today = timezone.localdate()
    start = start_date or (today - timedelta(days=30))
    end = end_date or today

    hostels = Hostel.objects.filter(tenant=tenant, is_deleted=False)
    if hostel_ids:
        hostels = hostels.filter(id__in=hostel_ids)

    rooms = Room.objects.filter(tenant=tenant, is_deleted=False, hostel__in=hostels)
    total_capacity = rooms.aggregate(total=Sum("capacity"))["total"] or 0
    total_occupied = rooms.aggregate(total=Sum("occupied"))["total"] or 0
    active_allocations = Allocation.objects.filter(
        tenant=tenant,
        is_deleted=False,
        room__hostel__in=hostels,
        status__in=ALLOCATION_OCCUPYING_STATUSES,
    ).count()
    pending_fees = HostelFee.objects.filter(
        tenant=tenant,
        is_deleted=False,
        hostel__in=hostels,
        status__in=["pending", "partial", "overdue"],
    ).count()

    occupancy_rate = round((total_occupied / total_capacity) * 100, 1) if total_capacity else 0.0

    payload: dict[str, Any] = {
        "report_type": report_type,
        "period": {"start": str(start), "end": str(end)},
        "generated_at": timezone.now().isoformat(),
        "summary": {
            "hostels": hostels.count(),
            "rooms": rooms.count(),
            "total_capacity": total_capacity,
            "total_occupied": total_occupied,
            "occupancy_rate": occupancy_rate,
            "active_allocations": active_allocations,
            "pending_fees": pending_fees,
        },
        "rows": [],
        "totals": {},
        "by_hostel": [
            {
                "id": str(h.id),
                "name": h.name,
                "capacity": h.capacity,
                "total_rooms": h.total_rooms,
            }
            for h in hostels
        ],
    }

    if report_type == "occupancy":
        rows = []
        for hostel in hostels:
            h_rooms = rooms.filter(hostel=hostel)
            h_capacity = h_rooms.aggregate(total=Sum("capacity"))["total"] or 0
            h_occupied = h_rooms.aggregate(occ=Sum("occupied"))["occ"] or 0
            rows.append({
                "hostel_name": hostel.name,
                "rooms": h_rooms.count(),
                "capacity": h_capacity,
                "occupied": h_occupied,
                "occupancy_rate": round((h_occupied / h_capacity) * 100, 1) if h_capacity else 0.0,
            })
        payload["rows"] = rows
        payload["totals"] = {"hostels": len(rows)}

    elif report_type == "maintenance":
        records = HostelMaintenance.objects.filter(
            tenant=tenant,
            is_deleted=False,
            hostel__in=hostels,
            reported_at__date__gte=start,
            reported_at__date__lte=end,
        ).select_related("hostel", "room").order_by("-reported_at")
        payload["rows"] = [
            {
                "reported_at": row.reported_at.date().isoformat(),
                "hostel": row.hostel.name if row.hostel_id else "",
                "title": row.title,
                "priority": row.priority,
                "status": row.status,
            }
            for row in records
        ]
        payload["totals"] = {
            "count": records.count(),
            "open": records.filter(status__in=MAINTENANCE_OPEN_STATUSES).count(),
        }

    elif report_type == "visitors":
        records = HostelVisitor.objects.filter(
            tenant=tenant,
            is_deleted=False,
            hostel__in=hostels,
            check_in_time__date__gte=start,
            check_in_time__date__lte=end,
        ).select_related("hostel", "student").order_by("-check_in_time")
        payload["rows"] = [
            {
                "check_in_time": row.check_in_time.date().isoformat() if row.check_in_time else "",
                "hostel": row.hostel.name if row.hostel_id else "",
                "visitor_name": row.visitor_name,
                "student": row.student.full_name if row.student_id else "",
                "purpose": row.purpose,
                "status": row.status,
            }
            for row in records
        ]
        payload["totals"] = {"count": records.count()}

    elif report_type == "fees":
        records = HostelFee.objects.filter(
            tenant=tenant,
            is_deleted=False,
            hostel__in=hostels,
            due_date__gte=start,
            due_date__lte=end,
        ).select_related("hostel", "student").order_by("-due_date")
        payload["rows"] = [
            {
                "due_date": str(row.due_date),
                "hostel": row.hostel.name if row.hostel_id else "",
                "student": row.student.full_name if row.student_id else "",
                "amount": str(row.amount),
                "amount_paid": str(row.amount_paid),
                "status": row.status,
            }
            for row in records
        ]
        payload["totals"] = {"count": records.count()}

    return payload