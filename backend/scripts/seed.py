"""Seed demo data for Corvinus Labs portal."""

import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models import (
    Lab,
    LabMembership,
    Organization,
    OrganizationMembership,
    OrganizationSettings,
    Role,
    Task,
    Tool,
    ToolAccess,
    User,
)

engine = create_async_engine(settings.database_url, echo=False)
Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Fixed UUIDs for reproducible demo
IDS = {
    "alice": uuid.UUID("11111111-1111-1111-1111-111111111101"),
    "bob": uuid.UUID("11111111-1111-1111-1111-111111111102"),
    "carol": uuid.UUID("11111111-1111-1111-1111-111111111103"),
    "dave": uuid.UUID("11111111-1111-1111-1111-111111111104"),
    "eve": uuid.UUID("11111111-1111-1111-1111-111111111105"),
    "frank": uuid.UUID("11111111-1111-1111-1111-111111111106"),
    "org_a": uuid.UUID("22222222-2222-2222-2222-222222222201"),
    "org_b": uuid.UUID("22222222-2222-2222-2222-222222222202"),
    "lab_perception": uuid.UUID("33333333-3333-3333-3333-333333333301"),
    "lab_simulation": uuid.UUID("33333333-3333-3333-3333-333333333302"),
    "lab_wet": uuid.UUID("33333333-3333-3333-3333-333333333303"),
    "lab_analysis": uuid.UUID("33333333-3333-3333-3333-333333333304"),
}


async def get_or_create_role(session: AsyncSession, org_id: uuid.UUID, name: str) -> Role:
    result = await session.execute(
        select(Role).where(Role.organization_id == org_id, Role.name == name)
    )
    role = result.scalar_one_or_none()
    if role:
        return role
    role = Role(organization_id=org_id, name=name, description=f"{name} role")
    session.add(role)
    await session.flush()
    return role


