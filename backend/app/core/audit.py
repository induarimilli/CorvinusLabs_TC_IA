import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AuditEvent,
    Lab,
    LabMembership,
    Notification,
    Organization,
    OrganizationMembership,
    Role,
    User,
)


@dataclass
class TenantContext:
    current_user: User
    current_organization: Organization
    current_membership: OrganizationMembership
    current_role: Role
    current_lab: Lab | None = None
    request_id: str = ""


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
    from sqlalchemy import select

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
