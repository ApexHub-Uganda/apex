# Apex Hub Database Schema

PostgreSQL with UUID primary keys, foreign keys, indexes, soft deletes, and audit fields.

## Core Patterns

Every tenant-scoped table includes:

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `tenant_id` | UUID FK | School ownership |
| `created_at` | DateTime | Auto-set on create |
| `updated_at` | DateTime | Auto-updated |
| `created_by_id` | UUID FK | Creating user |
| `updated_by_id` | UUID FK | Last updating user |
| `is_deleted` | Boolean | Soft delete flag |

## Entity Relationship Overview

```
Tenant (School)
├── Subscription → Plan
├── Users (accounts.User)
├── AcademicYear
│   └── Term
├── Class → Stream
├── Department → Subject
├── Student
│   ├── Parent / Guardian
│   ├── Admission
│   ├── MedicalRecord
│   └── AttendanceRecord
├── Staff / Teacher
├── FeeStructure → FeePayment → Invoice
├── Exam → Grade → ReportCard
├── Book → BorrowRecord
├── Hostel → Room → Allocation
├── Vehicle → Route → StudentTransport
├── Item → StockMovement
├── Leave / PerformanceReview
├── PayrollRun → Payslip
└── Announcement / Notification / SupportTicket
```

## Key Tables

### tenants_tenant
School/institution with branding (logo, favicon, banner, login_bg, custom colors).

### accounts_user
Custom user model with email login, role, tenant FK, 2FA fields.

### subscriptions_plan
Plan tiers: Basic, Premium, Premium Plus, Free Trial with limits and feature flags.

### subscriptions_subscription
Active subscription with trial, expiry, grace period, suspension status.

### subscriptions_paymentprovider
Payment gateway configuration. `method_type` is either `card` (Stripe, PayPal) or `mobile_money` (M-Pesa, MTN MoMo, Airtel Money).

### subscriptions_paymenttransaction
Checkout and billing ledger. Stores `payment_method` (`card` | `mobile_money`), masked `payer_phone` for mobile money, and card metadata (last four digits only) in `metadata` JSON — full card numbers are never persisted.

### audit_auditlog
Platform-wide audit trail for all significant actions.

### platform_platformbroadcast
System-wide super-admin broadcasts.

| Field | Description |
|-------|-------------|
| `channels` | JSON array: `email`, `sms`, `whatsapp` |
| `audience` | `all`, `trial`, `basic`, `premium`, `premium_plus`, `active` |
| `status` | `draft`, `scheduled`, `sent`, `cancelled`, `expired` |
| `recipient_count`, `delivered_count`, `failed_count`, `skipped_count` | Delivery aggregates |
| `starts_at`, `sent_at`, `cancelled_at` | Scheduling lifecycle |

### platform_platformbroadcastdelivery
Per-recipient, per-channel delivery log. FK to broadcast (CASCADE delete).

### platform_planadvertisement
Plan upgrade campaigns with `target_plan_slug`, `suggested_plan_slug`, `broadcast_count`.

### platform_whatsappsetting
WhatsApp Business API credentials (`provider`, `api_key`, `phone_number_id`, …).

### communication_notification
Tenant-scoped in-app notifications (also created by platform broadcast send).

### communication_emailmessage / communication_smsmessage
Outbound message audit rows created by integration services.

## Indexes

- All `tenant_id` columns indexed
- Composite indexes on frequently queried combinations (tenant + status, tenant + date)
- Unique constraints scoped to tenant where applicable

## Multi-Tenant Isolation

`TenantAwareManager` automatically filters querysets by current tenant from JWT context. Super administrators bypass tenant filtering.

## Migrations

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py seed_platform
```