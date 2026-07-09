"""Library role workspace summaries."""
from __future__ import annotations

from typing import Any

from django.utils import timezone

from apps.core.constants import UserRole, normalize_role
from apps.library.constants import BORROW_BORROWED, BORROW_OVERDUE, RESERVATION_PENDING
from apps.library.models import Book, BookReservation, BorrowRecord, LibraryFine
from apps.library.scoping import user_has_school_wide_library_access
from apps.tenants.role_permissions import get_user_feature_permissions


def _enabled(perms: dict, key: str) -> bool:
    return bool(perms.get(key, {}).get("can_read"))


def build_library_workspace(*, tenant, user) -> dict[str, Any]:
    role = normalize_role(getattr(user, "role", ""))
    perms = get_user_feature_permissions(tenant, user)
    is_school_wide = user_has_school_wide_library_access(user, tenant)

    payload: dict[str, Any] = {
        "role": role,
        "is_school_wide": is_school_wide,
        "features": {
            key: perms.get(key, {"can_read": False, "can_write": False})
            for key in (
                "librarian_workspace", "library_management", "book_categories",
                "borrowing", "returns", "reservations", "library_fines",
                "book_suppliers", "library_reports",
            )
        },
        "counts": {},
        "queues": {},
        "quick_links": [],
    }

    if not is_school_wide:
        return payload

    today = timezone.localdate()

    if _enabled(perms, "library_management"):
        payload["counts"]["total_books"] = Book.objects.filter(
            tenant=tenant, is_deleted=False,
        ).count()

    if _enabled(perms, "borrowing") or _enabled(perms, "returns"):
        overdue_qs = BorrowRecord.objects.filter(
            tenant=tenant,
            is_deleted=False,
            status__in=[BORROW_BORROWED, BORROW_OVERDUE],
            due_date__lt=today,
        )
        overdue_count = overdue_qs.count()
        payload["counts"]["overdue_loans"] = overdue_count
        payload["counts"]["overdue_borrows"] = overdue_count
        active_loans = BorrowRecord.objects.filter(
            tenant=tenant,
            is_deleted=False,
            status__in=[BORROW_BORROWED, BORROW_OVERDUE],
        )
        active_count = active_loans.count()
        payload["counts"]["active_loans"] = active_count
        payload["counts"]["active_borrows"] = active_count
        overdue_preview = overdue_qs.select_related("book", "student", "staff")[:20]
        payload["queues"]["overdue_loans"] = [
            {
                "id": str(row.id),
                "book": row.book.title if row.book_id else "",
                "borrower": (
                    row.student.full_name if row.student_id
                    else (row.staff.full_name if row.staff_id else "")
                ),
                "due_date": str(row.due_date),
            }
            for row in overdue_preview
        ]
        payload["queues"]["overdue_borrows"] = payload["queues"]["overdue_loans"]

    if _enabled(perms, "reservations"):
        pending = BookReservation.objects.filter(
            tenant=tenant, is_deleted=False, status=RESERVATION_PENDING,
        ).select_related("book", "student", "staff")
        payload["counts"]["pending_reservations"] = pending.count()
        payload["queues"]["pending_reservations"] = [
            {
                "id": str(row.id),
                "book": row.book.title if row.book_id else "",
                "borrower": (
                    row.student.full_name if row.student_id
                    else (row.staff.full_name if row.staff_id else "")
                ),
                "reserved_date": str(row.reserved_date),
                "expires_date": str(row.expires_date),
            }
            for row in pending[:20]
        ]

    if _enabled(perms, "library_fines"):
        payload["counts"]["pending_fines"] = LibraryFine.objects.filter(
            tenant=tenant, is_deleted=False, status="pending",
        ).count()

    if role == UserRole.LIBRARIAN and _enabled(perms, "librarian_workspace"):
        payload["quick_links"] = [
            {"label": "Issue Book", "path": "/school-admin/library/borrowing", "feature_key": "borrowing"},
            {"label": "Returns", "path": "/school-admin/library/returns", "feature_key": "returns"},
            {"label": "Reservations", "path": "/school-admin/library/reservations", "feature_key": "reservations"},
            {"label": "Library Reports", "path": "/school-admin/library/reports", "feature_key": "library_reports"},
        ]

    return payload