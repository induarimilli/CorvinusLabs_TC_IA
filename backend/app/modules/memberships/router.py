import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import TenantContext, write_audit
from app.core.auth import get_tenant_context
from app.core.database import get_db
from app.core.errors import ForbiddenError, NotFoundError
from app.core.permissions import Permission, authorize
from app.models import OrganizationMembership, Role, User
from app.schemas import MemberUpdate, MembershipOut, UserOut

router = APIRouter(prefix="/organizations", tags=["memberships"])


@router.get("/{org_id}/members", response_model=list[MembershipOut])
async def list_members(
    org_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.MEMBERS_MANAGE)
    result = await db.execute(
        select(OrganizationMembership)
        .options(selectinload(OrganizationMembership.role))
        .where(OrganizationMembership.organization_id == org_id)
    )
    memberships = result.scalars().all()
    return [
        MembershipOut(
            id=m.id,
            user_id=m.user_id,
            organization_id=m.organization_id,
            role_id=m.role_id,
            role_name=m.role.name,
            status=m.status,
            joined_at=m.joined_at,
        )
        for m in memberships
    ]


@router.get("/{org_id}/members/details")
async def list_members_with_users(
    org_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.MEMBERS_MANAGE)
    result = await db.execute(
        select(OrganizationMembership, User, Role)
        .join(User, User.id == OrganizationMembership.user_id)
        .join(Role, Role.id == OrganizationMembership.role_id)
        .where(OrganizationMembership.organization_id == org_id)
    )
    rows = result.all()
    return [
        {
            "membership": MembershipOut(
                id=m.id,
                user_id=m.user_id,
                organization_id=m.organization_id,
                role_id=m.role_id,
                role_name=r.name,
                status=m.status,
                joined_at=m.joined_at,
            ),
            "user": UserOut.model_validate(u),
        }
        for m, u, r in rows
    ]


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
        select(OrganizationMembership)
        .options(selectinload(OrganizationMembership.role))
        .where(OrganizationMembership.id == membership_id, OrganizationMembership.organization_id == org_id)
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise NotFoundError("Membership not found")

    if body.role_id:
        role_result = await db.execute(
            select(Role).where(Role.id == body.role_id, Role.organization_id == org_id)
        )
        new_role = role_result.scalar_one_or_none()
        if not new_role:
            raise NotFoundError("Role not found")
        if ctx.current_role.name == "Manager" and new_role.name == "Admin":
            raise ForbiddenError("Managers cannot assign Admin role")
        membership.role_id = body.role_id
    if body.status:
        membership.status = body.status

    await db.flush()
    await write_audit(
        db,
        organization_id=org_id,
        actor_user_id=ctx.current_user.id,
        action="member.updated",
        entity_type="OrganizationMembership",
        entity_id=membership.id,
        metadata={"status": membership.status},
    )
    role_result = await db.execute(select(Role).where(Role.id == membership.role_id))
    role = role_result.scalar_one()
    return MembershipOut(
        id=membership.id,
        user_id=membership.user_id,
        organization_id=membership.organization_id,
        role_id=membership.role_id,
        role_name=role.name,
        status=membership.status,
        joined_at=membership.joined_at,
    )


@router.get("/{org_id}/roles")
async def list_roles(
    org_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.MEMBERS_MANAGE)
    result = await db.execute(select(Role).where(Role.organization_id == org_id))
    roles = result.scalars().all()
    return [{"id": r.id, "name": r.name, "description": r.description} for r in roles]
