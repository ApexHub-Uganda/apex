# Apex Hub Deployment Guide

> **See also:** [Documentation index](README.md) · [Integrations](INTEGRATIONS.md) · [Broadcast integrations](BROADCAST_INTEGRATIONS.md)

## Prerequisites

- Docker & Docker Compose
- PostgreSQL 16+ (if not using Docker)
- Redis 7+ (if not using Docker)
- Node.js 22+ (for frontend development)
- Python 3.13+ (for backend development)

## Docker Deployment (Recommended)

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with production values

# 2. Build and start
docker compose -f deployment/docker-compose.yml up -d --build

# 3. Initialize database
docker compose -f deployment/docker-compose.yml exec backend python manage.py migrate
docker compose -f deployment/docker-compose.yml exec backend python manage.py seed_platform
docker compose -f deployment/docker-compose.yml exec backend python manage.py collectstatic --noinput
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| nginx | 80, 443 | Reverse proxy |
| frontend | 3000 | React SPA |
| backend | 8000 | Django API (Gunicorn) |
| db | 5432 | PostgreSQL |
| redis | 6379 | Cache & Celery broker |

## Manual Development Setup

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
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

## HTTPS Configuration

1. Obtain SSL certificates (Let's Encrypt recommended)
2. Update `deployment/nginx.conf` with SSL directives
3. Set `CORS_ALLOWED_ORIGINS` to your HTTPS domain
4. Set `DEBUG=False` in production
5. Generate a strong `SECRET_KEY`

## Environment Variables

See `.env.example` for all configuration options. Critical production settings:

- `SECRET_KEY` — Strong random key
- `DEBUG=False`
- `ALLOWED_HOSTS` — Your domain(s)
- `DATABASE_URL` — PostgreSQL connection string
- `REDIS_URL` — Redis connection string
- Payment gateway keys when ready
- `INTEGRATION_LIVE_DISPATCH` — set `True` only after email/SMS/WhatsApp provider credentials and HTTP dispatch are configured ([BROADCAST_INTEGRATIONS.md](BROADCAST_INTEGRATIONS.md))

## Celery Workers

```bash
celery -A apex_hub worker -l info
celery -A apex_hub beat -l info
```

## Health Checks

- API: `GET /api/v1/platform/health/`
- Database: Included in health endpoint
- Redis: Included in health endpoint

## Backup

```bash
docker compose exec db pg_dump -U apex_user apex_hub > backup.sql
```

## Scaling

- Increase Gunicorn workers: `--workers` in Dockerfile
- Add Celery workers for background tasks
- Use managed PostgreSQL and Redis in production
- Configure CDN for static/media files