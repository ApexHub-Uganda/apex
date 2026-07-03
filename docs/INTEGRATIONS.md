# Integrations Overview

Apex Hub connects to external gateways for **messaging**, **voice**, and **payments**. All integrations follow the same deployment pattern: configure database settings → validate → build provider payload → gate live dispatch.

## Master switch

```env
INTEGRATION_LIVE_DISPATCH=false   # development (default)
INTEGRATION_LIVE_DISPATCH=true    # production, after HTTP wiring
```

When `false`, the full pipeline runs (validation, logging, delivery records) but outbound provider calls return a structured failure. This is intentional for safe development.

## Integration map

| Domain | Service class | Settings model | API settings endpoint |
|--------|---------------|----------------|------------------------|
| Email | `EmailService` | `EmailSetting` | `/platform/email-settings/` |
| SMS | `SMSService` | `SMSSetting` | `/platform/sms-settings/` |
| WhatsApp | `WhatsAppService` | `WhatsAppSetting` | `/platform/whatsapp-settings/` |
| Voice | `CallService` | `CallSetting` | `/platform/call-settings/` |
| Payments | `PaymentService` | `PaymentProvider` | `/subscriptions/payments/providers/` |

Code: `backend/apps/platform/services/integrations.py`

## Provider adapter layer

Messaging uses pluggable adapters:

```
EmailService.send()
    → get_email_provider(config.provider)
    → adapter.validate_config()
    → adapter.build_request()    # exact production payload
    → adapter.dispatch()         # checks INTEGRATION_LIVE_DISPATCH
    → adapter.dispatch_live()    # HTTP/SMTP (implement at deployment)
```

Adapter code: `backend/apps/platform/services/providers/`

Developer guide: [backend/apps/platform/services/providers/README.md](../backend/apps/platform/services/providers/README.md)

### Supported providers

| Channel | Provider slugs |
|---------|----------------|
| Email | `smtp`, `sendgrid`, `mailgun` |
| SMS | `twilio`, `africas_talking`, `nexmo` |
| WhatsApp | `meta`, `twilio`, `africas_talking` |

## Testing integrations

### Channel readiness

```http
GET /api/v1/platform/broadcasts/channel_status/
GET /api/v1/platform/integrations/test/
```

Returns per-channel: `configured`, `active`, `ready`, `validation_errors`, `live_dispatch`.

### Send test message

```http
POST /api/v1/platform/integrations/test/
Content-Type: application/json
Authorization: Bearer <super_admin_token>

{
  "service": "email",
  "to": "admin@school.edu",
  "subject": "Test",
  "body": "Hello"
}
```

`service`: `email` | `sms` | `whatsapp` | `call` | `payment`

## Broadcast integration (primary consumer)

Platform broadcasts are the main multi-channel consumer:

- Audience resolution → school admins by plan/active status
- Per-channel delivery via `EmailService` / `SMSService` / `WhatsAppService`
- In-app `Notification` always created on send
- `PlatformBroadcastDelivery` audit trail

Full guide: [BROADCAST_INTEGRATIONS.md](BROADCAST_INTEGRATIONS.md)

## Payment integration

Checkout records a `PaymentTransaction` even when the gateway is disconnected:

- Card: last four + brand in metadata (never full PAN)
- Mobile money: masked phone in metadata
- HTTP 402 with user-facing message until gateway live

See [API.md](API.md) — Subscription payments section.

## Adding a new provider

1. Create adapter class in `providers/email.py`, `sms.py`, or `whatsapp.py`
2. Implement `validate_config`, `build_request`, `dispatch_live`
3. Register in `providers/registry.py`
4. Add model `choices` if new slug
5. Document fields in [BROADCAST_INTEGRATIONS.md](BROADCAST_INTEGRATIONS.md)
6. Add test in `test_integration_providers.py`

## Adding a new integration domain

1. Add `*Setting` model on `PlatformModel` (or reuse pattern)
2. Add `*Service` in `integrations.py` using provider pattern
3. Add ViewSet + serializer + URL
4. Expose in `IntegrationTestView` and channel status if applicable
5. Document env vars in `.env.example` and [DEPLOYMENT.md](DEPLOYMENT.md)

## Deployment checklist

- [ ] Create active setting record per channel
- [ ] Fill all required provider fields (see BROADCAST_INTEGRATIONS.md tables)
- [ ] Configure `EMAIL_BACKEND` for SMTP
- [ ] Implement `dispatch_live()` HTTP for chosen SMS/WhatsApp providers
- [ ] Set `INTEGRATION_LIVE_DISPATCH=true`
- [ ] Run integration test endpoint
- [ ] Send test broadcast to narrow audience
- [ ] Monitor `PlatformBroadcastDelivery` and `EmailMessage`/`SMSMessage` tables

## Related docs

- [BROADCAST_INTEGRATIONS.md](BROADCAST_INTEGRATIONS.md)
- [DEPLOYMENT.md](DEPLOYMENT.md)
- [BACKEND.md](BACKEND.md)