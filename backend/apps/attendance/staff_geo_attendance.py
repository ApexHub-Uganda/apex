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
    """
    Resolve the single Staff directory row for this portal user.

    Dual roles share one Staff record — signing in as teacher is the same
    attendance as bursar/DoS/HR on the same login.
    """
    if not user:
        return None
    try:
        staff = user.staff_profile
        if staff and not getattr(staff, "is_deleted", False):
            return staff
    except Exception:
        pass
    staff = Staff.objects.filter(user=user, is_deleted=False).first()
    if staff:
        return staff
    # Email fallback (legacy link gaps)
    email = (getattr(user, "email", None) or "").strip()
    if email and getattr(user, "tenant_id", None):
        return Staff.objects.filter(
            tenant_id=user.tenant_id, email__iexact=email, is_deleted=False,
        ).first()
    return None


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
    from apps.accounts.webauthn_service import webauthn_status

    staff = staff_for_user(user)
    fence = get_geofence(tenant)
    wa = webauthn_status(user)
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
        # Dual-role aware: one check-in for the person, all staff roles
        "shared_across_roles": True,
        "webauthn": wa,
        "requires_webauthn": True,
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
        if payload["checked_in"] and not payload["checked_out"]:
            payload["message"] = (
                f"Already signed in today at {payload['check_in']}. "
                "This applies to all your portal roles — no need to sign in again after switching role."
            )
    return payload


@transaction.atomic
def staff_check_in(
    *,
    tenant,
    user,
    lat,
    lng,
    accuracy_m=None,
    webauthn_assertion=None,
    request=None,
) -> dict[str, Any]:
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
    # Idempotent across dual roles: already signed in → friendly success, not error
    if rec and rec.check_in and not rec.check_out:
        status = staff_attendance_status(tenant=tenant, user=user)
        return {
            **status,
            "already_checked_in": True,
            "evaluation": evaluation,
            "message": (
                f"Already signed in today at {rec.check_in.strftime('%H:%M')}. "
                "Your check-in is shared across all roles on this account."
            ),
        }

    # Biometric second factor (prevents colleague proxy sign-in)
    webauthn_result = None
    from django.conf import settings as dj_settings

    if request is not None and getattr(dj_settings, "WEBAUTHN_REQUIRED_FOR_STAFF_CHECKIN", True):
        from apps.accounts.webauthn_service import WebAuthnError, require_verified_webauthn

        try:
            webauthn_result = require_verified_webauthn(request, user, webauthn_assertion)
        except WebAuthnError as exc:
            raise StaffAttendanceError(exc.message, code=exc.code) from exc

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
            remarks="Self check-in (GPS + biometric)",
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
        rec.remarks = "Self check-in (GPS + biometric)"
        rec.save()

    return {
        **staff_attendance_status(tenant=tenant, user=user),
        "evaluation": evaluation,
        "webauthn_verified": bool(webauthn_result),
        "message": f"Signed in at {rec.check_in.strftime('%H:%M')} (location + biometric verified).",
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
