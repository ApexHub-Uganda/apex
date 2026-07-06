import pytest

from apps.core.email_validation import (
    filter_deliverable_emails,
    is_deliverable_email,
    validate_deliverable_email,
)


class TestEmailValidation:
    def test_accepts_real_addresses(self):
        assert validate_deliverable_email("teacher@greenwoodacademy.ug") is None
        assert validate_deliverable_email("client.apexhub@gmail.com") is None

    def test_rejects_placeholder_domains(self):
        assert "not allowed" in validate_deliverable_email("user@example.com").lower()

    def test_rejects_demo_staff_ug_addresses(self):
        assert validate_deliverable_email("staff1@kra.ug") is not None

    def test_filter_removes_invalid(self):
        result = filter_deliverable_emails([
            "client.apexhub@gmail.com",
            "staff2@wgv.ug",
            "user@example.com",
        ])
        assert result == ["client.apexhub@gmail.com"]

    def test_is_deliverable_helper(self):
        assert is_deliverable_email("parent@realschool.org") is True
        assert is_deliverable_email("test@example.com") is False

    def test_bulk_import_rejects_dummy_email(self):
        from apps.core.bulk_import import ImportColumn, ImportSpec, _coerce_value

        col = ImportColumn("email", "Email", required=True, field_type="email")
        value, error = _coerce_value(col, "staff1@kra.ug")
        assert value is None
        assert error is not None