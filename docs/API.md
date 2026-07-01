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
| GET | `/subscriptions/plans/` | List plans |
| GET | `/subscriptions/current/` | Current tenant subscription |
| POST | `/subscriptions/upgrade/` | Upgrade plan |
| POST | `/subscriptions/downgrade/` | Downgrade plan |

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