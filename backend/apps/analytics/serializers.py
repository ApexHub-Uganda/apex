"""Analytics serializers (minimal - mostly service-driven)."""
from rest_framework import serializers

from apps.analytics.models import DashboardSnapshot


class DashboardSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardSnapshot
        fields = "__all__"