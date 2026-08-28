"""Lab onboarding and tool policy helpers."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Lab, LabOnboardingProgress, LabToolPolicy, Tool, ToolAccess

ONBOARDING_CHECKLIST = {
    "simulation": [
        {"id": "launch_isaac", "label": "Launch Isaac Sim from App Launcher"},
        {"id": "launch_protocol", "label": "Launch Protocol Tool (Corvinus Labs)"},
        {"id": "create_task", "label": "Add a task to your lab board"},
        {"id": "visit_team", "label": "Visit Team to see lab members"},
    ],
    "perception": [
        {"id": "launch_cvat", "label": "Launch CVAT from App Launcher"},
        {"id": "create_task", "label": "Add an annotation task to the board"},
        {"id": "visit_team", "label": "Visit Team to see lab members"},
    ],
    "default": [
        {"id": "explore_tools", "label": "Open App Launcher and explore available tools"},
        {"id": "create_task", "label": "Add a task to your lab board"},
        {"id": "visit_team", "label": "Visit Team to see lab members"},
    ],
}

# Scavenger hunt: each step has a route where its card appears.
# advance="button" → user clicks Continue; advance="navigate" → completes when highlight_nav is visited.
ONBOARDING_STEPS = {
    "simulation": [
        {
            "id": "welcome",
            "title": "Welcome to Simulation Lab",
            "content": "You're joining as a Contributor. This quick scavenger hunt will show you where everything lives.",
            "route": "/",
            "highlight_nav": None,
            "advance": "button",
        },
        {
            "id": "find_app_launcher",
            "title": "Find App Launcher",
            "content": "Click **App Launcher** in the sidebar. Isaac Sim and the Corvinus Labs Protocol Tool will be ready after you finish onboarding.",
            "route": "/",
            "highlight_nav": "/tools",
            "advance": "navigate",
        },
        {
            "id": "explore_tools",
            "title": "Research Tools",
            "content": "This is your App Launcher. Starter tools can be launched directly; CVAT requires a manager approval request.",
            "route": "/tools",
            "highlight_nav": None,
            "advance": "button",
        },
        {
            "id": "find_tasks",
            "title": "Find the Task Board",
            "content": "Click **Tasks** in the sidebar to see your lab's work board.",
            "route": "/tools",
            "highlight_nav": "/tasks",
            "advance": "navigate",
        },
        {
            "id": "explore_tasks",
            "title": "Task Board",
            "content": "Create and track simulation work here. Use **New Task** to add items to the board.",
            "route": "/tasks",
            "highlight_nav": None,
            "advance": "button",
        },
        {
            "id": "checklist",
            "title": "Your contributor checklist",
            "content": "Complete these tasks in your first week. Finish onboarding to unlock your starter tools.",
            "route": "/tasks",
            "highlight_nav": None,
            "advance": "complete",
        },
    ],
    "perception": [
        {
            "id": "welcome",
            "title": "Welcome to Perception Lab",
            "content": "You're joining as a Contributor focused on computer vision and annotation. Let's explore the portal.",
            "route": "/",
            "highlight_nav": None,
            "advance": "button",
        },
        {
            "id": "find_app_launcher",
            "title": "Find App Launcher",
            "content": "Click **App Launcher** in the sidebar. CVAT will be ready to launch after onboarding.",
            "route": "/",
            "highlight_nav": "/tools",
            "advance": "navigate",
        },
        {
            "id": "explore_tools",
            "title": "Research Tools",
            "content": "CVAT is your starter annotation tool. Isaac Sim and Protocol Tool require manager approval.",
            "route": "/tools",
            "highlight_nav": None,
            "advance": "button",
        },
        {
            "id": "find_tasks",
            "title": "Find the Task Board",
            "content": "Click **Tasks** in the sidebar to view labeling queues and review work.",
            "route": "/tools",
            "highlight_nav": "/tasks",
            "advance": "navigate",
        },
        {
            "id": "explore_tasks",
            "title": "Task Board",
            "content": "Track annotation and review work here. Use **New Task** to add items to the board.",
            "route": "/tasks",
            "highlight_nav": None,
            "advance": "button",
        },
        {
            "id": "checklist",
            "title": "Your contributor checklist",
            "content": "Complete these tasks in your first week. Finish onboarding to unlock CVAT.",
            "route": "/tasks",
            "highlight_nav": None,
            "advance": "complete",
        },
    ],
    "default": [
        {
            "id": "welcome",
            "title": "Welcome",
            "content": "Complete this scavenger hunt to learn the portal layout.",
            "route": "/",
            "highlight_nav": None,
            "advance": "button",
        },
        {
            "id": "find_app_launcher",
            "title": "Find App Launcher",
            "content": "Click **App Launcher** in the sidebar.",
            "route": "/",
            "highlight_nav": "/tools",
            "advance": "navigate",
        },
        {
            "id": "explore_tools",
            "title": "Research Tools",
            "content": "Access lab tools from here once onboarding is complete.",
            "route": "/tools",
            "highlight_nav": None,
            "advance": "button",
        },
        {
            "id": "find_tasks",
            "title": "Find Tasks",
            "content": "Click **Tasks** in the sidebar.",
            "route": "/tools",
            "highlight_nav": "/tasks",
            "advance": "navigate",
        },
        {
            "id": "explore_tasks",
            "title": "Task Board",
            "content": "View and create work items for your lab.",
            "route": "/tasks",
            "highlight_nav": None,
            "advance": "button",
        },
        {
            "id": "checklist",
            "title": "Your contributor checklist",
            "content": "Tasks to complete in your first week.",
            "route": "/tasks",
            "highlight_nav": None,
            "advance": "complete",
        },
    ],
}


def lab_onboarding_key(lab_name: str) -> str:
    name = lab_name.lower()
    if "simulation" in name:
        return "simulation"
    if "perception" in name:
        return "perception"
    return "default"


def get_steps_for_lab(lab_name: str) -> list[dict]:
    return ONBOARDING_STEPS[lab_onboarding_key(lab_name)]


def get_checklist_for_lab(lab_name: str) -> list[dict]:
    return ONBOARDING_CHECKLIST[lab_onboarding_key(lab_name)]


def current_step(steps: list[dict], completed: list[str]) -> dict | None:
    for step in steps:
        if step["id"] not in completed:
            return step
    return None


async def get_lab_policies(session: AsyncSession, lab_id: uuid.UUID) -> dict[str, str]:
    result = await session.execute(select(LabToolPolicy).where(LabToolPolicy.lab_id == lab_id))
    return {p.tool_type: p.access_mode for p in result.scalars().all()}


async def grant_onboarding_tools(
    session: AsyncSession,
    user_id: uuid.UUID,
    lab_id: uuid.UUID,
    org_id: uuid.UUID,
) -> list[uuid.UUID]:
    policies = await get_lab_policies(session, lab_id)
    auto_types = [t for t, mode in policies.items() if mode == "AUTO_ONBOARD"]
    if not auto_types:
        return []

    tools_result = await session.execute(
        select(Tool).where(Tool.organization_id == org_id, Tool.type.in_(auto_types), Tool.status == "ENABLED")
    )
    tools = tools_result.scalars().all()
    access_ids: list[uuid.UUID] = []

    for tool in tools:
        existing = await session.execute(
            select(ToolAccess).where(ToolAccess.tool_id == tool.id, ToolAccess.user_id == user_id)
        )
        if existing.scalar_one_or_none():
            continue
        access = ToolAccess(
            tool_id=tool.id,
            user_id=user_id,
            access_level="view",
            provisioning_status="REQUESTED",
        )
        session.add(access)
        await session.flush()
        access_ids.append(access.id)

    return access_ids


async def ensure_onboarding_record(
    session: AsyncSession,
    user_id: uuid.UUID,
    org_id: uuid.UUID,
    lab_id: uuid.UUID,
    lab_role: str,
) -> LabOnboardingProgress | None:
    if lab_role != "CONTRIBUTOR":
        return None

    existing = await session.execute(
        select(LabOnboardingProgress).where(
            LabOnboardingProgress.user_id == user_id,
            LabOnboardingProgress.lab_id == lab_id,
        )
    )
    record = existing.scalar_one_or_none()
    if record:
        return record

    record = LabOnboardingProgress(
        user_id=user_id,
        organization_id=org_id,
        lab_id=lab_id,
        lab_role=lab_role,
        steps_completed=[],
    )
    session.add(record)
    await session.flush()
    return record


async def pending_onboarding_for_user(
    session: AsyncSession, user_id: uuid.UUID, org_id: uuid.UUID | None = None
) -> list[dict]:
    query = select(LabOnboardingProgress, Lab).join(Lab, Lab.id == LabOnboardingProgress.lab_id).where(
        LabOnboardingProgress.user_id == user_id,
        LabOnboardingProgress.completed_at.is_(None),
        LabOnboardingProgress.lab_role == "CONTRIBUTOR",
    )
    if org_id:
        query = query.where(LabOnboardingProgress.organization_id == org_id)

    result = await session.execute(query)
    return [
        {
            "lab_id": str(p.lab_id),
            "organization_id": str(p.organization_id),
            "lab_name": lab.name,
            "lab_role": p.lab_role,
        }
        for p, lab in result.all()
    ]
