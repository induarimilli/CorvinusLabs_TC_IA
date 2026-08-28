"""Async tool access provisioning/revocation (connector mock + status updates)."""

import asyncio
import json
import uuid

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.connectors.registry import get_connector
from app.core.config import settings
from app.models import Tool, ToolAccess, User

engine = create_async_engine(settings.database_url, echo=False)
session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def process_access(session: AsyncSession, access_id: uuid.UUID, org_id: uuid.UUID) -> None:
    result = await session.execute(
        select(ToolAccess).where(ToolAccess.id == access_id)
    )
    access = result.scalar_one_or_none()
    if not access:
        return

    tool_result = await session.execute(select(Tool).where(Tool.id == access.tool_id))
    tool = tool_result.scalar_one_or_none()
    if not tool or tool.organization_id != org_id:
        return

    user_result = await session.execute(select(User).where(User.id == access.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return

    connector = get_connector(tool.type)
    status = access.provisioning_status

    if status == "REQUESTED":
        access.provisioning_status = "PROVISIONING"
        await session.commit()

        if "provision" in connector.capabilities():
            try:
                await connector.provision(access, tool, user)
                access.provisioning_status = "ACTIVE"
                access.access_level = "view"
            except Exception as e:
                access.provisioning_status = "FAILED"
                access.failure_reason = str(e)
        else:
            access.provisioning_status = "ACTIVE"
            access.access_level = "view"
        await session.commit()

    elif status == "PENDING_APPROVAL":
        return

    elif status == "REVOKING":
        if "revoke" in connector.capabilities():
            try:
                await connector.revoke(access, tool, user)
            except Exception:
                pass
        access.provisioning_status = "REVOKED"
        await session.commit()


async def run_worker() -> None:
    r = aioredis.from_url(settings.redis_url)
    print("Tool provisioning worker started")
    while True:
        try:
            item = await r.brpop("tool_provisioning", timeout=5)
            if not item:
                continue
            payload = json.loads(item[1])
            access_id = uuid.UUID(payload["access_id"])
            org_id = uuid.UUID(payload["organization_id"])
            async with session_factory() as session:
                await process_access(session, access_id, org_id)
        except Exception as e:
            print(f"Worker error: {e}")
        await asyncio.sleep(0.1)


if __name__ == "__main__":
    asyncio.run(run_worker())
