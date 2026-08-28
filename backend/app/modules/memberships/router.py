"""Org roster and lab membership management (Admin).

Lab role changes set role_change_notice + notification; they do not re-run onboarding.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import TenantContext, get_user_lab_role, write_audit, write_notification
from app.core.auth import get_tenant_context
from app.core.database import get_db
from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import Permission, authorize
from app.models import Lab, LabMembership, OrganizationMembership, Role, User
from app.schemas import (
    LabMemberAdd,
    LabMemberOut,
    LabMemberUpdate,
    MemberUpdate,
    MembershipOut,
    OrgRosterOut,
)

router = APIRouter(prefix="/organizations", tags=["memberships"])


@router.get("/{org_id}/members", response_model=list[MembershipOut])
async def list_members(
    org_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.MEMBERS_MANAGE)
    result = await db.execute(
        select(OrganizationMembership).where(OrganizationMembership.organization_id == org_id)
    )
    memberships = result.scalars().all()
    return [
        MembershipOut(
            id=m.id,
            user_id=m.user_id,
            organization_id=m.organization_id,
            org_role=m.org_role,
            status=m.status,
            joined_at=m.joined_at,
        )
        for m in memberships
    ]


@router.get("/{org_id}/members/roster", response_model=list[OrgRosterOut])
async def org_roster(
    org_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.MEMBERS_MANAGE)
    result = await db.execute(
        select(OrganizationMembership, User)
        .join(User, User.id == OrganizationMembership.user_id)
        .where(OrganizationMembership.organization_id == org_id)
    )
    rows = result.all()
    roster = []
    for mem, user in rows:
        lab_rows = await db.execute(
            select(LabMembership, Lab)
            .join(Lab, Lab.id == LabMembership.lab_id)
            .where(LabMembership.user_id == user.id, Lab.organization_id == org_id, LabMembership.status == "ACTIVE")
        )
        labs = [
            {"membership_id": str(lm.id), "lab_id": str(lm.lab_id), "lab_name": lab.name, "lab_role": lm.lab_role}
            for lm, lab in lab_rows.all()
        ]
        roster.append(OrgRosterOut(
            membership_id=mem.id,
            user_id=user.id,
            name=user.name,
            email=user.email,
            org_role=mem.org_role,
            status=mem.status,
            labs=labs,
        ))
    return roster


@router.get("/{org_id}/labs/{lab_id}/members", response_model=list[LabMemberOut])
async def list_lab_members(
    org_id: uuid.UUID,
    lab_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    if ctx.is_org_admin:
        authorize(ctx, Permission.LAB_MEMBERS_READ)
    else:
        lab_role = await get_user_lab_role(db, ctx.current_user.id, lab_id, org_id)
        if not lab_role:
            raise ForbiddenError("Not authorized for this lab")
        authorize(ctx, Permission.LAB_MEMBERS_READ, lab_role=lab_role)

    result = await db.execute(
        select(LabMembership, User)
        .join(User, User.id == LabMembership.user_id)
        .join(Lab, Lab.id == LabMembership.lab_id)
        .where(
            LabMembership.lab_id == lab_id,
            Lab.organization_id == org_id,
            LabMembership.status == "ACTIVE",
        )
    )
    return [
        LabMemberOut(
            membership_id=lm.id,
            user_id=u.id,
            name=u.name,
            email=u.email,
            lab_role=lm.lab_role,
            lab_id=lab_id,
        )
        for lm, u in result.all()
    ]


@router.post("/{org_id}/labs/{lab_id}/members", response_model=LabMemberOut)
async def add_lab_member(
    org_id: uuid.UUID,
    lab_id: uuid.UUID,
    body: LabMemberAdd,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.LAB_MEMBERS_MANAGE)
    if body.lab_role not in ("MANAGER", "CONTRIBUTOR"):
        raise ForbiddenError("lab_role must be MANAGER or CONTRIBUTOR")

    org_mem = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == body.user_id,
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.status == "ACTIVE",
        )
    )
    if not org_mem.scalar_one_or_none():
        raise NotFoundError("User is not an active org member")

    existing = await db.execute(
        select(LabMembership).where(LabMembership.user_id == body.user_id, LabMembership.lab_id == lab_id)
    )
    if existing.scalar_one_or_none():
        raise ConflictError("User already in this lab")

    role_result = await db.execute(
        select(Role).where(Role.organization_id == org_id, Role.name == ("Manager" if body.lab_role == "MANAGER" else "Contributor"))
    )
    role = role_result.scalar_one()

    lm = LabMembership(user_id=body.user_id, lab_id=lab_id, role_id=role.id, lab_role=body.lab_role)
    db.add(lm)
    await db.flush()

    user_result = await db.execute(select(User).where(User.id == body.user_id))
    user = user_result.scalar_one()
    await write_audit(
        db, organization_id=org_id, actor_user_id=ctx.current_user.id,
        action="lab_member.added", entity_type="LabMembership", entity_id=lm.id,
        metadata={"lab_id": str(lab_id), "lab_role": body.lab_role, "user_id": str(body.user_id)},
    )
    return LabMemberOut(
        membership_id=lm.id, user_id=user.id, name=user.name, email=user.email,
        lab_role=lm.lab_role, lab_id=lab_id,
    )


@router.patch("/{org_id}/labs/{lab_id}/members/{membership_id}", response_model=LabMemberOut)
async def update_lab_member(
    org_id: uuid.UUID,
    lab_id: uuid.UUID,
    membership_id: uuid.UUID,
    body: LabMemberUpdate,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.LAB_MEMBERS_MANAGE)
    result = await db.execute(
        select(LabMembership, User)
        .join(User, User.id == LabMembership.user_id)
        .join(Lab, Lab.id == LabMembership.lab_id)
        .where(LabMembership.id == membership_id, LabMembership.lab_id == lab_id, Lab.organization_id == org_id)
    )
    row = result.one_or_none()
    if not row:
        raise NotFoundError("Lab membership not found")
    lm, user = row

    if body.lab_role:
        if body.lab_role not in ("MANAGER", "CONTRIBUTOR"):
            raise ForbiddenError("Invalid lab_role")
        if lm.lab_role != body.lab_role:
            lm.lab_role = body.lab_role
            lm.role_change_notice = f"Your lab role was changed to {body.lab_role}."
            await write_notification(
                db,
                organization_id=org_id,
                user_id=user.id,
                type="role.changed",
                title="Role updated",
                message=f"Your role in this lab was changed to {body.lab_role}.",
            )
    if body.status:
        lm.status = body.status

    await db.flush()
    return LabMemberOut(
        membership_id=lm.id, user_id=user.id, name=user.name, email=user.email,
        lab_role=lm.lab_role, lab_id=lab_id,
    )


@router.patch("/{org_id}/members/{membership_id}", response_model=MembershipOut)
async def update_member(
    org_id: uuid.UUID,
    membership_id: uuid.UUID,
    body: MemberUpdate,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.MEMBERS_MANAGE)
    result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.id == membership_id, OrganizationMembership.organization_id == org_id
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise NotFoundError("Membership not found")

    if body.org_role:
        if body.org_role not in ("ADMIN", "MEMBER"):
            raise ForbiddenError("org_role must be ADMIN or MEMBER")
        if membership.org_role != body.org_role:
            membership.org_role = body.org_role
            await write_notification(
                db,
                organization_id=org_id,
                user_id=membership.user_id,
                type="role.changed",
                title="Role updated",
                message=f"Your organization role was changed to {body.org_role}.",
            )
    if body.status:
        membership.status = body.status

    await db.flush()
    return MembershipOut(
        id=membership.id,
        user_id=membership.user_id,
        organization_id=membership.organization_id,
        org_role=membership.org_role,
        status=membership.status,
        joined_at=membership.joined_at,
    )
