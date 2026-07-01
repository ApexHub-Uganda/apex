from django.contrib import admin

from apps.analytics.models import DashboardSnapshot


@admin.register(DashboardSnapshot)
class DashboardSnapshotAdmin(admin.ModelAdmin):
    list_display = ["snapshot_type", "tenant", "created_at"]