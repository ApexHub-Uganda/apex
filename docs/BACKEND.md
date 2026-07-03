# Backend Guide

Django 5 + Django REST Framework. Entry point: `backend/apex_hub/urls.py` → `/api/v1/`.

## App map

| App | Purpose |
|-----|---------|
| `core` | Base models, permissions, pagination, exceptions, seed commands |
| `accounts` | User model, JWT auth, login history |
| `tenants` | Schools, onboarding, suspension, branding |
| `subscriptions` | Plans, features, subscriptions, payments, upgrades, lifecycle |
| `platform` | Super-admin: settings, broadcasts, ads, maintenance, integrations |
| `communication` | Tenant announcements, notifications, SMS/email message logs |
| `audit` | Audit log export and listing |
| `academics`, `students`, `staff`, … | School operational modules |

## Request flow

```
HTTP Request
  → Middleware (CORS, maintenance, tenant context)
  → URL router (app urls.py)
  → ViewSet / APIView
  → Permission classes
  → Serializer (validate)
  → Service layer (business logic)
  → ORM / external integration
  → Response
```

## Models

### Tenant-scoped (`BaseModel`)

```python
# apps/core/models.py
class BaseModel(models.Model):
    id = UUIDField
    tenant = ForeignKey("tenants.Tenant", null=True)
    created_at, updated_at
    created_by, updated_by
    is_deleted  # soft delete
    objects = TenantAwareManager()
```

### Platform-scoped (`PlatformModel`)

No `tenant` FK. Used for cross-tenant platform configuration and broadcasts.

## Adding a new API resource

### 1. Model + migration

```bash
python manage.py makemigrations myapp
python manage.py migrate
```

### 2. Service module

Create `apps/myapp/services/my_feature.py`:

```python
class MyFeatureError(Exception):
    pass

def do_something(obj, *, actor) -> dict:
    # validate, mutate, return result dict
    ...
```

### 3. Serializer

`apps/myapp/serializers.py` — validation rules, read-only computed fields.

### 4. ViewSet

```python
class MyFeatureViewSet(viewsets.ModelViewSet):
    queryset = MyModel.objects.all()
    serializer_class = MyFeatureSerializer
    permission_classes = [IsSuperAdmin]  # or tenant permission

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def custom_action(self, request, pk=None):
        obj = self.get_object()
        result = my_service.do_something(obj, actor=request.user)
        return Response({"success": True, "data": result})
```

### 5. Register URL

`apps/myapp/urls.py` + include in `apex_hub/urls.py`.

### 6. Tests

`backend/tests/test_my_feature.py` — API + service unit tests.

## Platform app structure (reference)

Recent super-admin features follow this layout:

```
apps/platform/
├── models.py              # PlatformBroadcast, PlanAdvertisement, settings models
├── serializers.py
├── views.py               # ViewSets + custom actions
├── views_integrations.py  # Integration test endpoint
├── urls.py
├── middleware.py          # Maintenance mode
├── tasks.py               # Celery tasks
├── management/commands/   # One-off schedulers
└── services/
    ├── broadcasts.py      # Audience, send, schedule, delete
    ├── plan_advertisements.py
    ├── maintenance.py
    ├── integrations.py  # EmailService, SMSService, WhatsAppService
    └── providers/       # Provider adapters (see providers/README.md)
```

### Broadcast service pattern (template)

| Function | Role |
|----------|------|
| `preview_audience()` | Read-only stats |
| `send_platform_broadcast()` | Mutate + side effects |
| `schedule_platform_broadcast()` | State transition |
| `delete_platform_broadcast()` | Hard delete + cascade |
| `process_scheduled_broadcasts()` | Cron entry point |

ViewSet exposes these as `@action` methods; **never** set `status=sent` only in serializer — use `send` action.

## Subscriptions app structure

| Module | Role |
|--------|------|
| `plan_tiers.py` | Tier order, inheritance validation, comparison copy |
| `services.py` | Feature flags, plan assignment |
| `upgrade_services.py` | School-admin upgrade catalog |
| `subscription_lifecycle.py` | Calendar expiry processing |
| `tasks.py` | Celery wrapper |

## Permissions

```python
# apps/core/permissions.py
IsSuperAdmin      # role == super_admin
IsSchoolAdmin     # school admin roles
# Tenant object permissions on view get_queryset()
```

## Integrations entry points

| Service | File | Config model |
|---------|------|--------------|
| Email | `integrations.EmailService` | `EmailSetting` |
| SMS | `integrations.SMSService` | `SMSSetting` |
| WhatsApp | `integrations.WhatsAppService` | `WhatsAppSetting` |
| Payments | `integrations.PaymentService` | `PaymentProvider` |

Provider selection: `services/providers/registry.py`.

## Settings reference

`apex_hub/settings.py`:

- `INTEGRATION_LIVE_DISPATCH` — messaging HTTP gate
- `CELERY_BEAT_SCHEDULE` — periodic tasks
- `MAINTENANCE_MODE` — env default; runtime override via DB `GlobalSetting`

## Related docs

- [DATABASE.md](DATABASE.md)
- [INTEGRATIONS.md](INTEGRATIONS.md)
- [DEVELOPMENT.md](DEVELOPMENT.md)
- [FEATURES.md](FEATURES.md)