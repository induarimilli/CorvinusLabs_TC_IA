"""PRD Section 43 + scrutiny-list verification. Run with API up: python3 scripts/verify_prd.py"""

import asyncio
import json
import subprocess
import uuid
from datetime import datetime, timedelta, timezone

import httpx

BASE = "http://localhost:8000"
IDS = {
    "jordan": "11111111-1111-1111-1111-111111111101",
    "marcus": "11111111-1111-1111-1111-111111111102",
    "alice": "11111111-1111-1111-1111-111111111103",
    "carol": "11111111-1111-1111-1111-111111111104",
    "dave": "11111111-1111-1111-1111-111111111105",
    "org_robotics": "22222222-2222-2222-2222-222222222201",
    "org_biologics": "22222222-2222-2222-2222-222222222202",
    "lab_perception": "33333333-3333-3333-3333-333333333301",
    "lab_simulation": "33333333-3333-3333-3333-333333333302",
    "lab_analysis": "33333333-3333-3333-3333-333333333304",
}

results: list[dict] = []


def record(claim: str, how: str, result: str, evidence: str, fix: str = "No"):
    results.append({"claim": claim, "how": how, "result": result, "evidence": evidence, "fix": fix})


async def login(client: httpx.AsyncClient, user_id: str) -> dict:
    r = await client.post(f"{BASE}/auth/demo-login", json={"user_id": user_id})
    r.raise_for_status()
    return r.json()


