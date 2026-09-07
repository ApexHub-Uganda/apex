# Comprehensive Technical Discovery Report: Apex Hub

**Target System:** Apex Hub — Multi-Tenant School Management ERP SaaS  
**Project Workspace:** `h:\apex`  
**Discovery Mode:** Strictly Read-Only (Zero modifications, additions, or environment mutations)  
**Discovery Lead:** Senior Software Architect, Full-Stack Engineer, Security Reviewer, Database Architect & DevOps Engineer  

---

## 1. Executive Summary

### What Apex Hub Is
**Apex Hub** is an enterprise-grade, cloud-based, multi-tenant Software-as-a-Service (SaaS) School Management Enterprise Resource Planning (ERP) platform. It is engineered primarily for primary, secondary, and tertiary educational institutions in East Africa (with standard localization and currency in Uganda Shillings, `UGX`, supporting UNEB, Uganda Competence-Based Education, CBC, 8-4-4, and IGCSE curricula).

The platform serves two distinct user tiers:
1. **Platform Operators (Super Admins):** Manage school tenants, configure subscription tiers, publish system-wide announcements/advertisements, monitor system health, audit operator logs, and supervise billing and onboarding queues.
2. **School Community (Tenants):** School administrators, head teachers, directors of studies, class teachers, subject teachers, bursars, librarians, hostel wardens, transport managers, HR managers, and parents operating their respective institutional workflows.

### What the System Currently Does
The platform provides a functional multi-tenant core where multiple schools share a single PostgreSQL database with logical tenant data isolation, enforced both at the ORM layer (`TenantAwareManager`) and at the view/API layer (`TenantFilterMixin`). 

The system implements:
- **Authentication & Dual-Role Switching:** JWT-based stateless authentication supporting multiple active personas (e.g. a staff member who is also a parent).
- **Three-Tier Subscription Feature Gating:** Plan tiers (`free_trial` $\rightarrow$ `basic` $\rightarrow$ `premium` $\rightarrow$ `premium_plus`) where higher tiers inherit capabilities from lower tiers. Routes and actions are guarded by backend permissions and frontend `<FeatureGate>` and `<PermissionGate>` wrappers.
- **Academic & Operational Engine:** Timetabling with automated schedule generation drafts, continuous assessment schemes (BOT/MOT/EOT), exam marks lifecycle (draft $\rightarrow$ submit $\rightarrow$ approve $\rightarrow$ lock/reopen), report cards with ranking and division calculation, student promotion wizards, and bell schedule period grids.
- **Financial Accounting:** Dual-entry journal engine, student billing, termly fee structures, automated fee balances, payment recording, fee waivers/discounts, refunds, and fee-clearance thresholds governing parental access to student report cards.
- **Biometric & Geo-Fencing Attendance:** Campus perimeter polygons (`SchoolGeofence`) with WGS84 coordinates and WebAuthn (FIDO2/passkeys) hardware verification for staff check-in/out.
- **Communications & Broadcasts:** Multi-channel broadcasts (Email, SMS, WhatsApp, In-App) with audience resolution, delivery logging, and provider adapters.

### Overall Architecture
Apex Hub is structured as a decoupled Single Page Application (SPA) communicating over RESTful JSON APIs with a Django backend:
- **Client Tier:** React 19 SPA built with Vite 6, styled using Vanilla CSS custom properties alongside Bootstrap 5.3, with client-side state managed via TanStack React Query 5.
- **Application Tier:** Django 5.1+ running Django REST Framework (DRF), SimpleJWT with token blacklisting, Celery for periodic and asynchronous background jobs, and Redis as cache and message broker.
- **Persistence Tier:** PostgreSQL 16 (relational database with UUID primary keys, foreign key constraints, composite indexing, and soft deletion flags).
- **Edge / Ingress Tier:** Docker Compose with Nginx reverse proxy serving static and media assets and routing `/api/` traffic to Gunicorn application workers.

```
                                  [ Browser / Client ]
                                           │
                                    (HTTPS / WSS)
                                           ▼
                                 [ Nginx Reverse Proxy ]
                                    (Port 80 / 443)
                         ┌─────────────────┴─────────────────┐
                         ▼                                   ▼
             [ Frontend Static SPA ]                [ Backend API ]
             (Nginx / Vite Dev :3000)             (Gunicorn / Django :8000)
                                                             │
                         ┌───────────────────────────────────┼───────────────────────────────────┐
                         ▼                                   ▼                                   ▼
                 [ PostgreSQL 16 ]                    [ Redis 7.0 ]                       [ Celery Beat ]
              (Tenant Scoped Data)                 (Cache & Token Broker)               (Hourly Jobs / Expiry)
                         │
                         ▼
             [ External Providers ]
          (SMTP, Twilio, Meta WhatsApp,
           Africa's Talking, Gateways)
```

### Current Level of Completeness
- **Core Multi-Tenant Backend:** **High / Complete**. Models, managers, context middleware, DRF viewsets, serializers, and permission classes are thoroughly built out across 22 Django apps.
- **Frontend Portal Experience:** **High / Complete**. 50+ dedicated pages for super-admin and school-admin portals, specialized workspaces (Bursar, Teacher, HoD, DoS, Staff, Plan Editor, Broadcast), full-screen overlays, and interactive modals.
- **Test Suite:** **Extensive**. 65 test modules in `backend/tests/` verifying tenant isolation, role matrix permissions, billing engines, timetables, and integrations.
- **External Third-Party Gateways (Payment & SMS/WhatsApp):** **Simulated / Adapter-Ready**. The domain service layer builds complete, spec-compliant payloads for Stripe, PayPal, M-Pesa, MTN MoMo, Twilio, and Meta WhatsApp. Live external HTTP dispatches are conditionally gated behind `INTEGRATION_LIVE_DISPATCH=False` until production API keys and webhooks are plugged in.

### Critical Takeaways for Future Developers
1. **Never Bypass the Service Layer:** ViewSets are thin controllers. Business logic (subscription lifecycle, broadcast audience resolution, timetable generation, fee invoice calculation) lives strictly in `apps/<domain>/services/`.
2. **Tenant Scoping is Dual-Layered:** Tenant isolation is enforced by `TenantAwareManager` (which inspects thread-local `TenantContext`) and `TenantFilterMixin` on DRF viewsets. Bypassing these by querying `Model.all_objects` without a `tenant` filter risks data leakage between schools.
3. **Plan Inheritance is Mandatory:** Higher plan tiers must inherit lower-tier features (`apps.subscriptions.plan_tiers`). When adding new features, assign them to the appropriate tier and verify that inheritance cascades cleanly.
4. **Offline / Sandbox Gateway Design:** Payments and broadcasts will record failed delivery rows unless `INTEGRATION_LIVE_DISPATCH` is enabled and valid provider credentials are configured.

