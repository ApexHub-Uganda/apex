# Frontend Guide

React 19 SPA built with Vite. Source: `frontend/src/`.

## Structure

```
src/
├── App.jsx                 # Routes, providers, QueryClient
├── layouts/                # AuthLayout, SuperAdminLayout, SchoolAdminLayout
├── pages/
│   ├── auth/               # Login, register, password reset
│   ├── super-admin/        # Platform operator screens
│   ├── school-admin/       # School modules
│   └── shared/             # Profile, notifications, maintenance
├── components/             # Reusable UI (PageHeader, StatusBadge, FeatureGate, …)
├── hooks/                  # usePlanEditor, etc.
├── services/
│   ├── api.js              # Axios instance + JWT
│   └── moduleService.js    # CRUD + domain API helpers
├── context/                # AuthContext, TenantContext, MaintenanceContext
├── config/                 # navigation, featureRoutes, schoolModules
└── styles/global.css       # Design tokens + component styles
```

## Routing

Defined in `App.jsx`:

| Prefix | Layout | Guard |
|--------|--------|-------|
| `/login`, `/register` | `AuthLayout` | Public |
| `/super-admin/*` | `SuperAdminLayout` | `roles={['super_admin']}` |
| `/school-admin/*` | `SchoolAdminLayout` | `roles={['school_admin']}` + `FeatureGate` |

Navigation sidebar: `config/navigation.jsx`.

## API layer

### Axios (`services/api.js`)

- Base URL from `VITE_API_BASE_URL`
- Attaches `Authorization: Bearer <access>` from storage
- Handles 401 refresh or logout

### Service modules (`services/moduleService.js`)

Pattern for CRUD:

```javascript
export const myService = {
  list: (params) => api.get('/path/', { params }).then((r) => unwrapList(r)),
  get: (id) => api.get(`/path/${id}/`).then((r) => unwrapData(r)),
  create: (payload) => api.post('/path/', payload).then((r) => unwrapData(r)),
  update: (id, payload) => api.patch(`/path/${id}/`, payload).then((r) => unwrapData(r)),
  delete: (id) => api.delete(`/path/${id}/`).then((r) => unwrapData(r)),
  customAction: (id) => api.post(`/path/${id}/action/`).then((r) => unwrapData(r)),
};
```

**Always** use `unwrapList` / `unwrapData` — API responses may wrap payload in `{ data: … }`.

## Server state (React Query)

```javascript
const { data, isLoading } = useQuery({
  queryKey: ['broadcasts'],
  queryFn: () => broadcastService.list({ page_size: 50 }),
});

const mutation = useMutation({
  mutationFn: (id) => broadcastService.send(id),
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ['broadcasts'] }),
});
```

Query keys should be stable and invalidated after mutations affecting that list.

## UI patterns

### Generic module CRUD

`components/ModulePage.jsx` — table + modal form. Used for simpler admin lists.

### Professional workspace (preferred for workflows)

Used by **Broadcast**, **Advertise**, **Plan Editor**:

| Element | Implementation |
|---------|----------------|
| Page header | `PageHeader` + primary action button |
| List | Card grid with status badges + toolbar |
| Editor | Full-screen overlay (`plan-ad-editor-overlay`) |
| Confirmations | `alert.confirm` from `utils/notify.jsx` |
| Toasts | `notify.success / error / warning` |

Copy structure from `pages/super-admin/Broadcast.jsx` when adding multi-step operator tools.

### Plan editor

- Routes: `/super-admin/plans/new`, `/super-admin/plans/:planId/edit`
- `PlanEditor.jsx` + `PlanEditorWorkspace.jsx` + `hooks/usePlanEditor.js`
- Inherited features shown greyed/disabled per `plan_tiers` API rules

### Feature gating (school portal)

```jsx
<FeatureGate featureKey="library">
  <Library />
</FeatureGate>
```

Feature keys map in `config/featureRoutes.js` → plan feature slugs from backend.

## Maintenance mode

- `MaintenanceContext` polls platform maintenance state
- `MaintenanceBanner` for super admin
- Non–super-admins redirected to `/maintenance` when active
- Login shows formatted maintenance error

Files: `context/MaintenanceContext.jsx`, `components/MaintenanceBanner.jsx`, `pages/shared/Maintenance.jsx`.

## Styling

- Bootstrap 5 utilities + custom CSS variables in `global.css`
- Prefix component-specific rules (`broadcast-`, `plan-ad-`, `apex-card`)
- Framer Motion for card/overlay entrance animations

## Adding a new super-admin page

1. Create `pages/super-admin/MyPage.jsx`
2. Add service methods to `moduleService.js`
3. Register route in `App.jsx` under `/super-admin`
4. Add nav item in `config/navigation.jsx`
5. Add styles to `global.css` if new component family

## Adding a new school-admin module page

1. Add feature slug to backend plan catalog if gated
2. Add route feature mapping in `config/featureRoutes.js`
3. Create page under `pages/school-admin/`
4. Register in `App.jsx` with `<Gated featureKey={…}>`
5. Add to `config/schoolModules.js` and navigation

## Related docs

- [API.md](API.md)
- [FEATURES.md](FEATURES.md)
- [DEVELOPMENT.md](DEVELOPMENT.md)