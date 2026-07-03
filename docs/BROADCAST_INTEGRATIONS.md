# Platform Broadcast Integrations

Super-admin broadcasts deliver announcements to school admins through **email**, **SMS**, and **WhatsApp**. The full pipeline is implemented in code; outbound provider HTTP calls are gated until deployment.

> **See also:** [Documentation index](README.md) · [Integrations overview](INTEGRATIONS.md) · [Feature reference](FEATURES.md) · [Provider adapters](../backend/apps/platform/services/providers/README.md)

## How it works

1. Super admin composes a broadcast and selects channels + audience.
2. `preview` resolves school admins and shows reachability per channel.
3. `send` (or the scheduled job) creates:
   - In-app notifications for every recipient
   - `PlatformBroadcastDelivery` rows per recipient/channel
   - `EmailMessage` / `SMSMessage` audit rows where applicable
4. Each channel routes through a provider adapter that:
   - Validates platform settings
   - Normalizes phone numbers (E.164)
   - Builds the exact API/SMTP payload
   - Dispatches only when `INTEGRATION_LIVE_DISPATCH=true`

Until live dispatch is enabled, deliveries are marked **failed** with a clear deployment message. The broadcast still completes and stats are recorded.

## Environment

```env
# .env (production)
INTEGRATION_LIVE_DISPATCH=false   # set true when provider HTTP is wired
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
```

| Variable | Default | Purpose |
|----------|---------|---------|
| `INTEGRATION_LIVE_DISPATCH` | `false` | Master switch for provider HTTP/SMTP dispatch |
| `EMAIL_BACKEND` | console backend | Django email backend (SMTP in production) |
| `DEFAULT_FROM_EMAIL` | `noreply@apexhub.io` | Fallback sender |

## Platform settings (database)

Configure via API or Django admin:

| Channel | Model | Endpoint |
|---------|-------|----------|
| Email | `EmailSetting` | `GET/POST /api/v1/platform/email-settings/` |
| SMS | `SMSSetting` | `GET/POST /api/v1/platform/sms-settings/` |
| WhatsApp | `WhatsAppSetting` | `GET/POST /api/v1/platform/whatsapp-settings/` |

Set `is_active=true` on exactly one active record per channel (first active record wins).

### Email providers (`EmailSetting.provider`)

| Provider | Required fields |
|----------|-----------------|
| `smtp` | `host`, `port`, `from_email`, `username`, `password` (recommended) |
| `sendgrid` | `password` (API key), `from_email` |
| `mailgun` | `host` (API base URL), `password` (API key), `from_email` |

### SMS providers (`SMSSetting.provider`)

| Provider | Required fields |
|----------|-----------------|
| `twilio` | `api_key` (Account SID), `api_secret` (Auth Token), `sender_id` (From number) |
| `africas_talking` | `api_key`, `sender_id` |
| `nexmo` | `api_key`, `api_secret`, `sender_id` |

### WhatsApp providers (`WhatsAppSetting.provider`)

| Provider | Required fields |
|----------|-----------------|
| `meta` | `api_key` (access token), `phone_number_id` |
| `twilio` | `api_key`, `api_secret`, `phone_number_id` (WhatsApp sender) |
| `africas_talking` | `api_key`, `phone_number_id` |

## Broadcast API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/platform/broadcasts/` | List broadcasts |
| POST | `/platform/broadcasts/` | Create draft |
| POST | `/platform/broadcasts/preview/` | Audience + channel reachability |
| GET | `/platform/broadcasts/channel_status/` | Gateway readiness |
| POST | `/platform/broadcasts/{id}/send/` | Send now |
| POST | `/platform/broadcasts/{id}/schedule/` | Schedule (`starts_at`) |
| POST | `/platform/broadcasts/{id}/cancel/` | Cancel scheduled |
| POST | `/platform/broadcasts/{id}/duplicate/` | Clone as draft |
| GET | `/platform/broadcasts/{id}/deliveries/` | Per-recipient log |
| DELETE | `/platform/broadcasts/{id}/` | Permanently delete broadcast + delivery log |
| POST | `/platform/broadcasts/{id}/delete_broadcast/` | Same as DELETE (JSON response) |

### Test a single channel

```http
POST /api/v1/platform/integrations/test/
Authorization: Bearer <super_admin_token>
Content-Type: application/json

{
  "service": "whatsapp",
  "to": "+254712345678",
  "message": "Test message"
}
```

`service` may be `email`, `sms`, `whatsapp`, `call`, or `payment`.

```http
GET /api/v1/platform/integrations/test/
```

Returns the same channel readiness payload as `channel_status`.

## Deployment checklist

1. Create platform setting records for each channel you will use.
2. Set `is_active=true` and fill all required provider fields.
3. Configure Django `EMAIL_BACKEND` for SMTP if using the `smtp` email provider.
4. Implement `dispatch_live()` HTTP calls in `backend/apps/platform/services/providers/` for your chosen SMS/WhatsApp providers (payloads are already built).
5. Set `INTEGRATION_LIVE_DISPATCH=true` in production `.env`.
6. Send a test message via `/platform/integrations/test/`.
7. Send a small broadcast to a narrow audience and verify `deliveries/`.

## Scheduled broadcasts

Celery beat runs `platform.process_scheduled_broadcasts` hourly. You can also run:

```bash
python manage.py process_scheduled_broadcasts
```

## Developer guide

See [backend/apps/platform/services/providers/README.md](../backend/apps/platform/services/providers/README.md) for adapter architecture and how to wire live HTTP.