"""Subscription views."""
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsSchoolAdmin, IsSuperAdmin, TenantActivePermission
from apps.subscriptions.models import FeatureCategory, FeatureFlag, PaymentProvider, PaymentTransaction, Plan, Subscription
from apps.subscriptions.serializers import (
    FeatureCategorySerializer,
    FeatureFlagSerializer,
    PaymentProviderSerializer,
    PaymentTransactionSerializer,
    PlanSerializer,
    SubscriptionCreateSerializer,
    SubscriptionSerializer,
)
from apps.subscriptions.services import (
    get_feature_catalog,
    invalidate_catalog_cache,
    notify_tenant_subscription_update,
)


class PlanListView(generics.ListAPIView):
    queryset = Plan.objects.filter(is_active=True, is_public=True).prefetch_related("features")
    serializer_class = PlanSerializer
    permission_classes = [AllowAny]


class PlanViewSet(viewsets.ModelViewSet):
    queryset = Plan.objects.prefetch_related("features__category").all()
    serializer_class = PlanSerializer
    permission_classes = [IsSuperAdmin]
    filterset_fields = ["is_active", "is_public"]
    search_fields = ["name", "slug"]


class FeatureCatalogView(generics.ListAPIView):
    permission_classes = [IsSuperAdmin]

    def list(self, request: Request, *args, **kwargs) -> Response:
        categories = get_feature_catalog()
        total = sum(len(c["features"]) for c in categories)
        return Response({"success": True, "data": {"categories": categories, "total_features": total}})


class FeatureCategoryViewSet(viewsets.ModelViewSet):
    queryset = FeatureCategory.objects.prefetch_related("features").order_by("sort_order")
    serializer_class = FeatureCategorySerializer
    permission_classes = [IsSuperAdmin]
    search_fields = ["name", "slug"]

    def perform_create(self, serializer):
        super().perform_create(serializer)
        invalidate_catalog_cache()

    def perform_update(self, serializer):
        super().perform_update(serializer)
        invalidate_catalog_cache()

    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        invalidate_catalog_cache()


class FeatureFlagViewSet(viewsets.ModelViewSet):
    queryset = FeatureFlag.objects.select_related("category").order_by("category__sort_order", "sort_order")
    serializer_class = FeatureFlagSerializer
    permission_classes = [IsSuperAdmin]
    filterset_fields = ["category", "is_active", "show_in_nav"]
    search_fields = ["feature_key", "feature_name"]

    def perform_create(self, serializer):
        super().perform_create(serializer)
        invalidate_catalog_cache()

    def perform_update(self, serializer):
        super().perform_update(serializer)
        invalidate_catalog_cache()

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])
        invalidate_catalog_cache()


class SubscriptionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSchoolAdmin, TenantActivePermission]
    filterset_fields = ["status", "plan"]
    ordering_fields = ["created_at", "current_period_end"]

    def get_serializer_class(self):
        if self.action == "create":
            return SubscriptionCreateSerializer
        return SubscriptionSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_super_admin:
            tenant_id = self.request.query_params.get("tenant_id")
            qs = Subscription.objects.select_related("plan", "tenant")
            if tenant_id:
                return qs.filter(tenant_id=tenant_id)
            return qs
        return Subscription.objects.filter(tenant=user.tenant).select_related("plan")

    def get_permissions(self):
        if self.action in ("create", "destroy", "suspend"):
            return [IsSuperAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        sub = serializer.save()
        notify_tenant_subscription_update(sub, event="subscription_created")

    @action(detail=True, methods=["post"], permission_classes=[IsSuperAdmin])
    def activate(self, request: Request, pk: str = None) -> Response:
        sub = self.get_object()
        days = int(request.data.get("period_days", 30))
        sub.activate(period_days=days)
        notify_tenant_subscription_update(sub, event="subscription_activated")
        return Response(SubscriptionSerializer(sub).data)

    @action(detail=True, methods=["post"], permission_classes=[IsSuperAdmin])
    def suspend(self, request: Request, pk: str = None) -> Response:
        sub = self.get_object()
        sub.suspend()
        notify_tenant_subscription_update(sub, event="subscription_suspended")
        return Response({"success": True, "message": "Subscription suspended."})


class PlanUpgradeCatalogView(APIView):
    """Upgrade-eligible plans and payment options for school admins."""

    permission_classes = [IsSchoolAdmin, TenantActivePermission]

    def get(self, request: Request) -> Response:
        from apps.subscriptions.upgrade_services import get_upgrade_catalog

        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return Response(
                {"success": False, "error": {"message": "No school context."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"success": True, "data": get_upgrade_catalog(tenant)})


class PlanUpgradeCheckoutView(APIView):
    """Initiate plan upgrade checkout (stub — payment gateway not connected)."""

    permission_classes = [IsSchoolAdmin, TenantActivePermission]

    def post(self, request: Request) -> Response:
        from apps.subscriptions.upgrade_services import process_upgrade_checkout

        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return Response(
                {"success": False, "error": {"message": "No school context."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        plan_slug = request.data.get("plan_slug")
        if not plan_slug:
            return Response(
                {"success": False, "error": {"message": "plan_slug is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = process_upgrade_checkout(
                tenant,
                plan_slug=plan_slug,
                billing_cycle=request.data.get("billing_cycle", "monthly"),
                payment_method=request.data.get("payment_method", "card"),
                provider_slug=request.data.get("provider_slug", ""),
                phone_number=request.data.get("phone_number", ""),
                card_last_four=request.data.get("card_last_four", ""),
                card_brand=request.data.get("card_brand", ""),
                payer_name=request.data.get("payer_name", ""),
                actor=request.user,
            )
        except ValueError as exc:
            return Response(
                {"success": False, "error": {"message": str(exc)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"success": False, "message": result["message"], "data": result},
            status=status.HTTP_402_PAYMENT_REQUIRED,
        )


class CurrentSubscriptionView(generics.RetrieveAPIView):
    serializer_class = SubscriptionSerializer
    permission_classes = [IsSchoolAdmin]

    def get_object(self):
        tenant = getattr(self.request.user, "tenant", None)
        if tenant is None:
            return None
        return Subscription.objects.filter(
            tenant=tenant,
            status__in=["trial", "active", "grace_period"],
        ).select_related("plan").first()

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        instance = self.get_object()
        if instance is None:
            return Response(None)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class PaymentProviderViewSet(viewsets.ModelViewSet):
    queryset = PaymentProvider.objects.all()
    serializer_class = PaymentProviderSerializer
    permission_classes = [IsSuperAdmin]


class PaymentTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentTransactionSerializer
    permission_classes = [IsSchoolAdmin]
    filterset_fields = ["status", "provider", "tenant"]
    search_fields = ["reference", "external_id"]
    ordering_fields = ["created_at", "amount", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user
        qs = PaymentTransaction.objects.select_related("tenant", "provider", "subscription")
        if user.is_super_admin:
            return qs
        return qs.filter(tenant=user.tenant)