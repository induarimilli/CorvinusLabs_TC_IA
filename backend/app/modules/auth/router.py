import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_access_token, get_current_user
from app.core.database import get_db
from app.core.errors import NotFoundError
from app.core.permissions import is_staff
from app.core.audit import org_display_role
from app.models import Lab, LabMembership, Organization, OrganizationMembership, User
from app.schemas import (
    AuthResponse,
    DemoLoginRequest,
    DemoUserOut,
    LabOut,
    LabRoleSummary,
    MeResponse,
    MembershipOut,
    MembershipSummary,
    OrganizationOut,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _build_membership_summaries(
    memberships: list[OrganizationMembership],
    organizations: list[Organization],
    lab_rows: list[tuple[Lab, LabMembership]],
) -> list[MembershipSummary]:
    summaries: list[MembershipSummary] = []
    for m in memberships:
        org = next((o for o in organizations if o.id == m.organization_id), None)
        org_labs = [(lab, lm) for lab, lm in lab_rows if lab.organization_id == m.organization_id]
        lab_summaries = [
            LabRoleSummary(lab_id=lab.id, lab_name=lab.name, lab_role=lm.lab_role)
            for lab, lm in org_labs
        ]
        lab_roles = [ls.lab_role for ls in lab_summaries]
        primary = org_labs[0] if org_labs else None
        summaries.append(
            MembershipSummary(
                organization_id=m.organization_id,
                organization_name=org.name if org else "",
                org_role=m.org_role,
                effective_role=org_display_role(m.org_role, lab_roles),
                labs=lab_summaries,
                lab_id=primary[0].id if primary else None,
                lab_name=primary[0].name if primary else None,
                lab_role=primary[1].lab_role if primary else None,
            )
        )
    return summaries


@router.get("/demo-users", response_model=list[DemoUserOut])
async def list_demo_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.status == "ACTIVE").order_by(User.name)
    )
    users = result.scalars().all()
    demo_users = []

    for user in users:
        mem_result = await db.execute(
            select(OrganizationMembership, Organization)
            .join(Organization, Organization.id == OrganizationMembership.organization_id)
            .where(OrganizationMembership.user_id == user.id, OrganizationMembership.status == "ACTIVE")
        )
        memberships = mem_result.all()
        org_ids = [mem.organization_id for mem, _ in memberships]

        lab_result = await db.execute(
            select(Lab, LabMembership)
            .join(LabMembership, LabMembership.lab_id == Lab.id)
            .where(LabMembership.user_id == user.id, Lab.organization_id.in_(org_ids))
        ) if org_ids else None
        lab_rows = lab_result.all() if lab_result else []

        org_list = [org for _, org in memberships]
        mem_list = [mem for mem, _ in memberships]
        summaries = _build_membership_summaries(mem_list, org_list, lab_rows)

        primary = summaries[0] if summaries else None

        demo_users.append(
            DemoUserOut(
                id=user.id,
                name=user.name,
                email=user.email,
                platform_role=user.platform_role,
                primary_org=primary.organization_name if primary else None,
                primary_role=primary.effective_role if primary else None,
                membership_count=len(memberships),
                org_memberships=summaries,
            )
        )
    return demo_users


@router.post("/demo-login", response_model=AuthResponse)
async def demo_login(body: DemoLoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == body.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("User not found")

    token = create_access_token(user.id, user.email)

    if is_staff(user):
        return AuthResponse(
            access_token=token,
            user=UserOut.model_validate(user),
            is_staff=True,
            default_organization_id=None,
            default_lab_id=None,
        )

    mem_result = await db.execute(
        select(OrganizationMembership)
        .where(OrganizationMembership.user_id == user.id, OrganizationMembership.status == "ACTIVE")
        .order_by(OrganizationMembership.joined_at)
    )
    memberships = mem_result.scalars().all()
    if not memberships:
        raise NotFoundError("User has no active membership")

    org_ids = [m.organization_id for m in memberships]
    lab_result = await db.execute(
        select(Lab, LabMembership)
        .join(LabMembership, LabMembership.lab_id == Lab.id)
        .where(LabMembership.user_id == user.id, Lab.organization_id.in_(org_ids))
    )
    lab_rows = lab_result.all()

    org_result = await db.execute(select(Organization).where(Organization.id.in_(org_ids)))
    organizations = org_result.scalars().all()
    summaries = _build_membership_summaries(memberships, organizations, lab_rows)

    default_org = summaries[0]
    default_lab_id = default_org.lab_id if default_org.org_role != "ADMIN" else None

    return AuthResponse(
        access_token=token,
        user=UserOut.model_validate(user),
        is_staff=False,
        default_organization_id=default_org.organization_id,
        default_lab_id=default_lab_id,
    )


@router.get("/me", response_model=MeResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    mem_result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == current_user.id, OrganizationMembership.status == "ACTIVE"
        )
    )
    memberships = mem_result.scalars().all()
    org_ids = [m.organization_id for m in memberships]

    org_result = await db.execute(select(Organization).where(Organization.id.in_(org_ids))) if org_ids else None
    organizations = org_result.scalars().all() if org_result else []

    lab_result = await db.execute(
        select(Lab, LabMembership)
        .join(LabMembership, LabMembership.lab_id == Lab.id)
        .where(LabMembership.user_id == current_user.id, Lab.organization_id.in_(org_ids))
    ) if org_ids else None
    lab_rows = lab_result.all() if lab_result else []

    summaries = _build_membership_summaries(memberships, organizations, lab_rows)

    return MeResponse(
        user=UserOut.model_validate(current_user),
        is_staff=is_staff(current_user),
        memberships=[
            MembershipOut(
                id=m.id,
                user_id=m.user_id,
                organization_id=m.organization_id,
                org_role=m.org_role,
                status=m.status,
                joined_at=m.joined_at,
            )
            for m in memberships
        ],
        organizations=[OrganizationOut.model_validate(o) for o in organizations],
        labs=[LabOut.model_validate(lab) for lab, _ in lab_rows],
        membership_summaries=summaries,
        lab_memberships=[
            {
                "lab_id": str(lab.id),
                "lab_name": lab.name,
                "organization_id": str(lab.organization_id),
                "lab_role": lm.lab_role,
            }
            for lab, lm in lab_rows
        ],
    )
