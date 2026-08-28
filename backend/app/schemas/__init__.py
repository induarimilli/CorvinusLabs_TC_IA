import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr


class UserOut(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    avatar_url: str | None
    status: str

    model_config = {"from_attributes": True}


class RoleOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None

    model_config = {"from_attributes": True}


class OrganizationOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None
    plan: str
    status: str

    model_config = {"from_attributes": True}


class LabOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    description: str | None
    archived: bool

    model_config = {"from_attributes": True}


class MembershipOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    organization_id: uuid.UUID
    role_id: uuid.UUID
    role_name: str
    status: str
    joined_at: datetime

    model_config = {"from_attributes": True}


class DemoUserOut(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    organization_name: str
    organization_id: uuid.UUID
    role_name: str
    lab_name: str | None
    lab_id: uuid.UUID | None


class DemoLoginRequest(BaseModel):
    user_id: uuid.UUID
    organization_id: uuid.UUID | None = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    default_organization_id: uuid.UUID
    default_lab_id: uuid.UUID | None


class MeResponse(BaseModel):
    user: UserOut
    memberships: list[MembershipOut]
    organizations: list[OrganizationOut]
    labs: list[LabOut]


class ContextUpdateRequest(BaseModel):
    organization_id: uuid.UUID | None = None
    lab_id: uuid.UUID | None = None


class OrganizationSettingsOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    timezone: str
    date_format: str
    time_format: str
    task_default_assignee_id: uuid.UUID | None

    model_config = {"from_attributes": True}


class OrganizationSettingsUpdate(BaseModel):
    timezone: str | None = None
    date_format: str | None = None
    time_format: str | None = None


class OrganizationUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class LabCreate(BaseModel):
    name: str
    description: str | None = None


class LabUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    archived: bool | None = None


class MemberUpdate(BaseModel):
    role_id: uuid.UUID | None = None
    status: str | None = None


class InvitationCreate(BaseModel):
    email: EmailStr
    role_id: uuid.UUID
    lab_id: uuid.UUID | None = None
    expires_in_days: int = 7


class InvitationOut(BaseModel):
    id: uuid.UUID
    email: str
    role_id: uuid.UUID
    lab_id: uuid.UUID | None
    token: str
    status: str
    expires_at: datetime
    invite_link: str

    model_config = {"from_attributes": True}


class InvitationAcceptRequest(BaseModel):
    name: str | None = None


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    lab_id: uuid.UUID
    assignee_id: uuid.UUID | None = None
    status: str = "BACKLOG"
    priority: str = "MEDIUM"
    due_date: date | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    assignee_id: uuid.UUID | None = None
    status: str | None = None
    priority: str | None = None
    due_date: date | None = None
    version: int


class TaskOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    lab_id: uuid.UUID
    title: str
    description: str | None
    status: str
    priority: str
    assignee_id: uuid.UUID | None
    due_date: date | None
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskCommentCreate(BaseModel):
    content: str


class TaskCommentOut(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    author_id: uuid.UUID
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ToolCreate(BaseModel):
    name: str
    description: str | None = None
    type: str
    connector_config: dict | None = None


class ToolUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None


class ToolOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    description: str | None
    type: str
    status: str

    model_config = {"from_attributes": True}


class ToolAccessGrant(BaseModel):
    user_id: uuid.UUID
    access_level: str = "view"


class ToolAccessOut(BaseModel):
    id: uuid.UUID
    tool_id: uuid.UUID
    user_id: uuid.UUID
    access_level: str
    provisioning_status: str
    failure_reason: str | None
    granted_by_id: uuid.UUID | None

    model_config = {"from_attributes": True}


class ToolLaunchOut(BaseModel):
    launch_url: str


class AuditEventOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    actor_user_id: uuid.UUID | None
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    metadata: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DashboardStats(BaseModel):
    lab_count: int
    member_count: int
    open_tasks: int
    tool_count: int
    pending_invitations: int


class NotificationOut(BaseModel):
    id: uuid.UUID
    type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}
