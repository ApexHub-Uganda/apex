"""Finance data access — gated by Permission Settings feature grants."""
from __future__ import annotations

from apps.tenants.role_permissions import get_user_feature_permissions, user_is_school_admin

FINANCE_SCHOOL_WIDE_FEATURES = frozenset({
    "bursar_workspace",
    "assistant_bursar_workspace",
    "fee_structures",
    "fee_categories",
    "discounts",
    "student_billing",
    "invoice_generation",
    "payment_recording",
    "misc_income",
    "expenses",
    "refunds",
    "debtor_management",
    "finance_notes",
    "financial_reports",
    "finance_analytics",
    "transaction_approval",
    "budget_management",
    "financial_accounts",
    "accounting_periods",
})


def user_has_school_wide_finance_access(user, tenant=None) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if user_is_school_admin(user):
        return True
    tenant = tenant or getattr(user, "tenant", None)
    if tenant is None:
        return False
    perms = get_user_feature_permissions(tenant, user)
    return any(perms.get(key, {}).get("can_read") for key in FINANCE_SCHOOL_WIDE_FEATURES)


def filter_finance_queryset_for_user(queryset, user):
    """Tenant filtering is handled by TenantFilterMixin; finance requires feature grants."""
    if user_has_school_wide_finance_access(user, getattr(user, "tenant", None)):
        return queryset
    return queryset.none()


def user_can_approve_finance_transactions(user, tenant=None) -> bool:
    if user_is_school_admin(user):
        return True
    tenant = tenant or getattr(user, "tenant", None)
    if tenant is None:
        return False
    from apps.tenants.role_permissions import user_can_access_feature

    return user_can_access_feature(tenant, user, "transaction_approval", require_write=True)