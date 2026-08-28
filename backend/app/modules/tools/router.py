import asyncio
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import TenantContext, write_audit, write_notification
from app.core.auth import get_tenant_context
from app.core.database import async_session_factory, get_db
from app.core.errors import ForbiddenError, NotFoundError
from app.core.permissions import Permission, authorize
from app.models import Tool, ToolAccess, User
from app.schemas import ToolAccessGrant, ToolAccessOut, ToolCreate, ToolHealthOut, ToolLaunchOut, ToolOut, ToolSessionOut, ToolUpdate

router = APIRouter(tags=["tools"])

CATEGORY_TO_CONNECTOR = {
    "annotation": "cvat",
    "simulation": "isaac_sim",
    "protocol": "protocol_tool",
    "data_pipeline": "protocol_tool",
}


async def run_provisioning_job(access_id: uuid.UUID, org_id: uuid.UUID) -> None:
    await asyncio.sleep(0.2)
    async with async_session_factory() as session:
        from app.workers.provisioning import process_access
        await process_access(session, access_id, org_id)
        await session.commit()


def schedule_provisioning(background_tasks: BackgroundTasks, access_id: uuid.UUID, org_id: uuid.UUID) -> None:
    background_tasks.add_task(run_provisioning_job, access_id, org_id)


@router.get("/organizations/{org_id}/tools", response_model=list[ToolOut])
async def list_tools(
    org_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.TOOLS_READ)
    result = await db.execute(select(Tool).where(Tool.organization_id == org_id))
    return [ToolOut.model_validate(t) for t in result.scalars().all()]


@router.post("/organizations/{org_id}/tools", response_model=ToolOut)
async def create_tool(
    org_id: uuid.UUID,
    body: ToolCreate,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.TOOLS_MANAGE)
    connector_type = CATEGORY_TO_CONNECTOR.get(body.category)
    if not connector_type:
        from app.core.errors import APIError
        raise APIError("INVALID_CATEGORY", f"Unknown tool category: {body.category}", 400)

    config = dict(body.connector_config or {})
    if body.service_url:
        config["base_url"] = body.service_url

    tool = Tool(
        organization_id=org_id,
        name=body.name,
        description=body.description,
        type=connector_type,
        connector_config=config,
    )
    db.add(tool)
    await db.flush()
    await write_audit(
        db,
        organization_id=org_id,
        actor_user_id=ctx.current_user.id,
        action="tool.created",
        entity_type="Tool",
        entity_id=tool.id,
    )
    return ToolOut.model_validate(tool)


@router.patch("/tools/{tool_id}", response_model=ToolOut)
async def update_tool(
    tool_id: uuid.UUID,
    body: ToolUpdate,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.TOOLS_MANAGE)
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()
    if not tool:
        raise NotFoundError("Tool not found")
    authorize(ctx, Permission.TOOLS_MANAGE, tool)
    if body.name is not None:
        tool.name = body.name
    if body.description is not None:
        tool.description = body.description
    if body.status is not None:
        tool.status = body.status
    await db.flush()
    return ToolOut.model_validate(tool)


@router.get("/organizations/{org_id}/tool-access")
async def list_tool_access(
    org_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.TOOLS_READ)
    result = await db.execute(
        select(ToolAccess, Tool, User)
        .join(Tool, Tool.id == ToolAccess.tool_id)
        .join(User, User.id == ToolAccess.user_id)
        .where(Tool.organization_id == org_id)
    )
    rows = result.all()
    return [
        {
            "access": ToolAccessOut.model_validate(a),
            "tool_name": t.name,
            "user_name": u.name,
        }
        for a, t, u in rows
    ]


@router.get("/organizations/{org_id}/my-tools")
async def my_tools(
    org_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.TOOLS_READ)
    result = await db.execute(
        select(ToolAccess, Tool)
        .join(Tool, Tool.id == ToolAccess.tool_id)
        .where(ToolAccess.user_id == ctx.current_user.id, Tool.organization_id == org_id)
    )
    return [
        {
            "tool": ToolOut.model_validate(t),
            "access": ToolAccessOut.model_validate(a),
        }
        for a, t in result.all()
    ]


@router.post("/tools/{tool_id}/access", response_model=ToolAccessOut)
async def grant_access(
    tool_id: uuid.UUID,
    body: ToolAccessGrant,
    background_tasks: BackgroundTasks,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.TOOLS_GRANT)
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()
    if not tool:
        raise NotFoundError("Tool not found")
    authorize(ctx, Permission.TOOLS_GRANT, tool)

    existing = await db.execute(
        select(ToolAccess).where(ToolAccess.tool_id == tool_id, ToolAccess.user_id == body.user_id)
    )
    if existing.scalar_one_or_none():
        from app.core.errors import ConflictError
        raise ConflictError("Access already exists for this user")

    access = ToolAccess(
        tool_id=tool_id,
        user_id=body.user_id,
        access_level=body.access_level,
        granted_by_id=ctx.current_user.id,
        provisioning_status="REQUESTED",
    )
    db.add(access)
    await db.flush()
    await write_audit(
        db,
        organization_id=tool.organization_id,
        actor_user_id=ctx.current_user.id,
        action="tool_access.granted",
        entity_type="ToolAccess",
        entity_id=access.id,
    )
    schedule_provisioning(background_tasks, access.id, tool.organization_id)
    return ToolAccessOut.model_validate(access)


