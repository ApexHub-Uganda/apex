# Architecture

Apex Hub is a multi-tenant school management SaaS. One PostgreSQL database serves many schools (tenants); platform operators use a separate super-admin portal.

## High-level diagram

```
┌─────────────┐     HTTPS/JWT      ┌──────────────────────────────────┐
│  React SPA  │ ◄────────────────► │  Django REST API (Gunicorn)      │
│  (Vite)     │                    │  ┌────────────┐  ┌─────────────┐ │
└─────────────┘                    │  │ ViewSets   │→ │ Services    │ │
                                   │  └────────────┘  └──────┬──────┘ │
                                   └─────────────────────────┼────────┘
                                                             │
                    ┌────────────────────────────────────────┼────────┐
                    ▼                    ▼                   ▼        ▼
              PostgreSQL            Redis              Celery    External APIs
              (tenants, plans,      (cache, broker)    (beat)    (email, SMS,
               broadcasts, …)                                      WhatsApp, pay)
```

## Layers

| Layer | Responsibility | Location |
|-------|----------------|----------|
| **Presentation** | SPA, routing, forms, optimistic UI | `frontend/src/` |
| **API** | Auth, permissions, serialization, HTTP codes | `backend/apps/*/views.py` |
| **Domain services** | Business rules, orchestration, integrations | `backend/apps/*/services/` |
| **Data** | Models, migrations, query managers | `backend/apps/*/models.py` |
| **Infrastructure** | Settings, middleware, Celery, Docker | `apex_hub/`, `deployment/` |

**Rule:** Views call services; services call models and external integrations. Avoid business logic in serializers except validation.

## Multi-tenancy

- Every school is a `tenants.Tenant`.
- Tenant-scoped models inherit `apps.core.models.BaseModel` and use `TenantAwareManager`.
- JWT identifies the user; `TenantContext` resolves the active tenant from the user record.
- **Super admins** (`role=super_admin`, no tenant) bypass tenant filters and access `/platform/*`.

## Roles and portals

| Role | Portal prefix | Primary capabilities |
|------|---------------|----------------------|
| `super_admin` | `/super-admin` | Schools, plans, broadcasts, billing, platform settings |
| `school_admin` | `/school-admin` | Full school operations (feature-gated by plan) |
| Other roles | `/school-admin` (subset) | Module-specific access per plan features |

## Subscription and feature gating

```
Plan (slug, features M2M)
    └── Subscription (tenant, status: trial | active | grace_period | expired | …)
            └── tenant_has_feature() → school UI modules + API access
```

- Plan tiers are ordered: `free_trial` → `basic` → `premium` → `premium_plus`.
- Higher tiers **inherit** lower-tier features (`subscriptions/plan_tiers.py`).
- School routes wrap content in `<FeatureGate featureKey="…">` (`frontend/src/components/FeatureGate.jsx`).
- Lifecycle transitions (trial → grace → expired) run hourly via Celery (`subscriptions/subscription_lifecycle.py`).

## Platform vs tenant data

| Scope | Base model | Examples |
|-------|------------|----------|
| Platform-wide | `PlatformModel` | `PlatformBroadcast`, `PlanAdvertisement`, `GlobalSetting` |
| Per-tenant | `BaseModel` | `Student`, `Notification`, `Subscription` |

Platform broadcasts target school admins across tenants; delivery logs live in `PlatformBroadcastDelivery`.

## Authentication

- Email + password login → JWT access + refresh tokens.
- `rest_framework_simplejwt` with token blacklist on logout.
- Protected routes: `IsAuthenticated`; super-admin routes: `IsSuperAdmin`.

## Background jobs (Celery beat)

| Task | Schedule | Module |
|------|----------|--------|
| `subscriptions.process_subscription_lifecycle` | Hourly | Trial/grace/expiry |
| `platform.process_scheduled_broadcasts` | Hourly | Due platform broadcasts |

Management command equivalents exist for manual runs (see [DEVELOPMENT.md](DEVELOPMENT.md)).

## Error and response conventions

**List endpoints** — DRF pagination: `{ count, next, previous, results }`.

**Action endpoints** (send, approve, delete) — often:

```json
{ "success": true, "message": "Human-readable outcome", "data": { } }
```

**Errors** — `{ "success": false, "message": "…" }` or DRF `{ "detail": … }` (see `apps/core/exceptions.py`).

## Key design decisions

1. **Database-driven admin workflows** — Broadcasts, plans, advertisements, and notifications persist state in PostgreSQL; UI actions map to API mutations and service functions.
2. **Integration readiness** — Payment and messaging gateways build full payloads but gate live HTTP behind `INTEGRATION_LIVE_DISPATCH` until deployment.
3. **Auditability** — Deliveries, payment transactions, and audit logs retained for operator review.
4. **Professional super-admin UX** — Full-page workspaces (Plan Editor, Broadcast, Advertise) instead of generic CRUD modals where workflows are multi-step.

## Related docs

- [BACKEND.md](BACKEND.md) — implementation patterns
- [FRONTEND.md](FRONTEND.md) — UI structure
- [FEATURES.md](FEATURES.md) — feature map
- [INTEGRATIONS.md](INTEGRATIONS.md) — external systems