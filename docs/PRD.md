# Corvinus Labs Multi-Tenant Operations Portal

## Product Requirements Document

| | |
|---|---|
| **Status** | V1 Final Submission |
| **Product** | Corvinus Labs Portal |
| **Platform** | Responsive Web Application |
| **Primary Users** | Lab Owners, Lab Admins, Coordinators, Contributors, Viewers |

---

## 1. Overview

Corvinus Labs operates across multiple research labs that require access to different operational workflows, datasets, software tools, and Google Workspace resources.

The current challenge is that these workflows and tools can become fragmented across separate applications. The portal will provide a single operational entry point for managing users, coordinating work, connecting Google Workspace services, and launching lab tools.

The product is a **multi-tenant operational portal** in which each Lab is an isolated tenant. A user has one global identity but may belong to multiple Labs with different roles in each Lab.

The portal coordinates and launches external tools rather than attempting to replace them.

### Core Product Areas

1. **User Management & Onboarding**
2. **Task & Role Management**
3. **Google Ecosystem Integrations**
4. **App Launcher Hub**

> **Core principle:** Standardize the workflow before automating it.

The system should first establish clear ownership, permissions, workflows, and operational state before introducing additional automation.

---

# 2. Problem Statement

Researchers and operators need to move between identity management, task coordination, Google Workspace, and specialized laboratory tools.

Without a unified system, this creates several problems:

- Users may not know which tools they should have access to.
- Permissions can become difficult to reason about across Labs.
- Operational tasks can become disconnected from the tools required to complete them.
- Lab-specific resources can become mixed together.
- New team members need a consistent onboarding process.
- Integrations may fail independently of the underlying operational workflow.
- Adding another lab tool should not require rebuilding the application.

The portal addresses these problems by establishing a common operational layer across Labs.

---

# 3. Goals

## P0 Goals

### G1 — Establish Secure Multi-Tenancy

Users must only access resources belonging to Labs they are members of.

### G2 — Create a Unified Operational Workflow

Users should be able to discover their work, understand its state, and access the tools required to complete it.

### G3 — Standardize User Onboarding

New members should receive a clear onboarding checklist after joining a Lab.

### G4 — Establish Role-Based Access Control

Permissions must be determined by the user's role within the active Lab.

### G5 — Create a Unified Tool Launcher

Users should have a single place to access permitted internal and external tools.

### G6 — Make Integrations Resilient

External integration failures should not destroy successful portal operations.

---

# 4. Non-Goals

The portal will **not**:

- Replace Isaac Sim.
- Replace CVAT.
- Replace the Corvinus Labs Protocol Tool.
- Replace Google Workspace applications.
- Implement a full project-management platform.
- Implement task dependencies.
- Implement threaded task comments.
- Implement @mentions.
- Implement attachments as a general task feature.
- Implement a Kanban board.
- Automatically transition task stages.
- Automatically assign tasks.
- Provide a native mobile application.
- Build a generalized platform-admin system.

These capabilities may be considered after V1.

---

# 5. Users & Personas

## Owner

Responsible for overall Lab ownership and critical administrative actions.

**Primary needs**

- Manage Lab ownership.
- Manage administrators.
- Manage members.
- Configure integrations.
- Configure tools.
- Maintain operational visibility.

## Lab Admin

Responsible for Lab-level administration.

**Primary needs**

- Manage members and roles.
- Configure integrations.
- Configure tools.
- View operational activity.
- Manage tasks.

## Coordinator

Responsible for coordinating operational work.

**Primary needs**

- Create tasks.
- Assign tasks.
- Reassign tasks.
- Track pipeline progress.
- Invite members.

## Contributor

Responsible for executing assigned work.

**Primary needs**

- View assigned work.
- Update assigned tasks.
- Launch relevant tools.
- Complete onboarding.

## Viewer

Read-only participant.

**Primary needs**

- View permitted Lab information.
- View tasks.
- Launch permitted tools.

---

# 6. Core Product Model

The system follows this relationship:

```text
User → Membership → Lab → Role
```

A **User** is a global identity.

A **Membership** determines:

- Which Lab the user belongs to.
- Which role they have in that Lab.
- Whether their membership is active.

A user may therefore have different roles in different Labs.

### Example

| User | Robotics Lab | Perception Lab |
|---|---|---|
| User A | Lab Admin | Viewer |
| User B | Contributor | Coordinator |
| User C | Viewer | Contributor |

