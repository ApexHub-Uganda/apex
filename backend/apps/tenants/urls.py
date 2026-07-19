"""Tenant URL routes."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.tenants.campus_views import CampusViewSet
from apps.tenants.onboarding import CheckoutPlanView, ClaimTrialEmailView, OnboardingDetailView, SelectPlanView
from apps.tenants.school_settings_views import PdfTemplatePreviewView, SchoolSettingsView
from apps.tenants.views import (
    CurrentTenantView,
    RolePermissionMatrixView,
    SchoolContextView,
    TenantRegistrationView,
    TenantViewSet,
)

router = DefaultRouter()
router.register("campuses", CampusViewSet, basename="campus")
router.register("", TenantViewSet, basename="tenant")

urlpatterns = [
    path("register/", TenantRegistrationView.as_view(), name="tenant-register"),
    path("onboarding/<uuid:tenant_id>/", OnboardingDetailView.as_view(), name="tenant-onboarding"),
    path("onboarding/<uuid:tenant_id>/claim-trial/", ClaimTrialEmailView.as_view(), name="tenant-claim-trial"),
    path("onboarding/<uuid:tenant_id>/select-plan/", SelectPlanView.as_view(), name="tenant-select-plan"),
    path("onboarding/<uuid:tenant_id>/checkout/", CheckoutPlanView.as_view(), name="tenant-checkout"),
    path("context/", SchoolContextView.as_view(), name="tenant-context"),
    path("role-permissions/", RolePermissionMatrixView.as_view(), name="tenant-role-permissions"),
    path("current/", CurrentTenantView.as_view(), name="tenant-current"),
    # School profile + branding (persisted) and PDF chrome preview
    path("settings/", SchoolSettingsView.as_view(), name="tenant-school-settings"),
    path("pdf-preview/", PdfTemplatePreviewView.as_view(), name="tenant-pdf-preview"),
    path("", include(router.urls)),
]