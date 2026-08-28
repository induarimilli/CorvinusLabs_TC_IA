> **Implementation note (this codebase):** The portal intentionally corrects the earlier EDD framing where Lab was the sole tenant boundary for Admin. **Admin is organization-scoped** (`OrganizationMembership.org_role = ADMIN`). **Manager and Contributor are lab-scoped** (`LabMembership.lab_role`). Multi-org membership is supported. See [ARCHITECTURE.md](ARCHITECTURE.md) and [SCHEMA.md](SCHEMA.md).

---

**Engineering Design Document**

Multi-Tenant Lab Operations Portal

*Document 2 of 2 --- companion to the Product Requirements Document*

  ----------------------- -----------------------------------------------
  Product                 Corvinus Labs --- Multi-Tenant Lab Operations
                          Portal

  Document owner          Engineering

  Status                  Proposed

  Source of truth         Document 1 --- Product Requirements Document

  Scope target            MVP --- modular monolith
  ----------------------- -----------------------------------------------

1\. Purpose of This Document

The PRD defines what the product needs to do --- the problems, users,
workflows, permissions, and acceptance criteria. This document defines
how it gets built: the technology choices, the system architecture, the
data model, and the security mechanisms that implement those
requirements.

This is written for an MVP delivered on a short timeline. It favors a
small number of decisions explained clearly over an exhaustive
specification of every table and endpoint. Anything not dictated by the
PRD is called out explicitly as an engineering decision, so scope is
never confused with requirement.

2\. Architecture at a Glance

The system is built as a modular monolith: one backend application, one
database, one background worker. The PRD requires clear boundaries
between domains --- authentication, organizations, tasks, tools --- but
it does not require those domains to scale or deploy independently. A
monolith with well-defined internal modules satisfies the requirement
with far less operational overhead than microservices.

  --------------------------------------------------------------------------
  **Layer**        **Choice**            **Reason**
  ---------------- --------------------- -----------------------------------
  Frontend         React + TypeScript    Role-aware dashboards, forms, and
                                         task boards

  Backend          Python + FastAPI      Async support, strong request
                                         validation, fast to build

  Database         PostgreSQL            Relational data with real foreign
                                         keys and transactions

  Authentication   Supabase Auth         Handles identity; the app handles
                                         permissions

  Queue / cache    Redis                 One piece of infrastructure, two
                                         jobs

  File storage     S3-compatible object  Keeps large binary files out of the
                   storage               database
  --------------------------------------------------------------------------

+-----------------------------------------------------------------------+
| Browser (React)                                                       |
|                                                                       |
| \|                                                                    |
|                                                                       |
| v                                                                     |
|                                                                       |
| FastAPI \-\--\> Auth / RBAC layer                                     |
|                                                                       |
| \|                                                                    |
|                                                                       |
| +\-\--\> Domain modules (Tasks, Labs, Tools, Members)                 |
|                                                                       |
| \| \|                                                                 |
|                                                                       |
| \| v                                                                  |
|                                                                       |
| \| PostgreSQL (source of truth)                                       |
|                                                                       |
| \|                                                                    |
|                                                                       |
| +\-\--\> Redis (queue) \-\--\> Worker \-\--\> External tools (CVAT,   |
| Isaac Sim, Google)                                                    |
+-----------------------------------------------------------------------+

3\. The Decisions That Actually Matter

Most of this document is the working-out. These five choices are the
architecture --- everything else exists to support them.

3.1 Memberships, not a role field on the user

A User is a single global identity. Organization membership --- and the
role that comes with it --- lives on a separate OrganizationMembership
record. This is what allows the same person to be a Manager in one
organization and a Contributor in another, and it\'s the foundation the
authentication, authorization, and isolation design all build on.

3.2 Tenant isolation is enforced on the server, at every layer

Every query, cache key, file path, and background job carries the
organization ID and re-validates it. The frontend can be trusted to
shape a good user experience; it is never trusted to enforce a security
boundary.

3.3 Authorization is deny-by-default and resource-scoped

Role alone is not enough to grant access. A request is only authorized
if the caller has an active membership, holds the right permission, and
the resource in question actually belongs to their organization --- and,
for lab-scoped work, their lab. Seniority in the role hierarchy never
substitutes for that check.

3.4 One connector interface for every external tool

CVAT, Isaac Sim, and Google Workspace all implement the same
ToolConnector shape rather than being special-cased throughout the
codebase. Adding a new tool later means writing a new connector, not
touching core task or user logic.

