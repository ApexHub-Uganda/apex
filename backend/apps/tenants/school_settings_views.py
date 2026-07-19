"""School-admin settings + PDF template preview endpoints."""
from __future__ import annotations

from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from django.http import HttpResponse

from apps.core.exports import pdf_attachment_response
from apps.core.permissions import IsSchoolAdmin, IsSchoolPortalUser, TenantActivePermission
from apps.core.pdf_branding import build_tenant_branding
from apps.core.pdf_template import build_pdf_template_preview
from apps.tenants.serializers import SchoolSettingsSerializer
from apps.tenants.views import _resolve_user_tenant


class SchoolSettingsView(APIView):
    """
    GET/PATCH the current school profile & branding.

    School admins may update colours, logo, contacts, and motto/tagline.
    Other school portal users may read branding (for themed UI) but not write.
    """

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH", "POST"):
            return [IsAuthenticated(), IsSchoolAdmin(), TenantActivePermission()]
        return [IsAuthenticated(), IsSchoolPortalUser()]

    def get(self, request: Request) -> Response:
        tenant = _resolve_user_tenant(request.user)
        if tenant is None:
            return Response(
                {"success": False, "error": {"message": "No school linked to this account."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        ser = SchoolSettingsSerializer(tenant, context={"request": request})
        branding = build_tenant_branding(tenant, request=request)
        return Response({
            "success": True,
            "data": {
                **ser.data,
                "branding": branding,
            },
        })

    def patch(self, request: Request) -> Response:
        return self._update(request, partial=True)

    def put(self, request: Request) -> Response:
        return self._update(request, partial=False)

    def _update(self, request: Request, *, partial: bool) -> Response:
        tenant = _resolve_user_tenant(request.user)
        if tenant is None:
            return Response(
                {"success": False, "error": {"message": "No school linked to this account."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Support both multipart (logo file) and JSON.
        data = request.data
        ser = SchoolSettingsSerializer(
            tenant,
            data=data,
            partial=partial,
            context={"request": request},
        )
        ser.is_valid(raise_exception=True)
        ser.save()
        tenant.refresh_from_db()

        # Invalidate any feature/nav caches keyed by tenant if present.
        try:
            from apps.subscriptions.services import invalidate_tenant_cache
            invalidate_tenant_cache(str(tenant.id))
        except Exception:
            pass

        out = SchoolSettingsSerializer(tenant, context={"request": request})
        branding = build_tenant_branding(tenant, request=request)
        return Response({
            "success": True,
            "message": "School settings saved.",
            "data": {
                **out.data,
                "branding": branding,
                # Include refreshed portal context colours so SPA can re-apply theme.
                "context_patch": {
                    "name": tenant.name,
                    "email": tenant.email,
                    "phone": tenant.phone,
                    "address": tenant.address,
                    "city": tenant.city,
                    "country": tenant.country,
                    "timezone": tenant.timezone,
                    "website": tenant.website,
                    "tagline": tenant.tagline,
                    "logo": branding.get("logo_url"),
                    "primary_color": tenant.primary_color,
                    "secondary_color": tenant.secondary_color,
                    "accent_color": tenant.accent_color,
                },
            },
        })


class PdfTemplatePreviewView(APIView):
    """
    Download a sample A4 PDF that uses the school's live branding chrome.

    School admins use this from Settings → PDF template preview.
    """

    permission_classes = [IsAuthenticated, IsSchoolAdmin, TenantActivePermission]

    def get(self, request: Request) -> HttpResponse:
        tenant = _resolve_user_tenant(request.user)
        if tenant is None:
            return Response(
                {"success": False, "error": {"message": "No school linked to this account."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            pdf_bytes = build_pdf_template_preview(tenant=tenant, request=request)
        except Exception as exc:
            return Response(
                {
                    "success": False,
                    "error": {"message": f"Unable to generate PDF preview: {exc}"},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        code = (tenant.code or "school").lower()
        return pdf_attachment_response(
            pdf_bytes=pdf_bytes,
            filename=f"{code}-pdf-template-preview.pdf",
        )
