import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import TenantContext
from app.core.auth import get_tenant_context
from app.core.database import get_db
from app.core.permissions import Permission, authorize
from app.models import AuditEvent, Notification, User
from app.schemas import AuditEventOut, NotificationOut

router = APIRouter(tags=["audit"])


@router.get("/organizations/{org_id}/audit-events", response_model=list[AuditEventOut])
async def list_audit_events(
    org_id: uuid.UUID,
    action: str | None = Query(None),
    entity_type: str | None = Query(None),
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.AUDIT_READ)
    query = select(AuditEvent).where(AuditEvent.organization_id == org_id)
    if action:
        query = query.where(AuditEvent.action == action)
    if entity_type:
        query = query.where(AuditEvent.entity_type == entity_type)
    query = query.order_by(AuditEvent.created_at.desc()).limit(200)
    result = await db.execute(query)
    events = result.scalars().all()
    return [
        AuditEventOut(
            id=e.id,
            organization_id=e.organization_id,
            actor_user_id=e.actor_user_id,
            action=e.action,
            entity_type=e.entity_type,
            entity_id=e.entity_id,
            metadata=e.metadata_json,
            created_at=e.created_at,
        )
        for e in events
    ]


@router.get("/organizations/{org_id}/notifications", response_model=list[NotificationOut])
async def list_notifications(
    org_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification)
        .where(Notification.organization_id == org_id, Notification.user_id == ctx.current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    return [NotificationOut.model_validate(n) for n in result.scalars().all()]
