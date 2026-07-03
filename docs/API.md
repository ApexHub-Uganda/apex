# Apex Hub API Documentation

Base URL: `http://localhost:8000/api/v1/`

Interactive docs: `http://localhost:8000/api/docs/`

## Authentication

All endpoints except public auth routes require a JWT Bearer token.

```http
POST /api/v1/auth/login/
Content-Type: application/json

{
  "email": "admin@demoschool.edu",
  "password": "DemoSchool@2026"
}
```

Response includes `access` and `refresh` tokens. Include the access token in subsequent requests:

```http
Authorization: Bearer <access_token>
```

### Auth Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login/` | Login |
| POST | `/auth/logout/` | Logout (blacklist refresh token) |
| POST | `/auth/refresh/` | Refresh access token |
| POST | `/auth/register/` | School registration |
| GET | `/auth/me/` | Current user profile |
| POST | `/auth/password/reset/` | Request password reset |
| POST | `/auth/password/reset/confirm/` | Confirm password reset |
| POST | `/auth/email/verify/` | Verify email |
| GET | `/auth/sessions/` | Active sessions |
| GET | `/auth/login-history/` | Login history |

## Tenants

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tenants/` | List schools (super admin) |
| POST | `/tenants/` | Register school |
| GET | `/tenants/{id}/` | School details |
| PATCH | `/tenants/{id}/` | Update school |
| POST | `/tenants/{id}/verify/` | Verify school |
| POST | `/tenants/{id}/suspend/` | Suspend school |
| POST | `/tenants/{id}/restore/` | Restore school |
| PATCH | `/tenants/{id}/branding/` | Update branding/colors |

## Subscriptions

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/subscriptions/plans/` | List public plans |
| GET | `/subscriptions/current/` | Current tenant subscription |
| GET | `/subscriptions/upgrade/catalog/` | Upgrade plans, features, payment methods (school admin) |
| POST | `/subscriptions/upgrade/checkout/` | Initiate upgrade checkout (stub — returns 402) |
| GET | `/subscriptions/payments/transactions/` | Payment transaction ledger |
| GET | `/subscriptions/payments/providers/` | Configured payment providers |

### Payment checkout payload

School-admin upgrade and onboarding checkout accept the same payment fields. **Card is the default method**; clients may switch to mobile money.

```json
{
  "plan_slug": "premium",
  "billing_cycle": "monthly",
  "payment_method": "card",
  "provider_slug": "stripe",
  "payer_name": "Jane Doe",
  "card_last_four": "4242",
  "card_brand": "visa"
}
```

Mobile money:

```json
{
  "plan_slug": "premium",
  "billing_cycle": "monthly",
  "payment_method": "mobile_money",
  "provider_slug": "mpesa",
  "phone_number": "+256700000000"
}
```

Responses use HTTP `402 Payment Required` with `success: false` while sandbox gateways are disconnected. A failed `subscriptions_paymenttransaction` row is always recorded.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/tenants/onboarding/{tenant_id}/checkout/` | Registration paid-plan checkout (same payment fields) |

## Module Endpoints

Each module follows REST conventions with pagination, filtering, search, and sorting:

- `/academics/` — Years, terms, classes, streams, departments, subjects, timetables
- `/students/` — Students, parents, guardians, admissions, medical records
- `/staff/` — Staff and teacher profiles
- `/attendance/` — Student and staff attendance
- `/examinations/` — Exams, grades, report cards
- `/finance/` — Fee structures, payments, invoices
- `/library/` — Books, borrow records (Premium+)
- `/hostel/` — Hostels, rooms, allocations (Premium+)
- `/transport/` — Routes, vehicles, drivers (Premium+)
- `/inventory/` — Items, stock, procurement (Premium+)
- `/hr/` — Leave, performance reviews
- `/payroll/` — Salary structures, payroll runs, payslips
- `/communication/` — Announcements, SMS, email, notifications, support tickets
- `/analytics/` — Dashboard statistics
- `/audit/` — Audit logs
- `/platform/` — Super admin platform management

## Platform (Super Admin)

Base: `/api/v1/platform/`

### Broadcasts

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/broadcasts/` | List broadcasts (filter: `status`, `audience`, `severity`) |
| POST | `/broadcasts/` | Create draft |
| PATCH | `/broadcasts/{id}/` | Update draft/scheduled |
| DELETE | `/broadcasts/{id}/` | Delete broadcast + delivery log |
| POST | `/broadcasts/preview/` | Audience reachability preview |
| GET | `/broadcasts/channel_status/` | Email/SMS/WhatsApp gateway readiness |
| POST | `/broadcasts/{id}/send/` | Send now |
| POST | `/broadcasts/{id}/schedule/` | Schedule (`starts_at` ISO datetime) |
| POST | `/broadcasts/{id}/cancel/` | Cancel scheduled |
| POST | `/broadcasts/{id}/duplicate/` | Clone as draft |
| POST | `/broadcasts/{id}/delete_broadcast/` | Delete (JSON response) |
| GET | `/broadcasts/{id}/deliveries/` | Per-recipient delivery log |

Create payload example:

```json
{
  "title": "System Notice",
  "message": "Maintenance this weekend.",
  "channels": ["email", "sms", "whatsapp"],
  "audience": "all",
  "severity": "warning",
  "starts_at": "2026-07-10T09:00:00Z"
}
```

See [BROADCAST_INTEGRATIONS.md](BROADCAST_INTEGRATIONS.md) for channel configuration.

### Plan advertisements

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/plan-advertisements/` | CRUD |
| GET | `/plan-advertisements/plan_options/` | Plans that can advertise |
| POST | `/plan-advertisements/{id}/broadcast/` | Activate and notify schools |
| POST | `/plan-advertisements/{id}/pause/` | Pause |
| POST | `/plan-advertisements/{id}/end/` | End campaign |

### Platform notifications

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/notifications/` | Super-admin inbox |
| POST | `/notifications/{id}/approve/` | Approve registration |
| POST | `/notifications/{id}/dismiss/` | Dismiss |
| POST | `/notifications/{id}/delete_notification/` | Remove from inbox |
| POST | `/notifications/delete_all/` | Bulk remove |

### Integration settings & tests

| Method | Endpoint | Description |
|--------|----------|-------------|
| CRUD | `/email-settings/` | SMTP / SendGrid / Mailgun config |
| CRUD | `/sms-settings/` | SMS gateway config |
| CRUD | `/whatsapp-settings/` | WhatsApp Business API config |
| GET | `/integrations/test/` | Channel readiness |
| POST | `/integrations/test/` | Test email, sms, whatsapp, call, payment |

### Maintenance

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/PATCH | `/maintenance/` | Read/update maintenance mode |
| GET | `/settings/public/` | Public banner message (unauthenticated) |

## Common Query Parameters

| Parameter | Description |
|-----------|-------------|
| `page` | Page number |
| `page_size` | Items per page (max 100) |
| `search` | Full-text search |
| `ordering` | Sort field (prefix `-` for descending) |
| `tenant` | Filter by tenant (super admin only) |

## Response Format

```json
{
  "count": 100,
  "next": "http://localhost:8000/api/v1/students/?page=2",
  "previous": null,
  "results": []
}
```

## Error Format

```json
{
  "detail": "Error message",
  "code": "error_code",
  "errors": {}
}
```

## Rate Limits

- Anonymous: 100 requests/hour
- Authenticated: 1000 requests/hour
- Login: 10 requests/minute