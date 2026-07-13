"""Reusable bulk Excel/CSV import actions for viewsets."""
from __future__ import annotations

from typing import Any

from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.bulk_import import (
    DEFAULT_IMPORT_FORMAT,
    generate_import_template,
    is_supported_import_filename,
    parse_upload,
    unsupported_import_message,
    validate_rows,
)


class BulkImportMixin:
    """Add import-template, validate-import, and commit-import actions."""

    import_spec: Any = None

    def get_import_spec(self):
        if self.import_spec is None:
            raise NotImplementedError(f"{self.__class__.__name__} must define import_spec or get_import_spec()")
        return self.import_spec

    def get_import_row_resolver(self):
        return None

    def commit_import_rows(self, rows: list[dict], *, request: Request) -> dict[str, Any]:
        raise NotImplementedError

    @action(detail=False, methods=["get"], url_path="import-template")
    def import_template(self, request: Request) -> HttpResponse:
        spec = self.get_import_spec()
        file_format = (
            request.query_params.get("file_format")
            or request.query_params.get("format", DEFAULT_IMPORT_FORMAT)
        )
        content, filename, content_type = generate_import_template(spec, file_format=file_format)
        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(
        detail=False,
        methods=["post"],
        url_path="validate-import",
        parser_classes=[MultiPartParser, FormParser],
    )
    def validate_import(self, request: Request) -> Response:
        upload = request.FILES.get("file")
        if not upload:
            return Response(
                {"success": False, "message": "No file uploaded. Attach an Excel or CSV file."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not is_supported_import_filename(upload.name):
            return Response(
                {"success": False, "message": unsupported_import_message()},
                status=status.HTTP_400_BAD_REQUEST,
            )

        spec = self.get_import_spec()
        headers, raw_rows = parse_upload(upload)
        resolver = self.get_import_row_resolver()
        result = validate_rows(spec, headers, raw_rows, row_resolver=resolver)

        return Response({
            "success": True,
            "message": (
                f"Validated {result['total_rows']} rows — "
                f"{result['valid_count']} ready, {result['error_count']} issues."
            ),
            "data": result,
        })

    @action(detail=False, methods=["post"], url_path="commit-import")
    def commit_import(self, request: Request) -> Response:
        rows = request.data.get("rows")
        if not isinstance(rows, list) or not rows:
            return Response(
                {"success": False, "message": "No validated rows to import."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        spec = self.get_import_spec()
        resolver = self.get_import_row_resolver()
        revalidated = validate_rows(
            spec,
            list(spec.all_keys),
            [{k: str(v) if v is not None else "" for k, v in row.items() if not k.startswith("_")} for row in rows],
            row_resolver=resolver,
        )

        if not revalidated["can_commit"]:
            return Response(
                {"success": False, "message": "Import blocked — fix validation errors first.", "data": revalidated},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(revalidated["ready"]) != len(rows):
            return Response(
                {"success": False, "message": "Row data changed since validation. Re-validate the file.", "data": revalidated},
                status=status.HTTP_400_BAD_REQUEST,
            )

        outcome = self.commit_import_rows(revalidated["ready"], request=request)
        return Response({
            "success": True,
            "message": outcome.get("message", f"Imported {outcome.get('created', 0)} records."),
            "data": outcome,
        })