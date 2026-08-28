# Corvinus Labs Multi-Tenant Lab Operations Portal

Full-stack demo of the Corvinus Labs internal operations portal — multi-tenant, RBAC-enforced, with async tool and Google Workspace provisioning.

## Live demo (from GitHub)

GitHub hosts the **source**, not a permanent public app URL (this stack needs Postgres, Redis, API, and the SPA). Use one of:

| Option | Link / how |
|--------|------------|
| **Codespaces (recommended)** | [![Open in GitHub Codespaces](https://img.shields.io/badge/GitHub-Open%20in%20Codespaces-blue?logo=github)](https://codespaces.new/induarimilli/CorvinusLabs_TC_IA) — after create, open port **5173** (App); set visibility to **Public** if sharing |
| **Docker Compose** | `make up` locally, or in Codespaces after the container is ready |
| **Always-on URL** | Connect this repo to [Render](https://render.com) with [`render.yaml`](render.yaml) (Blueprint) — see [docs/LIVE_DEMO.md](docs/LIVE_DEMO.md) |

Repo: https://github.com/induarimilli/CorvinusLabs_TC_IA

## Run locally on your machine

Someone shared this repo? Clone it and run the portal on **your** computer.

### 1. Get the code

```bash
git clone https://github.com/induarimilli/CorvinusLabs_TC_IA.git
cd CorvinusLabs_TC_IA
```

No git? Download **Code → Download ZIP** on GitHub, unzip, and `cd` into the folder.

### 2. Prerequisites

| Tool | Version | Used for |
|------|---------|----------|
| **Git** | any | clone (optional if using ZIP) |
| **Docker Desktop** | recent | easiest full stack (Option A) |
| **Python** | 3.12+ | API (Option B) |
| **Node.js** | 20+ | frontend (Option B) |
| **PostgreSQL** | 16+ | database (Option B only) |
| **Redis** | 7+ | background jobs (Option B; optional for basic UI) |

You only need Docker for **Option A**. For **Option B**, install Python, Node, and Postgres locally.

### 3. Option A — Docker Compose (recommended)

Starts Postgres, Redis, API, worker, and the web app in containers. Good first choice on a new laptop.

```bash
make up
```

Wait until the command finishes (~1–2 minutes on first run). Then open:

| Service | URL |
|---------|-----|
| **App** | http://localhost:5173 |
| **API docs** | http://localhost:8000/docs |
| **Adminer** (DB UI) | http://localhost:8080 — System: PostgreSQL, Server: `postgres`, User/Password: `corvinus`, Database: `corvinus` |

Stop everything:

```bash
make down
```

View logs:

```bash
make logs
```

### 4. Option B — Native dev (no Docker)

Use this if you already run Postgres on your machine and prefer separate terminals.

**One-time setup:**

```bash
make install          # Python deps + npm packages
make setup-db         # creates DB user/db, runs migrations, seeds demo data
```

`setup-db` expects `psql` on your PATH and Postgres listening on `localhost:5432`. Copy env defaults if you need them:

```bash
cp .env.example .env   # optional; defaults match setup-db
```

**Run (two terminals):**

```bash
# Terminal 1 — API
make dev-api

# Terminal 2 — frontend
make dev-web
```

Open http://localhost:5173. API: http://localhost:8000/docs.

Redis is used for async provisioning workers. For a quick UI walkthrough, the API and frontend are enough; start Redis locally (`redis-server`) if you want background jobs to complete.

### 5. Try the demo

On the login screen, pick a seeded identity (no password):

| User | What to explore |
|------|-----------------|
| **Jordan Staff** | Platform analytics, create org |
| **Marcus Admin** | Labs, members, tools, audit |
| **Dave Okonkwo** | Manager vs Contributor by lab; multi-org |
| **Eve Nguyen** | Pending Simulation onboarding (after reset) |

Reset to a clean demo state anytime:

```bash
make demo-reset
```

### Troubleshooting

| Problem | Fix |
|---------|-----|
| Port 5173 or 8000 in use | Stop the other process or change ports in `docker-compose.yml` / `vite.config.ts` |
| `make setup-db` fails | Ensure Postgres is running; on macOS: `brew services start postgresql@16` |
| Docker build slow/fails | Ensure Docker Desktop is running; retry `make up` |
| Blank login / API errors | Check API at http://localhost:8000/docs; with Docker, run `make logs` |
| Old demo data | `make demo-reset` |

## Docs (point here in Q&A)

| Doc | What it covers |
|-----|----------------|
| [docs/PRD.md](docs/PRD.md) | Product requirements |
| [docs/DESIGN.md](docs/DESIGN.md) | Engineering design (with implementation notes) |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Local hosting, tenancy, roles, tools, GW, onboarding diagrams |
| [docs/SCHEMA.md](docs/SCHEMA.md) | Relational database schema |
| [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) | Short live rehearsal walkthrough |
| [docs/VIDEO_SCRIPT.md](docs/VIDEO_SCRIPT.md) | Filmed video demo script (VO + click paths) |
| [docs/LIVE_DEMO.md](docs/LIVE_DEMO.md) | Codespaces + Render hosting |
| [docs/erd.png](docs/erd.png) | ERD image (see SCHEMA for newer tables) |

## Architecture: Role Model (PRD correction)

**Intentional correction from earlier EDD implementation:** The PRD scopes Admin to the **organization** and Manager/Contributor to **labs**. Operational roles live on `LabMembership.lab_role` (`MANAGER` | `CONTRIBUTOR`); `OrganizationMembership.org_role` is only `ADMIN` | `MEMBER`.

- **Admin** — org-level: settings, labs, members, invitations, tool registry, audit, Google Workspace provision. Implicit visibility across labs.
- **Manager / Contributor** — resolved **per active lab**. Managers may launch all registered research tools **in labs they manage**; Contributors follow lab tool policies and requests.
- One person can be Manager in Lab A and Contributor in Lab B (Dave).
- Users can belong to multiple organizations with independent roles (Dave: Robotics + Biologics).
- **Staff** (`platform_role = STAFF`) is outside the tenant model — not grantable via org invites.

## Demo Users (4)

| User | Organizations & Roles |
|------|----------------------|
| Jordan Staff | Platform Staff |
| Marcus Admin | **Admin** @ Corvinus Robotics |
| Dave Okonkwo | **Manager** @ Perception · **Contributor** @ Simulation (Robotics) · **Admin** @ Biologics · **Manager** @ Analysis |
| Eve Nguyen | **Contributor** @ Perception (complete) · **Contributor** @ Simulation — **pending** scavenger-hunt onboarding after reset |

## Key Features

- Lab-scoped RBAC + org/lab switcher
- Admin Members + invitations (lab + role on invite)
- Contributor scavenger-hunt onboarding with lab starter tools
- Task board with valid transitions + optimistic locking (`version`)
- Research tools + Google Workspace tabs in App Launcher
- Async mock provisioning for tools and Google Workspace
- Audit log for org Admins
