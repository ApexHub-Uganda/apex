# Finance module architecture

## Money path

1. Define **fee structures** per class + term.
2. **Bill** class/term → invoices with line items + auto numbers + student balances.
3. **Record payment** (cash/bank/mpesa ref) → approval if required → receipt number → allocate to invoices → sync balance.
4. **Results clearance** reads term `StudentFeeBalance` (paid/billed %).
5. **PDF** receipts/invoices/statements use branded school template.

## Online payments

Gateway adapters exist under `apps/finance/services/gateway/`.
Live provider HTTP is not enabled. Initiate returns HTTP 503 with:

> Payment integrations will be enabled in a future release.

## Security

All endpoints use `RequiresFeature` + `TenantActivePermission` + existing RBAC.
No hardcoded role admin checks.

## Key APIs

| Method | Path | Feature |
|--------|------|---------|
| POST | `/finance/billing/bill-class/` | student_billing |
| POST | `/finance/billing/bill-student/` | student_billing |
| POST | `/finance/payments/` | payment_recording |
| GET | `/finance/payments/{id}/receipt.pdf` | payment_recording |
| GET | `/finance/invoices/{id}/pdf/` | invoice_generation |
| GET | `/finance/statements/{student_id}/pdf/` | parent_fee_statements / billing |
| POST | `/finance/online-payments/` | portal (gateway stub) |

## Balance formula (per term)

```
billed   = sum(invoices for term) - approved discounts
paid     = approved completed payments for term - processed refunds
balance  = billed - paid
```
