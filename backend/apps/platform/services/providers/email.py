"""Email provider adapters (SMTP, SendGrid, Mailgun)."""
from __future__ import annotations

from apps.platform.services.providers.base import BaseMessagingProvider, ProviderRequest, ProviderResponse


class SmtpEmailProvider(BaseMessagingProvider):
    provider_slug = "smtp"

    def validate_config(self, config) -> list[str]:
        errors = []
        if not config.host:
            errors.append("host")
        if not config.from_email:
            errors.append("from_email")
        if config.is_active and not config.username:
            errors.append("username (recommended for authenticated SMTP)")
        return errors

    def build_request(self, config, *, to: str, subject: str, message: str) -> ProviderRequest:
        return ProviderRequest(
            provider=self.provider_slug,
            endpoint=f"smtp://{config.host}:{config.port}",
            method="SMTP",
            body={
                "from": config.from_email,
                "to": [to] if isinstance(to, str) else to,
                "subject": subject,
                "text": message,
                "use_tls": config.use_tls,
            },
        )

    def dispatch_live(
        self,
        config,
        request: ProviderRequest,
        *,
        to: str,
        subject: str,
        message: str,
    ) -> ProviderResponse:
        from django.core.mail import send_mail

        try:
            sent = send_mail(
                subject,
                message,
                request.body["from"],
                [to],
                fail_silently=False,
                connection=None,
            )
        except Exception as exc:
            return ProviderResponse(
                success=False,
                message=f"SMTP send failed: {exc}",
                metadata={"provider": self.provider_slug, "endpoint": request.endpoint},
            )

        if sent:
            return ProviderResponse(
                success=True,
                message="Email accepted by SMTP gateway.",
                metadata={"provider": self.provider_slug, "endpoint": request.endpoint},
            )
        return ProviderResponse(
            success=False,
            message="SMTP gateway rejected the message.",
            metadata={"provider": self.provider_slug, "endpoint": request.endpoint},
        )


class SendgridEmailProvider(BaseMessagingProvider):
    provider_slug = "sendgrid"

    def validate_config(self, config) -> list[str]:
        errors = []
        if not config.password:
            errors.append("api_key (stored in password field)")
        if not config.from_email:
            errors.append("from_email")
        return errors

    def build_request(self, config, *, to: str, subject: str, message: str) -> ProviderRequest:
        return ProviderRequest(
            provider=self.provider_slug,
            endpoint="https://api.sendgrid.com/v3/mail/send",
            method="POST",
            headers={
                "Authorization": f"Bearer {config.password}",
                "Content-Type": "application/json",
            },
            body={
                "personalizations": [{"to": [{"email": to}]}],
                "from": {"email": config.from_email},
                "subject": subject,
                "content": [{"type": "text/plain", "value": message}],
            },
        )

    def dispatch_live(
        self,
        config,
        request: ProviderRequest,
        *,
        to: str,
        subject: str,
        message: str,
    ) -> ProviderResponse:
        return ProviderResponse(
            success=False,
            message=(
                "SendGrid live HTTP dispatch is not wired yet. "
                "Implement POST to the prepared endpoint in providers/email.py."
            ),
            metadata={"provider": self.provider_slug, "endpoint": request.endpoint, "request_body": request.body},
        )


class MailgunEmailProvider(BaseMessagingProvider):
    provider_slug = "mailgun"

    def validate_config(self, config) -> list[str]:
        errors = []
        if not config.host:
            errors.append("api_base (stored in host field, e.g. https://api.mailgun.net/v3/your-domain)")
        if not config.password:
            errors.append("api_key (stored in password field)")
        if not config.from_email:
            errors.append("from_email")
        return errors

    def build_request(self, config, *, to: str, subject: str, message: str) -> ProviderRequest:
        base = config.host.rstrip("/")
        return ProviderRequest(
            provider=self.provider_slug,
            endpoint=f"{base}/messages",
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            auth=("api", config.password),
            body={
                "from": config.from_email,
                "to": to,
                "subject": subject,
                "text": message,
            },
        )

    def dispatch_live(
        self,
        config,
        request: ProviderRequest,
        *,
        to: str,
        subject: str,
        message: str,
    ) -> ProviderResponse:
        return ProviderResponse(
            success=False,
            message=(
                "Mailgun live HTTP dispatch is not wired yet. "
                "Implement POST to the prepared endpoint in providers/email.py."
            ),
            metadata={"provider": self.provider_slug, "endpoint": request.endpoint, "request_body": request.body},
        )