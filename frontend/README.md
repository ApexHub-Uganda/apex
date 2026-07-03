# Apex Hub Frontend

React 19 SPA (Vite).

## Quick start

```bash
npm install
npm run dev
```

App: `http://localhost:3000`

Set `VITE_API_BASE_URL` in `.env` (see `.env.example`).

## Layout

```
src/
  pages/          # Route screens (super-admin, school-admin, auth)
  components/     # Shared UI
  services/       # API clients (api.js, moduleService.js)
  hooks/          # Reusable hooks
  context/        # Auth, tenant, maintenance
  config/         # Navigation, feature routes
  styles/         # global.css
```

## Documentation

- [docs/FRONTEND.md](../docs/FRONTEND.md) — routing, services, UI patterns
- [docs/FEATURES.md](../docs/FEATURES.md) — feature entry points
- [docs/DEVELOPMENT.md](../docs/DEVELOPMENT.md) — change workflow
- [docs/README.md](../docs/README.md) — full index