import uuid

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.google_workspace_client import (
    ensure_workspace_initialized,
    list_calendar_events,
    list_chat_messages,
    list_drive_files,
    send_chat_message,
    start_meet_session,
)
from app.core.audit import TenantContext, get_user_lab_ids, write_audit
from app.core.auth import get_tenant_context
from app.core.database import get_db
from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import Permission, authorize
from app.models import Lab, LabGoogleWorkspace
from app.schemas import (
    CalendarEventOut,
    ChatMessageCreate,
    ChatMessageOut,
    DriveFileOut,
    LabGoogleWorkspaceOut,
    MeetSessionOut,
)
from app.workers.google_workspace import run_workspace_provisioning

router = APIRouter(tags=["google-workspace"])


async def _get_active_workspace(
    db: AsyncSession, org_id: uuid.UUID, lab_id: uuid.UUID
) -> tuple[LabGoogleWorkspace, Lab]:
    result = await db.execute(
        select(LabGoogleWorkspace).where(
            LabGoogleWorkspace.lab_id == lab_id,
            LabGoogleWorkspace.organization_id == org_id,
        )
    )
    ws = result.scalar_one_or_none()
    if not ws:
        raise NotFoundError("Google Workspace not provisioned for this lab")
    if ws.provisioning_status != "ACTIVE":
        raise ForbiddenError(f"Google Workspace is not ready (status: {ws.provisioning_status})")
    lab_result = await db.execute(select(Lab).where(Lab.id == lab_id))
    lab = lab_result.scalar_one_or_none()
    ensure_workspace_initialized(ws.id, ws.lab_id, lab.name if lab else "Lab")
    return ws, lab  # type: ignore[return-value]


async def _require_workspace_access(
    ctx: TenantContext, db: AsyncSession, org_id: uuid.UUID, lab_id: uuid.UUID
) -> None:
    if ctx.is_org_admin:
        authorize(ctx, Permission.GOOGLE_WORKSPACE_MANAGE)
        return
    lab_ids = await get_user_lab_ids(db, ctx.current_user.id, org_id)
    if lab_id not in lab_ids:
        raise ForbiddenError("Not a member of this lab")
    authorize(ctx, Permission.GOOGLE_WORKSPACE_USE)


