# Feature Reference

Implemented features with code entry points. Use this when extending or debugging.

## Platform — Super Admin

### Platform broadcasts (email / SMS / WhatsApp)

Database-driven multi-channel announcements to school admins.

| Area | Path |
|------|------|
| Models | `backend/apps/platform/models.py` → `PlatformBroadcast`, `PlatformBroadcastDelivery` |
| Service | `backend/apps/platform/services/broadcasts.py` |
| API | `PlatformBroadcastViewSet` in `views.py` |
| Providers | `backend/apps/platform/services/providers/` |
| UI | `frontend/src/pages/super-admin/Broadcast.jsx` |
| API client | `broadcastService` in `moduleService.js` |
| Tests | `backend/tests/test_platform_broadcast.py`, `test_integration_providers.py` |
| Docs | [BROADCAST_INTEGRATIONS.md](BROADCAST_INTEGRATIONS.md) |

**Actions:** preview, send, schedule, cancel, duplicate, delete, deliveries, channel_status.

**Statuses:** `draft` → `scheduled` → `sent` | `cancelled` | `expired`.

### Plan editor workspace

Full-page plan + feature assignment (replaces modal).

| Area | Path |
|------|------|
| Routes | `/super-admin/plans/new`, `/super-admin/plans/:planId/edit` |
| UI | `PlanEditor.jsx`, `components/PlanEditorWorkspace.jsx`, `hooks/usePlanEditor.js` |
| Inheritance | `backend/apps/subscriptions/plan_tiers.py` |
| Tests | `backend/tests/test_plan_inheritance.py` |

### Plan upgrade advertisements

Targeted upgrade promos in school notification feeds.

| Area | Path |
|------|------|
| Model | `PlanAdvertisement` |
| Service | `backend/apps/platform/services/plan_advertisements.py` |
| UI | `frontend/src/pages/super-admin/Advertise.jsx` |
| Tests | `backend/tests/test_plan_advertisements.py` |

### Maintenance mode

| Area | Path |
|------|------|
| Service | `backend/apps/platform/services/maintenance.py` |
| Middleware | `backend/apps/platform/middleware.py` |
| Frontend | `MaintenanceContext.jsx`, `MaintenanceBanner.jsx`, `pages/shared/Maintenance.jsx` |
| Tests | `backend/tests/test_maintenance_mode.py` |

Super admin bypasses blocking; banner shows for operators.

### Platform notifications (registration todos)

| Area | Path |
|------|------|
| Model | `PlatformNotification`, `PlatformNotificationReceipt` |
| UI | `frontend/src/pages/super-admin/NotificationsTodos.jsx` |
| Service | `backend/apps/platform/services/notification_feed.py` |

## Subscriptions

### Plan feature inheritance

Higher tiers must include all lower-tier features.

| Area | Path |
|------|------|
| Logic | `backend/apps/subscriptions/plan_tiers.py` |
| Assignment | `assign_plan_features` in `services.py` |
| Upgrade catalog | `upgrade_services.py` |
| School UI copy | “Everything in Basic, plus…” in plan/upgrade pages |
| Tests | `test_plan_inheritance.py`, `test_plan_upgrade.py` |

### Subscription lifecycle (auto-expiry)

Calendar-based trial → grace → expired.

| Area | Path |
|------|------|
| Logic | `backend/apps/subscriptions/subscription_lifecycle.py` |
| Celery | `subscriptions/tasks.py` |
| Command | `management/commands/process_subscription_expiry.py` |
| Tests | `backend/tests/test_subscription_lifecycle.py` |

### Plan upgrade (school admin)

| Area | Path |
|------|------|
| UI | `frontend/src/pages/school-admin/PlanUpgrade.jsx` |
| API | `/subscriptions/upgrade/catalog/`, `/upgrade/checkout/` |
| Tests | `test_plan_upgrade.py` |

## Communication & notifications

### Notification delete (school + super admin)

Per-item and bulk delete with database-backed state.

| Area | Path |
|------|------|
| School API | `communication` notification ViewSet actions |
| Platform API | `PlatformNotificationViewSet` → `delete_notification`, `delete_all` |
| Feed API | `auth/notifications/feed/` delete actions |
| Tests | `backend/tests/test_notification_delete.py` |

### In-app notification feed

Synthetic items (plan ads) + real notifications; dismiss/delete per user.

| Area | Path |
|------|------|
| UI | `frontend/src/pages/shared/Notifications.jsx` |
| Service | `notificationFeedService` in `moduleService.js` |

## Integrations (stubs → deployment)

| Channel | Status | Doc |
|---------|--------|-----|
| Email (SMTP, SendGrid, Mailgun) | Payload ready; SMTP live when `INTEGRATION_LIVE_DISPATCH=true` | [INTEGRATIONS.md](INTEGRATIONS.md) |
| SMS (Twilio, AT, Nexmo) | Payload ready; HTTP stub | same |
| WhatsApp (Meta, Twilio, AT) | Payload ready; HTTP stub | [BROADCAST_INTEGRATIONS.md](BROADCAST_INTEGRATIONS.md) |
| Card / mobile money payments | Records failed txn; 402 response | [API.md](API.md) |

## Tenant administration

| Feature | Tests |
|---------|-------|
| Suspension / unsuspend | `test_tenant_suspension.py` |
| Isolation | `test_tenant_isolation.py` |
| School admin CRUD | `test_tenant_admin.py` |

## Extending a feature

1. Locate the row in this table.
2. Read the service module first (business rules).
3. Follow checklists in [DEVELOPMENT.md](DEVELOPMENT.md) and [BACKEND.md](BACKEND.md) / [FRONTEND.md](FRONTEND.md).
4. Add a row to this file when the feature is done.