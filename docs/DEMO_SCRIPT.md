# Live demo script (≈10–12 minutes)

Short rehearsal checklist. For a full **filmed** walkthrough with VO lines and click paths, use [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md).

Reset first: `make demo-reset`, then `make dev-api` and `make dev-web`. Open http://localhost:5173.

Docs for Q&A: [ARCHITECTURE.md](ARCHITECTURE.md) · [SCHEMA.md](SCHEMA.md) · [PRD.md](PRD.md) · [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md) · [LIVE_DEMO.md](LIVE_DEMO.md)

---

## Beat 1 — Admin invite (Marcus Admin)

1. Login as **Marcus Admin**.
2. **Members** → invite `someone@example.com` to **Simulation Lab** as **Contributor**.
3. Show invite link (UI + API log `[INVITE EMAIL]`). Point out org, lab, role on the accept page.

## Beat 2 — Contributor onboarding (Eve Nguyen)

1. Logout → login as **Eve Nguyen** (or accept a fresh invite).
2. Scavenger hunt: Continue on Dashboard → click highlighted **App Launcher** → Continue → click **Tasks** → checklist → **Finish onboarding**.
3. App Launcher: **Launch** Isaac Sim / Protocol Tool; **Request Access** on CVAT.

## Beat 3 — Dual lab roles (Dave Okonkwo)

1. Login as **Dave**.
2. Switch to **Perception Lab** → badge **Manager** → App Launcher shows Launch on tools; Dashboard can **Approve** Eve’s pending Isaac request if present.
3. Switch to **Simulation Lab** → badge **Contributor** → CVAT is Request (not Launch). Say: privileges follow active lab.
4. Optional: switch to **Corvinus Biologics** — Dave is Admin there (multi-org).

## Beat 4 — Google Workspace (Marcus)

1. **Labs** → Provision Workspace on a lab if needed; wait ~3s for **ACTIVE**.
2. **App Launcher** → Google Workspace tab → open Drive / Calendar / Chat / Meet.
3. Note: shared lab infra, no per-user tool grant.

## Beat 5 — Tool registry + audit (Marcus)

1. **Tools** → register a new tool (category + URL).
2. **Audit Log** → show `invitation.created`, `onboarding.completed`, `tool_access.*`, `google_workspace.*`, `tool.created`.

---

## Avoid on stage

- Don’t try to create tasks as Admin (correctly forbidden).
- Don’t cold-provision GW without saying you’ll wait a few seconds.
- Jordan Staff only if asked about platform-level org creation (requires admin invite email).
