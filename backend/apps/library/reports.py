"""Library analytics and report builders (aligned to current models)."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import Count, Sum
from django.utils import timezone

from apps.library.models import Book, BorrowRecord


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

    borrows = BorrowRecord.objects.filter(tenant=tenant, is_deleted=False)

    if report_type == "circulation":
        records = borrows.filter(
            borrowed_date__gte=start,
            borrowed_date__lte=end,
        ).select_related("book", "student").order_by("-borrowed_date")
        payload["rows"] = [
            {
                "borrowed_date": str(row.borrowed_date),
                "due_date": str(row.due_date),
                "returned_date": str(row.returned_date) if row.returned_date else "",
                "book": row.book.title if row.book_id else "",
                "borrower": row.student.full_name if row.student_id else "",
                "status": row.status,
                "fine_amount": _decimal_str(row.fine_amount),
            }
            for row in records
        ]
        payload["totals"] = {
            "count": records.count(),
            "returned": records.filter(status="returned").count(),
            "active": records.filter(status__in=["borrowed", "overdue"]).count(),
        }

    elif report_type == "overdue":
        records = borrows.filter(
            status__in=["borrowed", "overdue"],
            due_date__lt=today,
        ).select_related("book", "student").order_by("due_date")
        payload["rows"] = [
            {
                "book": row.book.title if row.book_id else "",
                "borrower": row.student.full_name if row.student_id else "",
                "borrowed_date": str(row.borrowed_date),
                "due_date": str(row.due_date),
                "days_overdue": (today - row.due_date).days,
                "fine_amount": _decimal_str(row.fine_amount),
            }
            for row in records
        ]
        payload["totals"] = {"count": records.count()}

    elif report_type == "fines":
        records = borrows.filter(
            fine_amount__gt=0,
            borrowed_date__gte=start,
            borrowed_date__lte=end,
        ).select_related("book", "student").order_by("-borrowed_date")
        total = records.aggregate(total=Sum("fine_amount"))["total"] or Decimal("0")
        payload["rows"] = [
            {
                "borrowed_date": str(row.borrowed_date),
                "book": row.book.title if row.book_id else "",
                "borrower": row.student.full_name if row.student_id else "",
                "amount": _decimal_str(row.fine_amount),
                "status": row.status,
            }
            for row in records
        ]
        payload["totals"] = {
            "count": records.count(),
            "total_amount": _decimal_str(total),
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

    else:
        # Fallback: circulation for unknown report types
        return build_library_reports(
            tenant=tenant,
            report_type="circulation",
            start_date=start_date,
            end_date=end_date,
        )

    return payload
