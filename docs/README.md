# Apex Hub Documentation

Central index for integrating, extending, and operating Apex Hub.

## Start here

| Document | Audience | Purpose |
|----------|----------|---------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | All developers | System layers, apps, data flow, design principles |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Contributors | Local setup, testing, change workflow, conventions |
| [BACKEND.md](BACKEND.md) | Backend devs | Django apps, services, API patterns, adding features |
| [FRONTEND.md](FRONTEND.md) | Frontend devs | React structure, routing, services, UI patterns |
| [FEATURES.md](FEATURES.md) | Product + engineering | Implemented features with code entry points |
| [INTEGRATIONS.md](INTEGRATIONS.md) | DevOps + backend | External gateways, env vars, provider extension |
| [API.md](API.md) | API consumers | REST endpoints, auth, payloads |
| [DATABASE.md](DATABASE.md) | Backend + DBAs | Schema patterns, key tables, migrations |
| [DEPLOYMENT.md](DEPLOYMENT.md) | DevOps | Docker, production env, Celery, HTTPS |

## Deep dives

| Topic | Document |
|-------|----------|
| Platform broadcasts (email / SMS / WhatsApp) | [BROADCAST_INTEGRATIONS.md](BROADCAST_INTEGRATIONS.md) |
| Email service (SMTP, school messaging, customization) | [EMAIL_SERVICE.md](EMAIL_SERVICE.md) |
| Messaging provider adapters (code-level) | [../backend/apps/platform/services/providers/README.md](../backend/apps/platform/services/providers/README.md) |

## Recommended reading order

### New to the project
1. [ARCHITECTURE.md](ARCHITECTURE.md)
2. [DEVELOPMENT.md](DEVELOPMENT.md)
3. [API.md](API.md)

### Adding a backend feature
1. [BACKEND.md](BACKEND.md) → service layer checklist
2. [DATABASE.md](DATABASE.md) → migrations
3. [DEVELOPMENT.md](DEVELOPMENT.md) → tests
4. [API.md](API.md) → document endpoints

### Adding a frontend screen
1. [FRONTEND.md](FRONTEND.md)
2. [FEATURES.md](FEATURES.md) → find similar UI to copy
3. [API.md](API.md) → wire services

### Connecting external services
1. [INTEGRATIONS.md](INTEGRATIONS.md)
2. [BROADCAST_INTEGRATIONS.md](BROADCAST_INTEGRATIONS.md) (if messaging)
3. Provider README under `backend/apps/platform/services/providers/`

## Change checklist (any feature)

Use this for every non-trivial change:

- [ ] **Model / migration** — schema change with reversible migration
- [ ] **Service layer** — business logic in `services/`, not views
- [ ] **Serializer validation** — input rules at API boundary
- [ ] **ViewSet / action** — thin HTTP layer, permissions applied
- [ ] **Frontend service** — `moduleService.js` or dedicated service module
- [ ] **UI** — page/component following existing patterns
- [ ] **Tests** — `backend/tests/test_<feature>.py` at minimum
- [ ] **Docs** — update [FEATURES.md](FEATURES.md) and relevant API/integration doc

## Project layout

```
apex/
├── backend/                 # Django 5 + DRF
│   ├── apex_hub/            # Settings, URLs, Celery
│   ├── apps/                # Domain apps (tenants, subscriptions, platform, …)
│   └── tests/               # Pytest suite
├── frontend/                # React 19 SPA
│   └── src/
│       ├── pages/           # Route-level screens
│       ├── components/      # Reusable UI
│       ├── services/        # API clients
│       ├── hooks/           # Shared React hooks
│       └── context/         # Auth, tenant, maintenance
├── docs/                    # This folder
└── deployment/              # Docker, Nginx
```

## Interactive API reference

When the backend is running: `http://localhost:8000/api/docs/` (drf-spectacular OpenAPI).