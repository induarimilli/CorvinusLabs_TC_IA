"""Platform Staff APIs: create org (requires admin invite email), deactivate, analytics.

Staff cannot be granted through org-scoped invitation/role endpoints.
"""

import uuid
import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit
from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.errors import ConflictError, NotFoundError
from app.core.permissions import Permission, authorize_platform, is_staff
from app.models import (
    Invitation,
    Organization,
    OrganizationMembership,
    OrganizationSettings,
    Role,
    Task,
    Tool,
    ToolAccess,
    User,
)
from app.schemas import OrganizationCreate, OrganizationCreateOut, PlatformAnalyticsOut, OrganizationOut

router = APIRouter(prefix="/platform", tags=["platform"])

FRONTEND_URL = "http://localhost:5173"

DEFAULT_ORG_TOOLS = [
    ("CVAT", "Annotation platform", "cvat"),
    ("Isaac Sim", "Simulation environment", "isaac_sim"),
    ("Protocol Tool", "Corvinus Labs protocol automation", "protocol_tool"),
]


async def _seed_default_org_tools(session: AsyncSession, org_id: uuid.UUID) -> None:
    for name, description, tool_type in DEFAULT_ORG_TOOLS:
        session.add(
            Tool(
                organization_id=org_id,
                name=name,
                description=description,
                type=tool_type,
                status="ENABLED",
            )
        )
    await session.flush()


async def _create_org_with_defaults(session: AsyncSession, name: str, slug: str, actor_id: uuid.UUID) -> Organization:
    existing = await session.execute(select(Organization).where(Organization.slug == slug))
    if existing.scalar_one_or_none():
        raise ConflictError(f"Organization slug '{slug}' already exists")

    org = Organization(name=name, slug=slug, status="ACTIVE")
    session.add(org)
    await session.flush()

    session.add(OrganizationSettings(organization_id=org.id))

    for role_name, desc in [
        ("Admin", "Organization administrator"),
        ("Manager", "Lab manager"),
        ("Contributor", "Lab contributor"),
    ]:
        session.add(Role(organization_id=org.id, name=role_name, description=desc))

    await session.flush()
    await _seed_default_org_tools(session, org.id)
    await write_audit(
        session,
        organization_id=org.id,
        actor_user_id=actor_id,
        action="organization.created",
        entity_type="Organization",
        entity_id=org.id,
        metadata={"name": name, "created_by": "platform_staff"},
    )
    return org


def _format_admin_invite_email(org_name: str, email: str, link: str) -> str:
    return (
        f"\n[INVITE EMAIL] To: {email}\n"
        f"Subject: You are invited to administer {org_name}\n\n"
        f"You have been invited as Organization Admin for {org_name}.\n"
        f"Accepting this invitation confirms your admin role and grants access to org management.\n\n"
        f"Accept invitation: {link}\n"
    )


@router.post("/organizations", response_model=OrganizationCreateOut)
async def create_organization(
    body: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    authorize_platform(current_user, Permission.PLATFORM_ORG_CREATE)
    slug = body.slug or re.sub(r"[^a-z0-9]+", "-", body.name.lower()).strip("-")
    org = await _create_org_with_defaults(db, body.name, slug, current_user.id)

    admin_role = await db.execute(
        select(Role).where(Role.organization_id == org.id, Role.name == "Admin")
    )
    admin_role_obj = admin_role.scalar_one()

    token = secrets.token_urlsafe(32)
    invitation = Invitation(
        organization_id=org.id,
        email=body.admin_invite_email,
        role_id=admin_role_obj.id,
        org_role="ADMIN",
        lab_role=None,
        lab_id=None,
        token=token,
        status="PENDING",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(invitation)
    await db.flush()

    link = f"{FRONTEND_URL}/invite/{token}"
    print(_format_admin_invite_email(org.name, body.admin_invite_email, link))

    return OrganizationCreateOut(
        organization=OrganizationOut.model_validate(org),
        admin_invite_email=body.admin_invite_email,
        admin_invite_link=link,
    )


@router.patch("/organizations/{org_id}/deactivate", response_model=OrganizationOut)
async def deactivate_organization(
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    authorize_platform(current_user, Permission.PLATFORM_ORG_DEACTIVATE)
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise NotFoundError("Organization not found")
    org.status = "DISABLED"
    await db.flush()
    await write_audit(
        db,
        organization_id=org.id,
        actor_user_id=current_user.id,
        action="organization.deactivated",
        entity_type="Organization",
        entity_id=org.id,
    )
    return OrganizationOut.model_validate(org)


@router.get("/analytics", response_model=PlatformAnalyticsOut)
async def platform_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    authorize_platform(current_user, Permission.PLATFORM_ANALYTICS_READ)

    active_orgs = await db.scalar(
        select(func.count()).select_from(Organization).where(Organization.status == "ACTIVE")
    )
    total_users = await db.scalar(select(func.count()).select_from(User).where(User.status == "ACTIVE"))
    total_tasks = await db.scalar(select(func.count()).select_from(Task))
    open_tasks = await db.scalar(select(func.count()).select_from(Task).where(Task.status != "DONE"))
    total_tools = await db.scalar(select(func.count()).select_from(Tool))
    tool_access_total = await db.scalar(select(func.count()).select_from(ToolAccess))
    tool_access_active = await db.scalar(
        select(func.count()).select_from(ToolAccess).where(ToolAccess.provisioning_status == "ACTIVE")
    )
    tool_access_failed = await db.scalar(
        select(func.count()).select_from(ToolAccess).where(ToolAccess.provisioning_status == "FAILED")
    )

    success_rate = 0.0
    if tool_access_total and tool_access_total > 0:
        success_rate = round((tool_access_active or 0) / tool_access_total * 100, 1)

    org_rows = await db.execute(
        select(Organization).where(Organization.status == "ACTIVE").order_by(Organization.name)
    )
    org_summaries = []
    for org in org_rows.scalars().all():
        member_count = await db.scalar(
            select(func.count())
            .select_from(OrganizationMembership)
            .where(OrganizationMembership.organization_id == org.id, OrganizationMembership.status == "ACTIVE")
        )
        task_count = await db.scalar(
            select(func.count()).select_from(Task).where(Task.organization_id == org.id)
        )
        org_summaries.append({
            "id": str(org.id),
            "name": org.name,
            "slug": org.slug,
            "member_count": member_count or 0,
            "task_count": task_count or 0,
        })

    return PlatformAnalyticsOut(
        active_organizations=active_orgs or 0,
        total_users=total_users or 0,
        total_tasks=total_tasks or 0,
        open_tasks=open_tasks or 0,
        total_tools=total_tools or 0,
        tool_provisioning_success_rate=success_rate,
        tool_access_active=tool_access_active or 0,
        tool_access_failed=tool_access_failed or 0,
        organizations=org_summaries,
    )