Changing the active Lab changes the user's effective permissions and accessible resources.

> **Requirement:** The multi-tenant model is a core product requirement.

---

# 7. Feature Requirements

## 7.1 User Management & Onboarding

### Authentication

V1 must support **Google Sign-In**.

Authentication establishes the user's global identity.

Authentication must **not** independently determine Lab access.

After authentication:

```text
Google Identity
      ↓
    User
      ↓
 Memberships
      ↓
  Active Lab
      ↓
     Role
      ↓
 Permissions
```

If a user has no Lab membership, the system should clearly explain that an invitation is required.

---

## 7.2 Lab Switching

Users with multiple memberships must be able to switch their active Lab.

Switching Labs changes:

- Dashboard
- Tasks
- Members
- Roles
- Tools
- Integration configuration
- Lab settings

A user with one Lab should enter that Lab directly.

The interface must support an arbitrary number of Lab memberships rather than hard-coding a two-Lab experience.

---

## 7.3 Roles & Permissions

V1 uses five roles:

1. Owner
2. Lab Admin
3. Coordinator
4. Contributor
5. Viewer

Permissions are Lab-scoped.

### Permission Matrix

| Capability | Owner | Lab Admin | Coordinator | Contributor | Viewer |
|---|:---:|:---:|:---:|:---:|:---:|
| View dashboard/tasks | ✓ | ✓ | ✓ | ✓ | ✓ |
| Launch permitted tools | ✓ | ✓ | ✓ | ✓ | ✓ |
| Create tasks | ✓ | ✓ | ✓ | ✓ | — |
| Update assigned tasks | ✓ | ✓ | ✓ | ✓ | — |
| Assign/reassign tasks | ✓ | ✓ | ✓ | — | — |
| Update/delete any task | ✓ | ✓ | ✓ | — | — |
| Invite members | ✓ | ✓ | ✓ | — | — |
| Change roles | ✓ | ✓ | — | — | — |
| Remove members | ✓ | ✓ | — | — | — |
| Configure tools | ✓ | ✓ | — | — | — |
| Connect/revoke integrations | ✓ | ✓ | — | — | — |
| Edit onboarding | ✓ | ✓ | — | — | — |
| View audit log | ✓ | ✓ | — | — | — |
| Transfer ownership/delete Lab | ✓ | — | — | — | — |

> **Security requirement:** Permissions must be enforced server-side.

---

# 8. Invitation Requirements

Coordinators and higher can invite members.

### Invitation Flow

1. Enter email.
2. Select Lab role.
3. Generate invitation.
4. Send/share invitation.
5. User validates invitation.
6. Membership is created.
7. Onboarding checklist begins.

Invitations must be:

- Single-use.
- Time-limited.
- Lab-specific.
- Role-specific.

Consumed invitations cannot be reused.

Expired invitations must be rejected.

An invitation cannot be modified to grant access to another Lab.

---

# 9. Onboarding

Every newly created membership receives an onboarding checklist.

### Minimum Checklist

1. Complete profile.
2. Review Lab tools.
3. Complete first assigned task.

The checklist remains visible until complete.

A future version may support role-specific onboarding tracks.

---

# 10. Task Management

Authorized users can:

- Create tasks.
- Edit tasks.
- Assign tasks.
- Reassign tasks.
- Change status.
- Change pipeline stage.
- Set priority.
- Set due date.
- Filter tasks.
- View task history.

Tasks are Lab-scoped.

## Statuses

| Status |
|---|
| Backlog |
| In Progress |
| Blocked |
| In Review |
| Done |
| Cancelled |

**Cancelled** can be reached from any state.

## Pipeline

| Stage |
|---|
| Collection |
| Processing |
| Annotation |
| Training |
| UX |

Pipeline stage and task status are separate concepts.

**Example**

```text
Pipeline: Annotation
Status:   Blocked
```

---

# 11. Task-to-Tool Connections

V1 tasks may contain a destination within a tool.

### Example

| Field | Value |
|---|---|
| **Task** | Annotate dataset 042 |
| **Pipeline** | Annotation |
| **Tool** | CVAT |
| **Target** | CVAT Job #184 |
| **Action** | Open CVAT Job |

The portal therefore connects operational intent with the tool required to execute the work.

---

# 12. Task History

