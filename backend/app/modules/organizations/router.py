import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import TenantContext, write_audit
from app.core.auth import get_tenant_context
from app.core.config import settings
from app.core.database import get_db
from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import Permission, authorize
from app.models import Invitation, Lab, LabGoogleWorkspace, LabMembership, OrganizationMembership, OrganizationSettings, Role, Task, Tool, User
from app.modules.google_workspace.service import request_lab_google_workspace
from app.schemas import (
    DashboardStats,
    InvitationOut,
    LabCreate,
    LabOut,
    LabSummaryOut,
    LabUpdate,
    OrganizationOut,
    OrganizationSettingsOut,
    OrganizationSettingsUpdate,
    OrganizationUpdate,
)

router = APIRouter(prefix="/organizations", tags=["organizations"])

FRONTEND_URL = getattr(settings, "frontend_url", "http://localhost:5173")


@router.get("/{org_id}", response_model=OrganizationOut)
async def get_organization(org_id: uuid.UUID, ctx: TenantContext = Depends(get_tenant_context)):
    if ctx.current_organization.id != org_id:
        raise ForbiddenError()
    authorize(ctx, Permission.ORG_SETTINGS_READ)
    return OrganizationOut.model_validate(ctx.current_organization)


@router.patch("/{org_id}", response_model=OrganizationOut)
async def update_organization(
    org_id: uuid.UUID,
    body: OrganizationUpdate,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    if ctx.current_organization.id != org_id:
        raise ForbiddenError()
    authorize(ctx, Permission.ORG_SETTINGS_WRITE)
    if body.name:
        ctx.current_organization.name = body.name
    await db.flush()
    return OrganizationOut.model_validate(ctx.current_organization)


@router.get("/{org_id}/settings", response_model=OrganizationSettingsOut)
async def get_settings(
    org_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.ORG_SETTINGS_READ)
    result = await db.execute(
        select(OrganizationSettings).where(OrganizationSettings.organization_id == org_id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        raise NotFoundError("Settings not found")
    return OrganizationSettingsOut.model_validate(settings)


@router.patch("/{org_id}/settings", response_model=OrganizationSettingsOut)
async def update_settings(
    org_id: uuid.UUID,
    body: OrganizationSettingsUpdate,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.ORG_SETTINGS_WRITE)
    result = await db.execute(
        select(OrganizationSettings).where(OrganizationSettings.organization_id == org_id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        raise NotFoundError("Settings not found")
    if body.timezone is not None:
        settings.timezone = body.timezone
    if body.date_format is not None:
        settings.date_format = body.date_format
    if body.time_format is not None:
        settings.time_format = body.time_format
    await db.flush()
    return OrganizationSettingsOut.model_validate(settings)


@router.get("/{org_id}/dashboard", response_model=DashboardStats)
async def get_dashboard(
    org_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.ORG_SETTINGS_READ)
    lab_count = await db.scalar(
        select(func.count()).select_from(Lab).where(Lab.organization_id == org_id, Lab.archived == False)
    )
    member_count = await db.scalar(
        select(func.count())
        .select_from(OrganizationMembership)
        .where(OrganizationMembership.organization_id == org_id, OrganizationMembership.status == "ACTIVE")
    )
    admin_count = await db.scalar(
        select(func.count())
        .select_from(OrganizationMembership)
        .where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.status == "ACTIVE",
            OrganizationMembership.org_role == "ADMIN",
        )
    )
    manager_count = await db.scalar(
        select(func.count())
        .select_from(LabMembership)
        .join(Lab, Lab.id == LabMembership.lab_id)
        .where(Lab.organization_id == org_id, LabMembership.lab_role == "MANAGER", LabMembership.status == "ACTIVE")
    )
    contributor_count = await db.scalar(
        select(func.count())
        .select_from(LabMembership)
        .join(Lab, Lab.id == LabMembership.lab_id)
        .where(Lab.organization_id == org_id, LabMembership.lab_role == "CONTRIBUTOR", LabMembership.status == "ACTIVE")
    )
    open_tasks = await db.scalar(
        select(func.count())
        .select_from(Task).where(Task.organization_id == org_id, Task.status != "DONE")
    )
    tool_count = await db.scalar(
        select(func.count()).select_from(Tool).where(Tool.organization_id == org_id)
    )
    pending_invitations = await db.scalar(
        select(func.count())
        .select_from(Invitation)
        .where(Invitation.organization_id == org_id, Invitation.status == "PENDING")
    )
    active_google_workspaces = await db.scalar(
        select(func.count())
        .select_from(LabGoogleWorkspace)
        .where(LabGoogleWorkspace.organization_id == org_id, LabGoogleWorkspace.provisioning_status == "ACTIVE")
    )
    labs_without_workspace = (lab_count or 0) - (active_google_workspaces or 0)

    status_rows = await db.execute(
        select(Task.status, func.count())
        .where(Task.organization_id == org_id)
        .group_by(Task.status)
    )
    tasks_by_status = {status: count for status, count in status_rows.all()}

    return DashboardStats(
        lab_count=lab_count or 0,
        member_count=member_count or 0,
        open_tasks=open_tasks or 0,
        tool_count=tool_count or 0,
        pending_invitations=pending_invitations or 0,
        manager_count=manager_count or 0,
        contributor_count=contributor_count or 0,
        admin_count=admin_count or 0,
        tasks_by_status=tasks_by_status,
        active_google_workspaces=active_google_workspaces or 0,
        labs_without_workspace=max(0, labs_without_workspace),
    )


@router.get("/{org_id}/dashboard/labs", response_model=list[LabSummaryOut])
async def get_dashboard_labs(
    org_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.ORG_SETTINGS_READ)
    labs = (await db.execute(
        select(Lab).where(Lab.organization_id == org_id, Lab.archived == False)
    )).scalars().all()

    summaries = []
    for lab in labs:
        member_count = await db.scalar(
            select(func.count()).select_from(LabMembership).where(
                LabMembership.lab_id == lab.id, LabMembership.status == "ACTIVE"
            )
        )
        open_tasks = await db.scalar(
            select(func.count()).select_from(Task).where(
                Task.lab_id == lab.id, Task.status != "DONE"
            )
        )
        ws = (await db.execute(
            select(LabGoogleWorkspace).where(LabGoogleWorkspace.lab_id == lab.id)
        )).scalar_one_or_none()
        summaries.append(LabSummaryOut(
            lab_id=lab.id,
            lab_name=lab.name,
            member_count=member_count or 0,
            open_tasks=open_tasks or 0,
            has_google_workspace=ws is not None,
            workspace_status=ws.provisioning_status if ws else None,
        ))
    return summaries


@router.get("/{org_id}/labs", response_model=list[LabOut])
async def list_labs(
    org_id: uuid.UUID,
    include_archived: bool = False,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.LABS_MANAGE if ctx.is_org_admin else Permission.TASKS_READ)
    query = select(Lab).where(Lab.organization_id == org_id)
    if not include_archived:
        query = query.where(Lab.archived == False)
    result = await db.execute(query)
    return [LabOut.model_validate(l) for l in result.scalars().all()]


@router.post("/{org_id}/labs", response_model=LabOut)
async def create_lab(
    org_id: uuid.UUID,
    body: LabCreate,
    background_tasks: BackgroundTasks,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.LABS_MANAGE)
    lab = Lab(organization_id=org_id, name=body.name, description=body.description)
    db.add(lab)
    await db.flush()

    manager_role = await db.execute(
        select(Role).where(Role.organization_id == org_id, Role.name == "Manager")
    )
    manager_role_obj = manager_role.scalar_one()

    if body.manager_user_id:
        mem = await db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == body.manager_user_id,
                OrganizationMembership.organization_id == org_id,
                OrganizationMembership.status == "ACTIVE",
            )
        )
        if not mem.scalar_one_or_none():
            raise NotFoundError("User is not an active org member")
        db.add(LabMembership(
            user_id=body.manager_user_id,
            lab_id=lab.id,
            role_id=manager_role_obj.id,
            lab_role="MANAGER",
            status="ACTIVE",
        ))
        await write_audit(
            db, organization_id=org_id, actor_user_id=ctx.current_user.id,
            action="lab.manager.assigned", entity_type="LabMembership",
            entity_id=lab.id, metadata={"user_id": str(body.manager_user_id)},
        )

    invite_out = None
    if body.invite_manager_email:
        token = secrets.token_urlsafe(32)
        invitation = Invitation(
            organization_id=org_id,
            email=body.invite_manager_email,
            role_id=manager_role_obj.id,
            org_role="MEMBER",
            lab_role="MANAGER",
            lab_id=lab.id,
            token=token,
            status="PENDING",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db.add(invitation)
        await db.flush()
        invite_out = f"{FRONTEND_URL}/invite/{token}"

    await write_audit(
        db, organization_id=org_id, actor_user_id=ctx.current_user.id,
        action="lab.created", entity_type="Lab", entity_id=lab.id,
        metadata={"invite_link": invite_out} if invite_out else None,
    )

    await request_lab_google_workspace(
        db,
        org_id,
        lab.id,
        ctx.current_user.id,
        background_tasks=background_tasks,
        auto=True,
    )

    lab_out = LabOut.model_validate(lab)
    return lab_out


@router.patch("/labs/{lab_id}", response_model=LabOut)
async def update_lab(
    lab_id: uuid.UUID,
    body: LabUpdate,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.LABS_MANAGE)
    result = await db.execute(select(Lab).where(Lab.id == lab_id))
    lab = result.scalar_one_or_none()
    if not lab:
        raise NotFoundError("Lab not found")
    authorize(ctx, Permission.LABS_MANAGE, lab)
    if body.name is not None:
        lab.name = body.name
    if body.description is not None:
        lab.description = body.description
    if body.archived is not None:
        lab.archived = body.archived
    await db.flush()
    await write_audit(
        db, organization_id=lab.organization_id, actor_user_id=ctx.current_user.id,
        action="lab.updated", entity_type="Lab", entity_id=lab.id,
    )
    return LabOut.model_validate(lab)
