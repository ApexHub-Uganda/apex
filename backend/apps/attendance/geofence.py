"""School campus geofence — free GPS perimeter for staff & class attendance."""
from __future__ import annotations

import math
from typing import Any

from django.db import transaction

from apps.attendance.models import SchoolGeofence

# Default GPS accuracy ceiling (metres). Refined mobile GPS is typically 20–200 m.
# Frontend waits for a sharper fix; this is the server-side safety net.
DEFAULT_MAX_ACCURACY_M = 600.0
# Never trust a reading worse than this (cell/IP-only ±2 km stays rejected).
HARD_MAX_ACCURACY_M = 1200.0


class GeofenceError(Exception):
    def __init__(self, message: str, *, code: str = "geofence_error"):
        self.message = message
        self.code = code
        super().__init__(message)


EARTH_RADIUS_M = 6_371_000.0


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in metres between two WGS84 points."""
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))


def point_in_polygon(lat: float, lng: float, vertices: list[dict[str, Any]]) -> bool:
    """Ray-casting PIP. vertices: [{lat, lng}, ...] (open or closed ring)."""
    if len(vertices) < 3:
        return False
    pts = [(float(v["lat"]), float(v["lng"])) for v in vertices]
    # Ensure closed ring
    if pts[0] != pts[-1]:
        pts = pts + [pts[0]]

    inside = False
    j = len(pts) - 1
    for i in range(len(pts)):
        yi, xi = pts[i]
        yj, xj = pts[j]
        # yi/xi are lat/lng; ray cast on lng (x) vs lat (y)
        intersects = ((yi > lat) != (yj > lat)) and (
            lng < (xj - xi) * (lat - yi) / (yj - yi + 1e-15) + xi
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def min_distance_to_polygon_m(lat: float, lng: float, vertices: list[dict[str, Any]]) -> float:
    """Approx min distance from point to any vertex or edge (haversine)."""
    if not vertices:
        return float("inf")
    pts = [(float(v["lat"]), float(v["lng"])) for v in vertices]
    best = min(haversine_m(lat, lng, p[0], p[1]) for p in pts)
    # Sample along edges for better edge distance
    for i in range(len(pts)):
        a = pts[i]
        b = pts[(i + 1) % len(pts)]
        for t in (0.25, 0.5, 0.75):
            plat = a[0] + (b[0] - a[0]) * t
            plng = a[1] + (b[1] - a[1]) * t
            best = min(best, haversine_m(lat, lng, plat, plng))
    return best


def get_geofence(tenant) -> SchoolGeofence | None:
    if tenant is None:
        return None
    return (
        SchoolGeofence.objects.filter(tenant=tenant, is_deleted=False)
        .order_by("-updated_at")
        .first()
    )


def geofence_payload(fence: SchoolGeofence | None) -> dict[str, Any]:
    if fence is None:
        return {
            "configured": False,
            "is_enabled": False,
            "vertices": [],
            "buffer_meters": 25,
            "name": "Main campus",
            "vertex_count": 0,
            "max_accuracy_m": DEFAULT_MAX_ACCURACY_M,
        }
    vertices = fence.vertices or []
    return {
        "configured": len(vertices) >= 4,
        "is_enabled": bool(fence.is_enabled and len(vertices) >= 4),
        "vertices": vertices,
        "buffer_meters": fence.buffer_meters,
        "name": fence.name or "Main campus",
        "vertex_count": len(vertices),
        "id": str(fence.id),
        "updated_at": fence.updated_at.isoformat() if fence.updated_at else None,
        "max_accuracy_m": DEFAULT_MAX_ACCURACY_M,
    }


def validate_vertices(raw: list) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or len(raw) < 4:
        raise GeofenceError(
            "Provide at least 4 boundary coordinates (polygon corners).",
            code="min_vertices",
        )
    if len(raw) > 64:
        raise GeofenceError("Maximum 64 boundary points allowed.", code="max_vertices")
    cleaned: list[dict[str, Any]] = []
    for i, item in enumerate(raw):
        try:
            lat = float(item.get("lat") if isinstance(item, dict) else item[0])
            lng = float(item.get("lng") if isinstance(item, dict) else item[1])
        except (TypeError, ValueError, IndexError, AttributeError) as exc:
            raise GeofenceError(f"Invalid coordinate at index {i}.", code="invalid_vertex") from exc
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            raise GeofenceError(f"Coordinate {i + 1} is out of range.", code="out_of_range")
        accuracy = item.get("accuracy_m") if isinstance(item, dict) else None
        try:
            accuracy_m = float(accuracy) if accuracy is not None and accuracy != "" else None
        except (TypeError, ValueError):
            accuracy_m = None
        if accuracy_m is not None and accuracy_m < 0:
            accuracy_m = None
        cleaned.append({
            "lat": round(lat, 7),
            "lng": round(lng, 7),
            "accuracy_m": round(accuracy_m, 1) if accuracy_m is not None else None,
            "label": f"P{i + 1}",
        })
    return cleaned


@transaction.atomic
def save_geofence(
    *,
    tenant,
    user,
    vertices: list,
    buffer_meters: int = 25,
    is_enabled: bool = True,
    name: str = "Main campus",
) -> SchoolGeofence:
    cleaned = validate_vertices(vertices)
    try:
        buffer = max(0, min(int(buffer_meters), 500))
    except (TypeError, ValueError):
        buffer = 25
    fence = get_geofence(tenant)
    if fence is None:
        fence = SchoolGeofence(tenant=tenant)
    fence.vertices = cleaned
    fence.buffer_meters = buffer
    fence.is_enabled = bool(is_enabled)
    fence.name = (name or "Main campus")[:100]
    fence.updated_by = user
    if not fence.created_by_id:
        fence.created_by = user
    fence.save()
    return fence


def evaluate_location(
    *,
    tenant,
    lat: float | None,
    lng: float | None,
    accuracy_m: float | None = None,
    max_accuracy_m: float | None = None,
) -> dict[str, Any]:
    """
    Check whether a GPS fix is inside the school perimeter.

    Returns { allowed, reason, code, distance_m, inside_polygon, buffer_meters, ... }
    """
    fence = get_geofence(tenant)
    payload = geofence_payload(fence)

    if not payload["is_enabled"]:
        # No enforcement when not configured/enabled
        return {
            "allowed": True,
            "enforced": False,
            "reason": "School boundary is not enabled; location not required.",
            "code": "not_enforced",
            "geofence": payload,
        }

    if lat is None or lng is None:
        return {
            "allowed": False,
            "enforced": True,
            "reason": "Location is required. Enable GPS and try again.",
            "code": "location_required",
            "geofence": payload,
        }

    try:
        lat_f = float(lat)
        lng_f = float(lng)
    except (TypeError, ValueError):
        return {
            "allowed": False,
            "enforced": True,
            "reason": "Invalid GPS coordinates.",
            "code": "invalid_coords",
            "geofence": payload,
        }

    acc = None
    if accuracy_m is not None and accuracy_m != "":
        try:
            acc = float(accuracy_m)
        except (TypeError, ValueError):
            acc = None

    # Soft default: allow typical phone GPS after a short outdoor wait
    threshold = float(max_accuracy_m) if max_accuracy_m is not None else DEFAULT_MAX_ACCURACY_M
    # Slightly relax threshold with the school's buffer (GPS drift allowance)
    buffer_m = float(fence.buffer_meters or 0) if fence else 0.0
    threshold = max(threshold, min(buffer_m * 4.0, 500.0)) if buffer_m else threshold
    threshold = min(threshold, HARD_MAX_ACCURACY_M)

    vertices = fence.vertices or []
    inside = point_in_polygon(lat_f, lng_f, vertices)
    # Distance to polygon edge (useful both inside and outside)
    edge_dist_m = min_distance_to_polygon_m(lat_f, lng_f, vertices)
    distance_m = 0.0 if inside else edge_dist_m

    if acc is not None and acc > threshold:
        # Soft pass A: clearly deep inside campus relative to uncertainty
        deep_inside = inside and edge_dist_m >= min(acc * 0.45, acc - 20.0)
        # Soft pass B: reported point is inside polygon and accuracy is not absurd
        # (still rejects pure cell/IP ~2000 m via HARD_MAX)
        inside_with_usable_gps = inside and acc <= HARD_MAX_ACCURACY_M and acc <= max(threshold * 1.5, 900.0)
        if acc > HARD_MAX_ACCURACY_M or not (deep_inside or inside_with_usable_gps):
            return {
                "allowed": False,
                "enforced": True,
                "reason": (
                    f"GPS accuracy is too low (±{acc:.0f} m). "
                    f"On your phone: Precise location ON, Location mode = High accuracy, open this site on HTTPS, "
                    f"stand outdoors, and wait until the red pin accuracy is under ±{threshold:.0f} m "
                    f"(first readings of ~1–2 km are normal network location — keep waiting)."
                ),
                "code": "poor_accuracy",
                "accuracy_m": acc,
                "max_accuracy_m": threshold,
                "geofence": payload,
            }

    # Uncertainty-aware buffer: phone GPS error circles often extend tens–hundreds of metres.
    # If the reported point is outside but the uncertainty circle still intersects campus,
    # treat as on-site (professional mobile geofencing practice).
    acc_pad = 0.0
    if acc is not None and acc > 0:
        # Cap pad so pure ±2 km cell fixes cannot "reach" a distant campus
        acc_pad = min(float(acc) * 0.85, 350.0)
    effective_buffer = buffer_m + acc_pad

    if inside or distance_m <= effective_buffer:
        if inside:
            reason = "Within school perimeter."
            code = "inside"
        elif acc is not None and distance_m <= acc_pad:
            reason = (
                f"GPS places you near campus (about {distance_m:.0f} m from the boundary) "
                f"within your phone’s accuracy of ±{acc:.0f} m — accepted."
            )
            code = "inside_uncertainty"
        else:
            reason = f"Within {buffer_m:.0f} m buffer of the boundary."
            code = "inside"
        return {
            "allowed": True,
            "enforced": True,
            "reason": reason,
            "code": code,
            "inside_polygon": inside,
            "distance_m": round(distance_m, 1),
            "accuracy_m": acc,
            "max_accuracy_m": threshold,
            "buffer_meters": buffer_m,
            "effective_buffer_m": round(effective_buffer, 1),
            "geofence": payload,
            "lat": lat_f,
            "lng": lng_f,
        }

    return {
        "allowed": False,
        "enforced": True,
        "reason": (
            f"You appear outside the school boundary"
            f"{f' (about {distance_m:.0f} m from the perimeter)' if distance_m < 50_000 else ''}"
            f"{f' with GPS accuracy ±{acc:.0f} m' if acc is not None else ''}. "
            "Move further onto campus, wait for a sharper GPS lock (smaller red circle), then try again."
        ),
        "code": "outside",
        "inside_polygon": False,
        "distance_m": round(distance_m, 1),
        "accuracy_m": acc,
        "max_accuracy_m": threshold,
        "buffer_meters": buffer_m,
        "effective_buffer_m": round(effective_buffer, 1),
        "geofence": payload,
        "lat": lat_f,
        "lng": lng_f,
    }
