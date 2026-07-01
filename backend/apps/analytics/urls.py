from django.urls import path

from apps.analytics.views import (
    AttendanceAnalyticsView,
    BillingOperationsView,
    EnrollmentAnalyticsView,
    PlatformAnalyticsView,
    PlatformDashboardView,
    PlansSubscriptionsHubView,
    RevenueAnalyticsView,
    SchoolDashboardView,
    SchoolDetailView,
)

urlpatterns = [
    path("dashboard/school/", SchoolDashboardView.as_view(), name="school-dashboard"),
    path("school/<uuid:tenant_id>/", SchoolDetailView.as_view(), name="school-detail"),
    path("dashboard/platform/", PlatformDashboardView.as_view(), name="platform-dashboard"),
    path("platform/", PlatformAnalyticsView.as_view(), name="platform-analytics"),
    path("plans-subscriptions/", PlansSubscriptionsHubView.as_view(), name="plans-subscriptions-hub"),
    path("billing/", BillingOperationsView.as_view(), name="billing-operations"),
    path("enrollment/", EnrollmentAnalyticsView.as_view(), name="enrollment-analytics"),
    path("attendance/", AttendanceAnalyticsView.as_view(), name="attendance-analytics"),
    path("revenue/", RevenueAnalyticsView.as_view(), name="revenue-analytics"),
]