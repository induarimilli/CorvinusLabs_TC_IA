# Architecture

System architecture for the Corvinus Labs Multi-Tenant Lab Operations Portal as implemented in this repository.

Related docs: [PRD.md](PRD.md) · [DESIGN.md](DESIGN.md) · [SCHEMA.md](SCHEMA.md) · [DEMO_SCRIPT.md](DEMO_SCRIPT.md)

---

## 1. Local hosting

Two supported ways to run locally.

### Dev mode (typical for demos)

```bash
make install && make setup-db   # once
make dev-api                   # terminal 1 → FastAPI :8000
make dev-web                   # terminal 2 → Vite :5173
```

```mermaid
flowchart LR
  browser[Browser]
  vite[Vite_frontend_5173]
  api[FastAPI_backend_8000]
  pg[(Postgres_5432)]

  browser -->|SPA| vite
  vite -->|"REST + JWT headers"| api
  api --> pg
```

| Service | URL |
|---------|-----|
| App | http://localhost:5173 |
| API / OpenAPI | http://localhost:8000/docs |
| Health | http://localhost:8000/health |

Demo auth is passwordless: `POST /auth/demo-login` with a seeded `user_id`.

### Docker Compose (full stack)

`docker compose up` starts Postgres, Redis, MinIO, Adminer, API, optional worker, and web.

```mermaid
flowchart TB
  subgraph host [Host_machine]
    browser[Browser]
  end
  subgraph compose [docker_compose]
    web[web_Vite_5173]
    api[api_FastAPI_8000]
    worker[worker_background]
    pg[(postgres_5432)]
    redis[(redis_6379)]
    minio[minio_9000]
    adminer[adminer_8080]
  end
  browser --> web
  browser --> api
  web --> api
  api --> pg
  api --> redis
  api --> minio
  worker --> pg
  worker --> redis
  adminer --> pg
```

Local demos usually use **in-process FastAPI BackgroundTasks** for tool and Google Workspace provisioning (no separate worker required).

---

## 2. Multi-tenant request path

Every org-scoped API call carries:

1. `Authorization: Bearer <JWT>` — global user identity  
2. `X-Organization-Id` — active tenant  
3. `X-Lab-Id` (optional) — lab context for lab-scoped RBAC and tool catalog  

```mermaid
sequenceDiagram
  participant UI as Frontend
  participant API as FastAPI
  participant Auth as get_current_user
  participant Ctx as get_tenant_context
  participant RBAC as authorize
  participant DB as Postgres

  UI->>API: Request + JWT + org/lab headers
  API->>Auth: Decode JWT, load User
  Auth->>DB: users by id
  Auth-->>API: User ACTIVE or 401
  API->>Ctx: Resolve org membership + lab role
  Ctx->>DB: organization_memberships, labs
  Ctx-->>API: TenantContext
  API->>RBAC: Permission vs Admin/Manager/Contributor
  RBAC-->>API: allow or 403
  API->>DB: Business query
  API-->>UI: JSON
```

**Invariants**

- Suspended users (`users.status != ACTIVE`) cannot authenticate.  
- Removed org membership cannot obtain `TenantContext`.  
- Resources with `organization_id` must match the header org (tenant isolation).  
- Non-admins must be members of `X-Lab-Id` when that header is set.

---

## 3. Role model

```mermaid
flowchart TB
  user[User_global_identity]
  staff[platform_role_STAFF]
  orgMem[OrganizationMembership]
  labMem[LabMembership]

  user --> staff
  user --> orgMem
  user --> labMem
  orgMem -->|org_role| adminOrMember[ADMIN_or_MEMBER]
  labMem -->|lab_role| mgrOrContrib[MANAGER_or_CONTRIBUTOR]
```