---

## 2. Verified Technology Stack

| Layer | Technology | Version | Evidence | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Frontend Framework** | React | `^19.0.0` | [`frontend/package.json:20`](file:///h:/apex/frontend/package.json#L20) | React 19 SPA |
| **Frontend Routing** | React Router DOM | `^7.1.1` | [`frontend/package.json:28`](file:///h:/apex/frontend/package.json#L28) | Declarative layout routing in `App.jsx` |
| **Frontend Server State**| TanStack React Query | `^5.62.8` | [`frontend/package.json:13`](file:///h:/apex/frontend/package.json#L13) | Query caching, optimistic invalidation |
| **Frontend UI / CSS** | Bootstrap & React-Bootstrap | `5.3.3` / `2.10.7` | [`frontend/package.json:16,21`](file:///h:/apex/frontend/package.json#L16) | Paired with 5,800+ lines in `global.css` |
| **Frontend Animation** | Framer Motion | `^11.15.0` | [`frontend/package.json:18`](file:///h:/apex/frontend/package.json#L18) | Used for overlay entrances and card transitions |
| **Frontend Build Tool** | Vite | `^6.0.6` | [`frontend/package.json:39`](file:///h:/apex/frontend/package.json#L39) | Configured in `vite.config.js` with dev proxy |
| **Backend Framework** | Django | `5.1.x` (`>=5.1,<6.0`) | [`backend/requirements.txt:1`](file:///h:/apex/backend/requirements.txt#L1) | Python 3.13 runtime base |
| **API Framework** | Django REST Framework | `3.15.x` (`>=3.15,<4.0`) | [`backend/requirements.txt:2`](file:///h:/apex/backend/requirements.txt#L2) | REST API under `/api/v1/` |
| **API Documentation** | drf-spectacular | `0.28.x` (`>=0.28`) | [`backend/requirements.txt:12`](file:///h:/apex/backend/requirements.txt#L12) | OpenAPI 3.0 schema at `/api/docs/` |
| **Authentication** | DRF SimpleJWT | `5.3.x` (`>=5.3,<6.0`) | [`backend/requirements.txt:3`](file:///h:/apex/backend/requirements.txt#L3) | Bearer tokens with token blacklisting |
| **Biometrics / Passkeys**| PyWebAuthn | `2.2.x` (`>=2.2,<3`) | [`backend/requirements.txt:19`](file:///h:/apex/backend/requirements.txt#L19) | FIDO2 passkey verification for staff check-in |
| **Database Engine** | PostgreSQL | `16-alpine` | [`deployment/docker-compose.yml:3`](file:///h:/apex/deployment/docker-compose.yml#L3) | SQLite used for pytest test execution |
| **Cache & Broker** | Redis | `7-alpine` | [`deployment/docker-compose.yml:21`](file:///h:/apex/deployment/docker-compose.yml#L21) | Redis Cache + Celery Broker |
| **Task Queue** | Celery | `5.4.x` (`>=5.4`) | [`backend/requirements.txt:11`](file:///h:/apex/backend/requirements.txt#L11) | Periodic hourly tasks configured |
| **Static File Serving** | WhiteNoise | `6.8.x` (`>=6.8`) | [`backend/requirements.txt:18`](file:///h:/apex/backend/requirements.txt#L18) | Manifest compressed storage |
| **WSGI Server** | Gunicorn | `23.0.x` (`>=23.0`) | [`backend/requirements.txt:9`](file:///h:/apex/backend/requirements.txt#L9) | Production WSGI application server |
| **Reverse Proxy** | Nginx | `alpine` | [`deployment/docker-compose.yml:75`](file:///h:/apex/deployment/docker-compose.yml#L75) | Unified reverse proxy routing |
| **Dev Tunnels** | Ngrok | Unknown | [`.env.example:28`](file:///h:/apex/.env.example#L28) | Configured for remote demo tunnels |

---

## 3. Project Structure Map

```
apex/
├── .env.example                     # Environment template (PostgreSQL, Redis, JWT, Ngrok, SMTP)
├── README.md                        # Project identity, quick-start, architecture index
├── backend/                         # Django REST API service
│   ├── apex_hub/                    # Project root package (settings.py, urls.py, wsgi.py, celery.py)
│   ├── apps/                        # Domain applications (22 modular apps)
│   │   ├── academics/               # Classes, streams, subjects, timetables, promotions, schemes
│   │   ├── accounts/                # Custom User, dual-role assignments, sessions, devices, WebAuthn
│   │   ├── admissions/              # Vacancies, applications, enrollment pipeline
│   │   ├── analytics/               # Computed dashboard snapshots
│   │   ├── attendance/              # Student/staff attendance, geofences, lesson attendance
│   │   ├── audit/                   # Platform and school immutable audit logging
│   │   ├── communication/           # Announcements, notifications, SMS/Email logs, tickets
│   │   ├── core/                    # BaseModel, TenantAwareManager, permissions, mixins, PDF engine
│   │   ├── events/                  # School calendar events and registrations
│   │   ├── examinations/            # Grading schemes, exam sessions, marks approval, report cards
│   │   ├── finance/                 # Fee structures, student balances, payments, double-entry journals
│   │   ├── hostel/                  # Hostels, rooms, student bed allocations
│   │   ├── hr/                      # Staff leave management, performance appraisals
│   │   ├── inventory/               # Stock items, movements, procurement orders
│   │   ├── library/                 # Books catalog, borrow/return records, overdue fines
│   │   ├── payroll/                 # Salary structures, payroll runs, payslips
│   │   ├── platform/                # Super-admin portal: broadcasts, ads, settings, providers
│   │   ├── staff/                   # Staff profiles, teachers, direct reports
│   │   ├── students/                # Students, parents, guardians, medical records
│   │   ├── subscriptions/           # Plans, features, subscription lifecycles, upgrades
│   │   ├── tenants/                 # Schools, campuses, role module permissions, onboarding
│   │   └── transport/               # Vehicles, drivers, routes, student transport
│   ├── manage.py                    # Django management CLI
│   ├── requirements.txt             # Pinned Python package dependencies
│   └── tests/                       # 65 automated pytest suites
├── frontend/                        # React 19 SPA client
│   ├── package.json                 # Node package configuration
│   ├── vite.config.js               # Vite build config with dev proxy and code splitting
│   ├── src/
│   │   ├── App.jsx                  # Main route tree, providers, query client
│   │   ├── components/              # Reusable UI: FeatureGate, StatusBadge, ApexLoader, PageHeader
│   │   ├── config/                  # navigation.jsx, featureRoutes.js, schoolModules.js, schoolRoles.js
│   │   ├── context/                 # AuthContext, TenantContext, MaintenanceContext, ThemeContext
│   │   ├── layouts/                 # AuthLayout, SuperAdminLayout, SchoolAdminLayout, OnboardingLayout
│   │   ├── pages/                   # Application pages (auth, super-admin, school-admin, shared)
│   │   ├── services/                # Axios API client, authService, moduleService, tenantService
│   │   ├── styles/global.css        # Comprehensive design system (5,800+ lines)
│   │   └── utils/                   # notify.jsx, formatting helpers, maintenance prompts
│   └── nginx-spa.conf               # Nginx configuration for containerized SPA
├── deployment/                      # Production orchestration
│   ├── docker-compose.yml           # Multi-service stack (db, redis, backend, frontend, nginx)
│   ├── Dockerfile.backend           # Python 3.13 slim container definition
│   ├── Dockerfile.frontend          # Multi-stage Node 22 build -> Nginx alpine
│   └── nginx.conf                   # Main reverse proxy configuration
└── docs/                            # Comprehensive engineering guides (14 markdown documents)
```

---

## 4. Architecture Overview

### Plain Language Description
Apex Hub operates as a cloud-native, multi-tenant platform where hundreds of schools share a single software instance while remaining strictly isolated from each other. 

```
[ School Admin / Teacher / Parent ]                 [ Platform Super Admin ]
                 │                                              │
                 ▼                                              ▼
        [ React Frontend ]                             [ React Frontend ]
     (/school-admin/* routes)                       (/super-admin/* routes)
                 │                                              │
                 └───────────────────────┬──────────────────────┘
                                         ▼
                            [ HTTPS / JWT Bearer Token ]
                                         │
                                         ▼
                         [ Django REST API Gateway ]
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   ▼                                           ▼
       [ Tenant Middleware ]                       [ Super Admin Bypass ]
 (Resolves school from User FK)              (Full access to /api/v1/platform/)
                   │                                           │
                   ▼                                           ▼
      [ Feature & Role Gates ]                         [ Domain Services ]
(Checks Plan Tier & Role Permissions)         (Audience Preview, Plan Inheritance)
                   │                                           │
                   └─────────────────────┬─────────────────────┘
                                         ▼
                         [ Domain Services Layer ]
                   (Billing, Academics, Exam Lifecycles)
                                         │
                                         ▼
                     [ ORM / TenantAwareManager ]
                     (Auto-filters WHERE tenant_id = ...)
                                         │
                                         ▼
                             [ PostgreSQL Database ]
```

1. **Request Ingestion:** The browser sends requests with an `Authorization: Bearer <access_token>` header. If the user belongs to a school, the request also passes `X-Tenant-ID`.
2. **Context Resolution:** The backend middleware reads the authenticated user record. If the user is a school member, their school (`Tenant`) is locked into a thread-local execution context (`TenantContext`).
3. **Authorization & Feature Gating:** Before executing business logic, the view checks two gates:
   - Does the school's active subscription plan include this module?
   - Does the user's role (e.g. Bursar vs. Teacher) have permission for this action?
4. **Data Isolation:** All database queries executed through `Model.objects` automatically apply a filter for the active school (`WHERE tenant_id = '...'`). Only Super Admins bypass this filter.
5. **Mutation & Audit:** When data is created or updated, audit fields (`created_by`, `updated_by`, `created_at`, `updated_at`) are automatically stamped, and sensitive mutations are recorded in the immutable audit log table.

---

## 5. Backend Architecture

### Django Structure & Settings
- **Configuration Root:** Located in [`backend/apex_hub/settings.py`](file:///h:/apex/backend/apex_hub/settings.py). Environment variables are parsed via `django-environ` from the root `.env`.
- **Installed Apps:** 22 local apps prefixed with `apps.`, alongside DRF, SimpleJWT, CORS headers, Django Filters, and WhiteNoise.
- **Middleware Pipeline (in order of execution):**
  1. `SecurityMiddleware`
  2. `WhiteNoiseMiddleware` (static assets)
  3. `CorsMiddleware` (CORS headers & Ngrok tunnel support)
  4. `SessionMiddleware`
  5. `CommonMiddleware`
  6. `CsrfViewMiddleware`
  7. `AuthenticationMiddleware`
  8. `TenantMiddleware` ([`backend/apps/tenants/middleware.py`](file:///h:/apex/backend/apps/tenants/middleware.py))
  9. `AuditMiddleware` ([`backend/apps/audit/middleware.py`](file:///h:/apex/backend/apps/audit/middleware.py))
  10. `MessageMiddleware`
  11. `XFrameOptionsMiddleware`
  12. `JWTAuthenticationMiddleware` ([`backend/apps/platform/middleware.py`](file:///h:/apex/backend/apps/platform/middleware.py))
  13. `MaintenanceModeMiddleware` ([`backend/apps/platform/middleware.py`](file:///h:/apex/backend/apps/platform/middleware.py))

### Model Scoping Patterns
The data layer enforces a strict dichotomy:
- **`apps.core.models.BaseModel`:** Abstract base model for all tenant-scoped entities. Includes a UUID primary key, `tenant` foreign key, audit stamps (`created_by`, `updated_by`), soft-delete flag (`is_deleted`), and uses `TenantAwareManager`.
- **`apps.core.models.PlatformModel`:** Abstract base model for cross-tenant, super-admin data (e.g. `Plan`, `FeatureFlag`, `PlatformBroadcast`, `GlobalSetting`). Omits the `tenant` field.

### Views, Serializers, and the Service Layer
- **Views:** Inherit from `BaseModelViewSet` ([`apps/core/views.py`](file:///h:/apex/backend/apps/core/views.py)), which integrates `TenantFilterMixin`, `AuditFieldsMixin`, and `SoftDeleteMixin`.
- **Serializers:** Validate boundary schemas. Email fields use `DeliverableEmailField` which verifies MX records and syntax.
- **Service Modules:** All complex business operations reside in dedicated service files:
  - `apps/subscriptions/services.py`: Feature flag resolution and plan assignment.
  - `apps/subscriptions/subscription_lifecycle.py`: Automated expiry, trial transitions, and grace periods.
  - `apps/platform/services/broadcasts.py`: Multi-channel audience resolution and delivery.
  - `apps/finance/services/billing.py`: Termly fee invoice generation and balance calculations.
  - `apps/academics/services/`: Timetable generation, promotion pipelines, and grade aggregations.

---

## 6. Frontend Architecture

### Routing and Layouts
Configured in [`frontend/src/App.jsx`](file:///h:/apex/frontend/src/App.jsx):
- **`/` & `/terms`:** Public marketing landing pages with lazy loading.
- **`/login`, `/register`, `/forgot-password`, `/reset-password`:** Public authentication forms wrapped in `AuthLayout`.
- **`/register/welcome`:** Post-registration wizard wrapped in `OnboardingLayout`.
- **`/super-admin/*`:** Super admin control center wrapped in `SuperAdminLayout` (protected by `ProtectedRoute roles={['super_admin']}`).
- **`/school-admin/*`:** School operational portal wrapped in `SchoolAdminLayout` (protected by `ProtectedRoute roles={SCHOOL_PORTAL_ROLES}`).

### State Management & Context
1. **`AuthContext` ([`frontend/src/context/AuthContext.jsx`](file:///h:/apex/frontend/src/context/AuthContext.jsx)):**
   - Manages user authentication state, tokens in local/session storage, and profile loading.
   - Provides `switchRole(role)` for instant switching between dual roles (e.g. Teacher $\leftrightarrow$ Parent) without re-authenticating.
2. **`TenantContext` ([`frontend/src/context/TenantContext.jsx`](file:///h:/apex/frontend/src/context/TenantContext.jsx)):**
   - Fetches the active school's context (`/api/v1/tenants/context/`) every 30 seconds via React Query.
   - Injects the school's dynamic branding colors into DOM CSS variables (`--apex-primary`, `--apex-secondary`, `--apex-accent`).
   - Evaluates `hasFeature(key)` and `canAccessModule(key)` to conditionally render UI components.
3. **`MaintenanceContext` ([`frontend/src/context/MaintenanceContext.jsx`](file:///h:/apex/frontend/src/context/MaintenanceContext.jsx)):**
   - Periodically polls platform maintenance status. If activated, non-super-admin users are redirected to `/maintenance`.

### Styling & Design Language
Defined in [`frontend/src/styles/global.css`](file:///h:/apex/frontend/src/styles/global.css):
- **Curated Palette:** Default brand colors are Teal (`#0F766E`), Coral (`#FF7F50`), and Sand Accent (`#F5E6CA`).
- **Typography:** Modern fonts loaded via Google Fonts (`Plus Jakarta Sans` for display headings, `Inter` for UI body text).
- **Design Tokens:** Extensive use of CSS variables for surfaces, elevations, borders, radiuses (`12px` / `16px`), glassmorphism (`rgba(255, 255, 255, 0.72)` backdrop blur), and smooth transitions.
- **UX Patterns:** Multi-step workflows (Plan Editor, Broadcasts, Advertisements, Student Workspaces) utilize full-page overlay workspaces rather than cramped modals.

---

## 7. Database Architecture

```
                               ┌───────────────────────────┐
                               │       tenants_tenant      │
                               └─────────────┬─────────────┘
                                             │
                      ┌──────────────────────┼──────────────────────┐
                      ▼                      ▼                      ▼
           ┌─────────────────────┐┌─────────────────────┐┌─────────────────────┐
           │  subscriptions_sub  ││    accounts_user    ││   academics_year    │
           └──────────┬──────────┘└──────────┬──────────┘└──────────┬──────────┘
                      │                      │                      │
                      ▼                      ▼                      ▼
           ┌─────────────────────┐┌─────────────────────┐┌─────────────────────┐
           │ subscriptions_plan  ││   staff_staff /     ││  academics_term /   │
           └─────────────────────┘│  students_student   ││  academics_class    │
                                  └──────────┬──────────┘└──────────┬──────────┘
                                             │                      │
                                             └───────────┬──────────┘
                                                         │
                      ┌──────────────────────────────────┼──────────────────────────────────┐
                      ▼                                  ▼                                  ▼
           ┌─────────────────────┐            ┌─────────────────────┐            ┌─────────────────────┐
           │ attendance_record / │            │   finance_invoice / │            │  examinations_exam /│
           │  attendance_geofence│            │  finance_feepayment │            │ examinations_report │
           └─────────────────────┘            └─────────────────────┘            └─────────────────────┘
```

### Central Entities & Relationships
1. **`tenants_tenant`:** The root entity for every educational institution. Stores school branding (logo, banner, colors), contact details, timezone, verification status, and suspension flags.
2. **`accounts_user`:** Custom user model inheriting `AbstractBaseUser` and `PermissionsMixin`. Uses email as the username. Linked to a tenant (nullable for Super Admins).
3. **`accounts_userroleassignment`:** Enables dual-role access. Maps a single user to multiple roles within a school (e.g. primary role = Teacher, secondary role = Parent).
4. **`subscriptions_plan` & `subscriptions_subscription`:** Manage commercial tiers. A plan defines student/staff limits and holds Many-to-Many relationships with `FeatureFlag` catalog rows via `PlanFeature`.
5. **`finance_feestructure`, `finance_feepayment`, `finance_invoice`:** Core billing models. Standardized on `currency = 'UGX'`. Linked to double-entry `finance_journalentry` and `finance_journalline`.
6. **`academics_academicyear`, `academics_term`, `academics_class`, `academics_stream`:** Define institutional organizational hierarchy. Classes are associated with curricula (`uneb`, `uganda_cbe`, `cbc`, `844`, `igcse`).

### Data Isolation & Integrity Constraints
- **Isolation:** Every tenant-scoped table has a mandatory indexed `tenant_id` foreign key with `on_delete=models.CASCADE`.
- **Soft Delete:** Records are flagged via `is_deleted = True` rather than executed as SQL `DELETE`.
- **Composite Uniqueness:** Uniqueness constraints are scoped per tenant (e.g. `unique_together = [("tenant", "admission_number")]` for students, and `[("tenant", "code")]` for classes, departments, and subjects).

---

## 8. User Roles and Permissions

| Role | Slug | Portal Scope | Key Responsibilities & Capabilities | Evidence |
| :--- | :--- | :--- | :--- | :--- |
| **Super Admin** | `super_admin` | `/super-admin` | Platform oversight, school onboarding approval, plan editing, system broadcasts, global settings. Bypasses tenant data filtering. | [`backend/apps/core/constants.py:29`](file:///h:/apex/backend/apps/core/constants.py#L29) |
| **School Admin** | `school_admin` | `/school-admin` | Full administrative control over school operations, role permissions, fee structures, staffing, and subscription upgrades. | [`backend/apps/core/constants.py:30`](file:///h:/apex/backend/apps/core/constants.py#L30) |
| **Head Teacher** | `head_teacher` | `/school-admin` | Executive academic supervision, report card approvals, staff attendance monitoring, school notices. | [`backend/apps/core/constants.py:31`](file:///h:/apex/backend/apps/core/constants.py#L31) |
| **Deputy Head Teacher** | `deputy_head_teacher` | `/school-admin` | Operational oversight, staff supervision, student discipline cases (`DisciplineRemark`). | [`backend/apps/core/constants.py:32`](file:///h:/apex/backend/apps/core/constants.py#L32) |
| **Director of Studies** | `director_of_studies` | `/school-admin` | Curriculum management, timetable generation wizard, exam schedules, promotion batches, grading schemes. | [`backend/apps/core/constants.py:33`](file:///h:/apex/backend/apps/core/constants.py#L33) |
| **Head of Department** | `head_of_department` | `/school-admin` | Subject allocations, departmental teaching assignments, syllabus progress reviews. | [`backend/apps/core/constants.py:34`](file:///h:/apex/backend/apps/core/constants.py#L34) |
| **Class Teacher** | `class_teacher` | `/school-admin` | Class register attendance, class notice board, student discipline remarks, report card remarks. | [`backend/apps/core/constants.py:36`](file:///h:/apex/backend/apps/core/constants.py#L36) |
| **Teacher** | `teacher` | `/school-admin` | Subject lesson attendance, marks entry, homework/assignment creation and grading, teaching schedule view. | [`backend/apps/core/constants.py:35`](file:///h:/apex/backend/apps/core/constants.py#L35) |
| **Bursar / Accountant** | `bursar` | `/school-admin` | Student billing, fee payment recording, invoice generation, waiver/discount requests, financial accounting journals. | [`backend/apps/core/constants.py:39`](file:///h:/apex/backend/apps/core/constants.py#L39) |
| **Assistant Bursar** | `assistant_bursar` | `/school-admin` | Front-desk receipt issuance, daily cash reconciliation, payment collection (requires Bursar approval for refunds/waivers). | [`backend/apps/core/constants.py:40`](file:///h:/apex/backend/apps/core/constants.py#L40) |
| **Librarian** | `librarian` | `/school-admin` | Book inventory catalog, issue/return tracking, overdue fine calculation. | [`backend/apps/core/constants.py:41`](file:///h:/apex/backend/apps/core/constants.py#L41) |
| **HR Manager** | `hr_manager` | `/school-admin` | Staff onboarding, leave approvals, salary structures, monthly payroll processing. | [`backend/apps/core/constants.py:42`](file:///h:/apex/backend/apps/core/constants.py#L42) |
| **Transport Manager** | `transport_manager` | `/school-admin` | Fleet management, driver assignments, route planning, student bus allocation. | [`backend/apps/core/constants.py:43`](file:///h:/apex/backend/apps/core/constants.py#L43) |
| **Hostel Manager** | `hostel_manager` | `/school-admin` | Boarding facilities, room inventory, student bed allocations. | [`backend/apps/core/constants.py:44`](file:///h:/apex/backend/apps/core/constants.py#L44) |
| **Inventory Manager** | `inventory_manager` | `/school-admin` | School store inventory, stock-in/out tracking, procurement requests. | [`backend/apps/core/constants.py:45`](file:///h:/apex/backend/apps/core/constants.py#L45) |
| **Parent** | `parent` | `/school-admin` | View fee balances, student academic report cards (subject to fee clearance policy), attendance history. | [`backend/apps/core/constants.py:37`](file:///h:/apex/backend/apps/core/constants.py#L37) |
| **Student** | `student` | Restricted | Profile information, enrolled subjects, timetable view (portal access currently minimal). | [`backend/apps/core/constants.py:38`](file:///h:/apex/backend/apps/core/constants.py#L38) |

---

## 9. Major Business Modules

| Module | Purpose | Main Users | Primary Backend Files | Primary Frontend Files | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Platform Administration** | Super admin operations, plan management, broadcasts, advertisements | Super Admin | `apps/platform/views.py`, `apps/platform/services/broadcasts.py` | `pages/super-admin/Broadcast.jsx`, `PlanEditor.jsx` | **Implemented** |
| **Subscription & Plans** | Tier inheritance, feature flag catalog, trial expiry, plan checkout | Super Admin, School Admin | `apps/subscriptions/plan_tiers.py`, `upgrade_services.py` | `pages/school-admin/PlanUpgrade.jsx`, `PlansAndSubscriptions.jsx` | **Implemented** |
| **Tenant Onboarding** | Public school registration, verification queue, campus setup | School Admin, Super Admin | `apps/tenants/views.py`, `apps/tenants/onboarding.py` | `pages/auth/Register.jsx`, `RegistrationWelcome.jsx` | **Implemented** |
| **Student & Parent Info** | Student registry, parent contacts, medical history, admissions | School Admin, Teachers | `apps/students/views.py`, `apps/admissions/views.py` | `pages/school-admin/Students.jsx`, `StudentWorkspace.jsx` | **Implemented** |
| **Academics & Timetable** | Academic years, terms, classes, streams, automated timetable generator | DoS, Head Teacher, Teachers | `apps/academics/views.py`, `timetable_grid_builder.py` | `pages/school-admin/Classes.jsx`, `TimetableWizard.jsx` | **Implemented** |
| **Examinations & Grading** | Exam sessions, marks entry, approval workflow, report cards | Teachers, HoD, DoS, Head Teacher | `apps/examinations/views.py`, `services/report_cards.py` | `pages/school-admin/MarksEntry.jsx`, `MarksApproval.jsx` | **Implemented** |
| **Finance & Billing** | Termly fee structures, student ledger, double-entry journals, receipts | Bursar, Assistant Bursar, School Admin | `apps/finance/views.py`, `apps/finance/services/billing.py` | `pages/school-admin/FinanceBilling.jsx`, `BursarWorkspace.jsx` | **Implemented** |
| **Attendance & Biometrics**| Student register, staff GPS check-in, geofencing, WebAuthn passkeys | Staff, Class Teachers, School Admin | `apps/attendance/views.py`, `apps/attendance/geofence.py` | `pages/school-admin/Attendance.jsx`, `StaffAttendance.jsx` | **Implemented** |
| **Staff & HR** | Staff directory, leave requests, performance reviews | HR Manager, School Admin | `apps/staff/views.py`, `apps/hr/views.py` | `pages/school-admin/Staff.jsx`, `HR.jsx`, `StaffWorkspace.jsx` | **Implemented** |
| **Payroll Management** | Salary structures, allowances/deductions, monthly payroll runs | HR Manager, Bursar | `apps/payroll/views.py` | `pages/school-admin/Payroll.jsx` | **Implemented** |
| **Library Management** | Book catalog, ISBN tracking, borrow/return ledger, fines | Librarian | `apps/library/views.py` | `pages/school-admin/Library.jsx` | **Implemented** |
| **Hostel Management** | Boarding hostel buildings, room inventory, student bed allocations | Hostel Manager | `apps/hostel/views.py` | `pages/school-admin/Hostel.jsx` | **Implemented** |
| **Transport Operations** | Buses/vans, drivers, pickup routes, student transport assignments | Transport Manager | `apps/transport/views.py` | `pages/school-admin/Transport.jsx` | **Implemented** |
| **Inventory & Store** | Consumables, equipment, stock movements, procurement requisitions | Inventory Manager | `apps/inventory/views.py` | `pages/school-admin/Inventory.jsx` | **Implemented** |
| **Communication** | In-app notices, SMS/email audit logs, support tickets | All School Roles | `apps/communication/views.py` | `pages/school-admin/Communication.jsx`, `Notifications.jsx` | **Implemented** |

---

## 10. End-to-End Workflow Traces

### Workflow 1: User Login & Dual-Role Session Initialization
1. **User Action:** User enters email and password into `pages/auth/Login.jsx`.
2. **Frontend Dispatch:** `authService.login()` invokes `POST /api/v1/auth/login/` via Axios (`api.js`).
3. **Backend Route & View:** Request routed through `apps/accounts/urls.py` to `CustomTokenObtainPairView` ([`backend/apps/accounts/views.py:43`](file:///h:/apex/backend/apps/accounts/views.py#L43)).
4. **Validation & Claims Injection:** `CustomTokenObtainPairSerializer.validate()`:
   - Validates user credentials against `accounts_user`.
   - Rejects non-super-admins if `MAINTENANCE_MODE` is active.
   - Logs the attempt in `LoginHistory` with IP and User-Agent.
   - Injects tenant claims into the JWT: `tenant_id`, `tenant_name`, `tenant_plan_slug`, `tenant_is_suspended`, `role`.
   - Checks `UserRoleAssignment` to restore the primary role if the user has multiple personas.
5. **Token Storage:** Frontend stores `access` and `refresh` tokens in `localStorage` and triggers `loadUser()`.
6. **Portal Redirection:** `ProtectedRoute` inspects the user's role:
   - `super_admin` $\rightarrow$ Redirects to `/super-admin`.
   - `school_admin` or school staff/parents $\rightarrow$ Redirects to `/school-admin`.
7. **Context Hydration:** `TenantProvider` mounts, querying `GET /api/v1/tenants/context/`, which loads tenant branding, active feature flags, and role permissions, applying dynamic CSS variables to the document root.

### Workflow 2: School Registration & Onboarding Pipeline
1. **User Action:** School administrator fills out the public registration form on `pages/auth/Register.jsx`.
2. **Frontend Dispatch:** `api.post('/tenants/register/', payload)`.
3. **Backend Route & View:** Handled by `TenantRegistrationView` ([`backend/apps/tenants/views.py:222`](file:///h:/apex/backend/apps/tenants/views.py#L222)).
4. **Data Persisted:** `TenantRegistrationSerializer.create()`:
   - Validates that school code and admin email are unique.
   - Creates the `Tenant` record with `status = 'pending'` and `registration_type = 'pending'`.
   - Creates the admin `User` record with `role = 'school_admin'`.
   - Automatically attaches a `Subscription` on the `free_trial` plan (14-day trial).
   - Triggers `create_registration_notification()` creating a pending `PlatformNotification` for super-admins.
5. **Onboarding Screen:** User is redirected to `/register/welcome`, presenting three onboarding pathways:
   - Claim trial via verification code (`/api/v1/tenants/onboarding/<id>/claim-trial/`).
   - Select a plan tier (`/api/v1/tenants/onboarding/<id>/select-plan/`).
   - Proceed to paid checkout (`/api/v1/tenants/onboarding/<id>/checkout/`).

### Workflow 3: Subscription Upgrade & Sandbox Payment Checkout
1. **User Action:** School admin navigates to `/school-admin/upgrade` (`pages/school-admin/PlanUpgrade.jsx`), selects a higher tier (e.g. `premium`), chooses a billing cycle (`monthly` or `yearly`), and inputs card or mobile money details.
2. **Frontend Dispatch:** `subscriptionService.checkoutUpgrade(payload)` posts to `POST /api/v1/subscriptions/upgrade/checkout/`.
3. **Backend Verification:** `process_upgrade_checkout()` in [`backend/apps/subscriptions/upgrade_services.py:199`](file:///h:/apex/backend/apps/subscriptions/upgrade_services.py#L199):
   - Confirms target plan tier is higher than the current tier via `plan_tiers.py`.
   - Verifies billing cycle and calculates the UGX/USD amount.
4. **Gateway Execution:** Calls `PaymentService.process_checkout()`:
   - Masks sensitive card/phone information. Full credit card numbers are never persisted.
   - Records a `PaymentTransaction` row with `status = 'failed'` (indicating that live payment gateways are disconnected in sandbox mode).
   - Generates an in-app `Notification` warning the school admin that sandbox mode is active.
5. **Response & UI Feedback:** Returns HTTP 200 with `{ success: false, requires_admin_activation: true, message: "..." }`. The frontend prompts the school admin to contact platform billing support or await manual super-admin activation.

### Workflow 4: Platform Broadcast Multi-Channel Dispatch
1. **User Action:** Super Admin opens `/super-admin/broadcast` (`pages/super-admin/Broadcast.jsx`), chooses audience filter (`all`, `active`, or by plan tier: `trial`, `basic`, `premium`), selects channels (`email`, `sms`, `whatsapp`), and writes announcement content.
2. **Audience Preview:** Frontend requests `POST /api/v1/platform/broadcasts/preview/`, returning recipient counts, total schools, and channel reachability statistics.
3. **Execution Dispatch:** Super Admin clicks "Send Broadcast", calling `POST /api/v1/platform/broadcasts/<id>/send/`.
4. **Backend Processing:** `send_platform_broadcast()` in [`backend/apps/platform/services/broadcasts.py:172`](file:///h:/apex/backend/apps/platform/services/broadcasts.py#L172):
   - Resolves recipient `User` records matching target schools.
   - For each recipient and selected channel, constructs branded email templates or text payloads.
   - Dispatches via `EmailService`, `SMSService`, or `WhatsAppService`.
   - Creates a delivery log entry in `PlatformBroadcastDelivery`.
   - Dispatches a real-time in-app notification to the school admin via `create_user_notification()`.
   - Atomically updates broadcast aggregate counters (`recipient_count`, `delivered_count`, `failed_count`).

### Workflow 5: Staff Attendance with Geofencing & WebAuthn Verification
1. **User Action:** Staff member opens `/school-admin/attendance/staff` on a mobile device and taps "Check In".
2. **Browser Telemetry:** The browser queries HTML5 Geolocation (`navigator.geolocation.getCurrentPosition`) for `lat`, `lng`, and `accuracy_m`.
3. **Biometric Assertion:** If passkeys are registered, the browser triggers `navigator.credentials.get()` requesting fingerprint/FaceID biometrics.
4. **API Submission:** Submits telemetry to `POST /api/v1/attendance/staff/check-in/`.
5. **Backend Verification:** `staff_check_in()` in [`backend/apps/attendance/staff_geo_attendance.py`](file:///h:/apex/backend/apps/attendance/staff_geo_attendance.py):
   - Fetches the school's `SchoolGeofence`.
   - Uses ray-casting point-in-polygon math to verify the coordinates fall within the campus boundary (plus allowance buffer).
   - Validates the WebAuthn cryptographic assertion signature against `WebAuthnCredential`.
   - Creates or updates today's `AttendanceRecord` stamping check-in time and exact GPS coordinates.

---

## 11. Deployment and Infrastructure

### Container Architecture
The platform is fully containerized using Docker and orchestrated via Docker Compose:
- **`apex_db`:** `postgres:16-alpine` on port `5432`. Data is persisted to named Docker volume `postgres_data`.
- **`apex_redis`:** `redis:7-alpine` on port `6379`. Provides Redis caching and Celery broker queues.
- **`apex_backend`:** Built from `deployment/Dockerfile.backend` (Python 3.13 slim). Collects static files, runs database migrations, and boots Gunicorn with 4 workers on port `8000`.
- **`apex_frontend`:** Built from `deployment/Dockerfile.frontend` via multi-stage build (Node 22 builds production assets $\rightarrow$ Nginx alpine serves SPA on port `80`).
- **`apex_nginx`:** Production edge reverse proxy on ports `80` and `443`. Implements upstream load balancing, static caching, proxy headers, and routing.

```
Incoming Traffic (HTTP :80 / HTTPS :443)
                 │
                 ▼
         [ apex_nginx ]
                 │
  ┌──────────────┼──────────────┬──────────────┐
  ▼              ▼              ▼              ▼
/api/*        /admin/*       /static/          /*
  │              │           /media/*          │
  └──────┬───────┘              │              │
         ▼                      ▼              ▼
  [ apex_backend ]       [ Disk Volumes ] [ apex_frontend ]
  (Gunicorn :8000)                        (Nginx SPA :80)
```

### Local Development vs. Production Execution
- **Local Development Mode:**
  - Backend: `python manage.py runserver` (active on port `8000`).
  - Frontend: `npm run dev` via Vite (active on port `3000`).
  - API Proxying: `vite.config.js` proxies `/api` requests directly to `http://localhost:8000`.
  - Database: Connects to local PostgreSQL or fallback SQLite test database.
- **Remote Demo / Ngrok Tunneling:**
  - Configured with `ngrok-tunnel.ps1` targeting domain `hungrily-throttle-nintendo.ngrok-free.dev`.
  - `TRUST_PROXY_HEADERS = True` and `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` ensure proper CSRF and HTTPS handling through tunnels.

---

## 12. Current Implementation Status

| Feature / Domain | Classification | Notes & Evidence |
| :--- | :--- | :--- |
| **Tenant Isolation Engine** | **Implemented** | ORM manager + view mixins thoroughly tested in `test_tenant_isolation.py`. |
| **JWT Authentication & Sessions** | **Implemented** | Token blacklisting, login history, and device tracking active. |
| **Dual-Role User Persona Switching** | **Implemented** | `UserRoleAssignment` model, `switchRole` frontend context, verified in `test_dual_roles.py`. |
| **Plan Hierarchy & Feature Gating** | **Implemented** | Plan tier inheritance validated in `plan_tiers.py` and frontend `<FeatureGate>`. |
| **Subscription Auto-Expiry (Celery)**| **Implemented** | Celery tasks in `subscriptions/tasks.py` and management commands. |
| **School Profile & Branding** | **Implemented** | Dynamic CSS variable injection and PDF headed paper customizer. |
| **Campus Geofencing & GPS Check-In** | **Implemented** | Point-in-polygon algorithm in `attendance/geofence.py`. |
| **WebAuthn Biometric Attendance** | **Implemented** | Passkey registration and assertion flow verified in `test_geofence_staff_attendance.py`. |
| **Automated Timetable Generation** | **Implemented** | Draft generation and conflict resolution engine in `timetable_grid_builder.py`. |
| **Student Promotion Wizard** | **Implemented** | Batch promotion sessions with undo capabilities in `PromotionBatch`. |
| **Double-Entry Financial Accounting** | **Implemented** | Chart of accounts, journal entries, ledgers, and billing engine. |
| **Results Access Fee Threshold Policy**| **Implemented** | Configurable fee clearance percentage controlling parental report card access. |
| **Platform Super-Admin Broadcasts** | **Implemented** | Multi-channel audience resolution and delivery tracking. |
| **Plan Upgrade Advertisements** | **Implemented** | Super admin promotional banners targeted by plan tier. |
| **Platform Maintenance Mode** | **Implemented** | Middleware bypass for super admins; polling and overlay banners on frontend. |
| **Live Payment Gateway Dispatches** | **Partially Implemented** | Full checkout payloads and transaction ledger built; live HTTP API calls stubbed until deployment credentials exist. |
| **Live SMS & WhatsApp Dispatches** | **Partially Implemented** | Gateway payload builders complete; outbound HTTP gated behind `INTEGRATION_LIVE_DISPATCH`. |
| **Real-time WebSockets** | **Not Found / Deferred** | Stack uses standard REST and React Query polling (30s interval); ASGI entry point exists but Channels is not installed. |

---

## 13. Architectural Concerns & Observations

| Concern | Evidence | Why It Matters | Severity | Requires Confirmation |
| :--- | :--- | :--- | :--- | :--- |
| **Middleware Execution Order** | [`settings.py:102,106`](file:///h:/apex/backend/apex_hub/settings.py#L102) | `TenantMiddleware` runs before `JWTAuthenticationMiddleware`. For non-session DRF requests, `request.user` is not set when `TenantMiddleware` executes. Views compensate via `TenantFilterMixin`, but thread-local `TenantContext` remains unpopulated during earlier middleware stages. | **Medium** | No (Confirmed by code inspection) |
| **Monolithic `global.css`** | [`frontend/src/styles/global.css`](file:///h:/apex/frontend/src/styles/global.css) | 5,843 lines of CSS in a single global stylesheet increases cognitive load and risks unintended style cascade collisions. | **Low** | No (Confirmed by code inspection) |
| **Sandbox Payment Gateway Failures** | [`upgrade_services.py:231`](file:///h:/apex/backend/apps/subscriptions/upgrade_services.py#L231) | Checkout always returns payment failure and records failed transactions. If user expectation was a completed payment loop, payment provider credentials and webhooks must be connected. | **Medium** | Yes (Confirm provider timeline) |
| **Live Dispatch Flag Gating** | [`settings.py:265`](file:///h:/apex/backend/apps/subscriptions/upgrade_services.py#L265) | Broadcasts mark SMS/WhatsApp deliveries as "failed" unless `INTEGRATION_LIVE_DISPATCH=True` is explicitly set in production `.env`. | **Low** | No (Documented design decision) |
| **Celery Worker Running Separately** | [`deployment/docker-compose.yml:56`](file:///h:/apex/deployment/docker-compose.yml#L56) | The compose configuration boots Gunicorn on the backend container, but does not define a dedicated worker container for `celery -A apex_hub worker` or `celery beat`. Background tasks rely on management command cron execution unless a worker is added. | **Medium** | Yes (Confirm background runner setup) |

---

## 14. Important Unknowns

1. **Target Production Payment Gateway:**
   - Placeholder fields exist for Stripe, Flutterwave, Paystack, and PesaPal, but no primary default gateway has been selected for live billing in Uganda.
2. **Production SMS & WhatsApp Provider Accounts:**
   - Configuration models support Africa's Talking, Twilio, and Meta Cloud API, but production credentials, sender IDs, and WhatsApp template approvals remain unconfigured in the repository.
3. **Production Domain & SSL Certificates:**
   - Domain `apexhub.space` is documented, but production DNS routing, Certbot/Let's Encrypt automation, or Cloudflare proxy configurations are not in the repository.
4. **Celery Worker Hosting Strategy:**
   - Whether periodic background tasks (hourly expiry, scheduled broadcasts) will run via Celery Beat or standard Linux `crontab` management commands in production.

---

## 15. Recommended Next Steps for Future Development

> [!IMPORTANT]
> The following recommendations are provided strictly for technical roadmap planning. No code has been modified or implemented during this discovery.

### Phase A: Deployment & Infrastructure Hardening
- **Add Celery & Celery Beat to Docker Compose:** Add dedicated service blocks in `deployment/docker-compose.yml` for Celery worker and beat processes to run scheduled background jobs reliably.
- **Configure Production Reverse Proxy SSL:** Introduce automated Let's Encrypt / Certbot container configurations or configure Cloudflare edge SSL in `deployment/nginx.conf`.
- **Review Middleware Ordering:** Shift `apps.platform.middleware.JWTAuthenticationMiddleware` ahead of `apps.tenants.middleware.TenantMiddleware` in `settings.py` so thread-local tenant context is consistently populated for all authenticated API requests.

### Phase B: Gateway Activation & Integration Pipelines
- **Select & Activate Primary Payment Gateway:** Connect a regional gateway (e.g. Flutterwave, PesaPal, or MTN MoMo API) by implementing the live webhook receiver in `apps/finance/services/gateway/` and setting `INTEGRATION_LIVE_DISPATCH=True`.
- **Configure Outbound Messaging Gateway:** Add verified credentials for Africa's Talking or Twilio to enable live delivery of platform broadcasts and automated student attendance SMS alerts to parents.

### Phase C: Codebase Maintainability & Modularization
- **Modularize Frontend Styles:** Split `frontend/src/styles/global.css` into domain CSS modules or styled component partials (e.g. `broadcast.css`, `plan-editor.css`, `workspace.css`) to improve maintainability.
- **Frontend Bundle Optimization:** Continue optimizing manual chunks in `vite.config.js` to ensure the heavy academic, financial, and workspace bundles are code-split and loaded on demand.

---

## Final Confirmation of Read-Only Compliance
- **No files were modified.**
- **No files were created in the project repository.**
- **No files were deleted or renamed.**
- **No packages or dependencies were installed or upgraded.**
- **No database mutations or migrations were executed.**
- **No Git branches were modified or code committed.**
- **The system discovery was conducted systematically using read-only filesystem inspection.**