@router.post("/tools/{tool_id}/access/request", response_model=ToolAccessOut)
async def request_access(
    tool_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.TOOLS_REQUEST)
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()
    if not tool:
        raise NotFoundError("Tool not found")
    authorize(ctx, Permission.TOOLS_REQUEST, tool)

    existing = await db.execute(
        select(ToolAccess).where(ToolAccess.tool_id == tool_id, ToolAccess.user_id == ctx.current_user.id)
    )
    if existing.scalar_one_or_none():
        from app.core.errors import ConflictError
        raise ConflictError("Access already requested or granted")

    access = ToolAccess(
        tool_id=tool_id,
        user_id=ctx.current_user.id,
        access_level="view",
        provisioning_status="REQUESTED",
    )
    db.add(access)
    await db.flush()
    schedule_provisioning(background_tasks, access.id, tool.organization_id)
    return ToolAccessOut.model_validate(access)


@router.delete("/tools/{tool_id}/access/{user_id}")
async def revoke_access(
    tool_id: uuid.UUID,
    user_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    authorize(ctx, Permission.TOOLS_REVOKE)
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()
    if not tool:
        raise NotFoundError("Tool not found")
    authorize(ctx, Permission.TOOLS_REVOKE, tool)

    access_result = await db.execute(
        select(ToolAccess).where(ToolAccess.tool_id == tool_id, ToolAccess.user_id == user_id)
    )
    access = access_result.scalar_one_or_none()
    if not access:
        raise NotFoundError("Access not found")

    access.provisioning_status = "REVOKING"
    await db.flush()
    schedule_provisioning(background_tasks, access.id, tool.organization_id)
    await write_audit(
        db,
        organization_id=tool.organization_id,
        actor_user_id=ctx.current_user.id,
        action="tool_access.revoked",
        entity_type="ToolAccess",
        entity_id=access.id,
    )
    return {"status": "REVOKING"}


@router.post("/tools/{tool_id}/launch", response_model=ToolLaunchOut)
async def launch_tool(
    tool_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    from app.connectors.registry import get_connector

    authorize(ctx, Permission.TOOLS_LAUNCH)
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()
    if not tool:
        raise NotFoundError("Tool not found")
    authorize(ctx, Permission.TOOLS_LAUNCH, tool)

    access_result = await db.execute(
        select(ToolAccess).where(
            ToolAccess.tool_id == tool_id,
            ToolAccess.user_id == ctx.current_user.id,
            ToolAccess.provisioning_status == "ACTIVE",
        )
    )
    if not access_result.scalar_one_or_none():
        raise ForbiddenError("No active access to this tool")

    connector = get_connector(tool.type)
    url = await connector.launch(tool, ctx.current_user)
    return ToolLaunchOut(launch_url=url)


@router.get("/tools/{tool_id}/session", response_model=ToolSessionOut)
async def get_tool_session(
    tool_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    from app.connectors.registry import get_connector

    authorize(ctx, Permission.TOOLS_LAUNCH)
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()
    if not tool:
        raise NotFoundError("Tool not found")
    authorize(ctx, Permission.TOOLS_LAUNCH, tool)

    access_result = await db.execute(
        select(ToolAccess).where(
            ToolAccess.tool_id == tool_id,
            ToolAccess.user_id == ctx.current_user.id,
            ToolAccess.provisioning_status == "ACTIVE",
        )
    )
    if not access_result.scalar_one_or_none():
        raise ForbiddenError("No active access to this tool")

    connector = get_connector(tool.type)
    launch_url = await connector.launch(tool, ctx.current_user)
    session_data = {}
    if hasattr(connector, "session_data"):
        session_data = await connector.session_data(tool, ctx.current_user)

    return ToolSessionOut(
        tool_id=tool.id,
        tool_name=tool.name,
        tool_type=tool.type,
        launch_url=launch_url,
        status="ACTIVE",
        session=session_data,
    )


@router.get("/tools/{tool_id}/health", response_model=ToolHealthOut)
async def tool_health(
    tool_id: uuid.UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    from app.connectors.registry import get_connector

    authorize(ctx, Permission.TOOLS_READ)
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()
    if not tool:
        raise NotFoundError("Tool not found")
    authorize(ctx, Permission.TOOLS_READ, tool)

    connector = get_connector(tool.type)
    healthy = await connector.health_check(tool)
    return ToolHealthOut(
        tool_id=tool.id,
        healthy=healthy,
        connector_type=tool.type,
        message="Connector reachable" if healthy else "Connector unavailable",
    )
