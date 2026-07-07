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

    def build_request(
        self,
        config,
        *,
        to: str,
        subject: str,
        message: str,
        html_body: str = "",
    ) -> ProviderRequest:
        return ProviderRequest(
            provider=self.provider_slug,
            endpoint=f"smtp://{config.host}:{config.port}",
            method="SMTP",
            body={
                "from": config.from_email,
                "to": [to] if isinstance(to, str) else to,
                "subject": subject,
                "text": message,
                "html": html_body,
                "use_tls": config.use_tls,
            },
        )

    def _smtp_connection(self, config):
        from django.conf import settings as django_settings
        from django.core.mail import get_connection

        backend = django_settings.EMAIL_BACKEND
        kwargs: dict = {"backend": backend, "fail_silently": False}
        if backend.endswith("smtp.EmailBackend"):
            kwargs.update({
                "host": config.host,
                "port": config.port,
                "username": config.username or None,
                "password": config.password or None,
                "use_tls": config.use_tls,
            })
        return get_connection(**kwargs)

    def dispatch_live(
        self,
        config,
        request: ProviderRequest,
        *,
        to: str,
        subject: str,
        message: str,
        html_body: str = "",
    ) -> ProviderResponse:
        from django.core.mail import EmailMultiAlternatives, send_mail

        try:
            with self._smtp_connection(config) as connection:
                html_content = html_body or request.body.get("html") or ""
                if html_content:
                    email = EmailMultiAlternatives(
                        subject,
                        message,
                        request.body["from"],
                        [to],
                        connection=connection,
                    )
                    email.attach_alternative(html_content, "text/html")
                    sent = email.send(fail_silently=False)
                else:
                    sent = send_mail(
                        subject,
                        message,
                        request.body["from"],
                        [to],
                        fail_silently=False,
                        connection=connection,
                    )
        except Exception as exc:
            from apps.platform.services.email_config import format_smtp_error

            return ProviderResponse(
                success=False,
                message=format_smtp_error(exc),
                metadata={
                    "provider": self.provider_slug,
                    "endpoint": request.endpoint,
                    "smtp_error": str(exc),
                },
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

    def build_request(
        self,
        config,
        *,
        to: str,
        subject: str,
        message: str,
        html_body: str = "",
    ) -> ProviderRequest:
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
        html_body: str = "",
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

    def build_request(
        self,
        config,
        *,
        to: str,
        subject: str,
        message: str,
        html_body: str = "",
    ) -> ProviderRequest:
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
        html_body: str = "",
    ) -> ProviderResponse:
        return ProviderResponse(
            success=False,
            message=(
                "Mailgun live HTTP dispatch is not wired yet. "
                "Implement POST to the prepared endpoint in providers/email.py."
            ),
            metadata={"provider": self.provider_slug, "endpoint": request.endpoint, "request_body": request.body},
        )