Important mutations create immutable history records.

### History Records

Each record contains:

- Actor.
- Timestamp.
- Changed field.
- Previous value.
- New value.

At minimum, history must capture:

- Status changes.
- Reassignments.
- Edits.

> **Requirement:** History is append-only.

---

# 13. Google Workspace Integrations

The portal supports:

- Google Drive
- Google Calendar
- Google Chat
- Google Meet

All four integrations must have mock implementations.

### Mock Capabilities

| Integration | Mock Workflow |
|---|---|
| Google Drive | Attach file to task |
| Google Calendar | Schedule review meeting |
| Google Chat | Post task event |
| Google Meet | Generate meeting link |

Mock integrations must be visibly labelled.

---

# 14. Google Calendar V1

Calendar is the primary live Google integration.

### Requirements

- Google OAuth consent.
- Authorization-code exchange.
- Per-Lab token storage.
- Access-token expiration handling.
- Refresh-token handling.
- Connect/revoke functionality.
- Create review meeting.
- Add Lab members as guests.
- Associate resulting event with task.

> **Credential ownership:** Google credentials are owned by the Lab rather than by individual users.

---

# 15. App Launcher

The App Launcher provides one location for accessing permitted operational tools.

## Initial Tools

### Robotics Lab

- Isaac Sim
- Protocol Tool
- Google Drive
- Google Calendar

### Perception Lab

- CVAT
- Protocol Tool
- Google Drive
- Google Calendar

Tool visibility depends on:

```text
Active Lab
    +
Membership
    +
Role
    +
Tool Configuration
```

Tools are registry-driven so adding a new tool does not require modifying the launcher UI.

---

# 16. Launch Types

The launcher supports four launch types.

## Web

Opens a web application.

## Deep Link

Opens a specific resource inside a tool.

## Desktop

Displays:

- Host
- Version
- Launch command
- Setup instructions
- Documentation

## Streamed

Reserved for browser-accessible streamed applications.

> **UX requirement:** The UI must never make an unavailable launch action appear clickable.

---

# 17. Security Requirements

> **Tenant isolation is a release-blocking requirement.**

Every tenant-owned request must validate:

1. Authentication.
2. Lab membership.
3. Required permission.

The server must **not** trust a Lab ID supplied by the client.

Attempting to manipulate a Lab ID in any of the following:

- URL
- Request body
- Query parameter
- Resource ID

must not expose another Lab's data.

The system must explicitly test forged Lab identifiers.

---

# 18. Reliability Requirements

External integration failure must not roll back the underlying portal operation.

### Example: Resilient Task Creation

```text
Create Task
     ↓
Task saved
     ↓
Calendar request fails
     ↓
Task remains saved
     ↓
Integration error shown
     ↓
User can retry
```

This keeps internal state authoritative and external services recoverable.

---

# 19. Seeded Demo Environment

The V1 application must ship with reproducible seed data.

At minimum, the seed environment must contain:

- Two Labs.
- Multiple users.
- Different memberships.
- Different roles.
- Different tasks.
- Different pipeline stages.
- Different tools.

The seed environment must exercise the **real database and authorization models** rather than hardcoded frontend conditions.

---

# 20. Success Criteria

V1 is successful when an evaluator can:

1. Sign in using Google.
2. Belong to multiple Labs.
3. Switch Labs.
4. Observe different permissions.
5. Invite another user.
6. Complete onboarding.
7. Create and assign a task.
8. Move a task through its workflow.
9. View task history.
10. Launch a Lab-specific tool.
11. Trigger Google Workspace mock workflows.
12. Connect Google Calendar.
13. Create a Calendar review meeting.
14. Observe that Lab credentials remain isolated.
15. Attempt cross-Lab access and receive rejection.
16. Add a tool through configuration without modifying launcher UI.

---

# 21. MVP → V1 Strategy

The MVP should first establish the foundational operational model.

### MVP

- Multi-tenancy
- Authentication abstraction
- Roles
- Tasks
- Pipeline
- Mock integrations
- Registry-driven tools

### V1

V1 then adds:

- Google Sign-In
- Five-role permissions
- Invitations
- Real onboarding
- Role management
- Ownership
- Append-only history
- Task-to-tool links
- Live Calendar integration
- Per-Lab OAuth
- Searchable launcher

This keeps the architecture demonstrable even when external APIs are unavailable.
