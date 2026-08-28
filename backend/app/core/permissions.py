from enum import Enum


class Permission(str, Enum):
    ORG_SETTINGS_READ = "org.settings.read"
    ORG_SETTINGS_WRITE = "org.settings.write"
    MEMBERS_INVITE = "members.invite"
    MEMBERS_MANAGE = "members.manage"
    LABS_MANAGE = "labs.manage"
    TASKS_READ = "tasks.read"
    TASKS_CREATE = "tasks.create"
    TASKS_UPDATE = "tasks.update"
    TASKS_DELETE = "tasks.delete"
    TOOLS_READ = "tools.read"
    TOOLS_MANAGE = "tools.manage"
    TOOLS_GRANT = "tools.grant"
    TOOLS_REVOKE = "tools.revoke"
    TOOLS_REQUEST = "tools.request"
    TOOLS_LAUNCH = "tools.launch"
    AUDIT_READ = "audit.read"
    INVITATIONS_CREATE = "invitations.create"


ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    "Admin": {
        Permission.ORG_SETTINGS_READ,
        Permission.ORG_SETTINGS_WRITE,
        Permission.MEMBERS_INVITE,
        Permission.MEMBERS_MANAGE,
        Permission.LABS_MANAGE,
        Permission.TASKS_READ,
        Permission.TASKS_CREATE,
        Permission.TASKS_UPDATE,
        Permission.TASKS_DELETE,
        Permission.TOOLS_READ,
        Permission.TOOLS_MANAGE,
        Permission.TOOLS_GRANT,
        Permission.TOOLS_REVOKE,
        Permission.TOOLS_LAUNCH,
        Permission.AUDIT_READ,
        Permission.INVITATIONS_CREATE,
    },
    "Manager": {
        Permission.TASKS_READ,
        Permission.TASKS_CREATE,
        Permission.TASKS_UPDATE,
        Permission.TASKS_DELETE,
        Permission.TOOLS_READ,
        Permission.TOOLS_GRANT,
        Permission.TOOLS_REVOKE,
        Permission.TOOLS_LAUNCH,
        Permission.MEMBERS_INVITE,
        Permission.INVITATIONS_CREATE,
    },
    "Contributor": {
        Permission.TASKS_READ,
        Permission.TASKS_UPDATE,
        Permission.TOOLS_READ,
        Permission.TOOLS_REQUEST,
        Permission.TOOLS_LAUNCH,
    },
}


def role_has_permission(role_name: str, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role_name, set())


def authorize(context, permission: Permission, resource=None) -> bool:
    from app.core.errors import ForbiddenError

    if not context.current_membership or context.current_membership.status != "ACTIVE":
        raise ForbiddenError("No active membership in this organization")

    if not role_has_permission(context.current_role.name, permission):
        raise ForbiddenError(f"Role {context.current_role.name} lacks permission {permission.value}")

    if resource is not None and hasattr(resource, "organization_id"):
        if resource.organization_id != context.current_organization.id:
            raise ForbiddenError("Resource belongs to a different organization")

    return True
