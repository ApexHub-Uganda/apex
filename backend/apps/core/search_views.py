"""Global portal search API."""
from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.portal_search import search_portal


class PortalSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        query = (request.query_params.get("q") or "").strip()
        try:
            limit = min(max(int(request.query_params.get("limit", 20)), 1), 50)
        except (TypeError, ValueError):
            limit = 20

        data = search_portal(request.user, query, limit=limit)
        return Response({"success": True, "data": data})