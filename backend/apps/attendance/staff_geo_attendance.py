"""Staff self check-in / check-out with campus geofence."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.attendance.geofence import evaluate_location, geofence_payload, get_geofence
from apps.attendance.models import AttendanceRecord
from apps.staff.models import Staff


class StaffAttendanceError(Exception):
    def __init__(self, message: str, *, code: str = "staff_attendance_error"):
        self.message = message
        self.code = code
        super().__init__(message)


def staff_for_user(user) -> Staff | None:
    if not user:
        return None
    try:
        staff = user.staff_profile
        if staff and not staff.is_deleted:
            return staff
    except Exception:
        pass
    return Staff.objects.filter(user=user, is_deleted=False).first()


def today_record(*, tenant, staff: Staff):
    today = timezone.localdate()
    return AttendanceRecord.objects.filter(
        tenant=tenant,
        attendee_type="staff",
        staff=staff,
        date=today,
        is_deleted=False,
    ).first()


def staff_attendance_status(*, tenant, user) -> dict[str, Any]:
    staff = staff_for_user(user)
    fence = get_geofence(tenant)
    payload = {
        "has_staff_profile": staff is not None,
        "staff_id": str(staff.id) if staff else None,
        "staff_name": staff.full_name if staff else None,
        "date": timezone.localdate().isoformat(),
        "geofence": geofence_payload(fence),
        "checked_in": False,
        "checked_out": False,
        "check_in": None,
        "check_out": None,
        "status": None,
        "record_id": None,
    }
    if staff is None:
        payload["message"] = "No staff HR profile is linked to this account."
        return payload
    rec = today_record(tenant=tenant, staff=staff)
    if rec:
        payload.update({
            "checked_in": rec.check_in is not None,
            "checked_out": rec.check_out is not None,
            "check_in": rec.check_in.isoformat(timespec="minutes") if rec.check_in else None,
            "check_out": rec.check_out.isoformat(timespec="minutes") if rec.check_out else None,
            "status": rec.status,
            "record_id": str(rec.id),
            "check_in_lat": float(rec.check_in_lat) if rec.check_in_lat is not None else None,
            "check_in_lng": float(rec.check_in_lng) if rec.check_in_lng is not None else None,
            "check_in_accuracy_m": float(rec.check_in_accuracy_m) if rec.check_in_accuracy_m is not None else None,
        })
    return payload


@transaction.atomic
def staff_check_in(*, tenant, user, lat, lng, accuracy_m=None) -> dict[str, Any]:
    staff = staff_for_user(user)
    if staff is None:
        raise StaffAttendanceError(
            "No staff profile is linked to your account. Contact HR/admin.",
            code="no_staff_profile",
        )

    evaluation = evaluate_location(tenant=tenant, lat=lat, lng=lng, accuracy_m=accuracy_m)
    if not evaluation.get("allowed"):
        raise StaffAttendanceError(
            evaluation.get("reason") or "Location check failed.",
            code=evaluation.get("code") or "location_denied",
        )

    now = timezone.localtime()
    today = now.date()
    rec = today_record(tenant=tenant, staff=staff)
    if rec and rec.check_in and not rec.check_out:
        raise StaffAttendanceError(
            f"Already signed in today at {rec.check_in.strftime('%H:%M')}.",
            code="already_checked_in",
        )

    lat_d = Decimal(str(round(float(lat), 7))) if lat is not None else None
    lng_d = Decimal(str(round(float(lng), 7))) if lng is not None else None
    acc_d = None
    if accuracy_m is not None and accuracy_m != "":
        try:
            acc_d = Decimal(str(round(float(accuracy_m), 2)))
        except (TypeError, ValueError):
            acc_d = None

    if rec is None:
        rec = AttendanceRecord.objects.create(
            tenant=tenant,
            attendee_type="staff",
            staff=staff,
            date=today,
            status="present",
            check_in=now.time().replace(microsecond=0),
            check_in_lat=lat_d,
            check_in_lng=lng_d,
            check_in_accuracy_m=acc_d,
            marked_by=user,
            remarks="Self check-in (GPS)",
            created_by=user,
            updated_by=user,
        )
    else:
        # Re-check-in after prior check-out same day
        rec.status = "present"
        rec.check_in = now.time().replace(microsecond=0)
        rec.check_out = None
        rec.check_in_lat = lat_d
        rec.check_in_lng = lng_d
        rec.check_in_accuracy_m = acc_d
        rec.check_out_lat = None
        rec.check_out_lng = None
        rec.check_out_accuracy_m = None
        rec.marked_by = user
        rec.updated_by = user
        rec.remarks = "Self check-in (GPS)"
        rec.save()

    return {
        **staff_attendance_status(tenant=tenant, user=user),
        "evaluation": evaluation,
        "message": f"Signed in at {rec.check_in.strftime('%H:%M')}.",
    }


@transaction.atomic
def staff_check_out(*, tenant, user, lat=None, lng=None, accuracy_m=None) -> dict[str, Any]:
    staff = staff_for_user(user)
    if staff is None:
        raise StaffAttendanceError("No staff profile linked.", code="no_staff_profile")

    rec = today_record(tenant=tenant, staff=staff)
    if rec is None or not rec.check_in:
        raise StaffAttendanceError("You have not signed in today.", code="not_checked_in")
    if rec.check_out:
        raise StaffAttendanceError(
            f"Already signed out at {rec.check_out.strftime('%H:%M')}.",
            code="already_checked_out",
        )

    # Check-out may optionally verify location when geofence is on
    evaluation = evaluate_location(tenant=tenant, lat=lat, lng=lng, accuracy_m=accuracy_m)
    if evaluation.get("enforced") and lat is not None and not evaluation.get("allowed"):
        raise StaffAttendanceError(
            evaluation.get("reason") or "Outside school perimeter.",
            code=evaluation.get("code") or "location_denied",
        )

    now = timezone.localtime()
    rec.check_out = now.time().replace(microsecond=0)
    if lat is not None and lng is not None:
        rec.check_out_lat = Decimal(str(round(float(lat), 7)))
        rec.check_out_lng = Decimal(str(round(float(lng), 7)))
        if accuracy_m is not None and accuracy_m != "":
            try:
                rec.check_out_accuracy_m = Decimal(str(round(float(accuracy_m), 2)))
            except (TypeError, ValueError):
                pass
    rec.updated_by = user
    rec.save()
    return {
        **staff_attendance_status(tenant=tenant, user=user),
        "evaluation": evaluation,
        "message": f"Signed out at {rec.check_out.strftime('%H:%M')}.",
    }
