# Development Guide

How to set up, test, and land changes systematically.

## Prerequisites

- Python 3.13+
- Node.js 22+
- PostgreSQL 16+ and Redis 7+ (or Docker Compose)

## Local setup

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_platform
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Environment

Copy repo root `.env.example` to `.env`. Minimum for local dev:

- `DATABASE_URL` / Postgres vars
- `SECRET_KEY`, `DEBUG=True`
- `INTEGRATION_LIVE_DISPATCH=False` (keeps messaging in dry-run mode)

See [DEPLOYMENT.md](DEPLOYMENT.md) for production variables.

## Testing

All tests use **pytest** with `pytest-django`:

```bash
cd backend
python -m pytest                    # full suite
python -m pytest tests/test_platform_broadcast.py -v
python -m pytest -k "delete" -v     # filter by name
```

### Test layout

| File | Covers |
|------|--------|
| `test_auth.py` | Login, JWT |
| `test_tenant_isolation.py` | Multi-tenant queryset filtering |
| `test_plan_inheritance.py` | Plan tier feature rules |
| `test_plan_upgrade.py` | Upgrade catalog |
| `test_subscription_lifecycle.py` | Trial/grace/expiry |
| `test_maintenance_mode.py` | Maintenance middleware |
| `test_notification_delete.py` | Notification bulk/single delete |
| `test_plan_advertisements.py` | Plan upgrade ads |
| `test_platform_broadcast.py` | Broadcast CRUD, send, schedule, delete |
| `test_integration_providers.py` | Email/SMS/WhatsApp provider payloads |

### Fixtures (`tests/conftest.py`)

- `api_client`, `super_admin`, `school_admin`, `tenant`, `plan`

Add fixtures when multiple tests need the same seeded data.

## Standard change workflow

### 1. Plan the change

- Identify affected app (`platform`, `subscriptions`, `communication`, …).
- Decide: model change? new service? new API action? new page?
- Find a similar feature in [FEATURES.md](FEATURES.md).

### 2. Backend (bottom-up)

```
models.py → migration → services/*.py → serializers.py → views.py → urls.py → tests
```

**Migrations:**

```bash
python manage.py makemigrations <app_label>
python manage.py migrate
```

Never edit applied migrations in shared branches.

### 3. Frontend

```
services/moduleService.js (or new service) → page/component → App.jsx route → navigation.jsx
```

Use React Query for server state:

```javascript
const { data } = useQuery({ queryKey: ['resource'], queryFn: () => service.list() });
const mutation = useMutation({ mutationFn: service.create, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['resource'] }) });
```

Notifications: `notify.success / notify.error` from `utils/notify.jsx`.

### 4. Document

Update [FEATURES.md](FEATURES.md) and any affected doc in `docs/`.

### 5. Verify

```bash
python -m pytest tests/test_<your_feature>.py -v
# Manual smoke via http://localhost:8000/api/docs/
```

## Code conventions

### Backend

- Services raise domain exceptions (`BroadcastError`, `PlanInheritanceError`); views catch and return HTTP 400 with `message`.
- Use `@transaction.atomic` on multi-row writes (broadcast send, subscription changes).
- Custom actions on ViewSets: `@action(detail=True, methods=["post"])`.
- Permissions: `IsSuperAdmin` for platform routes; tenant routes use default + object checks.

### Frontend

- API base: `services/api.js` (axios + JWT interceptor).
- Unwrap list responses via `unwrapList` in `moduleService.js`.
- Super-admin professional pages: `PageHeader`, card grids, editor overlays (see `Broadcast.jsx`, `Advertise.jsx`).
- Styles: global tokens in `styles/global.css`; BEM-like prefixes (`broadcast-card__`, `plan-ad-`).

## Management commands

| Command | Purpose |
|---------|---------|
| `seed_platform` | Demo data, plans, broadcasts |
| `process_subscription_expiry` | Run subscription lifecycle once |
| `process_scheduled_broadcasts` | Send due broadcasts once |

## Celery (optional local)

```bash
celery -A apex_hub worker -l info
celery -A apex_hub beat -l info
```

Beat schedule defined in `apex_hub/settings.py` → `CELERY_BEAT_SCHEDULE`.

## Debugging tips

- **403 on school routes** — check plan feature flags and `FeatureGate`.
- **Empty upgrade catalog** — run migrations; verify `subscriptions` migration `0004_payment_method_fields` applied.
- **Broadcast deliveries failed** — expected until `INTEGRATION_LIVE_DISPATCH=true`; check `GET /platform/broadcasts/channel_status/`.
- **Maintenance blocks login** — super admin is exempt; see `platform/middleware.py`.

## Related docs

- [BACKEND.md](BACKEND.md)
- [FRONTEND.md](FRONTEND.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)