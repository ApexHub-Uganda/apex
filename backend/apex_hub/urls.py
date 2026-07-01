"""Apex Hub URL configuration."""
from __future__ import annotations

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/v1/", include([
        path("auth/", include("apps.accounts.urls")),
        path("tenants/", include("apps.tenants.urls")),
        path("subscriptions/", include("apps.subscriptions.urls")),
        path("academics/", include("apps.academics.urls")),
        path("students/", include("apps.students.urls")),
        path("staff/", include("apps.staff.urls")),
        path("attendance/", include("apps.attendance.urls")),
        path("examinations/", include("apps.examinations.urls")),
        path("finance/", include("apps.finance.urls")),
        path("library/", include("apps.library.urls")),
        path("hostel/", include("apps.hostel.urls")),
        path("transport/", include("apps.transport.urls")),
        path("inventory/", include("apps.inventory.urls")),
        path("hr/", include("apps.hr.urls")),
        path("payroll/", include("apps.payroll.urls")),
        path("communication/", include("apps.communication.urls")),
        path("analytics/", include("apps.analytics.urls")),
        path("audit/", include("apps.audit.urls")),
        path("platform/", include("apps.platform.urls")),
    ])),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)