# Messaging Provider Adapters

Outbound email, SMS, and WhatsApp broadcasts use a small adapter layer so the rest of the app stays provider-agnostic.

> **See also:** [docs/EMAIL_SERVICE.md](../../../../docs/EMAIL_SERVICE.md) · [docs/INTEGRATIONS.md](../../../../docs/INTEGRATIONS.md) · [docs/BROADCAST_INTEGRATIONS.md](../../../../docs/BROADCAST_INTEGRATIONS.md) · [docs/BACKEND.md](../../../../docs/BACKEND.md)

## Layout

```
providers/
  base.py          # BaseMessagingProvider, phone normalization
  email.py         # SMTP, SendGrid, Mailgun
  sms.py           # Twilio, Africa's Talking, Nexmo
  whatsapp.py      # Meta Cloud API, Twilio, Africa's Talking
  registry.py      # Provider lookup + channel_status helpers
```

## Lifecycle

Each adapter implements:

1. **`validate_config(config)`** — list missing setting fields
2. **`build_request(...)`** — return a `ProviderRequest` with endpoint, method, headers, body
3. **`dispatch(...)`** — validate → build → check `INTEGRATION_LIVE_DISPATCH` → `dispatch_live()`

When `INTEGRATION_LIVE_DISPATCH=false` (default), `dispatch()` returns failure with `deployment_ready: true` and the prepared payload in metadata. No HTTP is attempted.

When `INTEGRATION_LIVE_DISPATCH=true`, `dispatch_live()` runs. **SMTP** is wired via Django `send_mail`. **HTTP providers** (SendGrid, Twilio, Meta WhatsApp, etc.) return a placeholder failure until you add the `requests` call in the matching `dispatch_live()` method.

## Adding live HTTP for a provider

Example for Twilio SMS in `sms.py`:

```python
import requests

def dispatch_live(self, config, request, *, to, subject, message):
    response = requests.post(
        request.endpoint,
        data=request.body,
        auth=request.auth,
        headers=request.headers,
        timeout=30,
    )
    if response.ok:
        data = response.json()
        return ProviderResponse(
            success=True,
            message="SMS accepted by Twilio.",
            external_id=data.get("sid", ""),
            metadata={"provider": self.provider_slug, "response": data},
        )
    return ProviderResponse(
        success=False,
        message=f"Twilio error: {response.text}",
        metadata={"status_code": response.status_code},
    )
```

The `request` object already contains the production URL and body — you only need to execute the HTTP call.

## Registering a new provider

1. Add a class in `email.py`, `sms.py`, or `whatsapp.py`.
2. Register it in `registry.py` under `EMAIL_PROVIDERS`, `SMS_PROVIDERS`, or `WHATSAPP_PROVIDERS`.
3. Add the provider choice to the corresponding Django model if needed.
4. Document required fields in `docs/BROADCAST_INTEGRATIONS.md`.

## Testing

```bash
cd backend
pytest tests/test_platform_broadcast.py tests/test_integration_providers.py -v
```

Use `POST /api/v1/platform/integrations/test/` with a super-admin token for manual smoke tests.