def hdr(token: str, org_id: str, lab_id: str | None = None) -> dict:
    h = {"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}
    if lab_id:
        h["X-Lab-Id"] = lab_id
    return h


def psql(sql: str) -> str:
    cmd = ["psql", "-h", "localhost", "-U", "corvinus", "-d", "corvinus", "-t", "-A", "-c", sql]
    env = {"PGPASSWORD": "corvinus"}
    return subprocess.check_output(cmd, env={**subprocess.os.environ, **env}, text=True).strip()


async def main() -> None:
    async with httpx.AsyncClient(timeout=15) as c:
        # --- Auth ---
        r = await c.post(f"{BASE}/auth/demo-login", json={"user_id": IDS["marcus"]})
        if r.status_code == 200 and r.json().get("access_token"):
            record("Auth: valid login succeeds", "POST /auth/demo-login as Marcus", "Verified working",
                   f"200, token length={len(r.json()['access_token'])}")
        else:
            record("Auth: valid login succeeds", "POST /auth/demo-login", "Verified broken", r.text, "Yes")

        bad = await c.post(f"{BASE}/auth/demo-login", json={"user_id": str(uuid.uuid4())})
        if bad.status_code in (401, 404) and "access_token" not in bad.text:
            record("Auth: invalid credentials fail", "POST demo-login with random UUID", "Verified working",
                   f"status={bad.status_code}, no token in body")
        else:
            record("Auth: invalid credentials fail", "POST demo-login random UUID", "Verified broken", bad.text, "Yes")

        no_auth = await c.get(f"{BASE}/auth/me")
        if no_auth.status_code == 401:
            record("Auth: no token → no protected data", "GET /auth/me without Authorization", "Verified working",
                   f"status={no_auth.status_code}")
        else:
            record("Auth: no token → no protected data", "GET /auth/me", "Verified broken", no_auth.text, "Yes")

        # --- Tenant isolation ---
        marcus = await login(c, IDS["marcus"])
        mt = marcus["access_token"]
        cross = await c.get(
            f"{BASE}/organizations/{IDS['org_biologics']}/tasks",
            headers=hdr(mt, IDS["org_biologics"]),
        )
        if cross.status_code == 403:
            record("Tenant isolation: Org A user → Org B tasks rejected", "Marcus + X-Org-Biologics header",
                   "Verified working", f"403 {cross.json().get('error', {}).get('message', cross.text)}")
        else:
            record("Tenant isolation: Org A user → Org B tasks rejected", "Marcus → Biologics tasks",
                   "Verified broken", f"status={cross.status_code} body={cross.text[:200]}", "Yes")

        alice = await login(c, IDS["alice"])
        at = alice["access_token"]
        r = await c.get(
            f"{BASE}/organizations/{IDS['org_robotics']}/labs/{IDS['lab_perception']}/members",
            headers=hdr(at, IDS["org_robotics"], IDS["lab_perception"]),
        )
        if r.status_code == 200:
            names = [m["name"] for m in r.json()]
            record("Lab-scoped: Manager sees own lab members", "Alice → Perception lab members",
                   "Verified working", f"200, members={names}")
        else:
            record("Lab-scoped: Manager sees own lab members", "GET lab members", "Verified broken", r.text, "Yes")

        wrong_lab = await c.get(
            f"{BASE}/organizations/{IDS['org_robotics']}/labs/{IDS['lab_simulation']}/members",
            headers=hdr(at, IDS["org_robotics"], IDS["lab_perception"]),
        )
        # Alice is NOT in simulation lab - should be 403
        if wrong_lab.status_code == 403:
            record("Lab-scoped: Manager blocked from other lab members", "Alice → Simulation lab members",
                   "Verified working", f"403")
        else:
            record("Lab-scoped: Manager blocked from other lab members", "Alice → Simulation",
                   "Partially working" if wrong_lab.status_code == 200 else "Verified broken",
                   f"status={wrong_lab.status_code} (Alice is Manager only in Perception)", "Maybe")

        # --- Invitations ---
        roles = (await c.get(f"{BASE}/organizations/{IDS['org_robotics']}/roles", headers=hdr(mt, IDS["org_robotics"]))).json()
        contrib_role = next(r for r in roles if r["name"] == "Contributor")
        inv = await c.post(
            f"{BASE}/organizations/{IDS['org_robotics']}/invitations",
            headers=hdr(mt, IDS["org_robotics"]),
            json={"email": "verify-prd@test.dev", "role_id": contrib_role["id"], "lab_id": IDS["lab_perception"], "expires_in_days": 7},
        )
        if inv.status_code == 200:
            token = inv.json()["token"]
            row = psql(
                f"SELECT organization_id, role_id, expires_at > now(), status FROM invitations WHERE token = '{token}'"
            )
            record("Invitations: Admin invite creates correct row", "POST invite + psql SELECT",
                   "Verified working" if "PENDING" in row else "Partially working",
                   f"db row: {row}")
            invite_link = inv.json().get("invite_link", "")
            accept = await c.post(f"{BASE}/invitations/{token}/accept", json={"name": "Verify User"})
            if accept.status_code == 200:
                mem = psql(f"SELECT count(*) FROM organization_memberships om JOIN users u ON u.id=om.user_id WHERE u.email='verify-prd@test.dev'")
                record("Invite link works end-to-end", f"POST accept on {invite_link[:50]}...", "Verified working",
                       f"accept 200, memberships={mem}")
            else:
                record("Invite link works end-to-end", "POST accept", "Verified broken", accept.text, "Yes")

            # Expired invitation
            psql(f"UPDATE invitations SET expires_at = now() - interval '1 day' WHERE token = '{token}' AND status='PENDING'")
            # create fresh expired invite
            inv2 = await c.post(
                f"{BASE}/organizations/{IDS['org_robotics']}/invitations",
                headers=hdr(mt, IDS["org_robotics"]),
                json={"email": "expired-prd@test.dev", "role_id": contrib_role["id"], "expires_in_days": 1},
            )
            tok2 = inv2.json()["token"]
            psql(f"UPDATE invitations SET expires_at = now() - interval '1 hour' WHERE token = '{tok2}'")
            exp = await c.post(f"{BASE}/invitations/{tok2}/accept", json={"name": "Expired User"})
            if exp.status_code == 409:
                record("Invitations: expired invite rejected", "UPDATE expires_at past + POST accept", "Verified working",
                       f"409 {exp.json().get('error', {}).get('message', '')}")
            else:
                record("Invitations: expired invite rejected", "expired accept", "Verified broken", exp.text, "Yes")
        else:
            record("Invitations: Admin invite creates correct row", "POST invite", "Verified broken", inv.text, "Yes")

        # --- Role management ---
        members = (await c.get(f"{BASE}/organizations/{IDS['org_robotics']}/members/details", headers=hdr(mt, IDS["org_robotics"]))).json()
        carol_mem = next(x for x in members if x["user"]["email"] == "carol@corvinus.dev")
        manager_role = next(r for r in roles if r["name"] == "Manager")
        patch = await c.patch(
            f"{BASE}/organizations/{IDS['org_robotics']}/members/{carol_mem['membership']['id']}",
            headers=hdr(mt, IDS["org_robotics"]),
            json={"role_id": manager_role["id"]},
        )
        if patch.status_code == 200:
            new_role = psql(
                f"SELECT r.name FROM organization_memberships om JOIN roles r ON r.id=om.role_id WHERE om.id='{carol_mem['membership']['id']}'"
            )
            record("Role mgmt: Admin changes role", "PATCH member role + psql", "Verified working",
                   f"role now={new_role}")
            # revert
            contrib_id = contrib_role["id"]
            await c.patch(
                f"{BASE}/organizations/{IDS['org_robotics']}/members/{carol_mem['membership']['id']}",
                headers=hdr(mt, IDS["org_robotics"]),
                json={"role_id": contrib_id},
            )
        else:
            record("Role mgmt: Admin changes role", "PATCH member", "Verified broken", patch.text, "Yes")

        carol = await login(c, IDS["carol"])
        ct = carol["access_token"]
        deny = await c.patch(
            f"{BASE}/organizations/{IDS['org_robotics']}/members/{carol_mem['membership']['id']}",
            headers=hdr(ct, IDS["org_robotics"]),
            json={"role_id": manager_role["id"]},
        )
        if deny.status_code == 403:
            record("Role mgmt: Contributor cannot change roles", "Carol PATCH member role", "Verified working", "403")
        else:
            record("Role mgmt: Contributor cannot change roles", "Carol PATCH", "Verified broken", deny.text, "Yes")

        # --- Tasks ---
        alice_mgr = await login(c, IDS["alice"])
        ah = hdr(alice_mgr["access_token"], IDS["org_robotics"], IDS["lab_perception"])
        create = await c.post(
            f"{BASE}/organizations/{IDS['org_robotics']}/tasks",
            headers=ah,
            json={"title": "PRD verify task", "lab_id": IDS["lab_perception"], "status": "BACKLOG", "priority": "HIGH"},
        )
        if create.status_code == 200:
            t = create.json()
            ok = t["organization_id"] == IDS["org_robotics"] and t["lab_id"] == IDS["lab_perception"]
            record("Tasks: Manager create → correct org/lab", "POST task as Alice Manager", "Verified working" if ok else "Verified broken",
                   f"org={t['organization_id']}, lab={t['lab_id']}")
            task_id = t["id"]
        else:
            record("Tasks: Manager create → correct org/lab", "POST task", "Verified broken", create.text, "Yes")
            task_id = None

        # Contributor assign (PRD Section 43)
        carol_h = hdr(ct, IDS["org_robotics"], IDS["lab_perception"])
        if task_id:
            tasks = (await c.get(f"{BASE}/organizations/{IDS['org_robotics']}/tasks", headers=carol_h)).json()
            target = next((x for x in tasks if x["id"] == task_id), t)
            assign = await c.patch(
                f"{BASE}/tasks/{task_id}",
                headers=carol_h,
                json={"assignee_id": IDS["dave"], "version": target["version"]},
            )
            if assign.status_code == 200 and assign.json()["assignee_id"] == IDS["dave"]:
                db_assignee = psql(f"SELECT assignee_id FROM tasks WHERE id='{task_id}'")
                record("Tasks: Contributor assigns task (PRD §43)", "Carol PATCH assignee_id", "Verified working",
                       f"assignee_id={assign.json()['assignee_id']}, db={db_assignee}")
            else:
                record("Tasks: Contributor assigns task (PRD §43)", "Carol PATCH assignee", "Verified broken",
                       f"status={assign.status_code} {assign.text[:200]}", "Yes")

            # Contributor edit unassigned task in lab (not own) - PRD full lab CRUD
            other = next((x for x in tasks if x.get("assignee_id") != IDS["carol"] and x["lab_id"] == IDS["lab_perception"]), None)
            if other:
                edit = await c.patch(
                    f"{BASE}/tasks/{other['id']}",
                    headers=carol_h,
                    json={"priority": "URGENT", "version": other["version"]},
                )
                if edit.status_code == 200:
                    record("Contributor full lab task CRUD (not assignee-only)", "Carol PATCH priority on lab task",
                           "Verified working", f"priority={edit.json()['priority']}")
                else:
                    record("Contributor full lab task CRUD", "Carol PATCH other task", "Verified broken", edit.text, "Yes")

            # Contributor blocked on other lab
            sim_tasks = [x for x in (await c.get(f"{BASE}/organizations/{IDS['org_robotics']}/tasks", headers=hdr(ct, IDS["org_robotics"]))).json()
                         if x["lab_id"] == IDS["lab_simulation"]]
            if sim_tasks:
                blocked = await c.patch(
                    f"{BASE}/tasks/{sim_tasks[0]['id']}",
                    headers=carol_h,
                    json={"priority": "LOW", "version": sim_tasks[0]["version"]},
                )
                if blocked.status_code == 403:
                    record("Contributor blocked outside own lab", "Carol PATCH Simulation lab task", "Verified working", "403")
                else:
                    record("Contributor blocked outside own lab", "Carol PATCH sim task", "Verified broken", blocked.text, "Yes")

            # Cross-org task access
            bio_task = psql(f"SELECT id FROM tasks WHERE organization_id='{IDS['org_biologics']}' LIMIT 1")
            if bio_task:
                cross_task = await c.patch(
                    f"{BASE}/tasks/{bio_task}",
                    headers=hdr(mt, IDS["org_robotics"]),
                    json={"title": "hack", "version": 1},
                )
                if cross_task.status_code in (403, 404):
                    record("Tasks: user outside task org denied", "Marcus PATCH Biologics task with Robotics header",
                           "Verified working", f"status={cross_task.status_code}")
                else:
                    record("Tasks: user outside task org denied", "cross-org PATCH", "Verified broken", cross_task.text, "Yes")

            # updated_at 500 regression
            ok_count = 0
            ver = assign.json()["version"] if assign.status_code == 200 else target["version"]
            for i in range(3):
                r = await c.patch(f"{BASE}/tasks/{task_id}", headers=carol_h,
                                  json={"priority": ["HIGH", "MEDIUM", "LOW"][i], "version": ver})
                if r.status_code == 200:
                    ver = r.json()["version"]
                    ok_count += 1
            record("Fixed async updated_at 500 bug", f"3 consecutive PATCHes on task {task_id}", 
                   "Verified working" if ok_count == 3 else "Verified broken",
                   f"{ok_count}/3 succeeded")

        # --- Tool access ---
        tools = (await c.get(f"{BASE}/organizations/{IDS['org_robotics']}/tools", headers=ah)).json()
        tool_id = tools[1]["id"] if len(tools) > 1 else tools[0]["id"]
        before = psql("SELECT count(*) FROM tool_access")
        grant = await c.post(
            f"{BASE}/tools/{tool_id}/access",
            headers=ah,
            json={"user_id": IDS["dave"], "access_level": "view"},
        )
        after = psql("SELECT count(*) FROM tool_access")
        if grant.status_code == 200 and int(after) > int(before):
            record("Tool access: Manager grant creates record", "POST /tools/{id}/access + psql count",
                   "Verified working", f"status=REQUESTED id={grant.json()['id']}")
            audit = psql(
                f"SELECT action, actor_user_id, organization_id FROM audit_events WHERE entity_id='{grant.json()['id']}' ORDER BY created_at DESC LIMIT 1"
            )
            if "tool_access.granted" in audit:
                record("Audit: tool grant creates event", "psql audit_events", "Verified working", audit)
            else:
                record("Audit: tool grant creates event", "psql", "Verified broken", audit or "no row", "Yes")
        else:
            record("Tool access: Manager grant creates record", "POST grant", "Verified broken", grant.text, "Yes")

        launch_block = await c.post(f"{BASE}/tools/{tool_id}/launch", headers=hdr(ct, IDS["org_robotics"]))
        if launch_block.status_code == 403:
            record("Tool access: Contributor without access blocked on launch", "Carol POST launch (no ACTIVE access)",
                   "Verified working", "403")
        else:
            record("Tool access: Contributor without access blocked", "POST launch", "Partially working",
                   f"status={launch_block.status_code} (Carol may have CVAT ACTIVE from seed)", "Maybe")

        # --- Alice org switch data isolation ---
        bio_h = hdr(at, IDS["org_biologics"], IDS["lab_analysis"])
        rob_tasks = (await c.get(f"{BASE}/organizations/{IDS['org_robotics']}/tasks", headers=hdr(at, IDS["org_robotics"]))).json()
        bio_tasks = (await c.get(f"{BASE}/organizations/{IDS['org_biologics']}/tasks", headers=bio_h)).json()
        rob_ids = {t["id"] for t in rob_tasks}
        bio_ids = {t["id"] for t in bio_tasks}
        leak = rob_ids & bio_ids
        if not leak and all(t["organization_id"] == IDS["org_biologics"] for t in bio_tasks):
            record("OrgLabSwitcher: Alice org switch changes task data", "GET tasks Robotics vs Biologics as Alice",
                   "Verified working", f"robotics={len(rob_tasks)} biologics={len(bio_tasks)} overlap=0")
        else:
            record("OrgLabSwitcher: no cross-org leak", "Alice tasks both orgs", "Verified broken", f"overlap={leak}", "Yes")

    print(json.dumps(results, indent=2))
    broken = [r for r in results if r["result"] in ("Verified broken", "Partially working")]
    print(f"\nSUMMARY: {len(results)} checks, {len(broken)} issues")
    for r in broken:
        print(f"  - {r['claim']}: {r['result']} — {r['evidence'][:120]}")


if __name__ == "__main__":
    asyncio.run(main())
