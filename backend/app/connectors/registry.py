import asyncio
import random

from app.connectors.base import ToolConnector
from app.models import Tool, ToolAccess, User


class CVATMockConnector:
    connector_type = "cvat"

    def capabilities(self) -> set[str]:
        return {"provision", "revoke", "launch", "health_check"}

    async def provision(self, access: ToolAccess, tool: Tool, user: User) -> None:
        await asyncio.sleep(random.uniform(2, 5))
        if random.random() < 0.1:
            raise RuntimeError("CVAT provisioning failed: simulated external error")

    async def revoke(self, access: ToolAccess, tool: Tool, user: User) -> None:
        await asyncio.sleep(1)

    async def launch(self, tool: Tool, user: User) -> str:
        return f"https://cvat.example.com/projects?user={user.email}&tool={tool.id}"

    async def health_check(self, tool: Tool) -> bool:
        return True


class IsaacSimMockConnector:
    connector_type = "isaac_sim"

    def capabilities(self) -> set[str]:
        return {"launch", "health_check"}

    async def provision(self, access: ToolAccess, tool: Tool, user: User) -> None:
        pass

    async def revoke(self, access: ToolAccess, tool: Tool, user: User) -> None:
        pass

    async def launch(self, tool: Tool, user: User) -> str:
        return f"https://isaac-sim.example.com/session?user={user.email}"

    async def health_check(self, tool: Tool) -> bool:
        return True


class GoogleDriveMockConnector:
    connector_type = "google_drive"

    def capabilities(self) -> set[str]:
        return {"launch", "health_check"}

    async def provision(self, access: ToolAccess, tool: Tool, user: User) -> None:
        await asyncio.sleep(1)

    async def revoke(self, access: ToolAccess, tool: Tool, user: User) -> None:
        pass

    async def launch(self, tool: Tool, user: User) -> str:
        return f"https://drive.google.com/mock/{tool.id}?user={user.email}"

    async def health_check(self, tool: Tool) -> bool:
        return True


CONNECTORS = {
    "cvat": CVATMockConnector(),
    "isaac_sim": IsaacSimMockConnector(),
    "google_drive": GoogleDriveMockConnector(),
}


def get_connector(tool_type: str) -> ToolConnector:
    connector = CONNECTORS.get(tool_type)
    if not connector:
        return GoogleDriveMockConnector()
    return connector
