"""Background Google Workspace provisioning: REQUESTED → PROVISIONING → ACTIVE (~2s mock)."""

import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.google_workspace_client import initialize_workspace
from app.core.database import async_session_factory
from app.models import Lab, LabGoogleWorkspace


async def process_workspace(session: AsyncSession, workspace_id: uuid.UUID) -> None:
    result = await session.execute(
        select(LabGoogleWorkspace).where(LabGoogleWorkspace.id == workspace_id)
    )
    ws = result.scalar_one_or_none()
    if not ws:
        return

    if ws.provisioning_status not in ("REQUESTED", "PROVISIONING"):
        return

    ws.provisioning_status = "PROVISIONING"
    await session.commit()

    await asyncio.sleep(2)

    lab_result = await session.execute(select(Lab).where(Lab.id == ws.lab_id))
    lab = lab_result.scalar_one_or_none()
    lab_name = lab.name if lab else "Lab"

    ws.provisioning_status = "ACTIVE"
    ws.drive_url = f"https://drive.google.com/drive/folders/mock-{ws.lab_id}"
    ws.calendar_id = f"lab-{ws.lab_id}@group.calendar.google.com"
    ws.chat_space_url = f"https://chat.google.com/room/mock-{ws.lab_id}"
    ws.meet_url = f"https://meet.google.com/mock-{str(ws.lab_id)[:8]}"

    initialize_workspace(ws.id, ws.lab_id, lab_name)
    await session.commit()


async def run_workspace_provisioning(workspace_id: uuid.UUID) -> None:
    """Background job — small delay ensures the creating transaction has committed."""
    await asyncio.sleep(0.5)
    async with async_session_factory() as session:
        await process_workspace(session, workspace_id)
