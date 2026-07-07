"""Finance workflow and approval constants."""
from __future__ import annotations

APPROVAL_PENDING = "pending"
APPROVAL_APPROVED = "approved"
APPROVAL_REJECTED = "rejected"
APPROVAL_REVERSED = "reversed"

APPROVAL_STATUSES = frozenset({
    APPROVAL_PENDING,
    APPROVAL_APPROVED,
    APPROVAL_REJECTED,
    APPROVAL_REVERSED,
})

PAYMENT_STATUS_PENDING = "pending"
PAYMENT_STATUS_COMPLETED = "completed"
PAYMENT_STATUS_FAILED = "failed"
PAYMENT_STATUS_REFUNDED = "refunded"

PERIOD_OPEN = "open"
PERIOD_CLOSED = "closed"

DISCOUNT_PENDING = "pending"
DISCOUNT_APPROVED = "approved"
DISCOUNT_REJECTED = "rejected"

REFUND_PENDING = "pending"
REFUND_APPROVED = "approved"
REFUND_REJECTED = "rejected"
REFUND_PROCESSED = "processed"

BALANCE_DEBTOR = "debtor"
BALANCE_CLEARED = "cleared"
BALANCE_CREDIT = "credit"