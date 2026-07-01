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

## Default Credentials (after seed)

| Role | Email | Password |
|------|-------|----------|
| Super Admin | superadmin@apexhub.io | ApexHub@2026 |
| School Admin | admin@demoschool.edu | DemoSchool@2026 |

## Project Structure

```
apex-hub/
├── backend/          # Django REST API
├── frontend/         # React SPA
├── deployment/       # Docker, Nginx, Gunicorn
├── docs/             # API & deployment docs
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