import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AuditEvent,
    Lab,
    LabMembership,
    Notification,
    Organization,
    OrganizationMembership,
    User,
)


@dataclass
class TenantContext:
    current_user: User
    current_organization: Organization
    current_membership: OrganizationMembership
    org_role: str  # ADMIN | MEMBER
    current_lab: Lab | None = None
    lab_role: str | None = None  # MANAGER | CONTRIBUTOR for current_lab header context
    request_id: str = ""

    @property
    def is_org_admin(self) -> bool:
        return self.org_role == "ADMIN"

    def effective_role(self, lab_role: str | None = None) -> str:
        if self.is_org_admin:
            return "Admin"
        role = lab_role or self.lab_role
        return org_display_role("MEMBER", [role] if role else [])


def org_display_role(org_role: str, lab_roles: list[str]) -> str:
    """Human-facing role label for an org context (header/login)."""
    if org_role == "ADMIN":
        return "Admin"
    if "MANAGER" in lab_roles:
        return "Manager"
    if "CONTRIBUTOR" in lab_roles:
        return "Contributor"
    return "Member"


async def get_user_lab_role(
    db: AsyncSession, user_id: uuid.UUID, lab_id: uuid.UUID, org_id: uuid.UUID
) -> str | None:
    result = await db.execute(
        select(LabMembership.lab_role)
        .join(Lab, Lab.id == LabMembership.lab_id)
        .where(
            LabMembership.user_id == user_id,
            LabMembership.lab_id == lab_id,
            LabMembership.status == "ACTIVE",
            Lab.organization_id == org_id,
        )
    )
    return result.scalar_one_or_none()


async def write_audit(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_user_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None = None,
    metadata: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=metadata,
    )
    db.add(event)
    return event


async def write_notification(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    type: str,
    title: str,
    message: str,
) -> Notification:
    notification = Notification(
        organization_id=organization_id,
        user_id=user_id,
        type=type,
        title=title,
        message=message,
    )
    db.add(notification)
    return notification


async def get_user_lab_ids(db: AsyncSession, user_id: uuid.UUID, org_id: uuid.UUID) -> list[uuid.UUID]:
    result = await db.execute(
        select(LabMembership.lab_id)
        .join(Lab, Lab.id == LabMembership.lab_id)
        .where(
            LabMembership.user_id == user_id,
            LabMembership.status == "ACTIVE",
            Lab.organization_id == org_id,
        )
    )
    return list(result.scalars().all())
