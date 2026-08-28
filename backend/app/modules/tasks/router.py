import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import TenantContext, get_user_lab_ids, get_user_lab_role, write_audit
from app.core.auth import get_tenant_context
from app.core.database import get_db
from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import Permission, authorize, valid_transition
from app.models import Lab, LabMembership, Task, TaskAttachment, TaskComment, User
from app.schemas import (
    TaskAttachmentCreate,
    TaskAttachmentOut,
    TaskCommentCreate,
    TaskCommentOut,
    TaskCreate,
    TaskOut,
    TaskUpdate,
)

router = APIRouter(tags=["tasks"])


async def _validate_assignee_in_lab(db: AsyncSession, assignee_id: uuid.UUID, lab_id: uuid.UUID, org_id: uuid.UUID) -> None:
    result = await db.execute(
        select(LabMembership)
        .join(Lab, Lab.id == LabMembership.lab_id)
        .where(
            LabMembership.user_id == assignee_id,
            LabMembership.lab_id == lab_id,
            LabMembership.status == "ACTIVE",
            Lab.organization_id == org_id,
        )
    )
    if not result.scalar_one_or_none():
        raise ForbiddenError("Assignee must be an active member of this lab")


async def _require_lab_access(ctx: TenantContext, db: AsyncSession, lab_id: uuid.UUID, permission: Permission) -> str | None:
    if ctx.is_org_admin:
        authorize(ctx, permission)
        return None
    lab_role = await get_user_lab_role(db, ctx.current_user.id, lab_id, ctx.current_organization.id)
    if not lab_role:
        raise ForbiddenError("Not authorized for this lab")
    authorize(ctx, permission, lab_role=lab_role)
    return lab_role


@router.get("/organizations/{org_id}/tasks")
async def list_tasks(
    org_id: uuid.UUID,
    lab_id: uuid.UUID | None = None,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.TASKS_READ)
    query = select(Task).where(Task.organization_id == org_id)

    if ctx.is_org_admin:
        if lab_id:
            query = query.where(Task.lab_id == lab_id)
    else:
        lab_ids = await get_user_lab_ids(db, ctx.current_user.id, org_id)
        if not lab_ids:
            return []
        query = query.where(Task.lab_id.in_(lab_ids))
        if lab_id:
            if lab_id not in lab_ids:
                raise ForbiddenError("Not authorized for this lab")
            query = query.where(Task.lab_id == lab_id)
        elif ctx.current_lab:
            query = query.where(Task.lab_id == ctx.current_lab.id)

    result = await db.execute(query.order_by(Task.created_at.desc()))
    return [TaskOut.model_validate(t) for t in result.scalars().all()]


