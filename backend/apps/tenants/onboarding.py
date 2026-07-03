"""Public school onboarding after registration."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import transaction
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.constants import RegistrationType
from apps.platform.services.integrations import PaymentService
from apps.platform.services.notifications import create_registration_notification
from apps.platform.views import PLATFORM_SETTINGS_DEFAULTS
from apps.subscriptions.models import Plan, Subscription
from apps.subscriptions.serializers import PlanSerializer
from apps.tenants.models import Tenant


def _public_settings() -> dict[str, Any]:
    from apps.platform.models import GlobalSetting

    data = {
        "support_email": PLATFORM_SETTINGS_DEFAULTS["support_email"],
        "platform_name": PLATFORM_SETTINGS_DEFAULTS["platform_name"],
    }
    setting = GlobalSetting.objects.filter(key="platform_config").first()
    if setting and setting.value:
        data["support_email"] = setting.value.get("support_email", data["support_email"])
        data["platform_name"] = setting.value.get("platform_name", data["platform_name"])
    return data


def _assign_plan(tenant: Tenant, plan: Plan, *, billing_cycle: str = "monthly") -> Subscription:
    from apps.tenants.services import assign_tenant_plan

    return assign_tenant_plan(
        tenant,
        plan,
        billing_cycle=billing_cycle,
        subscription_status="trial",
    )


class OnboardingDetailView(APIView):
    """Public onboarding context for a newly registered school."""

    permission_classes = [AllowAny]

    def get(self, request: Request, tenant_id: str) -> Response:
        try:
            tenant = Tenant.objects.get(pk=tenant_id)
        except Tenant.DoesNotExist:
            return Response(
                {"success": False, "error": {"message": "School not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        plans = Plan.objects.filter(is_active=True, is_public=True).order_by("sort_order", "price_monthly")
        sub = tenant.active_subscription

        return Response({
            "success": True,
            "data": {
                "school": {
                    "id": str(tenant.id),
                    "name": tenant.name,
                    "code": tenant.code,
                    "registration_type": tenant.registration_type,
                    "is_verified": tenant.is_verified,
                    "payment_attempted": tenant.payment_attempted,
                },
                "current_plan": sub.plan.slug if sub and sub.plan else None,
                "plans": PlanSerializer(plans, many=True).data,
                "settings": _public_settings(),
            },
        })


class ClaimTrialEmailView(APIView):
    """Mark school as requesting free trial via support email."""

    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request: Request, tenant_id: str) -> Response:
        try:
            tenant = Tenant.objects.get(pk=tenant_id)
        except Tenant.DoesNotExist:
            return Response(
                {"success": False, "error": {"message": "School not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        trial_plan = Plan.objects.filter(slug="free_trial").first()
        if trial_plan:
            _assign_plan(tenant, trial_plan)

        tenant.registration_type = RegistrationType.TRIAL_EMAIL
        tenant.save(update_fields=["registration_type", "updated_at"])

        notification = create_registration_notification(
            tenant,
            registration_type=RegistrationType.TRIAL_EMAIL,
            plan_name=trial_plan.name if trial_plan else "Free Trial",
            plan_slug=trial_plan.slug if trial_plan else "free_trial",
        )

        settings_data = _public_settings()
        return Response({
            "success": True,
            "message": (
                f"Trial request recorded. Email {settings_data['support_email']} to claim your offer, "
                "or wait for super admin approval."
            ),
            "data": {
                "support_email": settings_data["support_email"],
                "notification_id": str(notification.id),
            },
        })


class SelectPlanView(APIView):
    """Select a trial plan during onboarding."""

    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request: Request, tenant_id: str) -> Response:
        plan_slug = request.data.get("plan_slug")
        if not plan_slug:
            return Response(
                {"success": False, "error": {"message": "plan_slug is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            tenant = Tenant.objects.get(pk=tenant_id)
        except Tenant.DoesNotExist:
            return Response(
                {"success": False, "error": {"message": "School not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        plan = Plan.objects.filter(slug=plan_slug, is_active=True, is_public=True).first()
        if not plan:
            return Response(
                {"success": False, "error": {"message": "Plan not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        billing_cycle = request.data.get("billing_cycle", "monthly")
        _assign_plan(tenant, plan, billing_cycle=billing_cycle)

        tenant.registration_type = RegistrationType.TRIAL_PLAN
        tenant.save(update_fields=["registration_type", "updated_at"])

        notification = create_registration_notification(
            tenant,
            registration_type=RegistrationType.TRIAL_PLAN,
            plan_name=plan.name,
            plan_slug=plan.slug,
        )

        return Response({
            "success": True,
            "message": (
                f"{plan.name} plan selected. You may sign in, but dashboard access requires "
                "super admin approval."
            ),
            "data": {
                "plan": plan.slug,
                "notification_id": str(notification.id),
                "requires_approval": True,
            },
        })


class CheckoutPlanView(APIView):
    """Attempt paid plan checkout (stub until payment APIs are connected)."""

    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request: Request, tenant_id: str) -> Response:
        plan_slug = request.data.get("plan_slug")
        billing_cycle = request.data.get("billing_cycle", "monthly")

        if not plan_slug:
            return Response(
                {"success": False, "error": {"message": "plan_slug is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            tenant = Tenant.objects.get(pk=tenant_id)
        except Tenant.DoesNotExist:
            return Response(
                {"success": False, "error": {"message": "School not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        plan = Plan.objects.filter(slug=plan_slug, is_active=True, is_public=True).first()
        if not plan:
            return Response(
                {"success": False, "error": {"message": "Plan not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        amount = plan.price_yearly if billing_cycle == "yearly" else plan.price_monthly
        if amount <= 0:
            return Response(
                {"success": False, "error": {"message": "Selected plan does not require payment."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payment_result = PaymentService.process_checkout(
            tenant=tenant,
            plan=plan,
            amount=Decimal(str(amount)),
            billing_cycle=billing_cycle,
            currency=plan.currency,
            payment_method=request.data.get("payment_method", "card"),
            provider_slug=request.data.get("provider_slug", ""),
            phone_number=request.data.get("phone_number", ""),
            card_last_four=request.data.get("card_last_four", ""),
            card_brand=request.data.get("card_brand", ""),
            payer_name=request.data.get("payer_name", ""),
            )
        except ValueError as exc:
            return Response(
                {"success": False, "error": {"message": str(exc)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        _assign_plan(tenant, plan, billing_cycle=billing_cycle)
        tenant.registration_type = RegistrationType.PAID
        tenant.save(update_fields=["registration_type", "updated_at"])

        notification = create_registration_notification(
            tenant,
            registration_type=RegistrationType.PAID,
            plan_name=plan.name,
            plan_slug=plan.slug,
            payment_reference=payment_result.reference,
            extra_metadata=payment_result.metadata,
        )

        return Response({
            "success": False,
            "message": payment_result.message,
            "data": {
                "payment": payment_result.to_dict(),
                "notification_id": str(notification.id),
                "requires_activation": True,
            },
        }, status=status.HTTP_402_PAYMENT_REQUIRED)