| Layer | Field | Values | Scope |
|-------|--------|--------|--------|
| Platform | `users.platform_role` | `STAFF` / null | Create/deactivate orgs, platform analytics — not grantable via org invites |
| Organization | `organization_memberships.org_role` | `ADMIN`, `MEMBER` | Settings, members, invites, tool registry, audit, GW provision |
| Lab | `lab_memberships.lab_role` | `MANAGER`, `CONTRIBUTOR` | Tasks CRUD, tool launch/grant, team view |

Same person can be **Manager in Lab A** and **Contributor in Lab B** (e.g. Dave). UI role badge and tool privileges follow the **active lab** (`X-Lab-Id`).

Managers in the active lab may **launch all org-registered research tools** without a `ToolAccess` row. Contributors follow per-lab `lab_tool_policies`.

---

## 4. Research tool access & provisioning

```mermaid
stateDiagram-v2
  [*] --> None: No_row
  None --> PENDING_APPROVAL: Contributor_requests
  PENDING_APPROVAL --> REQUESTED: Manager_approves
  PENDING_APPROVAL --> None: Manager_denies
  REQUESTED --> PROVISIONING: Worker
  PROVISIONING --> ACTIVE: Success
  PROVISIONING --> FAILED: Connector_error
  ACTIVE --> REVOKING: Revoke
  REVOKING --> [*]
  None --> REQUESTED: Onboarding_AUTO_ONBOARD
```

Connectors (CVAT, Isaac Sim, Protocol Tool) live under `backend/app/connectors/`. Launch/session/health go through the connector registry.

Lab policies (`lab_tool_policies.access_mode`):

- `AUTO_ONBOARD` — granted when Contributor finishes lab onboarding  
- `REQUEST` — Contributor must request; Manager approves  

---

## 5. Google Workspace (lab infrastructure)

Shared per lab — **not** per-user `ToolAccess`.

```mermaid
flowchart LR
  admin[Org_Admin]
  ws[lab_google_workspace]
  members[Lab_Managers_and_Contributors]

  admin -->|POST provision| ws
  ws -->|REQUESTED_PROVISIONING_ACTIVE| ws
  members -->|Drive_Calendar_Chat_Meet_APIs| ws
```

State machine mirrors tools: `REQUESTED` → `PROVISIONING` → `ACTIVE` (mock ~2–3s via BackgroundTasks). Members of other labs in the same org cannot read Lab B’s workspace.

---

## 6. Contributor onboarding (scavenger hunt)

```mermaid
flowchart TD
  invite[Accept_invite_CONTRIBUTOR]
  progress[lab_onboarding_progress]
  guide[OnboardingGuide_UI]
  dash[Dashboard]
  tools[App_Launcher]
  tasks[Tasks]
  done[Complete_unlock_AUTO_ONBOARD_tools]

  invite --> progress
  progress --> guide
  guide --> dash
  dash -->|click_App_Launcher| tools
  tools -->|click_Tasks| tasks
  tasks --> done
```

Onboarding is first-login per lab. Role changes later show a banner (`role_change_notice`); they do **not** re-trigger onboarding.

---

## 7. Frontend structure

- React + Vite + TanStack Query  
- [`AuthContext`](../frontend/src/context/AuthContext.tsx) — token, orgId, labId  
- [`AppShell`](../frontend/src/components/layout/AppShell.tsx) — nav by effective role, onboarding guide, role-change banner  
- Org/lab switcher updates localStorage + API headers  

## 8. Backend module map

| Module | Responsibility |
|--------|----------------|
| `auth` | Demo login, `/auth/me` |
| `organizations` | Labs, dashboard stats, settings |
| `memberships` | Org roster, lab members, role updates |
| `invitations` | Create/accept invites |
| `tasks` | CRUD, transitions, optimistic locking |
| `tools` | Registry, catalog, access, launch |
| `google_workspace` | Provision + mock Drive/Calendar/Chat/Meet |
| `onboarding` | Scavenger steps + complete |
| `platform` | Staff org create (requires admin invite email) |
| `audit` | Audit events + notifications |
| `workers` | Tool + GW provisioning jobs |
