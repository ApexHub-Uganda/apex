"""Custom user manager."""
from __future__ import annotations

from typing import Any, Optional

from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    """Manager for custom User model."""

    def create_user(
        self,
        email: str,
        password: Optional[str] = None,
        **extra_fields: Any,
    ) -> Any:
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        email: str,
        password: Optional[str] = None,
        **extra_fields: Any,
    ) -> Any:
        from apps.core.constants import UserRole

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_email_verified", True)
        extra_fields.setdefault("role", UserRole.SUPER_ADMIN)

        if extra_fields.get("role") != UserRole.SUPER_ADMIN:
            raise ValueError("Superuser must have super_admin role.")
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")

        return self.create_user(email, password, **extra_fields)