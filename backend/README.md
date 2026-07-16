# postgresql://neondb_owner:npg_rcMBS7PilaV8@ep-noisy-wave-aszcydt8.c-4.eu-central-1.aws.neon.tech/neondb?sslmode=require
# npx neonctl@latest init

# postgresql://neondb_owner:npg_rcMBS7PilaV8@ep-noisy-wave-aszcydt8.c-4.eu-central-1.aws.neon.tech/neondb?sslmode=require
'''
Host
ep-noisy-wave-aszcydt8.c-4.eu-central-1.aws.neon.tech
Database
neondb
Role
neondb_owner
Password
************
Pooler host
ep-noisy-wave-aszcydt8-pooler.c-4.eu-central-1.aws.neon.tech
'''

# Apex Hub Backend

Django 5 + Django REST Framework API.

## Quick start

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_platform
python manage.py runserver
```

API: `http://localhost:8000/api/v1/` · OpenAPI: `http://localhost:8000/api/docs/`

## Layout

```
apex_hub/           # Settings, root URLs, Celery
apps/
  core/             # Base models, permissions
  accounts/         # Auth, users
  tenants/          # Schools
  subscriptions/    # Plans, billing, lifecycle
  platform/         # Super-admin, broadcasts, integrations
  communication/    # Notifications, messaging logs
  …                 # School modules (students, finance, …)
tests/              # Pytest
```

## Documentation

All guides live in the repo **`docs/`** folder:

- [docs/README.md](../docs/README.md) — documentation index
- [docs/BACKEND.md](../docs/BACKEND.md) — how to extend the API
- [docs/DEVELOPMENT.md](../docs/DEVELOPMENT.md) — testing and workflow
- [docs/INTEGRATIONS.md](../docs/INTEGRATIONS.md) — messaging and payments
- [apps/platform/services/providers/README.md](apps/platform/services/providers/README.md) — provider adapters

## Tests

```bash
python -m pytest -v
```