from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.subscriptions.views import (
    CurrentSubscriptionView,
    FeatureCatalogView,
    FeatureCategoryViewSet,
    FeatureFlagViewSet,
    PaymentProviderViewSet,
    PaymentTransactionViewSet,
    PlanListView,
    PlanViewSet,
    SubscriptionViewSet,
)

router = DefaultRouter()
router.register("plans/manage", PlanViewSet, basename="plan-manage")
router.register("features/categories", FeatureCategoryViewSet, basename="feature-category")
router.register("features/manage", FeatureFlagViewSet, basename="feature-manage")
router.register("", SubscriptionViewSet, basename="subscription")
router.register("payments/providers", PaymentProviderViewSet, basename="payment-provider")
router.register("payments/transactions", PaymentTransactionViewSet, basename="payment-transaction")

urlpatterns = [
    path("plans/", PlanListView.as_view(), name="plan-list"),
    path("features/catalog/", FeatureCatalogView.as_view(), name="feature-catalog"),
    path("current/", CurrentSubscriptionView.as_view(), name="subscription-current"),
    path("", include(router.urls)),
]