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

    async def session_data(self, tool: Tool, user: User) -> dict:
        return {
            "projects": [
                {"id": "p1", "name": "Object Detection v2", "tasks": 12, "completed": 8},
                {"id": "p2", "name": "Segmentation batch", "tasks": 45, "completed": 30},
            ],
            "active_jobs": 2,
            "user": user.email,
        }


class IsaacSimMockConnector:
    connector_type = "isaac_sim"

    def capabilities(self) -> set[str]:
        return {"provision", "revoke", "launch", "health_check"}

    async def provision(self, access: ToolAccess, tool: Tool, user: User) -> None:
        await asyncio.sleep(2)

    async def revoke(self, access: ToolAccess, tool: Tool, user: User) -> None:
        await asyncio.sleep(0.5)

    async def launch(self, tool: Tool, user: User) -> str:
        base = (tool.connector_config or {}).get("base_url", "https://isaac-sim.example.com")
        return f"{base}/session?user={user.email}&tool={tool.id}"

    async def health_check(self, tool: Tool) -> bool:
        return True

    async def session_data(self, tool: Tool, user: User) -> dict:
        return {
            "scene": "warehouse_grasp.usd",
            "gpu": "NVIDIA A100 (mock)",
            "physics_hz": 60,
            "robots": ["franka_panda", "ur5e"],
            "status": "ready",
            "user": user.email,
        }


class ProtocolToolMockConnector:
    connector_type = "protocol_tool"

    def capabilities(self) -> set[str]:
        return {"provision", "launch", "health_check"}

    async def provision(self, access: ToolAccess, tool: Tool, user: User) -> None:
        await asyncio.sleep(1)

    async def revoke(self, access: ToolAccess, tool: Tool, user: User) -> None:
        pass

    async def launch(self, tool: Tool, user: User) -> str:
        return f"https://protocol.corvinus.dev/run?tool={tool.id}&user={user.email}"

    async def health_check(self, tool: Tool) -> bool:
        return True

    async def session_data(self, tool: Tool, user: User) -> dict:
        return {
            "protocols": [
                {"id": "sop-001", "name": "Cell culture passage", "version": "2.1"},
                {"id": "sop-002", "name": "PCR amplification", "version": "1.4"},
            ],
            "active_runs": 1,
            "user": user.email,
        }


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
    "protocol_tool": ProtocolToolMockConnector(),
    "google_drive": GoogleDriveMockConnector(),
}

CONNECTOR_META = [
    {"type": "cvat", "label": "CVAT", "capabilities": ["provision", "revoke", "launch", "health_check"]},
    {"type": "isaac_sim", "label": "Isaac Sim", "capabilities": ["provision", "revoke", "launch", "health_check"]},
    {"type": "protocol_tool", "label": "Protocol Tool", "capabilities": ["provision", "launch", "health_check"]},
    {"type": "google_drive", "label": "Google Drive (legacy tool row)", "capabilities": ["launch", "health_check"]},
]


def get_connector(tool_type: str) -> ToolConnector:
    connector = CONNECTORS.get(tool_type)
    if not connector:
        return GoogleDriveMockConnector()
    return connector
