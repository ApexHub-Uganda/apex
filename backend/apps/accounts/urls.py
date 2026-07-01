"""Account URL routes."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.views import (
    ChangePasswordView,
    CustomTokenObtainPairView,
    LoginHistoryViewSet,
    LogoutView,
    MeView,
    NotificationFeedView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    UserDeviceViewSet,
    UserViewSet,
)

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("login-history", LoginHistoryViewSet, basename="login-history")
router.register("devices", UserDeviceViewSet, basename="device")

urlpatterns = [
    path("login/", CustomTokenObtainPairView.as_view(), name="token-obtain"),
    path("refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("notifications/feed/", NotificationFeedView.as_view(), name="notification-feed"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("", include(router.urls)),
]