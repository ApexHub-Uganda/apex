"""Thread-local tenant context."""
from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from apps.accounts.models import User
    from apps.tenants.models import Tenant

_state = threading.local()


class TenantContext:
    """Manage per-request tenant and user context."""

    @staticmethod
    def set_tenant(tenant: Optional[Tenant]) -> None:
        _state.tenant = tenant

    @staticmethod
    def get_tenant() -> Optional[Tenant]:
        return getattr(_state, "tenant", None)

    @staticmethod
    def set_user(user: Optional[User]) -> None:
        _state.user = user

    @staticmethod
    def get_user() -> Optional[User]:
        return getattr(_state, "user", None)

    @staticmethod
    def clear() -> None:
        _state.tenant = None
        _state.user = None