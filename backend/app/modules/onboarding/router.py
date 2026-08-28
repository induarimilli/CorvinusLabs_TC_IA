"""Contributor scavenger-hunt onboarding: status, advance, navigate, complete.

Completing grants AUTO_ONBOARD tools for the lab and kicks provisioning.
Also hosts dismiss-role-notice for post-onboarding role changes.
"""

import asyncio
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import TenantContext, write_audit
from app.core.auth import get_current_user, get_tenant_context
from app.core.database import async_session_factory, get_db
from app.core.errors import ConflictError, NotFoundError
from app.core.permissions import Permission, authorize
from app.models import Lab, LabMembership, LabOnboardingProgress, User
from app.modules.onboarding.service import (
    current_step,
    get_checklist_for_lab,
    get_steps_for_lab,
    grant_onboarding_tools,
    pending_onboarding_for_user,
)
from app.schemas import (
    OnboardingAdvanceOut,
    OnboardingChecklistItemOut,
    OnboardingCompleteOut,
    OnboardingStatusOut,
    OnboardingStepOut,
)

router = APIRouter(tags=["onboarding"])


async def run_provisioning_jobs(access_ids: list[uuid.UUID], org_id: uuid.UUID) -> None:
    await asyncio.sleep(0.2)
    async with async_session_factory() as session:
        from app.workers.provisioning import process_access

        for access_id in access_ids:
            await process_access(session, access_id, org_id)
        await session.commit()


def _build_status(lab: Lab, progress: LabOnboardingProgress | None) -> OnboardingStatusOut:
    steps = get_steps_for_lab(lab.name)
    checklist = get_checklist_for_lab(lab.name)
    completed_ids = list(progress.steps_completed or []) if progress else []
    step_outs = [OnboardingStepOut.model_validate(s) for s in steps]
    cur = current_step(steps, completed_ids)
    cur_out = OnboardingStepOut.model_validate(cur) if cur else None

    if not progress:
        return OnboardingStatusOut(
            required=False,
            completed=True,
            lab_id=lab.id,
            lab_name=lab.name,
            lab_role="MANAGER",
            steps=step_outs,
            completed_step_ids=completed_ids,
            current_step=None,
            checklist=[OnboardingChecklistItemOut.model_validate(c) for c in checklist],
        )

    return OnboardingStatusOut(
        required=progress.completed_at is None,
        completed=progress.completed_at is not None,
        lab_id=lab.id,
        lab_name=lab.name,
        lab_role=progress.lab_role,
        steps=step_outs,
        completed_step_ids=completed_ids,
        current_step=cur_out,
        checklist=[OnboardingChecklistItemOut.model_validate(c) for c in checklist],
        completed_at=progress.completed_at,
    )


@router.get("/organizations/{org_id}/labs/{lab_id}/onboarding", response_model=OnboardingStatusOut)
async def get_onboarding_status(
    org_id: uuid.UUID,
    lab_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.TOOLS_READ)
    lab_result = await db.execute(select(Lab).where(Lab.id == lab_id, Lab.organization_id == org_id))
    lab = lab_result.scalar_one_or_none()
    if not lab:
        raise NotFoundError("Lab not found")

    progress_result = await db.execute(
        select(LabOnboardingProgress).where(
            LabOnboardingProgress.user_id == ctx.current_user.id,
            LabOnboardingProgress.lab_id == lab_id,
        )
    )
    progress = progress_result.scalar_one_or_none()
    return _build_status(lab, progress)


@router.post("/organizations/{org_id}/labs/{lab_id}/onboarding/advance", response_model=OnboardingAdvanceOut)
async def advance_onboarding(
    org_id: uuid.UUID,
    lab_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.TOOLS_READ)
    lab_result = await db.execute(select(Lab).where(Lab.id == lab_id, Lab.organization_id == org_id))
    lab = lab_result.scalar_one_or_none()
    if not lab:
        raise NotFoundError("Lab not found")

    progress_result = await db.execute(
        select(LabOnboardingProgress).where(
            LabOnboardingProgress.user_id == ctx.current_user.id,
            LabOnboardingProgress.lab_id == lab_id,
            LabOnboardingProgress.organization_id == org_id,
        )
    )
    progress = progress_result.scalar_one_or_none()
    if not progress or progress.completed_at is not None:
        raise NotFoundError("No active onboarding for this lab")

    steps = get_steps_for_lab(lab.name)
    completed = list(progress.steps_completed or [])
    cur = current_step(steps, completed)
    if not cur:
        raise ConflictError("All steps already completed")

    if cur["advance"] == "complete":
        raise ConflictError("Use the complete endpoint for the final step")

    completed.append(cur["id"])
    progress.steps_completed = completed
    await db.flush()

    next_cur = current_step(steps, completed)
    return OnboardingAdvanceOut(
        completed_step_ids=completed,
        current_step=OnboardingStepOut.model_validate(next_cur) if next_cur else None,
    )


