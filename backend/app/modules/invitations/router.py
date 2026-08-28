import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import TenantContext, write_audit, write_notification
from app.core.auth import decode_token, get_tenant_context
from app.core.database import get_db
from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import Permission, authorize
from app.models import Invitation, LabMembership, OrganizationMembership, Role, User
from app.schemas import InvitationAcceptRequest, InvitationCreate, InvitationOut

router = APIRouter(tags=["invitations"])


@router.post("/organizations/{org_id}/invitations", response_model=InvitationOut)
async def create_invitation(
    org_id: uuid.UUID,
    body: InvitationCreate,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.INVITATIONS_CREATE)

    role_result = await db.execute(
        select(Role).where(Role.id == body.role_id, Role.organization_id == org_id)
    )
    role = role_result.scalar_one_or_none()
    if not role:
        raise NotFoundError("Role not found")
    if ctx.current_role.name == "Manager" and role.name == "Admin":
        raise ForbiddenError("Managers cannot invite Admins")

    token = secrets.token_urlsafe(32)
    invitation = Invitation(
        organization_id=org_id,
        email=body.email,
        role_id=body.role_id,
        lab_id=body.lab_id,
        token=token,
        status="PENDING",
        expires_at=datetime.now(timezone.utc) + timedelta(days=body.expires_in_days),
    )
    db.add(invitation)
    await db.flush()
    await write_audit(
        db,
        organization_id=org_id,
        actor_user_id=ctx.current_user.id,
        action="invitation.created",
        entity_type="Invitation",
        entity_id=invitation.id,
        metadata={"email": body.email},
    )
    base_url = str(request.base_url).rstrip("/")
    return InvitationOut(
        id=invitation.id,
        email=invitation.email,
        role_id=invitation.role_id,
        lab_id=invitation.lab_id,
        token=invitation.token,
        status=invitation.status,
        expires_at=invitation.expires_at,
        invite_link=f"http://localhost:5173/invite/{token}",
    )


@router.get("/invitations/{token}")
async def get_invitation(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Invitation).where(Invitation.token == token)
    )
    invitation = result.scalar_one_or_none()
    if not invitation:
        raise NotFoundError("Invitation not found")
    return {
        "email": invitation.email,
        "status": invitation.status,
        "expires_at": invitation.expires_at,
        "organization_id": invitation.organization_id,
    }


async def optional_current_user(
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        token = authorization.split(" ", 1)[1]
        payload = decode_token(token)
        user_id = uuid.UUID(payload["sub"])
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    except Exception:
        return None


@router.post("/invitations/{token}/accept")
async def accept_invitation(
    token: str,
    body: InvitationAcceptRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(optional_current_user),
):
    result = await db.execute(
        select(Invitation).where(
            Invitation.token == token,
            Invitation.status == "PENDING",
            Invitation.expires_at > datetime.now(timezone.utc),
        )
    )
    invitation = result.scalar_one_or_none()
    if not invitation:
        raise ConflictError("Invitation expired, already used, or not found")

    if current_user:
        user = current_user
    else:
        user_result = await db.execute(select(User).where(User.email == invitation.email))
        user = user_result.scalar_one_or_none()
        if not user:
            if not body.name:
                raise ConflictError("Name required for new user")
            user = User(name=body.name, email=invitation.email, status="ACTIVE")
            db.add(user)
            await db.flush()

    existing = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == invitation.organization_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError("User already a member of this organization")

    membership = OrganizationMembership(
        user_id=user.id,
        organization_id=invitation.organization_id,
        role_id=invitation.role_id,
        status="ACTIVE",
    )
    db.add(membership)

    if invitation.lab_id:
        lab_membership = LabMembership(
            user_id=user.id,
            lab_id=invitation.lab_id,
            role_id=invitation.role_id,
            status="ACTIVE",
        )
        db.add(lab_membership)

    await db.execute(
        update(Invitation)
        .where(Invitation.id == invitation.id, Invitation.status == "PENDING")
        .values(status="ACCEPTED")
    )
    await db.flush()
    await write_audit(
        db,
        organization_id=invitation.organization_id,
        actor_user_id=user.id,
        action="invitation.accepted",
        entity_type="Invitation",
        entity_id=invitation.id,
    )
    await write_notification(
        db,
        organization_id=invitation.organization_id,
        user_id=user.id,
        type="invitation.accepted",
        title="Welcome!",
        message=f"You have joined the organization.",
    )
    return {"user_id": str(user.id), "organization_id": str(invitation.organization_id)}
