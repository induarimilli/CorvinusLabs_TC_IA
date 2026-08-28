import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import TenantContext, get_user_lab_ids, write_audit
from app.core.auth import get_tenant_context
from app.core.database import get_db
from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import Permission, authorize
from app.models import Lab, Task, TaskComment
from app.schemas import TaskCreate, TaskOut, TaskUpdate, TaskCommentCreate, TaskCommentOut

router = APIRouter(tags=["tasks"])

TASK_TRANSITIONS = {
    "BACKLOG": {"TODO"},
    "TODO": {"IN_PROGRESS", "BACKLOG"},
    "IN_PROGRESS": {"BLOCKED", "DONE", "TODO"},
    "BLOCKED": {"IN_PROGRESS"},
    "DONE": set(),
}


def validate_transition(current: str, new: str) -> None:
    allowed = TASK_TRANSITIONS.get(current, set())
    if new != current and new not in allowed:
        raise ConflictError(f"Invalid transition from {current} to {new}")


@router.get("/organizations/{org_id}/tasks")
async def list_tasks(
    org_id: uuid.UUID,
    lab_id: uuid.UUID | None = None,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    from app.schemas import TaskOut

    authorize(ctx, Permission.TASKS_READ)
    query = select(Task).where(Task.organization_id == org_id)

    if ctx.current_role.name == "Manager":
        lab_ids = await get_user_lab_ids(db, ctx.current_user.id, org_id)
        query = query.where(Task.lab_id.in_(lab_ids))
    elif ctx.current_role.name == "Contributor":
        lab_ids = await get_user_lab_ids(db, ctx.current_user.id, org_id)
        query = query.where(Task.lab_id.in_(lab_ids))

    if lab_id:
        query = query.where(Task.lab_id == lab_id)
    elif ctx.current_lab:
        query = query.where(Task.lab_id == ctx.current_lab.id)

    result = await db.execute(query.order_by(Task.created_at.desc()))
    return [TaskOut.model_validate(t) for t in result.scalars().all()]


@router.post("/organizations/{org_id}/tasks", response_model=TaskOut)
async def create_task(
    org_id: uuid.UUID,
    body: TaskCreate,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.TASKS_CREATE)
    lab_result = await db.execute(
        select(Lab).where(Lab.id == body.lab_id, Lab.organization_id == org_id)
    )
    lab = lab_result.scalar_one_or_none()
    if not lab:
        raise NotFoundError("Lab not found")

    if ctx.current_role.name == "Manager":
        lab_ids = await get_user_lab_ids(db, ctx.current_user.id, org_id)
        if body.lab_id not in lab_ids:
            raise ForbiddenError("Not a member of this lab")

    task = Task(
        organization_id=org_id,
        lab_id=body.lab_id,
        title=body.title,
        description=body.description,
        status=body.status,
        priority=body.priority,
        assignee_id=body.assignee_id,
        due_date=body.due_date,
    )
    db.add(task)
    await db.flush()
    await write_audit(
        db,
        organization_id=org_id,
        actor_user_id=ctx.current_user.id,
        action="task.created",
        entity_type="Task",
        entity_id=task.id,
    )
    return TaskOut.model_validate(task)


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    from app.schemas import TaskOut

    authorize(ctx, Permission.TASKS_READ)
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundError("Task not found")
    authorize(ctx, Permission.TASKS_READ, task)
    return TaskOut.model_validate(task)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: uuid.UUID,
    body: TaskUpdate,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.TASKS_UPDATE)
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundError("Task not found")
    authorize(ctx, Permission.TASKS_UPDATE, task)

    if ctx.current_role.name == "Contributor" and task.assignee_id != ctx.current_user.id:
        raise ForbiddenError("Contributors can only edit their assigned tasks")

    if task.version != body.version:
        raise ConflictError("Task was modified by another user")

    if body.status and body.status != task.status:
        validate_transition(task.status, body.status)

    if body.title is not None:
        task.title = body.title
    if body.description is not None:
        task.description = body.description
    if body.assignee_id is not None:
        task.assignee_id = body.assignee_id
    if body.status is not None:
        task.status = body.status
    if body.priority is not None:
        task.priority = body.priority
    if body.due_date is not None:
        task.due_date = body.due_date
    task.version += 1

    await db.flush()
    await write_audit(
        db,
        organization_id=task.organization_id,
        actor_user_id=ctx.current_user.id,
        action="task.updated",
        entity_type="Task",
        entity_id=task.id,
        metadata={"status": task.status},
    )
    return TaskOut.model_validate(task)


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.TASKS_DELETE)
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundError("Task not found")
    authorize(ctx, Permission.TASKS_DELETE, task)
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
    authorize(ctx, Permission.TASKS_UPDATE)
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundError("Task not found")
    authorize(ctx, Permission.TASKS_UPDATE, task)

    comment = TaskComment(task_id=task_id, author_id=ctx.current_user.id, content=body.content)
    db.add(comment)
    await db.flush()
    return TaskCommentOut.model_validate(comment)


@router.get("/tasks/{task_id}/comments")
async def list_comments(
    task_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    from app.schemas import TaskCommentOut

    authorize(ctx, Permission.TASKS_READ)
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundError("Task not found")
    authorize(ctx, Permission.TASKS_READ, task)

    comments = await db.execute(
        select(TaskComment).where(TaskComment.task_id == task_id).order_by(TaskComment.created_at)
    )
    return [TaskCommentOut.model_validate(c) for c in comments.scalars().all()]
