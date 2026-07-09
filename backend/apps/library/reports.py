"""Library analytics and report builders."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import Count, Sum
from django.utils import timezone

from apps.library.constants import BORROW_BORROWED, BORROW_OVERDUE, BORROW_RETURNED, FINE_PENDING
from apps.library.models import Book, BookReservation, BorrowRecord, LibraryFine


def _decimal_str(value) -> str:
    return str(value or Decimal("0"))


def build_library_reports(
    *,
    tenant,
    report_type: str = "circulation",
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    today = timezone.localdate()
    start = start_date or (today - timedelta(days=30))
    end = end_date or today

    payload: dict[str, Any] = {
        "report_type": report_type,
        "period": {"start": str(start), "end": str(end)},
        "generated_at": timezone.now().isoformat(),
        "rows": [],
        "totals": {},
    }

    if report_type == "circulation":
        records = BorrowRecord.objects.filter(
            tenant=tenant,
            is_deleted=False,
            borrowed_date__gte=start,
            borrowed_date__lte=end,
        ).select_related("book", "student", "staff").order_by("-borrowed_date")
        payload["rows"] = [
            {
                "borrowed_date": str(row.borrowed_date),
                "due_date": str(row.due_date),
                "returned_date": str(row.returned_date) if row.returned_date else "",
                "book": row.book.title if row.book_id else "",
                "borrower": (
                    row.student.full_name if row.student_id
                    else (row.staff.full_name if row.staff_id else "")
                ),
                "borrower_type": row.borrower_type,
                "status": row.status,
                "fine_amount": _decimal_str(row.fine_amount),
            }
            for row in records
        ]
        payload["totals"] = {
            "count": records.count(),
            "returned": records.filter(status=BORROW_RETURNED).count(),
            "active": records.filter(status__in=[BORROW_BORROWED, BORROW_OVERDUE]).count(),
        }

    elif report_type == "overdue":
        records = BorrowRecord.objects.filter(
            tenant=tenant,
            is_deleted=False,
            status__in=[BORROW_BORROWED, BORROW_OVERDUE],
            due_date__lt=today,
        ).select_related("book", "student", "staff").order_by("due_date")
        payload["rows"] = [
            {
                "book": row.book.title if row.book_id else "",
                "borrower": (
                    row.student.full_name if row.student_id
                    else (row.staff.full_name if row.staff_id else "")
                ),
                "borrowed_date": str(row.borrowed_date),
                "due_date": str(row.due_date),
                "days_overdue": (today - row.due_date).days,
                "fine_amount": _decimal_str(row.fine_amount),
            }
            for row in records
        ]
        payload["totals"] = {"count": records.count()}

    elif report_type == "fines":
        fines = LibraryFine.objects.filter(
            tenant=tenant,
            is_deleted=False,
            created_at__date__gte=start,
            created_at__date__lte=end,
        ).select_related("borrow_record", "borrow_record__book", "student", "staff").order_by("-created_at")
        total = fines.aggregate(total=Sum("amount"))["total"] or Decimal("0")
        pending = fines.filter(status=FINE_PENDING).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        payload["rows"] = [
            {
                "created_at": row.created_at.date().isoformat(),
                "book": row.borrow_record.book.title if row.borrow_record_id and row.borrow_record.book_id else "",
                "borrower": (
                    row.student.full_name if row.student_id
                    else (row.staff.full_name if row.staff_id else "")
                ),
                "amount": _decimal_str(row.amount),
                "status": row.status,
                "paid_date": str(row.paid_date) if row.paid_date else "",
            }
            for row in fines
        ]
        payload["totals"] = {
            "count": fines.count(),
            "total_amount": _decimal_str(total),
            "pending_amount": _decimal_str(pending),
        }

    elif report_type == "inventory":
        books = Book.objects.filter(tenant=tenant, is_deleted=False).annotate(
            loan_count=Count("borrow_records"),
        ).order_by("title")
        payload["rows"] = [
            {
                "title": book.title,
                "author": book.author,
                "isbn": book.isbn,
                "total_copies": book.total_copies,
                "available_copies": book.available_copies,
                "loan_count": book.loan_count,
            }
            for book in books
        ]
        totals = books.aggregate(
            total_copies=Sum("total_copies"),
            available_copies=Sum("available_copies"),
        )
        payload["totals"] = {
            "book_count": books.count(),
            "total_copies": totals["total_copies"] or 0,
            "available_copies": totals["available_copies"] or 0,
        }

    elif report_type == "reservations":
        reservations = BookReservation.objects.filter(
            tenant=tenant,
            is_deleted=False,
            reserved_date__gte=start,
            reserved_date__lte=end,
        ).select_related("book", "student", "staff").order_by("-reserved_date")
        payload["rows"] = [
            {
                "reserved_date": str(row.reserved_date),
                "expires_date": str(row.expires_date),
                "book": row.book.title if row.book_id else "",
                "borrower": (
                    row.student.full_name if row.student_id
                    else (row.staff.full_name if row.staff_id else "")
                ),
                "status": row.status,
            }
            for row in reservations
        ]
        payload["totals"] = {"count": reservations.count()}

    return payload