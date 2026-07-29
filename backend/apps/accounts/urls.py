"""Account URL routes."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from apps.accounts.dual_role_views import (
    DualRoleCandidatesView,
    DualRoleGrantView,
    DualRoleOptionsView,
    DualRoleRevokePreviewView,
    DualRoleRevokeView,
    SwitchRoleView,
)
from apps.accounts.webauthn_views import (
    WebAuthnAuthenticateOptionsView,
    WebAuthnCredentialDeleteView,
    WebAuthnRegisterOptionsView,
    WebAuthnRegisterVerifyView,
    WebAuthnStatusView,
)
from apps.accounts.views import (
    ChangePasswordView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    HeadedPaperPdfView,
    LoginHistoryViewSet,
    LogoutView,
    MeAvatarView,
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
    path("refresh/", CustomTokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("me/avatar/", MeAvatarView.as_view(), name="me-avatar"),
    path("me/headed-paper.pdf", HeadedPaperPdfView.as_view(), name="me-headed-paper"),
    path("switch-role/", SwitchRoleView.as_view(), name="switch-role"),
    path("dual-roles/options/", DualRoleOptionsView.as_view(), name="dual-role-options"),
    path("dual-roles/candidates/", DualRoleCandidatesView.as_view(), name="dual-role-candidates"),
    path("dual-roles/grant/", DualRoleGrantView.as_view(), name="dual-role-grant"),
    path("dual-roles/revoke/preview/", DualRoleRevokePreviewView.as_view(), name="dual-role-revoke-preview"),
    path("dual-roles/revoke/", DualRoleRevokeView.as_view(), name="dual-role-revoke"),
    path("webauthn/status/", WebAuthnStatusView.as_view(), name="webauthn-status"),
    path("webauthn/register/options/", WebAuthnRegisterOptionsView.as_view(), name="webauthn-register-options"),
    path("webauthn/register/verify/", WebAuthnRegisterVerifyView.as_view(), name="webauthn-register-verify"),
    path("webauthn/authenticate/options/", WebAuthnAuthenticateOptionsView.as_view(), name="webauthn-auth-options"),
    path(
        "webauthn/credentials/<uuid:credential_id>/",
        WebAuthnCredentialDeleteView.as_view(),
        name="webauthn-credential-delete",
    ),
    path("notifications/feed/", NotificationFeedView.as_view(), name="notification-feed"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("", include(router.urls)),
]