async def seed() -> None:
    async with Session() as session:
        existing = await session.execute(select(User).limit(1))
        if existing.scalar_one_or_none():
            print("Database already seeded, skipping.")
            return

        users = [
            User(id=IDS["alice"], name="Alice Chen", email="alice@corvinus.dev", status="ACTIVE"),
            User(id=IDS["bob"], name="Bob Martinez", email="bob@corvinus.dev", status="ACTIVE"),
            User(id=IDS["carol"], name="Carol Wu", email="carol@corvinus.dev", status="ACTIVE"),
            User(id=IDS["dave"], name="Dave Okonkwo", email="dave@corvinus.dev", status="ACTIVE"),
            User(id=IDS["eve"], name="Eve Nakamura", email="eve@corvinus.dev", status="ACTIVE"),
            User(id=IDS["frank"], name="Frank Liu", email="frank@corvinus.dev", status="ACTIVE"),
        ]
        session.add_all(users)

        org_a = Organization(
            id=IDS["org_a"], name="Corvinus Robotics", slug="corvinus-robotics", status="ACTIVE"
        )
        org_b = Organization(
            id=IDS["org_b"], name="Corvinus Biologics", slug="corvinus-biologics", status="ACTIVE"
        )
        session.add_all([org_a, org_b])
        await session.flush()

        for org in [org_a, org_b]:
            session.add(OrganizationSettings(organization_id=org.id))

        roles_a = {
            "Admin": await get_or_create_role(session, org_a.id, "Admin"),
            "Manager": await get_or_create_role(session, org_a.id, "Manager"),
            "Contributor": await get_or_create_role(session, org_a.id, "Contributor"),
        }
        roles_b = {
            "Admin": await get_or_create_role(session, org_b.id, "Admin"),
            "Manager": await get_or_create_role(session, org_b.id, "Manager"),
            "Contributor": await get_or_create_role(session, org_b.id, "Contributor"),
        }

        lab_perception = Lab(
            id=IDS["lab_perception"], organization_id=org_a.id,
            name="Perception Lab", description="Computer vision research"
        )
        lab_simulation = Lab(
            id=IDS["lab_simulation"], organization_id=org_a.id,
            name="Simulation Lab", description="Robotics simulation"
        )
        lab_wet = Lab(
            id=IDS["lab_wet"], organization_id=org_b.id,
            name="Wet Lab", description="Wet lab experiments"
        )
        lab_analysis = Lab(
            id=IDS["lab_analysis"], organization_id=org_b.id,
            name="Analysis Lab", description="Data analysis"
        )
        session.add_all([lab_perception, lab_simulation, lab_wet, lab_analysis])
        await session.flush()

        memberships = [
            OrganizationMembership(user_id=IDS["alice"], organization_id=org_a.id, role_id=roles_a["Admin"].id),
            OrganizationMembership(user_id=IDS["bob"], organization_id=org_a.id, role_id=roles_a["Manager"].id),
            OrganizationMembership(user_id=IDS["carol"], organization_id=org_a.id, role_id=roles_a["Contributor"].id),
            OrganizationMembership(user_id=IDS["dave"], organization_id=org_a.id, role_id=roles_a["Contributor"].id),
            OrganizationMembership(user_id=IDS["alice"], organization_id=org_b.id, role_id=roles_b["Manager"].id),
            OrganizationMembership(user_id=IDS["eve"], organization_id=org_b.id, role_id=roles_b["Admin"].id),
            OrganizationMembership(user_id=IDS["frank"], organization_id=org_b.id, role_id=roles_b["Contributor"].id),
        ]
        session.add_all(memberships)

        lab_memberships = [
            LabMembership(user_id=IDS["bob"], lab_id=lab_perception.id, role_id=roles_a["Manager"].id),
            LabMembership(user_id=IDS["carol"], lab_id=lab_perception.id, role_id=roles_a["Contributor"].id),
            LabMembership(user_id=IDS["dave"], lab_id=lab_simulation.id, role_id=roles_a["Contributor"].id),
            LabMembership(user_id=IDS["alice"], lab_id=lab_wet.id, role_id=roles_b["Manager"].id),
            LabMembership(user_id=IDS["frank"], lab_id=lab_analysis.id, role_id=roles_b["Contributor"].id),
        ]
        session.add_all(lab_memberships)

        tools_a = [
            Tool(organization_id=org_a.id, name="CVAT", description="Annotation tool", type="cvat", status="ENABLED"),
            Tool(organization_id=org_a.id, name="Isaac Sim", description="Simulation", type="isaac_sim", status="ENABLED"),
            Tool(organization_id=org_a.id, name="Google Drive", description="File storage", type="google_drive", status="ENABLED"),
        ]
        tools_b = [
            Tool(organization_id=org_b.id, name="CVAT", description="Annotation tool", type="cvat", status="ENABLED"),
            Tool(organization_id=org_b.id, name="Google Drive", description="File storage", type="google_drive", status="ENABLED"),
        ]
        session.add_all(tools_a + tools_b)
        await session.flush()

        tasks = [
            Task(organization_id=org_a.id, lab_id=lab_perception.id, title="Calibrate depth cameras",
                 status="BACKLOG", priority="HIGH", assignee_id=IDS["carol"]),
            Task(organization_id=org_a.id, lab_id=lab_perception.id, title="Label training batch #42",
                 status="TODO", priority="MEDIUM", assignee_id=IDS["carol"], due_date=date.today()),
            Task(organization_id=org_a.id, lab_id=lab_perception.id, title="Review model metrics",
                 status="IN_PROGRESS", priority="HIGH", assignee_id=IDS["carol"]),
            Task(organization_id=org_a.id, lab_id=lab_perception.id, title="Fix annotation pipeline",
                 status="BLOCKED", priority="URGENT", assignee_id=IDS["bob"]),
            Task(organization_id=org_a.id, lab_id=lab_simulation.id, title="Import URDF models",
                 status="DONE", priority="LOW", assignee_id=IDS["dave"]),
            Task(organization_id=org_a.id, lab_id=lab_simulation.id, title="Run grasp simulation",
                 status="IN_PROGRESS", priority="MEDIUM", assignee_id=IDS["dave"]),
            Task(organization_id=org_b.id, lab_id=lab_wet.id, title="Prepare cell cultures",
                 status="TODO", priority="HIGH", assignee_id=IDS["alice"]),
            Task(organization_id=org_b.id, lab_id=lab_analysis.id, title="Analyze sequencing data",
                 status="IN_PROGRESS", priority="MEDIUM", assignee_id=IDS["frank"]),
            Task(organization_id=org_b.id, lab_id=lab_analysis.id, title="Update lab notebook",
                 status="BACKLOG", priority="LOW", assignee_id=IDS["frank"]),
        ]
        session.add_all(tasks)

        tool_access = [
            ToolAccess(tool_id=tools_a[0].id, user_id=IDS["carol"], access_level="view",
                       provisioning_status="ACTIVE", granted_by_id=IDS["bob"]),
            ToolAccess(tool_id=tools_a[1].id, user_id=IDS["dave"], access_level="view",
                       provisioning_status="FAILED", failure_reason="Isaac Sim node unavailable",
                       granted_by_id=IDS["bob"]),
            ToolAccess(tool_id=tools_b[0].id, user_id=IDS["frank"], access_level="view",
                       provisioning_status="PROVISIONING", granted_by_id=IDS["eve"]),
        ]
        session.add_all(tool_access)

        from app.core.audit import write_audit
        await write_audit(
            session,
            organization_id=org_a.id,
            actor_user_id=IDS["alice"],
            action="organization.created",
            entity_type="Organization",
            entity_id=org_a.id,
        )
        await write_audit(
            session,
            organization_id=org_a.id,
            actor_user_id=IDS["bob"],
            action="tool_access.granted",
            entity_type="ToolAccess",
            metadata={"tool": "CVAT", "user": "Carol Wu"},
        )

        await session.commit()
        print("Seed complete: 2 orgs, 6 users, 4 labs, 9 tasks, 5 tools, 3 tool access records")


if __name__ == "__main__":
    asyncio.run(seed())
