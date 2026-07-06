# Email Service

Guide to configuring, operating, and extending outbound email in Apex Hub.

> **See also:** [BROADCAST_INTEGRATIONS.md](BROADCAST_INTEGRATIONS.md) · [INTEGRATIONS.md](INTEGRATIONS.md) · [Provider adapters](../backend/apps/platform/services/providers/README.md)

## Overview

Email is used for:

| Flow | Entry point |
|------|-------------|
| School announcements & broadcasts | `apps/communication/services/messaging.py` |
| Direct school emails | `EmailMessage` → `send_email_message()` |
| Platform super-admin broadcasts | `apps/platform/services/broadcasts.py` |
| Future password reset / transactional mail | `EmailService.send()` |

All outbound mail routes through **`EmailService`** (`apps/platform/services/integrations.py`), which delegates to a **provider adapter** (`apps/platform/services/providers/email.py`).

## Architecture

```
.env (EMAIL_*)
    ↓
email_config.ensure_email_config()  →  EmailSetting (DB)
    ↓
EmailService.send()
    ↓
get_email_provider(provider)  →  SmtpEmailProvider | SendgridEmailProvider | MailgunEmailProvider
    ↓
adapter.dispatch()  →  dispatch_live() when INTEGRATION_LIVE_DISPATCH=true
```

### Key files

| File | Role |
|------|------|
| `backend/apex_hub/settings.py` | Reads `EMAIL_*` env vars |
| `backend/apps/platform/services/email_config.py` | Syncs env → `EmailSetting`, SMTP diagnostics, error formatting |
| `backend/apps/platform/services/integrations.py` | `EmailService` — multi-recipient send, audit logging |
| `backend/apps/platform/services/providers/email.py` | SMTP / SendGrid / Mailgun adapters |
| `backend/apps/platform/services/providers/registry.py` | Provider lookup, channel status |
| `backend/apps/communication/services/messaging.py` | School-level email dispatch for announcements/broadcasts |
| `backend/apps/core/email_validation.py` | Rejects placeholder / demo recipient addresses |

## Configuration

### 1. Environment variables (`.env`)

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-account@gmail.com
EMAIL_HOST_PASSWORD=your-16-char-app-password
DEFAULT_FROM_EMAIL=your-account@gmail.com

# Required for real delivery (not just in-app simulation)
INTEGRATION_LIVE_DISPATCH=True
```

| Variable | Purpose |
|----------|---------|
| `EMAIL_BACKEND` | Django mail backend. Use SMTP backend in production. |
| `EMAIL_HOST` | SMTP hostname |
| `EMAIL_PORT` | SMTP port (587 for TLS, 465 for SSL) |
| `EMAIL_USE_TLS` | `True` for STARTTLS on port 587 |
| `EMAIL_HOST_USER` | SMTP username (often the mailbox address) |
| `EMAIL_HOST_PASSWORD` | SMTP password or app password (spaces are stripped automatically) |
| `DEFAULT_FROM_EMAIL` | Default `From` header |
| `INTEGRATION_LIVE_DISPATCH` | Master switch — must be `True` for live SMTP |

On startup / first send, `sync_email_settings_from_env()` copies these values into the active `EmailSetting` database record.

### 2. Gmail checklist

1. Enable **2-Step Verification** on the Google account
2. Create an **App Password** (Google Account → Security → 2-Step Verification → App passwords)
3. Paste the 16-character password into `EMAIL_HOST_PASSWORD` (no spaces)
4. Restart the Django backend after changing `.env`
5. Ensure staff/parent records use **real, deliverable** email addresses (not seed/demo addresses)

### 3. Database settings (super-admin)

Super-admins can also manage `EmailSetting` via:

- Django admin
- `GET/POST /api/v1/platform/email-settings/`

Fields map to provider adapters:

| Field | SMTP | SendGrid | Mailgun |
|-------|------|----------|---------|
| `provider` | `smtp` | `sendgrid` | `mailgun` |
| `host` | SMTP host | — | API base URL |
| `port` | SMTP port | — | — |
| `use_tls` | STARTTLS flag | — | — |
| `username` | SMTP user | — | — |
| `password` | SMTP / app password | API key | API key |
| `from_email` | Sender address | Sender address | Sender address |
| `is_active` | Must be `true` | Must be `true` | Must be `true` |

**Precedence:** Active `EmailSetting` in DB is used when present; env sync fills gaps when `EMAIL_HOST` is set.

## Sending email from code

```python
from apps.platform.services.integrations import EmailService

