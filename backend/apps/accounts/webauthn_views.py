"""WebAuthn API for staff biometric enrollment & verification."""
from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.webauthn_service import (
    WebAuthnError,
    begin_authentication,
    begin_registration,
    complete_registration,
    list_credentials,
    revoke_credential,
    webauthn_status,
)
from apps.core.permissions import TenantActivePermission


class WebAuthnStatusView(APIView):
    permission_classes = [IsAuthenticated, TenantActivePermission]

    def get(self, request: Request) -> Response:
        return Response({"success": True, "data": webauthn_status(request.user)})


class WebAuthnRegisterOptionsView(APIView):
    permission_classes = [IsAuthenticated, TenantActivePermission]

    def post(self, request: Request) -> Response:
        try:
            options = begin_registration(request, request.user)
        except WebAuthnError as exc:
            return Response({"success": False, "message": exc.message, "code": exc.code}, status=400)
        except Exception as exc:
            return Response(
                {"success": False, "message": f"Unable to start biometric registration: {exc}", "code": "register_options"},
                status=400,
            )
        return Response({"success": True, "data": options})


class WebAuthnRegisterVerifyView(APIView):
    permission_classes = [IsAuthenticated, TenantActivePermission]

    def post(self, request: Request) -> Response:
        credential = request.data.get("credential") or request.data
        device_label = request.data.get("device_label") or request.data.get("label") or ""
        if isinstance(credential, dict) and "credential" in credential and "id" not in credential:
            credential = credential["credential"]
        try:
            data = complete_registration(
                request,
                request.user,
                credential if isinstance(credential, dict) else request.data,
                device_label=str(device_label or ""),
            )
        except WebAuthnError as exc:
            return Response({"success": False, "message": exc.message, "code": exc.code}, status=400)
        except Exception as exc:
            return Response(
                {"success": False, "message": f"Biometric registration failed: {exc}", "code": "register_verify"},
                status=400,
            )
        return Response({"success": True, "message": data.get("message"), "data": data})


class WebAuthnAuthenticateOptionsView(APIView):
    permission_classes = [IsAuthenticated, TenantActivePermission]

    def post(self, request: Request) -> Response:
        try:
            options = begin_authentication(request, request.user)
        except WebAuthnError as exc:
            return Response({"success": False, "message": exc.message, "code": exc.code}, status=400)
        except Exception as exc:
            return Response(
                {"success": False, "message": f"Unable to start biometric verification: {exc}", "code": "auth_options"},
                status=400,
            )
        return Response({"success": True, "data": options})


class WebAuthnCredentialDeleteView(APIView):
    permission_classes = [IsAuthenticated, TenantActivePermission]

    def delete(self, request: Request, credential_id: str) -> Response:
        try:
            data = revoke_credential(user=request.user, credential_pk=credential_id)
        except WebAuthnError as exc:
            return Response({"success": False, "message": exc.message, "code": exc.code}, status=400)
        return Response({"success": True, "message": data.get("message"), "data": data})

    def post(self, request: Request, credential_id: str) -> Response:
        # Allow POST delete for clients that cannot send DELETE easily
        return self.delete(request, credential_id)
