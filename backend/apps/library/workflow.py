"""Library circulation workflows."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.library.constants import (
    BORROW_BORROWED,
    BORROW_OVERDUE,
    BORROW_RETURNED,
    BORROWER_STAFF,
    BORROWER_STUDENT,
    DEFAULT_DAILY_FINE_RATE,
    DEFAULT_LOAN_DAYS,
    DEFAULT_RENEWAL_DAYS,
    FINE_PAID,
    FINE_PENDING,
    FINE_WAIVED,
    MAX_RENEWALS,
    RESERVATION_FULFILLED,
    RESERVATION_PENDING,
)
from apps.library.models import Book, BookReservation, BorrowRecord, LibraryFine


class LibraryWorkflowError(Exception):
    def __init__(self, message: str, *, code: str = "library_workflow_error"):
        self.message = message
        self.code = code
        super().__init__(message)


def calculate_fine(*, borrow_record: BorrowRecord, as_of: date | None = None) -> Decimal:
    """Compute overdue fine for a borrow record."""
    if borrow_record.status == BORROW_RETURNED and borrow_record.returned_date:
        end_date = borrow_record.returned_date
    else:
        end_date = as_of or timezone.localdate()

    if end_date <= borrow_record.due_date:
        return Decimal("0")

    days_overdue = (end_date - borrow_record.due_date).days
    return Decimal(DEFAULT_DAILY_FINE_RATE) * days_overdue


def _validate_borrower(*, borrower_type: str, student=None, staff=None) -> None:
    if borrower_type == BORROWER_STUDENT:
        if student is None:
            raise LibraryWorkflowError("Student borrower is required.", code="missing_student")
        if staff is not None:
            raise LibraryWorkflowError("Staff must not be set for student borrows.", code="invalid_borrower")
    elif borrower_type == BORROWER_STAFF:
        if staff is None:
            raise LibraryWorkflowError("Staff borrower is required.", code="missing_staff")
        if student is not None:
            raise LibraryWorkflowError("Student must not be set for staff borrows.", code="invalid_borrower")
    else:
        raise LibraryWorkflowError("Invalid borrower type.", code="invalid_borrower_type")


def _adjust_available_copies(book: Book, delta: int) -> None:
    book.available_copies = max(0, book.available_copies + delta)
    if book.available_copies > book.total_copies:
        book.available_copies = book.total_copies
    book.save(update_fields=["available_copies", "updated_at"])


@transaction.atomic
def issue_book(
    *,
    tenant,
    book: Book,
    user,
    borrower_type: str = BORROWER_STUDENT,
    student=None,
    staff=None,
    borrowed_date: date | None = None,
    due_date: date | None = None,
    notes: str = "",
) -> BorrowRecord:
    if book.tenant_id != tenant.id:
        raise LibraryWorkflowError("Book does not belong to this school.", code="invalid_book")
    if book.available_copies < 1:
        raise LibraryWorkflowError("No copies available for this book.", code="no_copies")

    _validate_borrower(borrower_type=borrower_type, student=student, staff=staff)

    borrowed = borrowed_date or timezone.localdate()
    due = due_date or (borrowed + timedelta(days=DEFAULT_LOAN_DAYS))

    record = BorrowRecord.objects.create(
        tenant=tenant,
        book=book,
        student=student,
        staff=staff,
        borrower_type=borrower_type,
        borrowed_date=borrowed,
        due_date=due,
        status=BORROW_BORROWED,
        notes=(notes or "").strip(),
        created_by=user,
        updated_by=user,
    )
    _adjust_available_copies(book, -1)
    return record


@transaction.atomic
def return_book(
    *,
    borrow_record: BorrowRecord,
    user,
    returned_date: date | None = None,
    create_fine: bool = True,
) -> BorrowRecord:
    if borrow_record.status not in {BORROW_BORROWED, BORROW_OVERDUE}:
        raise LibraryWorkflowError("Only active loans can be returned.", code="invalid_status")

    returned = returned_date or timezone.localdate()
    fine_amount = calculate_fine(borrow_record=borrow_record, as_of=returned)

    borrow_record.status = BORROW_RETURNED
    borrow_record.returned_date = returned
    borrow_record.fine_amount = fine_amount
    borrow_record.updated_by = user
    borrow_record.save(update_fields=[
        "status", "returned_date", "fine_amount", "updated_by", "updated_at",
    ])

    _adjust_available_copies(borrow_record.book, 1)

    if create_fine and fine_amount > 0:
        LibraryFine.objects.create(
            tenant=borrow_record.tenant,
            borrow_record=borrow_record,
            student=borrow_record.student,
            staff=borrow_record.staff,
            amount=fine_amount,
            status=FINE_PENDING,
            created_by=user,
            updated_by=user,
        )

    return borrow_record


@transaction.atomic
def renew_book(
    *,
    borrow_record: BorrowRecord,
    user,
    renewal_days: int = DEFAULT_RENEWAL_DAYS,
) -> BorrowRecord:
    if borrow_record.status != BORROW_BORROWED:
        raise LibraryWorkflowError("Only borrowed items can be renewed.", code="invalid_status")
    if borrow_record.renewal_count >= MAX_RENEWALS:
        raise LibraryWorkflowError("Maximum renewals reached.", code="max_renewals")
    if timezone.localdate() > borrow_record.due_date:
        raise LibraryWorkflowError("Overdue items must be returned before renewal.", code="overdue")

    borrow_record.due_date = borrow_record.due_date + timedelta(days=renewal_days)
    borrow_record.renewal_count += 1
    borrow_record.updated_by = user
    borrow_record.save(update_fields=[
        "due_date", "renewal_count", "updated_by", "updated_at",
    ])
    return borrow_record


@transaction.atomic
def reserve_book(
    *,
    tenant,
    book: Book,
    user,
    borrower_type: str = BORROWER_STUDENT,
    student=None,
    staff=None,
    reserved_date: date | None = None,
    expires_date: date | None = None,
    notes: str = "",
) -> BookReservation:
    if book.tenant_id != tenant.id:
        raise LibraryWorkflowError("Book does not belong to this school.", code="invalid_book")

    _validate_borrower(borrower_type=borrower_type, student=student, staff=staff)

    reserved = reserved_date or timezone.localdate()
    expires = expires_date or (reserved + timedelta(days=DEFAULT_LOAN_DAYS))

    pending_exists = BookReservation.objects.filter(
        tenant=tenant,
        book=book,
        is_deleted=False,
        status=RESERVATION_PENDING,
        student=student if borrower_type == BORROWER_STUDENT else None,
        staff=staff if borrower_type == BORROWER_STAFF else None,
    ).exists()
    if pending_exists:
        raise LibraryWorkflowError("A pending reservation already exists.", code="duplicate_reservation")

    return BookReservation.objects.create(
        tenant=tenant,
        book=book,
        student=student,
        staff=staff,
        borrower_type=borrower_type,
        reserved_date=reserved,
        expires_date=expires,
        status=RESERVATION_PENDING,
        notes=(notes or "").strip(),
        created_by=user,
        updated_by=user,
    )


@transaction.atomic
def fulfill_reservation(
    *,
    reservation: BookReservation,
    user,
) -> BorrowRecord:
    if reservation.status != RESERVATION_PENDING:
        raise LibraryWorkflowError("Only pending reservations can be fulfilled.", code="invalid_status")

    record = issue_book(
        tenant=reservation.tenant,
        book=reservation.book,
        user=user,
        borrower_type=reservation.borrower_type,
        student=reservation.student,
        staff=reservation.staff,
        notes=reservation.notes,
    )
    reservation.status = RESERVATION_FULFILLED
    reservation.fulfilled_borrow = record
    reservation.updated_by = user
    reservation.save(update_fields=[
        "status", "fulfilled_borrow", "updated_by", "updated_at",
    ])
    return record


@transaction.atomic
def mark_fine_paid(*, fine: LibraryFine, user) -> LibraryFine:
    if fine.status != FINE_PENDING:
        raise LibraryWorkflowError("Only pending fines can be marked paid.", code="invalid_status")
    fine.status = FINE_PAID
    fine.paid_date = timezone.localdate()
    fine.updated_by = user
    fine.save(update_fields=["status", "paid_date", "updated_by", "updated_at"])
    return fine


@transaction.atomic
def waive_fine(*, fine: LibraryFine, user) -> LibraryFine:
    if fine.status != FINE_PENDING:
        raise LibraryWorkflowError("Only pending fines can be waived.", code="invalid_status")
    fine.status = FINE_WAIVED
    fine.updated_by = user
    fine.save(update_fields=["status", "updated_by", "updated_at"])
    return fine