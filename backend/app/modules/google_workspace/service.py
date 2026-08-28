"""Google Workspace provisioning helpers."""

import uuid

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit
from app.models import LabGoogleWorkspace
from app.workers.google_workspace import run_workspace_provisioning


async def request_lab_google_workspace(
    db: AsyncSession,
    org_id: uuid.UUID,
    lab_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    *,
    background_tasks: BackgroundTasks,
) -> LabGoogleWorkspace:
    existing = await db.execute(
        select(LabGoogleWorkspace).where(LabGoogleWorkspace.lab_id == lab_id)
    )
    existing_ws = existing.scalar_one_or_none()
    if existing_ws:
        if existing_ws.provisioning_status in ("REQUESTED", "PROVISIONING"):
            background_tasks.add_task(run_workspace_provisioning, existing_ws.id)
        return existing_ws

    ws = LabGoogleWorkspace(
        organization_id=org_id,
        lab_id=lab_id,
        provisioning_status="REQUESTED",
    )
    db.add(ws)
    await db.flush()
    await write_audit(
        db,
        organization_id=org_id,
        actor_user_id=actor_user_id,
        action="google_workspace.provision_requested",
        entity_type="LabGoogleWorkspace",
        entity_id=ws.id,
        metadata={"lab_id": str(lab_id), "auto": True},
    )
    background_tasks.add_task(run_workspace_provisioning, ws.id)
    return ws
