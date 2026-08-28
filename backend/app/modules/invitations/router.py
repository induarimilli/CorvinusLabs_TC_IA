"""Invitations: create (Admin), inspect by token, accept (creates user/memberships).

Invite email/log includes org, lab, and role. Contributor accept starts lab onboarding.
"""

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import TenantContext, write_audit, write_notification
from app.core.auth import decode_token, get_tenant_context
from app.core.database import get_db
from app.core.errors import ConflictError, NotFoundError
from app.core.permissions import Permission, authorize
from app.models import Invitation, Lab, LabMembership, Organization, OrganizationMembership, Role, User
from app.modules.onboarding.service import ensure_onboarding_record
from app.schemas import InvitationAcceptRequest, InvitationCreate, InvitationOut

router = APIRouter(tags=["invitations"])

FRONTEND_URL = "http://localhost:5173"


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


def _invite_link(token: str) -> str:
    return f"{FRONTEND_URL}/invite/{token}"


def _format_invite_email(
    email: str,
    org_name: str,
    lab_name: str | None,
    org_role: str | None,
    lab_role: str | None,
    link: str,
) -> str:
    if org_role == "ADMIN":
        role_line = "Organization Admin"
        confirm_line = (
            "By accepting this invitation, you confirm that you are joining as the organization administrator."
        )
    else:
        role_line = f"{lab_role or 'Member'} in {lab_name or 'the lab'}"
        confirm_line = (
            f"By accepting this invitation, you confirm your role as {lab_role} in {lab_name} "
            f"so your onboarding experience matches your responsibilities."
        )

    return (
        f"\n[INVITE EMAIL] To: {email}\n"
        f"Subject: Invitation to {org_name}\n\n"
        f"Organization: {org_name}\n"
        f"Lab: {lab_name or '— (org-wide)'}\n"
        f"Role: {role_line}\n\n"
        f"{confirm_line}\n\n"
        f"Accept invitation: {link}\n"
    )


@router.post("/organizations/{org_id}/invitations", response_model=InvitationOut)
async def create_invitation(
    org_id: uuid.UUID,
    body: InvitationCreate,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.INVITATIONS_CREATE)

    if body.lab_role not in ("MANAGER", "CONTRIBUTOR"):
        from app.core.errors import ForbiddenError
        raise ForbiddenError("lab_role must be MANAGER or CONTRIBUTOR")

    lab_result = await db.execute(select(Lab).where(Lab.id == body.lab_id, Lab.organization_id == org_id))
    lab = lab_result.scalar_one_or_none()
    if not lab:
        raise NotFoundError("Lab not found")

    org_result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = org_result.scalar_one()

    role_name = "Manager" if body.lab_role == "MANAGER" else "Contributor"
    role_result = await db.execute(
        select(Role).where(Role.organization_id == org_id, Role.name == role_name)
    )
    role = role_result.scalar_one()

    token = secrets.token_urlsafe(32)
    invitation = Invitation(
        organization_id=org_id,
        email=body.email,
        role_id=role.id,
        org_role="MEMBER",
        lab_role=body.lab_role,
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
        metadata={"email": body.email, "lab_role": body.lab_role, "lab_id": str(body.lab_id)},
    )
    link = _invite_link(token)
    print(_format_invite_email(body.email, org.name, lab.name, "MEMBER", body.lab_role, link))
    return InvitationOut(
        id=invitation.id,
        email=invitation.email,
        lab_id=invitation.lab_id,
        lab_role=invitation.lab_role,
        token=invitation.token,
        status=invitation.status,
        expires_at=invitation.expires_at,
        invite_link=link,
    )


@router.get("/organizations/{org_id}/invitations")
async def list_invitations(
    org_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.INVITATIONS_CREATE)
    result = await db.execute(
        select(Invitation).where(Invitation.organization_id == org_id).order_by(Invitation.created_at.desc())
    )
    invitations = result.scalars().all()
    return [
        {
            "id": str(inv.id),
            "email": inv.email,
            "lab_role": inv.lab_role,
            "lab_id": str(inv.lab_id) if inv.lab_id else None,
            "status": inv.status,
            "expires_at": inv.expires_at.isoformat(),
            "invite_link": _invite_link(inv.token) if inv.status == "PENDING" else None,
        }
        for inv in invitations
    ]


