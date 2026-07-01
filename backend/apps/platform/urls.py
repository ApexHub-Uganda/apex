from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.platform.views_integrations import IntegrationTestView
from apps.platform.views import (
    APIKeyViewSet,
    CallSettingViewSet,
    EmailSettingViewSet,
    GlobalSettingViewSet,
    HealthCheckView,
    MaintenanceModeView,
    PlatformBroadcastViewSet,
    PlatformNewsViewSet,
    PlatformNotificationViewSet,
    PlatformSettingsView,
    PublicPlatformSettingsView,
    SMSSettingViewSet,
    SchoolsManagementView,
    SystemHealthLogViewSet,
)

router = DefaultRouter()
router.register("settings", GlobalSettingViewSet, basename="global-setting")
router.register("email-settings", EmailSettingViewSet, basename="email-setting")
router.register("sms-settings", SMSSettingViewSet, basename="sms-setting")
router.register("call-settings", CallSettingViewSet, basename="call-setting")
router.register("notifications", PlatformNotificationViewSet, basename="platform-notification")
router.register("api-keys", APIKeyViewSet, basename="api-key")
router.register("news", PlatformNewsViewSet, basename="platform-news")
router.register("broadcasts", PlatformBroadcastViewSet, basename="platform-broadcast")
router.register("health-logs", SystemHealthLogViewSet, basename="health-log")

urlpatterns = [
    path("integrations/test/", IntegrationTestView.as_view(), name="integration-test"),
    path("settings/public/", PublicPlatformSettingsView.as_view(), name="platform-settings-public"),
    path("settings/general/", PlatformSettingsView.as_view(), name="platform-settings"),
    path("schools/", SchoolsManagementView.as_view(), name="schools-management"),
    path("health/", HealthCheckView.as_view(), name="health-check"),
    path("maintenance/", MaintenanceModeView.as_view(), name="maintenance-mode"),
    path("", include(router.urls)),
]