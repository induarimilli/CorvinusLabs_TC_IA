import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import create_access_token, get_current_user
from app.core.database import get_db
from app.core.errors import NotFoundError
from app.models import Lab, LabMembership, Organization, OrganizationMembership, User
from app.schemas import AuthResponse, DemoLoginRequest, DemoUserOut, LabOut, MeResponse, MembershipOut, OrganizationOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/demo-users", response_model=list[DemoUserOut])
async def list_demo_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User, OrganizationMembership, Organization)
        .join(OrganizationMembership, OrganizationMembership.user_id == User.id)
        .join(Organization, Organization.id == OrganizationMembership.organization_id)
        .where(OrganizationMembership.status == "ACTIVE", User.status == "ACTIVE")
    )
    rows = result.all()
    demo_users = []
    for user, membership, org in rows:
        role_result = await db.execute(
            select(OrganizationMembership)
            .options(selectinload(OrganizationMembership.role))
            .where(OrganizationMembership.id == membership.id)
        )
        m = role_result.scalar_one()
        lab_result = await db.execute(
            select(Lab, LabMembership)
            .join(LabMembership, LabMembership.lab_id == Lab.id)
            .where(LabMembership.user_id == user.id, Lab.organization_id == org.id)
            .limit(1)
        )
        lab_row = lab_result.first()
        lab, _ = lab_row if lab_row else (None, None)
        demo_users.append(
            DemoUserOut(
                id=user.id,
                name=user.name,
                email=user.email,
                organization_name=org.name,
                organization_id=org.id,
                role_name=m.role.name if m.role else "Unknown",
                lab_name=lab.name if lab else None,
                lab_id=lab.id if lab else None,
            )
        )
    return demo_users


@router.post("/demo-login", response_model=AuthResponse)
async def demo_login(body: DemoLoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == body.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("User not found")

    mem_query = select(OrganizationMembership).where(
        OrganizationMembership.user_id == user.id, OrganizationMembership.status == "ACTIVE"
    )
    if body.organization_id:
        mem_query = mem_query.where(OrganizationMembership.organization_id == body.organization_id)
    mem_result = await db.execute(mem_query.limit(1))
    membership = mem_result.scalar_one_or_none()
    if not membership and body.organization_id:
        raise NotFoundError("User has no active membership in this organization")
    if not membership:
        mem_result = await db.execute(
            select(OrganizationMembership)
            .where(OrganizationMembership.user_id == user.id, OrganizationMembership.status == "ACTIVE")
            .limit(1)
        )
        membership = mem_result.scalar_one_or_none()
    if not membership:
        raise NotFoundError("User has no active membership")

    lab_result = await db.execute(
        select(Lab)
        .join(LabMembership, LabMembership.lab_id == Lab.id)
        .where(LabMembership.user_id == user.id, Lab.organization_id == membership.organization_id)
        .limit(1)
    )
    lab = lab_result.scalar_one_or_none()

    token = create_access_token(user.id, user.email)
    return AuthResponse(
        access_token=token,
        user=UserOut.model_validate(user),
        default_organization_id=membership.organization_id,
        default_lab_id=lab.id if lab else None,
    )


@router.get("/me", response_model=MeResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    mem_result = await db.execute(
        select(OrganizationMembership)
        .options(selectinload(OrganizationMembership.role))
        .where(OrganizationMembership.user_id == current_user.id, OrganizationMembership.status == "ACTIVE")
    )
    memberships = mem_result.scalars().all()
    org_ids = [m.organization_id for m in memberships]

    org_result = await db.execute(select(Organization).where(Organization.id.in_(org_ids)))
    organizations = org_result.scalars().all()

    lab_result = await db.execute(
        select(Lab)
        .join(LabMembership, LabMembership.lab_id == Lab.id)
        .where(LabMembership.user_id == current_user.id, Lab.organization_id.in_(org_ids))
    )
    labs = lab_result.scalars().all()

    return MeResponse(
        user=UserOut.model_validate(current_user),
        memberships=[
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
        ],
        organizations=[OrganizationOut.model_validate(o) for o in organizations],
        labs=[LabOut.model_validate(l) for l in labs],
    )
