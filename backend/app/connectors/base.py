from typing import Protocol

from app.models import Tool, ToolAccess, User


class ToolConnector(Protocol):
    connector_type: str

    def capabilities(self) -> set[str]: ...

    async def provision(self, access: ToolAccess, tool: Tool, user: User) -> None: ...

    async def revoke(self, access: ToolAccess, tool: Tool, user: User) -> None: ...

    async def launch(self, tool: Tool, user: User) -> str: ...

    async def health_check(self, tool: Tool) -> bool: ...
