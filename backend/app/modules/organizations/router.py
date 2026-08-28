import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import TenantContext
from app.core.auth import get_tenant_context
from app.core.database import get_db
from app.core.errors import NotFoundError
from app.core.permissions import Permission, authorize
from app.models import Invitation, Lab, OrganizationMembership, OrganizationSettings, Task, Tool
from app.schemas import (
    DashboardStats,
    LabCreate,
    LabOut,
    LabUpdate,
    OrganizationOut,
    OrganizationSettingsOut,
    OrganizationSettingsUpdate,
    OrganizationUpdate,
)

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("/{org_id}", response_model=OrganizationOut)
async def get_organization(
    org_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
):
    if ctx.current_organization.id != org_id:
        from app.core.errors import ForbiddenError
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
        from app.core.errors import ForbiddenError
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
    authorize(ctx, Permission.TASKS_READ)
    lab_count = await db.scalar(
        select(func.count()).select_from(Lab).where(Lab.organization_id == org_id, Lab.archived == False)
    )
    member_count = await db.scalar(
        select(func.count())
        .select_from(OrganizationMembership)
        .where(OrganizationMembership.organization_id == org_id, OrganizationMembership.status == "ACTIVE")
    )
    open_tasks = await db.scalar(
        select(func.count())
        .select_from(Task)
        .where(Task.organization_id == org_id, Task.status != "DONE")
    )
    tool_count = await db.scalar(
        select(func.count()).select_from(Tool).where(Tool.organization_id == org_id)
    )
    pending_invitations = await db.scalar(
        select(func.count())
        .select_from(Invitation)
        .where(Invitation.organization_id == org_id, Invitation.status == "PENDING")
    )
    return DashboardStats(
        lab_count=lab_count or 0,
        member_count=member_count or 0,
        open_tasks=open_tasks or 0,
        tool_count=tool_count or 0,
        pending_invitations=pending_invitations or 0,
    )


@router.get("/{org_id}/labs", response_model=list[LabOut])
async def list_labs(
    org_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.TASKS_READ)
    result = await db.execute(
        select(Lab).where(Lab.organization_id == org_id, Lab.archived == False)
    )
    return [LabOut.model_validate(l) for l in result.scalars().all()]


@router.post("/{org_id}/labs", response_model=LabOut)
async def create_lab(
    org_id: uuid.UUID,
    body: LabCreate,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    from app.core.audit import write_audit

    authorize(ctx, Permission.LABS_MANAGE)
    lab = Lab(organization_id=org_id, name=body.name, description=body.description)
    db.add(lab)
    await db.flush()
    await write_audit(
        db,
        organization_id=org_id,
        actor_user_id=ctx.current_user.id,
        action="lab.created",
        entity_type="Lab",
        entity_id=lab.id,
    )
    return LabOut.model_validate(lab)


@router.patch("/labs/{lab_id}", response_model=LabOut)
async def update_lab(
    lab_id: uuid.UUID,
    body: LabUpdate,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    from app.core.audit import write_audit

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
        db,
        organization_id=lab.organization_id,
        actor_user_id=ctx.current_user.id,
        action="lab.updated",
        entity_type="Lab",
        entity_id=lab.id,
    )
    return LabOut.model_validate(lab)