@router.get("/invitations/{token}")
async def get_invitation(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Invitation).where(Invitation.token == token))
    invitation = result.scalar_one_or_none()
    if not invitation:
        raise NotFoundError("Invitation not found")

    org_result = await db.execute(select(Organization).where(Organization.id == invitation.organization_id))
    org = org_result.scalar_one()

    lab_name = None
    if invitation.lab_id:
        lab_result = await db.execute(select(Lab).where(Lab.id == invitation.lab_id))
        lab = lab_result.scalar_one_or_none()
        lab_name = lab.name if lab else None

    role_display = invitation.org_role if invitation.org_role == "ADMIN" else invitation.lab_role

    return {
        "email": invitation.email,
        "status": invitation.status,
        "expires_at": invitation.expires_at,
        "organization_id": str(invitation.organization_id),
        "organization_name": org.name,
        "org_role": invitation.org_role,
        "lab_role": invitation.lab_role,
        "lab_id": str(invitation.lab_id) if invitation.lab_id else None,
        "lab_name": lab_name,
        "role_display": role_display,
        "confirmation_message": (
            "By accepting, you confirm this role so your onboarding and dashboard are configured correctly."
        ),
    }


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

    if current_user and current_user.email.lower() != invitation.email.lower():
        current_user = None

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
    existing_mem = existing.scalar_one_or_none()

    target_org_role = invitation.org_role or "MEMBER"
    if not existing_mem:
        membership = OrganizationMembership(
            user_id=user.id,
            organization_id=invitation.organization_id,
            role_id=invitation.role_id,
            org_role=target_org_role,
            status="ACTIVE",
        )
        db.add(membership)
    elif existing_mem.status != "ACTIVE":
        existing_mem.status = "ACTIVE"
        existing_mem.org_role = target_org_role
        existing_mem.role_id = invitation.role_id
    elif target_org_role == "ADMIN":
        existing_mem.org_role = "ADMIN"
        existing_mem.role_id = invitation.role_id

    onboarding_required = False
    if invitation.lab_id and invitation.lab_role:
        lab_mem = await db.execute(
            select(LabMembership).where(
                LabMembership.user_id == user.id,
                LabMembership.lab_id == invitation.lab_id,
            )
        )
        existing_lab = lab_mem.scalar_one_or_none()
        if not existing_lab:
            db.add(LabMembership(
                user_id=user.id,
                lab_id=invitation.lab_id,
                role_id=invitation.role_id,
                lab_role=invitation.lab_role or "CONTRIBUTOR",
                status="ACTIVE",
            ))
        elif existing_lab.status != "ACTIVE":
            existing_lab.status = "ACTIVE"
            existing_lab.lab_role = invitation.lab_role or existing_lab.lab_role

        if invitation.lab_role == "CONTRIBUTOR":
            record = await ensure_onboarding_record(
                db, user.id, invitation.organization_id, invitation.lab_id, invitation.lab_role
            )
            onboarding_required = record is not None and record.completed_at is None

    update_result = await db.execute(
        update(Invitation)
        .where(Invitation.id == invitation.id, Invitation.status == "PENDING")
        .values(status="ACCEPTED")
    )
    if update_result.rowcount == 0:
        raise ConflictError("Invitation already accepted")

    await db.flush()
    await write_audit(
        db,
        organization_id=invitation.organization_id,
        actor_user_id=user.id,
        action="invitation.accepted",
        entity_type="Invitation",
        entity_id=invitation.id,
        metadata={"lab_role": invitation.lab_role, "org_role": invitation.org_role},
    )

    role_label = invitation.org_role if invitation.org_role == "ADMIN" else invitation.lab_role
    await write_notification(
        db,
        organization_id=invitation.organization_id,
        user_id=user.id,
        type="invitation.accepted",
        title="Welcome!",
        message=f"You have joined as {role_label}.",
    )
    return {
        "user_id": str(user.id),
        "organization_id": str(invitation.organization_id),
        "lab_id": str(invitation.lab_id) if invitation.lab_id else None,
        "onboarding_required": onboarding_required,
        "org_role": invitation.org_role,
        "lab_role": invitation.lab_role,
    }
