# Apex Hub — The Easy Way

Enterprise-grade, cloud-based, multi-tenant School Management ERP SaaS.

## Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19, Bootstrap 5, React Router, Axios, React Query, Framer Motion |
| Backend | Django 5+, Django REST Framework, JWT |
| Database | PostgreSQL |
| Cache/Queue | Redis, Celery-ready |
| Deployment | Docker, Gunicorn, Nginx |

## Quick Start

```bash
# Copy environment file
cp .env.example .env

# Start all services
docker compose -f deployment/docker-compose.yml up -d --build

# Run migrations & seed data
docker compose -f deployment/docker-compose.yml exec backend python manage.py migrate
docker compose -f deployment/docker-compose.yml exec backend python manage.py seed_platform

# Access
# Frontend: http://localhost:3000
# API:      http://localhost:8000/api/v1/
# API Docs: http://localhost:8000/api/docs/
```

## Subscription payments

Checkout supports **credit/debit card** (default — card number, expiry, CVC, name on card) and **mobile money** (phone number only). Both paths record a failed transaction while sandbox gateway APIs are disconnected; see [docs/API.md](docs/API.md) for payload fields.

## Platform broadcasts (email / SMS / WhatsApp)

Super-admin broadcasts resolve school-admin audiences, log deliveries, and build provider-ready payloads for SMTP, Twilio, Meta WhatsApp, and other gateways. Outbound messages remain **failed** until `INTEGRATION_LIVE_DISPATCH=true` and provider credentials are configured at deployment. See [docs/BROADCAST_INTEGRATIONS.md](docs/BROADCAST_INTEGRATIONS.md).

## Default Credentials (after seed)

| Role | Email | Password |
|------|-------|----------|
| Super Admin | superadmin@apexhub.io | ApexHub@2026 |
| School Admin | admin@demoschool.edu | DemoSchool@2026 |

## Documentation

Full documentation index: **[docs/README.md](docs/README.md)**

| Guide | Description |
|-------|-------------|
| [Architecture](docs/ARCHITECTURE.md) | System design and data flow |
| [Development](docs/DEVELOPMENT.md) | Setup, testing, change workflow |
| [Backend](docs/BACKEND.md) | Django apps, services, API patterns |
| [Frontend](docs/FRONTEND.md) | React structure and UI conventions |
| [Features](docs/FEATURES.md) | Feature map with code locations |
| [Integrations](docs/INTEGRATIONS.md) | Email, SMS, WhatsApp, payments |
| [API](docs/API.md) | REST reference |
| [Database](docs/DATABASE.md) | Schema and migrations |
| [Deployment](docs/DEPLOYMENT.md) | Production operations |

## Project Structure

```
apex/
├── backend/          # Django REST API
├── frontend/         # React SPA
├── deployment/       # Docker, Nginx, Gunicorn
├── docs/             # Architecture, development, API, integrations
├── media/            # Uploaded files
└── static/           # Static assets
```

## Color Scheme

- Primary: Teal `#0F766E`
- Secondary: Coral `#FF7F50`
- Accent: Sand `#F5E6CA`

Schools can customize interface colors; Apex Hub admin retains default branding.

## License

Proprietary — Apex Hub © 2026