@router.post("/organizations/{org_id}/labs/{lab_id}/onboarding/advance-navigate", response_model=OnboardingAdvanceOut)
async def advance_onboarding_navigate(
    org_id: uuid.UUID,
    lab_id: uuid.UUID,
    visited_path: str = Query(...),
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """Complete a navigate-type step when the user visits the target path."""
    authorize(ctx, Permission.TOOLS_READ)
    lab_result = await db.execute(select(Lab).where(Lab.id == lab_id, Lab.organization_id == org_id))
    lab = lab_result.scalar_one_or_none()
    if not lab:
        raise NotFoundError("Lab not found")

    progress_result = await db.execute(
        select(LabOnboardingProgress).where(
            LabOnboardingProgress.user_id == ctx.current_user.id,
            LabOnboardingProgress.lab_id == lab_id,
            LabOnboardingProgress.organization_id == org_id,
        )
    )
    progress = progress_result.scalar_one_or_none()
    if not progress or progress.completed_at is not None:
        return OnboardingAdvanceOut(completed_step_ids=list(progress.steps_completed or []) if progress else [], current_step=None)

    steps = get_steps_for_lab(lab.name)
    completed = list(progress.steps_completed or [])
    cur = current_step(steps, completed)
    if not cur or cur["advance"] != "navigate" or cur.get("highlight_nav") != visited_path:
        cur_out = OnboardingStepOut.model_validate(cur) if cur else None
        return OnboardingAdvanceOut(completed_step_ids=completed, current_step=cur_out)

    completed.append(cur["id"])
    progress.steps_completed = completed
    await db.flush()

    next_cur = current_step(steps, completed)
    return OnboardingAdvanceOut(
        completed_step_ids=completed,
        current_step=OnboardingStepOut.model_validate(next_cur) if next_cur else None,
    )


@router.get("/auth/onboarding/pending")
async def list_pending_onboarding(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await pending_onboarding_for_user(db, current_user.id)


@router.post("/organizations/{org_id}/labs/{lab_id}/onboarding/complete", response_model=OnboardingCompleteOut)
async def complete_onboarding(
    org_id: uuid.UUID,
    lab_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.TOOLS_READ)
    lab_result = await db.execute(select(Lab).where(Lab.id == lab_id, Lab.organization_id == org_id))
    lab = lab_result.scalar_one_or_none()
    if not lab:
        raise NotFoundError("Lab not found")

    progress_result = await db.execute(
        select(LabOnboardingProgress).where(
            LabOnboardingProgress.user_id == ctx.current_user.id,
            LabOnboardingProgress.lab_id == lab_id,
            LabOnboardingProgress.organization_id == org_id,
        )
    )
    progress = progress_result.scalar_one_or_none()
    if not progress:
        raise NotFoundError("No onboarding required for this lab")
    if progress.completed_at is not None:
        return OnboardingCompleteOut(completed=True, tools_granted=0)

    steps = get_steps_for_lab(lab.name)
    completed = list(progress.steps_completed or [])
    cur = current_step(steps, completed)
    if cur and cur["id"] != "checklist":
        raise ConflictError("Complete all scavenger hunt steps first")

    if "checklist" not in completed:
        completed.append("checklist")
        progress.steps_completed = completed

    from datetime import datetime, timezone

    progress.completed_at = datetime.now(timezone.utc)
    access_ids = await grant_onboarding_tools(db, ctx.current_user.id, lab_id, org_id)
    await db.flush()

    await write_audit(
        db,
        organization_id=org_id,
        actor_user_id=ctx.current_user.id,
        action="onboarding.completed",
        entity_type="LabOnboardingProgress",
        entity_id=progress.id,
        metadata={"lab_id": str(lab_id), "tools_granted": len(access_ids)},
    )

    if access_ids:
        background_tasks.add_task(run_provisioning_jobs, access_ids, org_id)

    return OnboardingCompleteOut(completed=True, tools_granted=len(access_ids))


@router.post("/organizations/{org_id}/labs/{lab_id}/membership/dismiss-role-notice")
async def dismiss_role_notice(
    org_id: uuid.UUID,
    lab_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(LabMembership).where(
            LabMembership.user_id == ctx.current_user.id,
            LabMembership.lab_id == lab_id,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise NotFoundError("Lab membership not found")
    membership.role_change_notice = None
    await db.flush()
    return {"dismissed": True}
