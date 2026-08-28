"""
Auth helpers: JWT issue/verify, current user, and tenant context.

Requires X-Organization-Id (and optional X-Lab-Id) for org-scoped routes.
Suspended users and inactive memberships are rejected here — not only in the UI.
"""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header, Request
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import TenantContext, get_user_lab_role
from app.core.config import settings
from app.core.database import get_db
from app.core.errors import ForbiddenError, UnauthorizedError
from app.models import Lab, LabMembership, Organization, OrganizationMembership, User


def create_access_token(user_id: uuid.UUID, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as e:
        raise UnauthorizedError("Invalid or expired token") from e


async def get_current_user(
    request: Request,
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedError()
    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    user_id = uuid.UUID(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or user.status != "ACTIVE":
        raise UnauthorizedError("User not found or suspended")
    return user


async def get_tenant_context(
    request: Request,
    current_user: User = Depends(get_current_user),
    x_organization_id: str | None = Header(None, alias="X-Organization-Id"),
    x_lab_id: str | None = Header(None, alias="X-Lab-Id"),
    db: AsyncSession = Depends(get_db),
) -> TenantContext:
    if not x_organization_id:
        raise ForbiddenError("Organization context required (X-Organization-Id header)")

    org_id = uuid.UUID(x_organization_id)
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    organization = result.scalar_one_or_none()
    if not organization or organization.status != "ACTIVE":
        raise ForbiddenError("Organization not found or disabled")

    result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == current_user.id,
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.status == "ACTIVE",
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise ForbiddenError("No active membership in this organization")

    org_role = membership.org_role or "MEMBER"

    current_lab = None
    lab_role = None
    if x_lab_id:
        lab_id = uuid.UUID(x_lab_id)
        lab_result = await db.execute(
            select(Lab).where(Lab.id == lab_id, Lab.organization_id == org_id)
        )
        current_lab = lab_result.scalar_one_or_none()
        if not current_lab:
            raise ForbiddenError("Lab not found in this organization")
        if org_role != "ADMIN":
            lab_role = await get_user_lab_role(db, current_user.id, lab_id, org_id)
            if not lab_role:
                raise ForbiddenError("Not a member of this lab")

    return TenantContext(
        current_user=current_user,
        current_organization=organization,
        current_membership=membership,
        org_role=org_role,
        current_lab=current_lab,
        lab_role=lab_role,
        request_id=getattr(request.state, "request_id", ""),
    )
