"""Seed demo data — lab-scoped roles."""

import asyncio
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.permissions import PLATFORM_ROLE
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

IDS = {
    "jordan": uuid.UUID("11111111-1111-1111-1111-111111111101"),
    "marcus": uuid.UUID("11111111-1111-1111-1111-111111111102"),
    "alice": uuid.UUID("11111111-1111-1111-1111-111111111103"),
    "carol": uuid.UUID("11111111-1111-1111-1111-111111111104"),
    "dave": uuid.UUID("11111111-1111-1111-1111-111111111105"),
    "org_robotics": uuid.UUID("22222222-2222-2222-2222-222222222201"),
    "org_biologics": uuid.UUID("22222222-2222-2222-2222-222222222202"),
    "lab_perception": uuid.UUID("33333333-3333-3333-3333-333333333301"),
    "lab_simulation": uuid.UUID("33333333-3333-3333-3333-333333333302"),
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
            print("Database already seeded. Run make demo-reset to re-seed.")
            return

        users = [
            User(id=IDS["jordan"], name="Jordan Staff", email="jordan@corvinus.dev",
                 status="ACTIVE", platform_role=PLATFORM_ROLE),
            User(id=IDS["marcus"], name="Marcus Admin", email="marcus@corvinus.dev", status="ACTIVE"),
            User(id=IDS["alice"], name="Alice Chen", email="alice@corvinus.dev", status="ACTIVE"),
            User(id=IDS["carol"], name="Carol Wu", email="carol@corvinus.dev", status="ACTIVE"),
            User(id=IDS["dave"], name="Dave Okonkwo", email="dave@corvinus.dev", status="ACTIVE"),
        ]
        session.add_all(users)

        org_a = Organization(id=IDS["org_robotics"], name="Corvinus Robotics", slug="corvinus-robotics", status="ACTIVE")
        org_b = Organization(id=IDS["org_biologics"], name="Corvinus Biologics", slug="corvinus-biologics", status="ACTIVE")
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

        lab_perception = Lab(id=IDS["lab_perception"], organization_id=org_a.id, name="Perception Lab", description="Computer vision & annotation")
        lab_simulation = Lab(id=IDS["lab_simulation"], organization_id=org_a.id, name="Simulation Lab", description="Robotics simulation")
        lab_analysis = Lab(id=IDS["lab_analysis"], organization_id=org_b.id, name="Analysis Lab", description="Data analysis pipeline")
        session.add_all([lab_perception, lab_simulation, lab_analysis])
        await session.flush()

        # Org roles: ADMIN or MEMBER only
        session.add_all([
            OrganizationMembership(user_id=IDS["marcus"], organization_id=org_a.id, role_id=roles_a["Admin"].id, org_role="ADMIN"),
            OrganizationMembership(user_id=IDS["alice"], organization_id=org_a.id, role_id=roles_a["Manager"].id, org_role="MEMBER"),
            OrganizationMembership(user_id=IDS["carol"], organization_id=org_a.id, role_id=roles_a["Contributor"].id, org_role="MEMBER"),
            OrganizationMembership(user_id=IDS["dave"], organization_id=org_a.id, role_id=roles_a["Contributor"].id, org_role="MEMBER"),
            OrganizationMembership(user_id=IDS["dave"], organization_id=org_b.id, role_id=roles_b["Admin"].id, org_role="ADMIN"),
            OrganizationMembership(user_id=IDS["alice"], organization_id=org_b.id, role_id=roles_b["Contributor"].id, org_role="MEMBER"),
        ])

        # Lab roles: MANAGER or CONTRIBUTOR per lab (can differ across orgs and labs)
        session.add_all([
            LabMembership(user_id=IDS["alice"], lab_id=lab_perception.id, role_id=roles_a["Manager"].id, lab_role="MANAGER"),
            LabMembership(user_id=IDS["carol"], lab_id=lab_perception.id, role_id=roles_a["Contributor"].id, lab_role="CONTRIBUTOR"),
            LabMembership(user_id=IDS["dave"], lab_id=lab_perception.id, role_id=roles_a["Manager"].id, lab_role="MANAGER"),
            LabMembership(user_id=IDS["dave"], lab_id=lab_simulation.id, role_id=roles_a["Contributor"].id, lab_role="CONTRIBUTOR"),
            LabMembership(user_id=IDS["alice"], lab_id=lab_analysis.id, role_id=roles_b["Contributor"].id, lab_role="CONTRIBUTOR"),
        ])

        tools_a = [
            Tool(organization_id=org_a.id, name="CVAT", description="Annotation platform", type="cvat", status="ENABLED"),
            Tool(organization_id=org_a.id, name="Isaac Sim", description="Simulation environment", type="isaac_sim", status="ENABLED"),
            Tool(organization_id=org_a.id, name="Protocol Tool", description="Protocol automation", type="protocol_tool", status="ENABLED"),
        ]
        session.add_all(tools_a)
        await session.flush()

        session.add_all([
            Task(organization_id=org_a.id, lab_id=lab_perception.id, title="Label training batch #42",
                 status="TODO", priority="HIGH", assignee_id=IDS["carol"], due_date=date.today()),
            Task(organization_id=org_a.id, lab_id=lab_perception.id, title="Review model metrics",
                 status="IN_PROGRESS", priority="MEDIUM", assignee_id=IDS["carol"]),
            Task(organization_id=org_a.id, lab_id=lab_perception.id, title="Calibrate depth cameras",
                 status="BACKLOG", priority="LOW"),
            Task(organization_id=org_a.id, lab_id=lab_simulation.id, title="Import URDF models",
                 status="DONE", priority="LOW", assignee_id=IDS["dave"]),
            Task(organization_id=org_a.id, lab_id=lab_simulation.id, title="Run grasp simulation",
                 status="IN_PROGRESS", priority="MEDIUM", assignee_id=IDS["dave"]),
            Task(organization_id=org_b.id, lab_id=lab_analysis.id, title="Analyze sequencing data",
                 status="TODO", priority="HIGH", assignee_id=IDS["alice"]),
        ])

        session.add_all([
            ToolAccess(
                tool_id=tools_a[0].id, user_id=IDS["carol"], access_level="view",
                provisioning_status="ACTIVE", granted_by_id=IDS["alice"],
            ),
            ToolAccess(
                tool_id=tools_a[1].id, user_id=IDS["alice"], access_level="view",
                provisioning_status="ACTIVE", granted_by_id=IDS["alice"],
            ),
            ToolAccess(
                tool_id=tools_a[1].id, user_id=IDS["dave"], access_level="view",
                provisioning_status="ACTIVE", granted_by_id=IDS["alice"],
            ),
            ToolAccess(
                tool_id=tools_a[2].id, user_id=IDS["alice"], access_level="view",
                provisioning_status="ACTIVE", granted_by_id=IDS["alice"],
            ),
        ])

        await session.commit()
        print("Seed complete: multi-org roles — Alice=MANAGER@Perception+CONTRIBUTOR@Analysis; Dave=MANAGER@Perception+CONTRIBUTOR@Simulation+ADMIN@Biologics")


if __name__ == "__main__":
    asyncio.run(seed())
