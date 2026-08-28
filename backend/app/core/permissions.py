from enum import Enum


class Permission(str, Enum):
    PLATFORM_ORG_CREATE = "platform.org.create"
    PLATFORM_ORG_DEACTIVATE = "platform.org.deactivate"
    PLATFORM_ANALYTICS_READ = "platform.analytics.read"

    ORG_SETTINGS_READ = "org.settings.read"
    ORG_SETTINGS_WRITE = "org.settings.write"
    MEMBERS_MANAGE = "members.manage"
    LABS_MANAGE = "labs.manage"
    TASKS_READ = "tasks.read"
    TASKS_CREATE = "tasks.create"
    TASKS_UPDATE = "tasks.update"
    TASKS_DELETE = "tasks.delete"
    TASKS_ASSIGN = "tasks.assign"
    TOOLS_READ = "tools.read"
    TOOLS_MANAGE = "tools.manage"
    TOOLS_GRANT = "tools.grant"
    TOOLS_REVOKE = "tools.revoke"
    TOOLS_LAUNCH = "tools.launch"
    TOOLS_REQUEST = "tools.request"
    AUDIT_READ = "audit.read"
    INVITATIONS_CREATE = "invitations.create"
    LAB_MEMBERS_READ = "lab.members.read"
    LAB_MEMBERS_MANAGE = "lab.members.manage"
    GOOGLE_WORKSPACE_MANAGE = "google_workspace.manage"
    GOOGLE_WORKSPACE_USE = "google_workspace.use"


PLATFORM_ROLE = "STAFF"

PLATFORM_PERMISSIONS: set[Permission] = {
    Permission.PLATFORM_ORG_CREATE,
    Permission.PLATFORM_ORG_DEACTIVATE,
    Permission.PLATFORM_ANALYTICS_READ,
}

# Effective role names map to permissions (Admin = org-level; Manager/Contributor = lab-level)
ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    "Admin": {
        Permission.ORG_SETTINGS_READ,
        Permission.ORG_SETTINGS_WRITE,
        Permission.MEMBERS_MANAGE,
        Permission.LABS_MANAGE,
        Permission.TASKS_READ,
        Permission.INVITATIONS_CREATE,
        Permission.AUDIT_READ,
        Permission.TOOLS_READ,
        Permission.TOOLS_MANAGE,
        Permission.LAB_MEMBERS_READ,
        Permission.LAB_MEMBERS_MANAGE,
        Permission.GOOGLE_WORKSPACE_MANAGE,
        Permission.GOOGLE_WORKSPACE_USE,
    },
    "Manager": {
        Permission.TASKS_READ,
        Permission.TASKS_CREATE,
        Permission.TASKS_UPDATE,
        Permission.TASKS_DELETE,
        Permission.TASKS_ASSIGN,
        Permission.TOOLS_READ,
        Permission.TOOLS_GRANT,
        Permission.TOOLS_REVOKE,
        Permission.TOOLS_LAUNCH,
        Permission.LAB_MEMBERS_READ,
        Permission.GOOGLE_WORKSPACE_USE,
    },
    "Contributor": {
        Permission.TASKS_READ,
        Permission.TASKS_CREATE,
        Permission.TASKS_UPDATE,
        Permission.TASKS_DELETE,
        Permission.TASKS_ASSIGN,
        Permission.TOOLS_READ,
        Permission.TOOLS_LAUNCH,
        Permission.TOOLS_REQUEST,
        Permission.LAB_MEMBERS_READ,
        Permission.GOOGLE_WORKSPACE_USE,
    },
}


def is_staff(user) -> bool:
    return getattr(user, "platform_role", None) == PLATFORM_ROLE


def authorize_platform(user, permission: Permission) -> bool:
    from app.core.errors import ForbiddenError

    if not is_staff(user):
        raise ForbiddenError("Platform access required")
    if permission not in PLATFORM_PERMISSIONS:
        raise ForbiddenError(f"Staff lacks platform permission {permission.value}")
    return True


def role_has_permission(role_name: str, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role_name, set())


def authorize(context, permission: Permission, resource=None, *, lab_role: str | None = None) -> bool:
    from app.core.errors import ForbiddenError

    if not context.current_membership or context.current_membership.status != "ACTIVE":
        raise ForbiddenError("No active membership in this organization")

    effective = context.effective_role(lab_role)
    if not role_has_permission(effective, permission):
        raise ForbiddenError(f"Role {effective} lacks permission {permission.value}")

    if resource is not None and hasattr(resource, "organization_id"):
        if resource.organization_id != context.current_organization.id:
            raise ForbiddenError("Resource belongs to a different organization")

    return True


TASK_TRANSITIONS: dict[str, set[str]] = {
    "BACKLOG": {"TODO"},
    "TODO": {"IN_PROGRESS", "BACKLOG"},
    "IN_PROGRESS": {"BLOCKED", "DONE", "TODO"},
    "BLOCKED": {"IN_PROGRESS"},
    "DONE": set(),
}


def valid_transition(current: str, new: str) -> bool:
    if current == new:
        return True
    return new in TASK_TRANSITIONS.get(current, set())
