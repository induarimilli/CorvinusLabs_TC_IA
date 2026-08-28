# Corvinus Labs Multi-Tenant Lab Operations Portal

A full-stack demo of the Corvinus Labs internal operations portal — multi-tenant, RBAC-enforced, with async tool provisioning.

## Quick Start (Local — no Docker)

```bash
cd "/Users/induarimilli/Library/CloudStorage/OneDrive-andrew.cmu.edu/CorvinusLabs_Technical_Challenge "
make install && make setup-db
make dev-api   # terminal 1
make dev-web   # terminal 2
```

| Service | URL |
|---------|-----|
| **App** | http://localhost:5173 |
| **API docs** | http://localhost:8000/docs |

## Architecture: Role Model (PRD correction)

**Intentional correction from earlier EDD implementation:** The PRD scopes Admin to the **organization** and Manager/Contributor to **labs**. Operational roles now live on `LabMembership.lab_role` (`MANAGER` | `CONTRIBUTOR`), while `OrganizationMembership.org_role` is only `ADMIN` | `MEMBER`.

- **Admin** — org-level: settings, labs, members, invitations, tool registry, audit. Implicit access to all labs (no `LabMembership` required).
- **Manager / Contributor** — resolved **per lab** from `LabMembership.lab_role` for the lab being acted on.
- One person can be **Manager in Lab A** and **Contributor in Lab B** within the same org (Alice demo persona).
- Users can belong to **multiple organizations**, each with independent org-level and lab-level roles (Alice: two orgs; Dave: Admin in one org, Manager and Contributor in different labs of another).

Staff (`User.platform_role = STAFF`) remains a platform tier outside the tenant model.

## Demo Users

| User | Organizations & Roles |
|------|----------------------|
| Jordan Staff | Platform Staff |
| Marcus Admin | **Admin** @ Corvinus Robotics |
| Alice Chen | **Manager** @ Perception Lab (Robotics) · **Contributor** @ Analysis Lab (Biologics) |
| Carol Wu | **Contributor** @ Perception Lab (Robotics) |
| Dave Okonkwo | **Manager** @ Perception + **Contributor** @ Simulation (Robotics) · **Admin** @ Corvinus Biologics |

## Key Features

- **Admin task board** — lab switcher to view any lab's kanban
- **Members page** — org roster + per-lab role breakdown
- **Tool registry** — Admin registers tools via connector types (CVAT, Isaac Sim, Protocol Tool)
- **Invitations** — Admin-only; assigns lab role on accept
- **Google Workspace tab** — lab-scoped provisioning (Drive/Calendar/Chat/Meet), shared for all lab members; mock API hooks at `/google-workspace/{drive|calendar|chat|meet}/...`
- **Research tool connectors** — CVAT, Isaac Sim, Protocol Tool via connector API (`/tools/{id}/session`, `/tools/{id}/health`, `/tools/{id}/launch`)
- **Task detail** — read-only view → Edit → Save (single `task.updated` audit event)

## Reset Demo

```bash
make demo-reset
```

Runs migrations through `003` (lab roles + Google Workspace table).
