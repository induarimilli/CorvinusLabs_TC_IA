#!/usr/bin/env python3
"""User Stories Testing Pass — execute against live API, record evidence."""
from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

API = "http://127.0.0.1:8000"
ORG_R = "22222222-2222-2222-2222-222222222201"  # Robotics
ORG_B = "22222222-2222-2222-2222-222222222202"  # Biologics
LAB_PERC = "33333333-3333-3333-3333-333333333301"
LAB_SIM = "33333333-3333-3333-3333-333333333302"
LAB_ANAL = "33333333-3333-3333-3333-333333333304"
UID = {
    "marcus": "11111111-1111-1111-1111-111111111102",
    # Aliases: former Alice/Carol personas folded into Dave/Eve (4-user seed)
    "alice": "11111111-1111-1111-1111-111111111105",  # Dave — Manager @ Perception
    "carol": "11111111-1111-1111-1111-111111111106",  # Eve — Contributor @ Perception
    "dave": "11111111-1111-1111-1111-111111111105",
    "jordan": "11111111-1111-1111-1111-111111111101",
    "eve": "11111111-1111-1111-1111-111111111106",
}

results: list[dict] = []


def req(method, path, *, token=None, org=None, lab=None, body=None, raw=False):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if org:
        headers["X-Organization-Id"] = org
    if lab:
        headers["X-Lab-Id"] = lab
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(f"{API}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=15) as resp:
            text = resp.read().decode()
            if raw:
                return resp.status, text
            return resp.status, json.loads(text) if text else {}
    except urllib.error.HTTPError as e:
        text = e.read().decode()
        try:
            payload = json.loads(text) if text else {}
        except json.JSONDecodeError:
            payload = {"raw": text}
        return e.code, payload


def login(uid):
    status, data = req("POST", "/auth/demo-login", body={"user_id": uid})
    assert status == 200, data
    return data["access_token"], data


def record(story, result, evidence):
    results.append({"story": story, "result": result, "evidence": evidence})
    print(f"\n=== {story}: {result} ===")
    print(evidence)


def psql(sql: str) -> str:
    out = subprocess.check_output(
        ["psql", "-h", "localhost", "-d", "corvinus", "-U", "corvinus", "-t", "-A", "-c", sql],
        env={**dict(**{k: v for k, v in __import__("os").environ.items()}), "PGPASSWORD": "corvinus"},
        text=True,
    )
    return out.strip()


# -------- 1.1 Invite + accept --------
def test_1_1():
    tok, _ = login(UID["marcus"])
    email = f"tester_{int(time.time())}@corvinus.dev"
    status, inv = req(
        "POST",
        f"/organizations/{ORG_R}/invitations",
        token=tok,
        org=ORG_R,
        body={"email": email, "lab_id": LAB_SIM, "lab_role": "CONTRIBUTOR", "expires_in_days": 7},
    )
    if status != 200:
        record("1.1", "Fail", f"Invite create failed: {status} {inv}")
        return
    invite_token = inv.get("token")
    invite_link = inv.get("invite_link")
    db_row = psql(
        f"SELECT email, lab_role, status, lab_id::text, organization_id::text, expires_at "
        f"FROM invitations WHERE token = '{invite_token}'"
    )
    # Accept without being logged in as that user
    status2, accepted = req(
        "POST",
        f"/invitations/{invite_token}/accept",
        body={"name": "Tester Invitee"},
    )
    mem = psql(
        f"SELECT om.org_role, lm.lab_role, l.name FROM users u "
        f"JOIN organization_memberships om ON om.user_id=u.id "
        f"JOIN lab_memberships lm ON lm.user_id=u.id "
        f"JOIN labs l ON l.id=lm.lab_id "
        f"WHERE u.email='{email}' AND om.organization_id='{ORG_R}' AND lm.lab_id='{LAB_SIM}'"
    )
    ok = (
        status == 200
        and invite_token
        and invite_link
        and "CONTRIBUTOR" in db_row
        and LAB_SIM in db_row
        and ORG_R in db_row
        and status2 == 200
        and "CONTRIBUTOR" in mem
        and "Simulation Lab" in mem
    )
    record(
        "1.1",
        "Pass" if ok else "Fail",
        f"Create invite HTTP {status}; token={invite_token and invite_token[:12]}…; link={invite_link}; "
        f"DB row: {db_row}; Accept HTTP {status2} body={accepted}; Membership: {mem}. "
        f"Note: invite created via Admin API (same endpoints as Admin UI Members page).",
    )


# -------- 1.2 Expired invite --------
def test_1_2():
    tok, _ = login(UID["marcus"])
    email = f"expired_{int(time.time())}@corvinus.dev"
    status, inv = req(
        "POST",
        f"/organizations/{ORG_R}/invitations",
        token=tok,
        org=ORG_R,
        body={"email": email, "lab_id": LAB_SIM, "lab_role": "CONTRIBUTOR"},
    )
    token = inv["token"]
    psql(f"UPDATE invitations SET expires_at = NOW() - INTERVAL '1 day' WHERE token = '{token}'")
    status2, body = req("POST", f"/invitations/{token}/accept", body={"name": "Should Fail"})
    mem_count = psql(f"SELECT count(*) FROM users WHERE email='{email}'")
    ok = status2 in (400, 409, 422) and mem_count == "0"
    # also check no org membership for that email
    record(
        "1.2",
        "Pass" if ok else "Fail",
        f"Forced expires_at to past. Accept HTTP {status2} body={body}. "
        f"Users with that email count={mem_count} (expect 0).",
    )


# -------- 1.3 Suspended user --------
def test_1_3():
    tok, _ = login(UID["eve"])
    # Suspend Eve at user level
    psql(f"UPDATE users SET status='SUSPENDED' WHERE id='{UID['eve']}'")
    status, body = req("GET", "/auth/me", token=tok)
    # also org-scoped
    status2, body2 = req(
        "GET", f"/organizations/{ORG_R}/tasks", token=tok, org=ORG_R, lab=LAB_SIM
    )
    # restore
    psql(f"UPDATE users SET status='ACTIVE' WHERE id='{UID['eve']}'")
    # Also test REMOVED membership
    tok_c, _ = login(UID["carol"])
    # save + set removed for Carol in Robotics briefly — careful, carol is multi-role
    # Use a safer approach: suspend alice's membership? Better: create temp and remove.
    # Test membership REMOVED for Eve after re-login
    tok_e, _ = login(UID["eve"])
    psql(
        f"UPDATE organization_memberships SET status='REMOVED' "
        f"WHERE user_id='{UID['eve']}' AND organization_id='{ORG_R}'"
    )
    status3, body3 = req(
        "GET", f"/organizations/{ORG_R}/tasks", token=tok_e, org=ORG_R, lab=LAB_SIM
    )
    psql(
        f"UPDATE organization_memberships SET status='ACTIVE' "
        f"WHERE user_id='{UID['eve']}' AND organization_id='{ORG_R}'"
    )
    ok = status in (401, 403) and status2 in (401, 403) and status3 in (401, 403)
    record(
        "1.3",
        "Pass" if ok else "Fail",
        f"User SUSPENDED: GET /auth/me → {status} {body}; GET tasks → {status2} {body2}. "
        f"Membership REMOVED: GET tasks → {status3} {body3}. Both restored after test.",
    )


# -------- 1.4 Contributor cannot change roles --------
def test_1_4():
    # Carol is CONTRIBUTOR in Perception; get her membership id there via roster as marcus
    tok_m, _ = login(UID["marcus"])
    st, roster = req("GET", f"/organizations/{ORG_R}/members/roster", token=tok_m, org=ORG_R)
    carol = next(r for r in roster if r["email"] == "eve@corvinus.dev")
    perc_mem = next(l for l in carol["labs"] if l["lab_id"] == LAB_PERC)
    mem_id = perc_mem["membership_id"]

    tok_c, _ = login(UID["carol"])
    # Attempt role change as Contributor in Perception context
    status, body = req(
        "PATCH",
        f"/organizations/{ORG_R}/labs/{LAB_PERC}/members/{mem_id}",
        token=tok_c,
        org=ORG_R,
        lab=LAB_PERC,
        body={"lab_role": "MANAGER"},
    )
    # Also try org member update
    status2, body2 = req(
        "PATCH",
        f"/organizations/{ORG_R}/members/{carol['membership_id']}",
        token=tok_c,
        org=ORG_R,
        lab=LAB_PERC,
        body={"org_role": "ADMIN"},
    )
    ok = status == 403 and status2 == 403
    record(
        "1.4",
        "Pass" if ok else "Fail",
        f"Contributor Carol PATCH lab member role → {status} {body}; "
        f"PATCH org membership → {status2} {body2}. Expect 403 both.",
    )


# -------- 1.5 Dual lab roles --------
def test_1_5():
    tok, me = login(UID["dave"])
    # Dave: Manager @ Perception, Contributor @ Simulation
    st, labs_p = req(
        "GET", f"/organizations/{ORG_R}/labs/{LAB_PERC}/members", token=tok, org=ORG_R, lab=LAB_PERC
    )
    st2, labs_s = req(
        "GET", f"/organizations/{ORG_R}/labs/{LAB_SIM}/members", token=tok, org=ORG_R, lab=LAB_SIM
    )
    dave_p = next((m for m in (labs_p or []) if m.get("email") == "dave@corvinus.dev"), None)
    dave_s = next((m for m in (labs_s or []) if m.get("email") == "dave@corvinus.dev"), None)

    # Manager action: approve tool access / list pending — only managers
    st3, pending_as_mgr = req(
        "GET",
        f"/organizations/{ORG_R}/tool-access/pending",
        token=tok,
        org=ORG_R,
        lab=LAB_PERC,
    )
    # Contributor cannot grant tools (need lab header so role resolves)
    cvat_id = _tool_id(tok, ORG_R, "cvat", lab=LAB_PERC)
    st4, grant_as_contrib = req(
        "POST",
        f"/tools/{cvat_id}/access",
        token=tok,
        org=ORG_R,
        lab=LAB_SIM,
        body={"user_id": UID["eve"], "access_level": "view"},
    )
    ok = (
        dave_p
        and dave_p["lab_role"] == "MANAGER"
        and dave_s
        and dave_s["lab_role"] == "CONTRIBUTOR"
        and st3 == 200
        and st4 == 403
    )
    record(
        "1.5",
        "Pass" if ok else "Partial" if dave_p and dave_s else "Fail",
        f"Dave Perception role={dave_p}; Simulation role={dave_s}. "
        f"As Manager@Perception pending tool-access → {st3}. "
        f"As Contributor@Sim grant access → {st4} {grant_as_contrib}. "
        f"UI lab switcher not click-tested (no browser automation); API lab-header context exercised.",
    )


def _tool_id(tok, org, ttype, lab=None):
    st, tools = req("GET", f"/organizations/{org}/tools", token=tok, org=org, lab=lab)
    if not isinstance(tools, list):
        raise RuntimeError(f"tools list failed {st} {tools}")
    for t in tools:
        if t["type"] == ttype:
            return t["id"]
    return tools[0]["id"]


# -------- 1.6 Staff not via org invite --------
def test_1_6():
    tok, _ = login(UID["marcus"])
    # Invite schema only allows MANAGER|CONTRIBUTOR lab roles
    status, body = req(
        "POST",
        f"/organizations/{ORG_R}/invitations",
        token=tok,
        org=ORG_R,
        body={"email": "staff_try@corvinus.dev", "lab_id": LAB_SIM, "lab_role": "STAFF"},
    )
    # Try elevating someone to staff via org member update — no platform_role field
    st2, roster = req("GET", f"/organizations/{ORG_R}/members/roster", token=tok, org=ORG_R)
    alice_mem = next(r for r in roster if r["email"] == "dave@corvinus.dev")
    status2, body2 = req(
        "PATCH",
        f"/organizations/{ORG_R}/members/{alice_mem['membership_id']}",
        token=tok,
        org=ORG_R,
        body={"org_role": "STAFF"},
    )
    alice_role = psql(f"SELECT COALESCE(platform_role,'') FROM users WHERE id='{UID['alice']}'")
    alice_org = psql(
        f"SELECT org_role FROM organization_memberships WHERE user_id='{UID['alice']}' "
        f"AND organization_id='{ORG_R}'"
    )
    ok = status == 403 and alice_role == "" and alice_org == "MEMBER"
    record(
        "1.6",
        "Pass" if ok else "Fail",
        f"Invite lab_role=STAFF → {status} {body}. "
        f"PATCH org_role=STAFF → {status2} {body2} (Alice org_role still {alice_org}). "
        f"Alice platform_role DB='{alice_role}'. Staff only via users.platform_role.",
    )


# -------- 2.1 Manager CRUD own lab / deny other --------
def test_2_1():
    tok, _ = login(UID["alice"])  # Manager @ Perception only in Robotics
    # Create in Perception
    st, created = req(
        "POST",
        f"/organizations/{ORG_R}/tasks",
        token=tok,
        org=ORG_R,
        lab=LAB_PERC,
        body={"title": "Mgr CRUD test", "lab_id": LAB_PERC, "status": "BACKLOG", "priority": "LOW"},
    )
    tid = created.get("id")
    st_u, updated = req(
        "PATCH",
        f"/tasks/{tid}",
        token=tok,
        org=ORG_R,
        lab=LAB_PERC,
        body={"title": "Mgr CRUD updated", "version": created["version"]},
    )
    # Assign
    st_a, assigned = req(
        "PATCH",
        f"/tasks/{tid}",
        token=tok,
        org=ORG_R,
        lab=LAB_PERC,
        body={"assignee_id": UID["carol"], "version": updated["version"]},
    )
    # Fail create in Simulation (Alice not in Sim)
    st_fail, fail_body = req(
        "POST",
        f"/organizations/{ORG_R}/tasks",
        token=tok,
        org=ORG_R,
        lab=LAB_SIM,
        body={"title": "Should fail", "lab_id": LAB_SIM, "status": "BACKLOG"},
    )
    st_d, deleted = req("DELETE", f"/tasks/{tid}", token=tok, org=ORG_R, lab=LAB_PERC)
    ok = st == 200 and st_u == 200 and st_a == 200 and st_fail == 403 and st_d in (200, 204)
    record(
        "2.1",
        "Pass" if ok else "Fail",
        f"Create Perc {st}; Update {st_u}; Assign {st_a}; Create Sim (other lab) {st_fail} {fail_body}; Delete {st_d}.",
    )


# -------- 2.2 Contributor full task CRUD in own lab --------
def test_2_2():
    tok, _ = login(UID["carol"])  # Contributor @ Perception
    # Create unassigned task
    st, created = req(
        "POST",
        f"/organizations/{ORG_R}/tasks",
        token=tok,
        org=ORG_R,
        lab=LAB_PERC,
        body={"title": "Contrib unassigned", "lab_id": LAB_PERC, "status": "BACKLOG"},
    )
    # Edit + reassign (not assigned to carol — unassigned)
    st2, upd = req(
        "PATCH",
        f"/tasks/{created['id']}",
        token=tok,
        org=ORG_R,
        lab=LAB_PERC,
        body={"title": "Contrib edited", "assignee_id": UID["dave"], "version": created["version"]},
    )
    # Out of lab: Analysis lab in Biologics — Carol is Admin there actually!
    # Use Dave as Contributor @ Sim attempting Perception... wait Dave is Manager there.
    # Eve is Contributor only @ Sim — try create in Perception
    tok_e, _ = login(UID["eve"])
    st3, fail = req(
        "POST",
        f"/organizations/{ORG_R}/tasks",
        token=tok_e,
        org=ORG_R,
        lab=LAB_PERC,
        body={"title": "Eve out of lab", "lab_id": LAB_PERC},
    )
    # cleanup
    req("DELETE", f"/tasks/{created['id']}", token=tok, org=ORG_R, lab=LAB_PERC)
    ok = st == 200 and st2 == 200 and st3 == 403
    record(
        "2.2",
        "Pass" if ok else "Fail",
        f"Carol create unassigned {st}; edit+reassign {st2} {upd.get('assignee_id')}; "
        f"Eve create in Perception (not member) {st3} {fail}.",
    )


# -------- 2.3 Admin read-only tasks --------
def test_2_3():
    tok, _ = login(UID["marcus"])
    st, tasks = req("GET", f"/organizations/{ORG_R}/tasks", token=tok, org=ORG_R)
    st_dash, dash = req("GET", f"/organizations/{ORG_R}/dashboard", token=tok, org=ORG_R)
    st_c, create_body = req(
        "POST",
        f"/organizations/{ORG_R}/tasks",
        token=tok,
        org=ORG_R,
        body={"title": "Admin should fail", "lab_id": LAB_PERC},
    )
    # cross-lab visibility: both Perception and Simulation tasks present
    labs_seen = {t["lab_id"] for t in tasks} if isinstance(tasks, list) else set()
    ok = (
        st == 200
        and len(tasks) > 0
        and LAB_PERC in labs_seen
        and LAB_SIM in labs_seen
        and st_c == 403
        and st_dash == 200
    )
    record(
        "2.3",
        "Pass" if ok else "Fail",
        f"List tasks {st} count={len(tasks) if isinstance(tasks,list) else 0} labs={labs_seen}; "
        f"dashboard {st_dash} keys={list(dash) if isinstance(dash,dict) else dash}; "
        f"Admin create task {st_c} {create_body}.",
    )


# -------- 2.4 Valid transitions --------
def test_2_4():
    tok, _ = login(UID["alice"])
    st, t = req(
        "POST",
        f"/organizations/{ORG_R}/tasks",
        token=tok,
        org=ORG_R,
        lab=LAB_PERC,
        body={"title": "Transition walk", "lab_id": LAB_PERC, "status": "BACKLOG"},
    )
    tid, ver = t["id"], t["version"]
    # BACKLOG → TODO
    st1, t = req("PATCH", f"/tasks/{tid}", token=tok, org=ORG_R, lab=LAB_PERC, body={"status": "TODO", "version": ver})
    ver = t["version"]
    # TODO → IN_PROGRESS
    st2, t = req("PATCH", f"/tasks/{tid}", token=tok, org=ORG_R, lab=LAB_PERC, body={"status": "IN_PROGRESS", "version": ver})
    ver = t["version"]
    # Invalid: get a BACKLOG and jump to DONE
    st_b, tb = req(
        "POST",
        f"/organizations/{ORG_R}/tasks",
        token=tok,
        org=ORG_R,
        lab=LAB_PERC,
        body={"title": "Bad transition", "lab_id": LAB_PERC, "status": "BACKLOG"},
    )
    st_bad, bad = req(
        "PATCH",
        f"/tasks/{tb['id']}",
        token=tok,
        org=ORG_R,
        lab=LAB_PERC,
        body={"status": "DONE", "version": tb["version"]},
    )
    req("DELETE", f"/tasks/{tid}", token=tok, org=ORG_R, lab=LAB_PERC)
    req("DELETE", f"/tasks/{tb['id']}", token=tok, org=ORG_R, lab=LAB_PERC)
    ok = st1 == 200 and st2 == 200 and st_bad == 409
    record(
        "2.4",
        "Pass" if ok else "Fail",
        f"BACKLOG→TODO {st1}; TODO→IN_PROGRESS {st2}; BACKLOG→DONE {st_bad} {bad}.",
    )


# -------- 2.5 Read-only + edit + single audit (API + UI code check) --------
def test_2_5():
    tok, _ = login(UID["alice"])
    st, t = req(
        "POST",
        f"/organizations/{ORG_R}/tasks",
        token=tok,
        org=ORG_R,
        lab=LAB_PERC,
        body={"title": "Audit multi-field", "lab_id": LAB_PERC, "status": "BACKLOG", "priority": "LOW"},
    )
    before = psql(
        f"SELECT count(*) FROM audit_events WHERE entity_id='{t['id']}' AND action='task.updated'"
    )
    st2, t2 = req(
        "PATCH",
        f"/tasks/{t['id']}",
        token=tok,
        org=ORG_R,
        lab=LAB_PERC,
        body={
            "title": "Audit multi-field v2",
            "priority": "HIGH",
            "description": "changed",
            "version": t["version"],
        },
    )
    after = psql(
        f"SELECT count(*) FROM audit_events WHERE entity_id='{t['id']}' AND action='task.updated'"
    )
    req("DELETE", f"/tasks/{t['id']}", token=tok, org=ORG_R, lab=LAB_PERC)

    # Check TaskDetailPage for edit mode UX
    import pathlib
    detail = pathlib.Path(
        "/Users/induarimilli/Library/CloudStorage/OneDrive-andrew.cmu.edu/CorvinusLabs_Technical_Challenge /frontend/src/pages/tasks/TaskDetailPage.tsx"
    ).read_text()
    has_edit_mode = "editing" in detail or "isEditing" in detail or "setEditing" in detail
    single_audit = int(after) - int(before) == 1
    if single_audit and has_edit_mode:
        result = "Pass"
    elif single_audit and not has_edit_mode:
        result = "Partial"
    else:
        result = "Fail"
    record(
        "2.5",
        result,
        f"Multi-field PATCH → {st2}; audit task.updated count delta={int(after)-int(before)} (expect 1). "
        f"TaskDetailPage has edit-mode UX: {has_edit_mode}. "
        f"{'UI Edit/Cancel/Save not click-tested (no browser).' if has_edit_mode else 'UI may lack explicit Edit step.'}",
    )


# -------- 2.6 Optimistic concurrency --------
def test_2_6():
    tok, _ = login(UID["alice"])
    st, t = req(
        "POST",
        f"/organizations/{ORG_R}/tasks",
        token=tok,
        org=ORG_R,
        lab=LAB_PERC,
        body={"title": "Conflict test", "lab_id": LAB_PERC},
    )
    v = t["version"]
    st1, t1 = req(
        "PATCH", f"/tasks/{t['id']}", token=tok, org=ORG_R, lab=LAB_PERC,
        body={"title": "First save", "version": v},
    )
    st2, t2 = req(
        "PATCH", f"/tasks/{t['id']}", token=tok, org=ORG_R, lab=LAB_PERC,
        body={"title": "Second save same version", "version": v},
    )
    req("DELETE", f"/tasks/{t['id']}", token=tok, org=ORG_R, lab=LAB_PERC)
    ok = st1 == 200 and st2 == 409
    record("2.6", "Pass" if ok else "Fail", f"First save {st1}; second with stale version {st2} {t2}.")


# -------- 2.7 Cross-org isolation --------
def test_2_7():
    tok_a, _ = login(UID["alice"])  # Robotics + Biologics contrib
    # Get a Biologics task while in Biologics context
    st, tasks_b = req("GET", f"/organizations/{ORG_B}/tasks", token=tok_a, org=ORG_B, lab=LAB_ANAL)
    if not tasks_b:
        record("2.7", "Blocked", "No tasks in Biologics Analysis Lab to use as cross-org target.")
        return
    bio_task = tasks_b[0]["id"]
    # As Marcus (Robotics Admin only — not in Biologics), request Bio task with Robotics org header
    tok_m, _ = login(UID["marcus"])
    st2, body2 = req("GET", f"/tasks/{bio_task}", token=tok_m, org=ORG_R)
    # Also Alice requesting Bio task while org context is Robotics
    st3, body3 = req("GET", f"/tasks/{bio_task}", token=tok_a, org=ORG_R, lab=LAB_PERC)
    ok = st2 in (403, 404) and st3 in (403, 404)
    record(
        "2.7",
        "Pass" if ok else "Fail",
        f"Biologics task {bio_task}. Marcus(Robotics) GET → {st2} {body2}. "
        f"Alice with Robotics org header GET → {st3} {body3}.",
    )


# -------- 3.1 Provision GW --------
def test_3_1():
    tok, _ = login(UID["marcus"])
    # Use Analysis? Perception may already be provisioned — check Simulation
    st0, existing = req(
        "GET", f"/organizations/{ORG_R}/labs/{LAB_SIM}/google-workspace",
        token=tok, org=ORG_R,
    )
    if existing and existing.get("provisioning_status") == "ACTIVE":
        # Already provisioned — inspect state history via audit / current record
        record(
            "3.1",
            "Partial",
            f"Simulation Lab GW already ACTIVE (cannot re-observe REQUESTED→ACTIVE without reset). "
            f"Current: {existing}. Re-run after demo-reset to see state machine.",
        )
        return
    if existing and existing.get("provisioning_status") in ("REQUESTED", "PROVISIONING"):
        statuses = [existing["provisioning_status"]]
        for _ in range(10):
            time.sleep(0.5)
            _, cur = req(
                "GET", f"/organizations/{ORG_R}/labs/{LAB_SIM}/google-workspace",
                token=tok, org=ORG_R,
            )
            if cur:
                statuses.append(cur["provisioning_status"])
                if cur["provisioning_status"] == "ACTIVE":
                    break
        ok = "REQUESTED" in statuses or "PROVISIONING" in statuses
        record("3.1", "Pass" if ok and statuses[-1] == "ACTIVE" else "Partial", f"Status trail: {statuses}")
        return
    st, ws = req(
        "POST",
        f"/organizations/{ORG_R}/labs/{LAB_SIM}/google-workspace/provision",
        token=tok,
        org=ORG_R,
    )
    statuses = [ws.get("provisioning_status")]
    for _ in range(12):
        time.sleep(0.4)
        _, cur = req(
            "GET", f"/organizations/{ORG_R}/labs/{LAB_SIM}/google-workspace",
            token=tok, org=ORG_R,
        )
        if cur:
            statuses.append(cur["provisioning_status"])
            if cur["provisioning_status"] == "ACTIVE":
                break
    ok = st == 200 and statuses[0] == "REQUESTED" and statuses[-1] == "ACTIVE"
    record("3.1", "Pass" if ok else "Fail", f"Provision HTTP {st}; status trail {statuses}; final {cur if 'cur' in dir() else ws}")


# -------- 3.2 Shared GW no per-user grant --------
def test_3_2():
    tok_m, _ = login(UID["marcus"])
    # Ensure Perception provisioned
    st, ws = req("GET", f"/organizations/{ORG_R}/labs/{LAB_PERC}/google-workspace", token=tok_m, org=ORG_R)
    if not ws or ws.get("provisioning_status") != "ACTIVE":
        req("POST", f"/organizations/{ORG_R}/labs/{LAB_PERC}/google-workspace/provision", token=tok_m, org=ORG_R)
        for _ in range(15):
            time.sleep(0.4)
            _, ws = req("GET", f"/organizations/{ORG_R}/labs/{LAB_PERC}/google-workspace", token=tok_m, org=ORG_R)
            if ws and ws.get("provisioning_status") == "ACTIVE":
                break
    tok_alice, _ = login(UID["alice"])  # Manager Perc
    tok_carol, _ = login(UID["carol"])  # Contrib Perc
    st_a, files_a = req(
        "GET", f"/organizations/{ORG_R}/labs/{LAB_PERC}/google-workspace/drive/files",
        token=tok_alice, org=ORG_R, lab=LAB_PERC,
    )
    st_c, files_c = req(
        "GET", f"/organizations/{ORG_R}/labs/{LAB_PERC}/google-workspace/drive/files",
        token=tok_carol, org=ORG_R, lab=LAB_PERC,
    )
    # Confirm no ToolAccess-style rows for google
    ga = psql("SELECT count(*) FROM tool_access ta JOIN tools t ON t.id=ta.tool_id WHERE t.type LIKE '%google%'")
    ok = st_a == 200 and st_c == 200 and isinstance(files_a, list) and isinstance(files_c, list) and ga == "0"
    record(
        "3.2",
        "Pass" if ok else "Fail",
        f"Alice drive files {st_a} n={len(files_a) if isinstance(files_a,list) else files_a}; "
        f"Carol {st_c} n={len(files_c) if isinstance(files_c,list) else files_c}; "
        f"google-like tool_access rows={ga}.",
    )


# -------- 3.3 Unprovisioned empty state --------
def test_3_3():
    # Analysis lab likely unprovisioned
    tok, _ = login(UID["alice"])  # contrib in Analysis
    st, ws = req(
        "GET", f"/organizations/{ORG_B}/labs/{LAB_ANAL}/google-workspace",
        token=tok, org=ORG_B, lab=LAB_ANAL,
    )
    # Also list endpoint
    st2, listing = req("GET", f"/organizations/{ORG_B}/google-workspace", token=tok, org=ORG_B, lab=LAB_ANAL)
    # Frontend message check
    import pathlib
    tools_page = pathlib.Path(
        "/Users/induarimilli/Library/CloudStorage/OneDrive-andrew.cmu.edu/CorvinusLabs_Technical_Challenge /frontend/src/pages/tools/ToolsPage.tsx"
    ).read_text()
    has_empty = "No Google Workspace provisioned" in tools_page
    ok = (ws is None or st == 200 and ws is None) and has_empty
    # GET returns null with 200 typically
    record(
        "3.3",
        "Pass" if (st == 200 and ws is None and has_empty) else "Partial" if st == 200 and ws is None else "Fail",
        f"Analysis Lab GW GET → HTTP {st} body={ws}. Org listing {st2}={listing}. "
        f"UI empty-state copy present: {has_empty}.",
    )


# -------- 3.4 Lab B isolation --------
def test_3_4():
    # Eve is only Simulation Lab member — try Perception GW
    tok, _ = login(UID["eve"])
    st, body = req(
        "GET", f"/organizations/{ORG_R}/labs/{LAB_PERC}/google-workspace",
        token=tok, org=ORG_R, lab=LAB_SIM,
    )
    st2, body2 = req(
        "GET", f"/organizations/{ORG_R}/labs/{LAB_PERC}/google-workspace/drive/files",
        token=tok, org=ORG_R, lab=LAB_SIM,
    )
    ok = st == 403 and st2 == 403
    record(
        "3.4",
        "Pass" if ok else "Fail",
        f"Eve (Sim only) GET Perception GW → {st} {body}; drive/files → {st2} {body2}.",
    )


# -------- 4.1 Launcher separation --------
def test_4_1():
    import pathlib
    page = pathlib.Path(
        "/Users/induarimilli/Library/CloudStorage/OneDrive-andrew.cmu.edu/CorvinusLabs_Technical_Challenge /frontend/src/pages/tools/ToolsPage.tsx"
    ).read_text()
    has_tabs = "Research Tools" in page and "Google Workspace" in page and "setTab" in page
    # Live HTML won't show SPA content; confirm API sections exist
    tok, _ = login(UID["dave"])
    st1, cat = req(
        "GET", f"/organizations/{ORG_R}/labs/{LAB_SIM}/tools-catalog",
        token=tok, org=ORG_R, lab=LAB_SIM,
    )
    st2, gw = req("GET", f"/organizations/{ORG_R}/google-workspace", token=tok, org=ORG_R, lab=LAB_SIM)
    ok = has_tabs and st1 == 200 and st2 == 200
    record(
        "4.1",
        "Pass" if ok else "Partial" if has_tabs else "Fail",
        f"ToolsPage has Research Tools + Google Workspace tabs (setTab): {has_tabs}. "
        f"tools-catalog HTTP {st1} n={len(cat) if isinstance(cat,list) else cat}; "
        f"google-workspace list HTTP {st2}. UI visual separation not screenshot-verified.",
    )


# -------- 4.2 Contributor access states --------
def test_4_2():
    tok, _ = login(UID["dave"])  # Contrib @ Sim — has isaac+protocol ACTIVE, cvat request
    st, cat = req(
        "GET", f"/organizations/{ORG_R}/labs/{LAB_SIM}/tools-catalog",
        token=tok, org=ORG_R, lab=LAB_SIM,
    )
    by_type = {i["tool"]["type"]: i for i in cat}
    isaac = by_type.get("isaac_sim", {})
    cvat = by_type.get("cvat", {})
    # Launch without access
    if cvat and not cvat.get("can_launch"):
        st_l, launch = req("POST", f"/tools/{cvat['tool']['id']}/launch", token=tok, org=ORG_R, lab=LAB_SIM)
    else:
        st_l, launch = None, "cvat unexpectedly launchable"
    ok = (
        st == 200
        and isaac.get("can_launch") is True
        and isaac.get("access", {}).get("provisioning_status") == "ACTIVE"
        and cvat.get("can_launch") is False
        and (cvat.get("can_request") is True or (cvat.get("access") or {}).get("provisioning_status") == "PENDING_APPROVAL")
        and st_l == 403
    )
    record(
        "4.2",
        "Pass" if ok else "Fail",
        f"Catalog: isaac can_launch={isaac.get('can_launch')} status={isaac.get('access')}; "
        f"cvat can_launch={cvat.get('can_launch')} can_request={cvat.get('can_request')} access={cvat.get('access')}; "
        f"launch CVAT → {st_l} {launch}.",
    )


# -------- 4.3 Launch blocked API --------
def test_4_3():
    tok, _ = login(UID["eve"])  # no tools until onboarding complete — may have none ACTIVE
    st, cat = req(
        "GET", f"/organizations/{ORG_R}/labs/{LAB_SIM}/tools-catalog",
        token=tok, org=ORG_R, lab=LAB_SIM,
    )
    # Find a tool she cannot launch
    target = next((i for i in cat if not i.get("can_launch")), None)
    if not target:
        # complete? use carol's pending isaac as contrib at perception for isaac without access
        tok, _ = login(UID["carol"])
        st, cat = req(
            "GET", f"/organizations/{ORG_R}/labs/{LAB_PERC}/tools-catalog",
            token=tok, org=ORG_R, lab=LAB_PERC,
        )
        target = next((i for i in cat if i["tool"]["type"] == "isaac_sim" and not i.get("can_launch")), None)
    if not target:
        record("4.3", "Blocked", f"Could not find a tool without launch access. catalog={cat}")
        return
    st_l, body = req(
        "POST", f"/tools/{target['tool']['id']}/launch",
        token=tok, org=ORG_R, lab=LAB_PERC if target["tool"]["type"] == "isaac_sim" else LAB_SIM,
    )
    record(
        "4.3",
        "Pass" if st_l == 403 else "Fail",
        f"Launch {target['tool']['name']} without ACTIVE access → {st_l} {body}.",
    )


# -------- 4.4 Admin register tool --------
def test_4_4():
    tok, _ = login(UID["marcus"])
    name = f"New Tool {int(time.time())}"
    st, tool = req(
        "POST",
        f"/organizations/{ORG_R}/tools",
        token=tok,
        org=ORG_R,
        body={
            "name": name,
            "description": "Registered via admin API",
            "category": "annotation",
            "service_url": "https://example.com/tool",
        },
    )
    tok_d, _ = login(UID["dave"])
    st2, cat = req(
        "GET", f"/organizations/{ORG_R}/labs/{LAB_PERC}/tools-catalog",
        token=tok_d, org=ORG_R, lab=LAB_PERC,
    )
    # Dave is manager in Perception → sees all tools with launch
    found = next((i for i in cat if i["tool"]["name"] == name), None)
    ok = st == 200 and found is not None
    record(
        "4.4",
        "Pass" if ok else "Fail",
        f"Create tool HTTP {st} id={tool.get('id') if isinstance(tool,dict) else tool}; "
        f"appears in Dave Perception catalog: {bool(found)} ({found}). "
        f"Created via Admin Tools API (same as Admin UI).",
    )


# -------- 5 Cold open (API path + frontend structure; no browser) --------
def test_5():
    # Simulate cold path via API as Alice
    tok, login_data = login(UID["alice"])
    st_me, me = req("GET", "/auth/me", token=tok)
    st_t, tasks = req("GET", f"/organizations/{ORG_R}/tasks", token=tok, org=ORG_R, lab=LAB_PERC)
    # Move a task
    backlog = next((t for t in tasks if t["status"] == "BACKLOG"), None) or (tasks[0] if tasks else None)
    moved = None
    if backlog and backlog["status"] == "BACKLOG":
        st_m, moved = req(
            "PATCH", f"/tasks/{backlog['id']}", token=tok, org=ORG_R, lab=LAB_PERC,
            body={"status": "TODO", "version": backlog["version"]},
        )
    else:
        st_m = None
    st_tools, catalog = req(
        "GET", f"/organizations/{ORG_R}/labs/{LAB_PERC}/tools-catalog",
        token=tok, org=ORG_R, lab=LAB_PERC,
    )
    st_team, team = req(
        "GET", f"/organizations/{ORG_R}/labs/{LAB_PERC}/members",
        token=tok, org=ORG_R, lab=LAB_PERC,
    )
    st_audit, audit = req("GET", f"/organizations/{ORG_R}/audit", token=tok, org=ORG_R)
    # Marcus has audit; Alice Manager may not
    if st_audit == 403:
        tok_m, _ = login(UID["marcus"])
        st_audit, audit = req("GET", f"/organizations/{ORG_R}/audit", token=tok_m, org=ORG_R)
    recent_actions = [a.get("action") for a in (audit or [])[:15]] if isinstance(audit, list) else []
    has_task_update = "task.updated" in recent_actions or (moved and st_m == 200)

    # Login page reachable
    try:
        with urllib.request.urlopen("http://127.0.0.1:5173/login", timeout=5) as r:
            login_html_ok = r.status == 200
    except Exception as e:
        login_html_ok = False

    friction = [
        "No browser automation available — cold open exercised via API + confirming SPA login route loads (HTTP 200).",
        "Audit log is Admin-only in nav; Manager cannot view audit for own actions without switching to Admin persona.",
        "Demo login requires knowing to pick a persona card — no real email/password auth.",
    ]
    ok_core = st_me == 200 and st_t == 200 and st_tools == 200 and st_team == 200 and login_html_ok
    record(
        "5",
        "Partial" if ok_core else "Fail",
        f"Login page HTTP ok={login_html_ok}; demo-login Alice → org={login_data.get('default_organization_id')} "
        f"lab={login_data.get('default_lab_id')}; /auth/me {st_me}; tasks {st_t} n={len(tasks) if isinstance(tasks,list) else tasks}; "
        f"task move {st_m}; tools-catalog {st_tools} n={len(catalog) if isinstance(catalog,list) else catalog}; "
        f"lab members {st_team} n={len(team) if isinstance(team,list) else team}; "
        f"audit HTTP {st_audit} recent_actions={recent_actions[:8]}; task.updated seen={has_task_update}. "
        f"Friction: {'; '.join(friction)}",
    )


def main():
    print("API health:", req("GET", "/health"))
    test_1_1()
    test_1_2()
    test_1_3()
    test_1_4()
    test_1_5()
    test_1_6()
    test_2_1()
    test_2_2()
    test_2_3()
    test_2_4()
    test_2_5()
    test_2_6()
    test_2_7()
    test_3_1()
    test_3_2()
    test_3_3()
    test_3_4()
    test_4_1()
    test_4_2()
    test_4_3()
    test_4_4()
    test_5()

    print("\n\n======== SUMMARY ========")
    from collections import Counter
    c = Counter(r["result"] for r in results)
    for r in results:
        print(f"{r['story']}: {r['result']}")
    print(dict(c))
    with open("/tmp/user_stories_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Wrote /tmp/user_stories_results.json")


if __name__ == "__main__":
    main()