@router.get("/organizations/{org_id}/labs/{lab_id}/google-workspace", response_model=LabGoogleWorkspaceOut | None)
async def get_lab_google_workspace(
    org_id: uuid.UUID,
    lab_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    await _require_workspace_access(ctx, db, org_id, lab_id)
    result = await db.execute(
        select(LabGoogleWorkspace).where(
            LabGoogleWorkspace.lab_id == lab_id,
            LabGoogleWorkspace.organization_id == org_id,
        )
    )
    ws = result.scalar_one_or_none()
    return LabGoogleWorkspaceOut.model_validate(ws) if ws else None


@router.post("/organizations/{org_id}/labs/{lab_id}/google-workspace/provision", response_model=LabGoogleWorkspaceOut)
async def provision_google_workspace(
    org_id: uuid.UUID,
    lab_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.GOOGLE_WORKSPACE_MANAGE)
    lab = await db.execute(select(Lab).where(Lab.id == lab_id, Lab.organization_id == org_id))
    if not lab.scalar_one_or_none():
        raise NotFoundError("Lab not found")

    existing = await db.execute(
        select(LabGoogleWorkspace).where(LabGoogleWorkspace.lab_id == lab_id)
    )
    existing_ws = existing.scalar_one_or_none()
    if existing_ws:
        if existing_ws.provisioning_status in ("REQUESTED", "PROVISIONING"):
            background_tasks.add_task(run_workspace_provisioning, existing_ws.id)
            return LabGoogleWorkspaceOut.model_validate(existing_ws)
        raise ConflictError("Google Workspace already provisioned for this lab")

    ws = LabGoogleWorkspace(
        organization_id=org_id,
        lab_id=lab_id,
        provisioning_status="REQUESTED",
    )
    db.add(ws)
    await db.flush()
    await write_audit(
        db, organization_id=org_id, actor_user_id=ctx.current_user.id,
        action="google_workspace.provision_requested", entity_type="LabGoogleWorkspace", entity_id=ws.id,
        metadata={"lab_id": str(lab_id)},
    )
    background_tasks.add_task(run_workspace_provisioning, ws.id)
    return LabGoogleWorkspaceOut.model_validate(ws)


@router.get("/organizations/{org_id}/google-workspace")
async def list_google_workspace(
    org_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    if ctx.is_org_admin:
        authorize(ctx, Permission.GOOGLE_WORKSPACE_MANAGE)
        result = await db.execute(
            select(LabGoogleWorkspace, Lab)
            .join(Lab, Lab.id == LabGoogleWorkspace.lab_id)
            .where(LabGoogleWorkspace.organization_id == org_id)
        )
    else:
        authorize(ctx, Permission.GOOGLE_WORKSPACE_USE)
        lab_ids = await get_user_lab_ids(db, ctx.current_user.id, org_id)
        result = await db.execute(
            select(LabGoogleWorkspace, Lab)
            .join(Lab, Lab.id == LabGoogleWorkspace.lab_id)
            .where(LabGoogleWorkspace.organization_id == org_id, LabGoogleWorkspace.lab_id.in_(lab_ids))
        )

    rows = result.all()
    for ws, _ in rows:
        if ws.provisioning_status in ("REQUESTED", "PROVISIONING"):
            background_tasks.add_task(run_workspace_provisioning, ws.id)

    return [
        {
            **LabGoogleWorkspaceOut.model_validate(ws).model_dump(),
            "lab_name": lab.name,
        }
        for ws, lab in rows
    ]


# --- Mock Google Workspace API hooks (Drive, Calendar, Chat, Meet) ---

@router.get(
    "/organizations/{org_id}/labs/{lab_id}/google-workspace/drive/files",
    response_model=list[DriveFileOut],
)
async def list_drive(
    org_id: uuid.UUID,
    lab_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    await _require_workspace_access(ctx, db, org_id, lab_id)
    ws, _ = await _get_active_workspace(db, org_id, lab_id)
    return [DriveFileOut(**f) for f in list_drive_files(ws.id)]


@router.get(
    "/organizations/{org_id}/labs/{lab_id}/google-workspace/calendar/events",
    response_model=list[CalendarEventOut],
)
async def list_calendar(
    org_id: uuid.UUID,
    lab_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    await _require_workspace_access(ctx, db, org_id, lab_id)
    ws, _ = await _get_active_workspace(db, org_id, lab_id)
    return [CalendarEventOut(**e) for e in list_calendar_events(ws.id)]


@router.get(
    "/organizations/{org_id}/labs/{lab_id}/google-workspace/chat/messages",
    response_model=list[ChatMessageOut],
)
async def list_chat(
    org_id: uuid.UUID,
    lab_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    await _require_workspace_access(ctx, db, org_id, lab_id)
    ws, _ = await _get_active_workspace(db, org_id, lab_id)
    return [ChatMessageOut(**m) for m in list_chat_messages(ws.id)]


@router.post(
    "/organizations/{org_id}/labs/{lab_id}/google-workspace/chat/messages",
    response_model=ChatMessageOut,
)
async def post_chat(
    org_id: uuid.UUID,
    lab_id: uuid.UUID,
    body: ChatMessageCreate,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    await _require_workspace_access(ctx, db, org_id, lab_id)
    ws, _ = await _get_active_workspace(db, org_id, lab_id)
    msg = send_chat_message(ws.id, ctx.current_user.name, body.content)
    return ChatMessageOut(**msg)


@router.post(
    "/organizations/{org_id}/labs/{lab_id}/google-workspace/meet/start",
    response_model=MeetSessionOut,
)
async def start_meet(
    org_id: uuid.UUID,
    lab_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    await _require_workspace_access(ctx, db, org_id, lab_id)
    ws, _ = await _get_active_workspace(db, org_id, lab_id)
    session = start_meet_session(ws.id, ws.meet_url or "")
    return MeetSessionOut(**session)