@router.get("/tasks/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundError("Task not found")
    await _require_lab_access(ctx, db, task.lab_id, Permission.TASKS_READ)
    authorize(ctx, Permission.TASKS_READ, task)
    return TaskOut.model_validate(task)


@router.post("/organizations/{org_id}/tasks", response_model=TaskOut)
async def create_task(
    org_id: uuid.UUID,
    body: TaskCreate,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    lab_result = await db.execute(
        select(Lab).where(Lab.id == body.lab_id, Lab.organization_id == org_id)
    )
    lab = lab_result.scalar_one_or_none()
    if not lab:
        raise NotFoundError("Lab not found")

    await _require_lab_access(ctx, db, body.lab_id, Permission.TASKS_CREATE)

    if body.assignee_id:
        lr = None if ctx.is_org_admin else await get_user_lab_role(db, ctx.current_user.id, body.lab_id, org_id)
        authorize(ctx, Permission.TASKS_ASSIGN, lab_role=lr)
        await _validate_assignee_in_lab(db, body.assignee_id, body.lab_id, org_id)

    task = Task(
        organization_id=org_id,
        lab_id=body.lab_id,
        title=body.title,
        description=body.description,
        status=body.status or "BACKLOG",
        priority=body.priority or "MEDIUM",
        assignee_id=body.assignee_id,
        due_date=body.due_date,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)
    await write_audit(
        db,
        organization_id=org_id,
        actor_user_id=ctx.current_user.id,
        action="task.created",
        entity_type="Task",
        entity_id=task.id,
        metadata={"assignee_id": str(body.assignee_id) if body.assignee_id else None},
    )
    return TaskOut.model_validate(task)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: uuid.UUID,
    body: TaskUpdate,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundError("Task not found")

    lab_role = await _require_lab_access(ctx, db, task.lab_id, Permission.TASKS_UPDATE)
    authorize(ctx, Permission.TASKS_UPDATE, task, lab_role=lab_role)

    if task.version != body.version:
        raise ConflictError("Task was modified by another user — refresh and retry")

    if body.status and body.status != task.status:
        if not valid_transition(task.status, body.status):
            raise ConflictError(f"Invalid transition from {task.status} to {body.status}")

    if body.assignee_id is not None and body.assignee_id != task.assignee_id:
        authorize(ctx, Permission.TASKS_ASSIGN, lab_role=lab_role)
        if body.assignee_id:
            await _validate_assignee_in_lab(db, body.assignee_id, task.lab_id, task.organization_id)

    if body.title is not None:
        task.title = body.title
    if body.description is not None:
        task.description = body.description
    if body.assignee_id is not None:
        task.assignee_id = body.assignee_id or None
    if body.status is not None:
        task.status = body.status
    if body.priority is not None:
        task.priority = body.priority
    if body.due_date is not None:
        task.due_date = body.due_date
    task.version += 1

    await db.flush()
    await db.refresh(task)
    await write_audit(
        db,
        organization_id=task.organization_id,
        actor_user_id=ctx.current_user.id,
        action="task.updated",
        entity_type="Task",
        entity_id=task.id,
        metadata={"status": task.status, "assignee_id": str(task.assignee_id) if task.assignee_id else None},
    )
    return TaskOut.model_validate(task)


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundError("Task not found")

    lab_role = await _require_lab_access(ctx, db, task.lab_id, Permission.TASKS_DELETE)
    authorize(ctx, Permission.TASKS_DELETE, task, lab_role=lab_role)

    await db.delete(task)
    await write_audit(
        db,
        organization_id=task.organization_id,
        actor_user_id=ctx.current_user.id,
        action="task.deleted",
        entity_type="Task",
        entity_id=task.id,
    )
    return {"deleted": True}


@router.post("/tasks/{task_id}/comments", response_model=TaskCommentOut)
async def add_comment(
    task_id: uuid.UUID,
    body: TaskCommentCreate,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundError("Task not found")
    lab_role = await _require_lab_access(ctx, db, task.lab_id, Permission.TASKS_UPDATE)
    authorize(ctx, Permission.TASKS_UPDATE, task, lab_role=lab_role)

    comment = TaskComment(task_id=task_id, author_id=ctx.current_user.id, content=body.content)
    db.add(comment)
    await db.flush()
    await db.refresh(comment)
    return TaskCommentOut.model_validate(comment)


@router.get("/tasks/{task_id}/comments")
async def list_comments(
    task_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundError("Task not found")
    lab_role = await _require_lab_access(ctx, db, task.lab_id, Permission.TASKS_READ)
    authorize(ctx, Permission.TASKS_READ, task, lab_role=lab_role)

    comments = await db.execute(
        select(TaskComment).where(TaskComment.task_id == task_id).order_by(TaskComment.created_at)
    )
    return [TaskCommentOut.model_validate(c) for c in comments.scalars().all()]


@router.get("/tasks/{task_id}/attachments", response_model=list[TaskAttachmentOut])
async def list_attachments(
    task_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundError("Task not found")
    lab_role = await _require_lab_access(ctx, db, task.lab_id, Permission.TASKS_READ)
    authorize(ctx, Permission.TASKS_READ, task, lab_role=lab_role)

    attachments = await db.execute(
        select(TaskAttachment).where(TaskAttachment.task_id == task_id).order_by(TaskAttachment.created_at)
    )
    return [TaskAttachmentOut.model_validate(a) for a in attachments.scalars().all()]


@router.post("/tasks/{task_id}/attachments", response_model=TaskAttachmentOut)
async def add_attachment(
    task_id: uuid.UUID,
    body: TaskAttachmentCreate,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundError("Task not found")
    lab_role = await _require_lab_access(ctx, db, task.lab_id, Permission.TASKS_UPDATE)
    authorize(ctx, Permission.TASKS_UPDATE, task, lab_role=lab_role)

    attachment = TaskAttachment(
        task_id=task_id,
        uploaded_by_id=ctx.current_user.id,
        file_name=body.file_name,
        file_url=f"demo://attachments/{task_id}/{body.file_name}",
        file_type=body.file_type,
        file_size=len(body.file_name),
    )
    db.add(attachment)
    await db.flush()
    await db.refresh(attachment)
    return TaskAttachmentOut.model_validate(attachment)
