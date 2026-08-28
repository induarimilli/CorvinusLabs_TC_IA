# Corvinus Labs Multi-Tenant Lab Operations Portal

A full-stack demo of the Corvinus Labs internal operations portal — multi-tenant, RBAC-enforced, with async tool provisioning.

## Quick Start (Local — no Docker)

**Important:** run all commands from the project root (the folder that contains `Makefile`), not from your home directory.

```bash
cd "/Users/induarimilli/Library/CloudStorage/OneDrive-andrew.cmu.edu/CorvinusLabs_Technical_Challenge "
make install      # Python + npm dependencies (first time only)
make setup-db     # Create DB, run migrations, seed demo data (first time only)
```

Start in **two terminals** (both `cd` into the project folder first):

```bash
# Terminal 1
cd "/Users/induarimilli/Library/CloudStorage/OneDrive-andrew.cmu.edu/CorvinusLabs_Technical_Challenge "
make dev-api

# Terminal 2
cd "/Users/induarimilli/Library/CloudStorage/OneDrive-andrew.cmu.edu/CorvinusLabs_Technical_Challenge "
make dev-web
```

Without Make, you can run the same commands directly:

```bash
cd "/Users/induarimilli/Library/CloudStorage/OneDrive-andrew.cmu.edu/CorvinusLabs_Technical_Challenge /backend"
uvicorn app.main:app --reload --port 8000

cd "/Users/induarimilli/Library/CloudStorage/OneDrive-andrew.cmu.edu/CorvinusLabs_Technical_Challenge /frontend"
npm run dev
```

| Service | URL |
|---------|-----|
| **App** | http://localhost:5173 |
| **API docs** | http://localhost:8000/docs |
| **Database** | `psql -h localhost -U corvinus -d corvinus` (password: `corvinus`) |

## Quick Start (Docker)

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.

```bash
make up
```

| Service | URL |
|---------|-----|
| **App** | http://localhost:5173 |
| **API docs** | http://localhost:8000/docs |
| **Adminer (DB UI)** | http://localhost:8080 |

Adminer: System **PostgreSQL**, Server **postgres**, User **corvinus**, Password **corvinus**, Database **corvinus**

## Demo Users

Log in by clicking any user on the login page:

| User | Org | Role | Lab |
|------|-----|------|-----|
| Alice Chen | Corvinus Robotics | Admin | — |
| Bob Martinez | Corvinus Robotics | Manager | Perception Lab |
| Carol Wu | Corvinus Robotics | Contributor | Perception Lab |
| Dave Okonkwo | Corvinus Robotics | Contributor | Simulation Lab |
| Alice Chen | Corvinus Biologics | Manager | Wet Lab |
| Eve Nakamura | Corvinus Biologics | Admin | — |
| Frank Liu | Corvinus Biologics | Contributor | Analysis Lab |

**Cross-org demo:** Log in as Alice — she's Admin in Robotics and Manager in Biologics. Use the org switcher in the header to see tenant isolation.

## Demo Walkthrough

### Admin (Alice @ Robotics)
1. Dashboard shows org stats
2. **Members** — change a member's role
3. **Labs** — create a new lab
4. **Tool Registry** — register a tool
5. **Invitations** — invite by email, copy the invite link
6. **Audit Log** — see all actions recorded

### Manager (Bob @ Robotics)
1. Dashboard shows lab overview
2. **Tasks** — create task, move through Kanban columns
3. **Team** — grant Carol access to a tool, watch status go REQUESTED → PROVISIONING → ACTIVE

### Contributor (Carol @ Robotics)
1. **My Work** on dashboard
2. **Tasks** — work assigned tasks
3. **Tools** — launch CVAT (already ACTIVE)

### Tenant isolation
1. Log in as Alice
2. Switch org from Robotics → Biologics
3. All data changes — different labs, tasks, tools

### Invitations
1. Admin creates invite, copies link
2. Open link in incognito: `/invite/{token}`
3. Accept — creates real membership

## Reset Demo Data

```bash
make demo-reset
```

## Architecture

- **Backend:** Python + FastAPI (modular monolith)
- **Frontend:** React + TypeScript + Vite
- **Database:** PostgreSQL (15 ERD tables, see `docs/erd.png`)
- **Queue:** Redis (async tool provisioning worker in Docker; local dev uses in-process tasks)
- **Storage:** MinIO (S3-compatible, Docker only)

Every protected route resolves: `currentUser → currentOrganization → currentMembership → currentRole` before touching domain logic.

## Vertical slice summary

| Slice | Built | Stubbed |
|-------|-------|---------|
| 0 Scaffold | Docker Compose, Alembic, 15 tables, Adminer, ERD in docs | — |
| 1 Auth | TenantContext, demo login with org picker, JWT sessions | Supabase GoTrue (JWT issued by app) |
| 2 Seed | 2 orgs, cross-org Alice, mixed task/tool states | — |
| 3 Dashboard | Role-branching stats, profile, org/lab switcher | — |
| 4 Admin | Members, labs, tools, settings, audit log | — |
| 5 Tasks | CRUD, Kanban, state machine, optimistic lock, comments API | Attachments UI (API ready) |
| 6 Invites | Create link, accept flow, conditional update | Email delivery |
| 7 Tools | ToolConnector mocks, async provisioning, status badges | Real CVAT/Isaac Sim APIs |
| 8 Polish | Manager team/grant UI, Contributor launcher | — |
| 9 Demo | README walkthrough, smoke checklist, demo-reset | — |

## Smoke Checklist

- [ ] Login page lists seeded users
- [ ] Admin: invite, manage members/labs, view audit log
- [ ] Manager: create/assign tasks, grant tool access, watch provisioning
- [ ] Contributor: scoped view, work tasks, launch granted tool
- [ ] Org switcher changes all data (no cross-tenant leakage)
- [ ] Refresh page — all actions persisted
- [ ] Adminer shows live DB changes