3.5 Tool provisioning is asynchronous and stateful

Granting access to an external tool doesn\'t mean the access exists yet
--- it means a request has been recorded. A background worker attempts
the provisioning and the record moves through explicit states, including
a real FAILED state, instead of the system pretending every grant
succeeds instantly.

4\. Multi-Tenant Isolation

This is the most important mechanism in the system, so it\'s worth
walking through concretely rather than describing abstractly.

Every authenticated request resolves four things before any business
logic runs:

+-----------------------------------------------------------------------+
| currentUser who is making this request                                |
|                                                                       |
| currentOrganization which tenant they claim to act in                 |
|                                                                       |
| currentMembership do they actually belong to that org?                |
|                                                                       |
| currentRole what are they allowed to do there?                        |
+-----------------------------------------------------------------------+

If currentMembership doesn\'t exist, or isn\'t active, the request is
denied before it reaches any domain logic.

The attack case

A user who belongs to Organization A sends:

  -----------------------------------------------------------------------
  GET /organizations/B/tasks

  -----------------------------------------------------------------------

Authentication succeeds --- they are a real, logged-in user. But the
backend then looks up their membership in Organization B, finds none,
and returns 403 before the tasks table is ever queried. Nothing about
this depends on the frontend hiding a link or a button.

The same pattern is repeated everywhere tenant data is touched:

- **Database:** every tenant-owned table stores organization_id
  directly, even where it could be inferred through a parent record, so
  filtering is explicit rather than dependent on a join.

- **Cache:** keys are namespaced as org:{orgId}:tools, never a bare
  tools:{id}.

- **Background jobs:** job payloads carry organizationId, and the worker
  re-validates ownership rather than trusting the ID it was handed.

- **Files:** storage paths are namespaced by organization and lab, and
  download URLs are only issued after an authorization check.

5\. Data Model

The core entities and how they relate:

+-----------------------------------------------------------------------+
| User \--\< OrganizationMembership \>\-- Organization \--              |
| OrganizationSettings                                                  |
|                                                                       |
| \| \|                                                                 |
|                                                                       |
| \| v                                                                  |
|                                                                       |
| \| Role (org-scoped: Admin / Manager / Contributor)                   |
|                                                                       |
| \|                                                                    |
|                                                                       |
| +\--\< LabMembership \>\-- Lab \-- Organization                       |
|                                                                       |
| Organization \--\< Lab \--\< Task \--\< TaskComment                   |
|                                                                       |
| +\--\< TaskAttachment                                                 |
|                                                                       |
| Organization \--\< Tool \--\< ToolAccess \>\-- User                   |
|                                                                       |
| Organization \--\< Invitation                                         |
|                                                                       |
| Organization \--\< AuditEvent (append-only)                           |
|                                                                       |
| Organization \--\< Notification                                       |
+-----------------------------------------------------------------------+

A few constraints worth naming because they\'re what actually prevents
bad states:

- One active membership per user per organization (unique on user +
  organization).

- One membership per user per lab (unique on user + lab).

- No duplicate tool grants (unique on tool + user).

- Invitations are accepted with a conditional update --- WHERE status =
  \'PENDING\' AND expires_at \> NOW() --- so an expired or already-used
  invitation can\'t be double-processed, even under a race between two
  requests.

6\. Authorization Model

Permissions attach to roles; roles attach to membership --- never to the
user globally. In simplified form:

+-----------------------------------------------------------------------+
| def authorize(context, permission, resource=None):                    |
|                                                                       |
| if not context.currentMembership or context.currentMembership.status  |
| != \"ACTIVE\":                                                        |
|                                                                       |
| raise ForbiddenError()                                                |
|                                                                       |
| if not role_has_permission(context.currentRole, permission):          |
|                                                                       |
| raise ForbiddenError()                                                |
|                                                                       |
| if resource and resource.organization_id !=                           |
| context.currentOrganization.id:                                       |
|                                                                       |
| raise ForbiddenError()                                                |
|                                                                       |
| return True                                                           |
+-----------------------------------------------------------------------+

  -----------------------------------------------------------------------
  **Role**        **Scope**
  --------------- -------------------------------------------------------
  Admin           Organization and member management, all labs and tools,
                  audit access

  Manager         Full task and tool control within their own labs

  Contributor     Own work, tasks in their labs, tools they\'ve been
                  explicitly granted
  -----------------------------------------------------------------------

