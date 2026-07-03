# Role Permissions & Plan Inheritance

School portal access is computed as:

```
Effective access = Subscription plan modules ∩ School admin role permissions ∩ User role
```

## Roles

All school portal users operate under `/school-admin` with privileges **capped at school admin**. No role can access modules or features outside the school's paid plan.

| Role | Slug |
|------|------|
| School Admin | `school_admin` |
| Head Teacher | `head_teacher` |
| Deputy Head Teacher | `deputy_head_teacher` |
| Director of Studies | `director_of_studies` |
| Head of Department | `head_of_department` |
| Teacher | `teacher` |
| Parent | `parent` |
| Bursar / Accountant | `bursar` |
| Librarian | `librarian` |
| HR Manager | `hr_manager` |
| Transport Manager | `transport_manager` |
| Hostel Manager | `hostel_manager` |
| Inventory Manager | `inventory_manager` |

Legacy slugs (`finance_officer`, `hostel_warden`, etc.) are normalized automatically.

## Permission Settings

School admins configure per-role **read/write** access per module at:

- UI: `/school-admin/settings/permissions`
- API: `GET/PUT/POST /api/v1/tenants/role-permissions/`

School admins always receive full read/write on all plan-enabled modules (computed, not stored).

## API Context

`GET /api/v1/tenants/context/` returns role-filtered payload:

- `module_menu` — plan modules the user may read
- `module_permissions` — `{ module_key: { can_read, can_write } }`
- `permissions` — flat tokens e.g. `finance.read`
- `role_profile` — dashboard title, subtitle, quick actions
- `dashboard_widgets` — plan widgets filtered by role

## Frontend Gates

- **FeatureGate** — plan feature + role module read permission
- **PermissionGate** — role module write permission for mutations

## Database

`SchoolRoleModulePermission` stores tenant overrides:

- `tenant`, `role`, `module_key`, `can_read`, `can_write`

Defaults live in `backend/apps/tenants/role_permissions.py` until customized.