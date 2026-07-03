"""Super-admin integration test endpoints (stubs until live APIs are connected)."""
from __future__ import annotations

from decimal import Decimal

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsSuperAdmin
from apps.platform.services.integrations import (
    CallService,
    EmailService,
    PaymentService,
    SMSService,
    WhatsAppService,
)
from apps.platform.services.providers import get_integration_channel_status
from apps.subscriptions.models import Plan
from apps.tenants.models import Tenant


class IntegrationTestView(APIView):
    """Test email, SMS, WhatsApp, call, or payment integrations."""

    permission_classes = [IsSuperAdmin]

    def get(self, request: Request) -> Response:
        return Response({"success": True, "data": get_integration_channel_status()})

    def post(self, request: Request) -> Response:
        service = request.data.get("service", "")
        payload = request.data

        if service == "email":
            result = EmailService.send(
                payload.get("to", ""),
                payload.get("subject", "Apex Hub test email"),
                payload.get("body", "Integration test message."),
            )
        elif service == "sms":
            result = SMSService.send(
                payload.get("to", ""),
                payload.get("message", "Apex Hub test SMS."),
            )
        elif service == "whatsapp":
            result = WhatsAppService.send(
                payload.get("to", ""),
                payload.get("message", "Apex Hub test WhatsApp message."),
            )
        elif service == "call":
            result = CallService.place_call(
                payload.get("to", ""),
                payload.get("message", ""),
            )
        elif service == "payment":
            tenant = Tenant.objects.filter(pk=payload.get("tenant_id")).first()
            plan = Plan.objects.filter(slug=payload.get("plan_slug", "basic")).first()
            if not tenant or not plan:
                return Response({
                    "success": False,
                    "error": {"message": "tenant_id and valid plan_slug required for payment test."},
                }, status=400)
            result = PaymentService.process_checkout(
                tenant=tenant,
                plan=plan,
                amount=Decimal(str(plan.price_monthly)),
            )
        else:
            return Response({
                "success": False,
                "error": {"message": "service must be one of: email, sms, whatsapp, call, payment"},
            }, status=400)

        return Response({
            "success": result.success,
            "message": result.message,
            "data": result.to_dict(),
        }, status=200 if result.success else 502)