Being higher in the role hierarchy never bypasses the resource check ---
an Admin in Organization A still cannot touch Organization B\'s data.
Role and resource ownership are both required, every time.

7\. Task Lifecycle

+-----------------------------------------------------------------------+
| BACKLOG -\> TODO -\> IN_PROGRESS -\> DONE                             |
|                                                                       |
| \|                                                                    |
|                                                                       |
| v                                                                     |
|                                                                       |
| BLOCKED (returns to IN_PROGRESS)                                      |
+-----------------------------------------------------------------------+

Transitions are checked against an explicit allow-list rather than
accepting any status value. Concurrent edits use optimistic locking:
each task carries a version number, and if two people edit the same task
at once, the second write receives a conflict response instead of
silently overwriting the first.

8\. Tool Access --- Why It\'s Asynchronous

Granting access to CVAT or Isaac Sim can\'t be instant, because the
external system might be slow, rate-limited, or briefly unavailable.
Making the manager\'s request hang while that resolves would be poor UX
and a fragile design, so provisioning happens in the background.

+-----------------------------------------------------------------------+
| REQUESTED -\> PROVISIONING -\> ACTIVE                                 |
|                                                                       |
| \\-\> FAILED                                                          |
|                                                                       |
| ACTIVE -\> REVOKING -\> REVOKED                                       |
+-----------------------------------------------------------------------+

A manager\'s request creates a REQUESTED record; a queued job then calls
the tool\'s connector. Success moves the record to ACTIVE, failure moves
it to FAILED with a reason attached. The UI never claims access exists
until it actually does.

The ToolConnector interface is the same shape for every tool, but
capabilities differ --- Isaac Sim might only support launch() and
healthCheck(), while CVAT supports full provisioning and revocation. The
application checks what a connector supports before calling it, rather
than assuming.

9\. API Shape

A representative sample, not the full surface:

+-----------------------------------------------------------------------+
| POST /organizations/{orgId}/invitations create invite, queue email    |
|                                                                       |
| POST /invitations/{token}/accept validate + create memberships        |
|                                                                       |
| GET /organizations/{orgId}/tasks tenant-scoped list                   |
|                                                                       |
| POST /organizations/{orgId}/tasks create (validates lab + assignee    |
| are in-org)                                                           |
|                                                                       |
| PATCH /tasks/{taskId} state transition, optimistic lock               |
|                                                                       |
| POST /tools/{toolId}/access manager grants access, async provisioning |
|                                                                       |
| DELETE /tools/{toolId}/access/{userId} revoke, async                  |
+-----------------------------------------------------------------------+

Errors follow one consistent shape across every endpoint:

+-----------------------------------------------------------------------+
| {                                                                     |
|                                                                       |
| \"error\": {                                                          |
|                                                                       |
| \"code\": \"TOOL_ACCESS_DENIED\",                                     |
|                                                                       |
| \"message\": \"\...\",                                                |
|                                                                       |
| \"requestId\": \"\...\"                                               |
|                                                                       |
| }                                                                     |
|                                                                       |
| }                                                                     |
+-----------------------------------------------------------------------+

10\. Reliability, In Brief

- **Retries:** transient failures (timeouts, 429/502/503) are retried
  with backoff; permission and validation errors never are.

- **Idempotency:** provisioning jobs check current state before acting,
  so retrying a grant can\'t create a duplicate account on the external
  side.

- **Audit trail:** every meaningful mutation --- invitations, role
  changes, task changes, tool grants and revocations --- writes an
  append-only AuditEvent with actor, organization, action, resource, and
  timestamp, so "what happened" stays answerable even after a failure.

11\. Explicitly Out of Scope for This Build

Being direct about this is more useful than a document that implies
everything was built:

- No microservices, no Kubernetes, no message bus --- one process, one
  worker.

- No transactional outbox for job dispatch --- jobs are queued directly
  after the database commit; the first hardening step in a longer build.

- No dedicated caching layer beyond the queue --- caching is a later
  optimization, not a launch requirement.

- Google Calendar, Chat, and Meet integrations are stubbed behind the
  connector interface rather than fully implemented.

- No formal audit-retention policy, uptime SLA, or disaster-recovery
  runbook --- appropriate for a demo, not yet for production.

12\. Summary

+-----------------------------------------------------------------------+
| **The idea that ties it together**                                    |
|                                                                       |
| *Every request, resource, background job, and file has an explicit    |
| path back to its organization, and access is never granted by         |
| identity alone --- only by active, verified membership.*              |
+-----------------------------------------------------------------------+
