"""Hostel summary and typed reports (aligned to current models)."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from django.db.models import Sum
from django.utils import timezone

from apps.hostel.models import Allocation, Hostel, Room


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
        status__in=["active", "current", "occupied"],
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

    elif report_type in {"maintenance", "visitors", "fees"}:
        # Models for these report types are not present yet — return occupancy-style allocations.
        records = Allocation.objects.filter(
            tenant=tenant,
            is_deleted=False,
            room__hostel__in=hostels,
        ).select_related("student", "room", "room__hostel").order_by("-start_date")
        if start_date:
            records = records.filter(start_date__gte=start)
        if end_date:
            records = records.filter(start_date__lte=end)
        payload["rows"] = [
            {
                "start_date": str(row.start_date) if row.start_date else "",
                "end_date": str(row.end_date) if row.end_date else "",
                "hostel": row.room.hostel.name if row.room_id and row.room.hostel_id else "",
                "room": row.room.room_number if row.room_id else "",
                "student": row.student.full_name if row.student_id else "",
                "status": row.status,
                "bed_number": row.bed_number or "",
            }
            for row in records
        ]
        payload["totals"] = {"count": records.count()}
        payload["summary"]["note"] = (
            f"Detailed '{report_type}' entities are not available yet; "
            "showing room allocations for the selected period."
        )

    return payload