result = EmailService.send(
    to=["teacher@school.edu", "parent@school.edu"],  # str or list
    subject="Term opening notice",
    body="School reopens Monday at 8:00 AM.",
    tenant=tenant,          # optional — scopes audit log
    log_attempt=True,       # writes EmailMessage rows
)

if result.success:
    print(result.message)
else:
    print(result.message, result.metadata)
```

`EmailService.send()` returns an `IntegrationResult` with per-recipient delivery metadata when multiple addresses are supplied.

## School messaging integration

When a school admin publishes an announcement or sends a broadcast with the **email** channel:

1. `messaging.py` resolves recipients by audience (staff / parents / students / all)
2. `filter_deliverable_emails()` removes placeholder/demo addresses
3. `_dispatch_email()` formats the body with school name footer
4. `EmailService.send()` delivers via the configured provider

Recipient emails come from:

- `Staff.email`, `Staff.personal_email`, linked `User.email`
- `Parent.email`, `Parent.alternate_email`
- `Student.email` (when set)

## Diagnostics

### SMTP health (super-admin)

`diagnose_smtp_config()` in `email_config.py` returns non-secret status:

```python
from apps.platform.services.email_config import diagnose_smtp_config
print(diagnose_smtp_config())
```

Included in platform integration channel status via `registry.channel_status()`.

### Common errors

| Symptom | Cause | Fix |
|---------|-------|-----|
| `535 Username and Password not accepted` | Invalid Gmail app password | Regenerate app password, update `.env`, restart backend |
| `No deliverable email addresses found` | Recipients use demo/placeholder emails | Update staff/parent records with real addresses |
| `Email service is not configured` | No `EmailSetting` and no `EMAIL_HOST` | Set `.env` or create platform email settings |
| `INTEGRATION_LIVE_DISPATCH` false | Dispatch disabled | Set `INTEGRATION_LIVE_DISPATCH=True` in `.env` |
| In-app notification only | Email channel skipped or all recipients filtered | Check channels array and recipient emails |

Friendly SMTP errors are produced by `format_smtp_error()` in `email_config.py`.

## Customization

### Switch provider (SMTP → SendGrid)

1. Set `EmailSetting.provider = "sendgrid"`
2. Store API key in `password` field
3. Set `from_email` to a verified sender
4. Implement HTTP dispatch in `SendgridEmailProvider.dispatch_live()` (placeholder exists in `providers/email.py`)
5. Register provider in `providers/registry.py` if adding a new slug

### Add a new provider

1. Create a class in `providers/email.py` extending `BaseMessagingProvider`
2. Implement `validate_config`, `build_request`, `dispatch_live`
3. Register in `EMAIL_PROVIDERS` dict in `providers/registry.py`
4. Add choice to `EmailSetting.provider` model field if needed
5. Document required fields in this file

### Custom email templates

Currently school emails use plain text from `_format_email_body()` in `messaging.py`. To customize:

1. Add HTML template support to `EmailService.send()` (`html_body` parameter is reserved)
2. Extend `SmtpEmailProvider.dispatch_live()` to use `EmailMultiAlternatives`
3. Or render templates in `messaging.py` before calling `EmailService.send()`

### Per-tenant sender addresses

Pass `from_email=` to `EmailService.send()`, or store a tenant-level `reply_to` / `from_email` on the `Tenant` model and resolve in `EmailService._get_config()`.

### Disable audit logging

Pass `log_attempt=False` to `EmailService.send()` for internal/system mail that should not create `EmailMessage` rows.

## Testing

```bash
cd backend

# Provider + messaging tests
pytest tests/test_integration_providers.py tests/test_school_messaging.py -q

# Email validation
pytest tests/test_email_validation.py -q
```

### Manual SMTP test

```bash
cd backend
python -c "
import os, django, smtplib
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apex_hub.settings')
django.setup()
from apps.platform.services.email_config import ensure_email_config
r = ensure_email_config()
s = smtplib.SMTP(r.host, r.port, timeout=15)
s.ehlo(); s.starttls(); s.ehlo()
s.login(r.username, r.password)
print('SMTP OK')
s.quit()
"
```

### Integration test endpoint

Super-admins: `POST /api/v1/platform/integrations/test/` with `{ "channel": "email", "recipient": "you@domain.com" }`.

## Security notes

- Never commit real passwords to git — use `.env` only
- Rotate app passwords if exposed in chat or logs
- `EmailSetting.password` is stored in the database; restrict super-admin access
- Recipient validation blocks disposable and demo domains before send