import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr


class UserOut(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    avatar_url: str | None
    status: str
    platform_role: str | None = None

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
    org_role: str
    status: str
    joined_at: datetime

    model_config = {"from_attributes": True}


class OrgRosterOut(BaseModel):
    membership_id: uuid.UUID
    user_id: uuid.UUID
    name: str
    email: str
    org_role: str
    status: str
    labs: list[dict]


class LabRoleSummary(BaseModel):
    lab_id: uuid.UUID
    lab_name: str
    lab_role: str


class DemoUserOut(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    platform_role: str | None = None
    primary_org: str | None = None
    primary_role: str | None = None
    membership_count: int = 0
    org_memberships: list["MembershipSummary"] = []


class MembershipSummary(BaseModel):
    organization_id: uuid.UUID
    organization_name: str
    org_role: str
    effective_role: str
    labs: list[LabRoleSummary] = []
    lab_id: uuid.UUID | None = None
    lab_name: str | None = None
    lab_role: str | None = None


class DemoLoginRequest(BaseModel):
    user_id: uuid.UUID


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    is_staff: bool = False
    default_organization_id: uuid.UUID | None = None
    default_lab_id: uuid.UUID | None = None


class MeResponse(BaseModel):
    user: UserOut
    is_staff: bool = False
    memberships: list[MembershipOut]
    organizations: list[OrganizationOut]
    labs: list[LabOut]
    membership_summaries: list[MembershipSummary] = []
    lab_memberships: list[dict] = []
    pending_onboarding: list[dict] = []
    role_change_notices: list[dict] = []


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


class OrganizationCreate(BaseModel):
    name: str
    slug: str | None = None
    admin_invite_email: EmailStr


class OrganizationCreateOut(BaseModel):
    organization: OrganizationOut
    admin_invite_email: str
    admin_invite_link: str


class OnboardingStepOut(BaseModel):
    id: str
    title: str
    content: str
    route: str
    highlight_nav: str | None = None
    advance: str  # button | navigate | complete


class OnboardingChecklistItemOut(BaseModel):
    id: str
    label: str


class OnboardingStatusOut(BaseModel):
    required: bool
    completed: bool
    lab_id: uuid.UUID
    lab_name: str
    lab_role: str
    steps: list[OnboardingStepOut] = []
    completed_step_ids: list[str] = []
    current_step: OnboardingStepOut | None = None
    checklist: list[OnboardingChecklistItemOut] = []
    completed_at: datetime | None = None


class OnboardingAdvanceOut(BaseModel):
    completed_step_ids: list[str]
    current_step: OnboardingStepOut | None = None


class OnboardingCompleteOut(BaseModel):
    completed: bool
    tools_granted: int


class PlatformAnalyticsOut(BaseModel):
    active_organizations: int
    total_users: int
    total_tasks: int
    open_tasks: int
    total_tools: int
    tool_provisioning_success_rate: float
    tool_access_active: int
    tool_access_failed: int
    organizations: list[dict]


class LabCreate(BaseModel):
    name: str
    description: str | None = None
    manager_user_id: uuid.UUID | None = None
    invite_manager_email: EmailStr | None = None


class LabUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    archived: bool | None = None


class LabMemberOut(BaseModel):
    membership_id: uuid.UUID | None = None
    user_id: uuid.UUID
    name: str
    email: str
    lab_role: str
    lab_id: uuid.UUID


class LabMemberAdd(BaseModel):
    user_id: uuid.UUID
    lab_role: str  # MANAGER | CONTRIBUTOR


class LabMemberUpdate(BaseModel):
    lab_role: str | None = None
    status: str | None = None


class MemberUpdate(BaseModel):
    org_role: str | None = None
    status: str | None = None


class InvitationCreate(BaseModel):
    email: EmailStr
    lab_id: uuid.UUID
    lab_role: str  # MANAGER | CONTRIBUTOR
    expires_in_days: int = 7


class InvitationOut(BaseModel):
    id: uuid.UUID
    email: str
    lab_id: uuid.UUID
    lab_role: str
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


class TaskAttachmentCreate(BaseModel):
    file_name: str
    file_type: str | None = None


class TaskAttachmentOut(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    uploaded_by_id: uuid.UUID
    file_name: str
    file_url: str
    file_type: str | None
    file_size: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ToolCreate(BaseModel):
    name: str
    description: str | None = None
    category: str
    service_url: str | None = None
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


class LabToolCatalogItem(BaseModel):
    tool: ToolOut
    access_mode: str
    access: ToolAccessOut | None = None
    can_launch: bool = False
    can_request: bool = False


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
    manager_count: int = 0
    contributor_count: int
    admin_count: int = 0
    tasks_by_status: dict[str, int] = {}
    active_google_workspaces: int = 0
    labs_without_workspace: int = 0


class LabSummaryOut(BaseModel):
    lab_id: uuid.UUID
    lab_name: str
    member_count: int
    open_tasks: int
    has_google_workspace: bool
    workspace_status: str | None = None


class NotificationOut(BaseModel):
    id: uuid.UUID
    type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LabGoogleWorkspaceOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    lab_id: uuid.UUID
    drive_url: str | None
    calendar_id: str | None
    chat_space_url: str | None
    meet_url: str | None
    provisioning_status: str
    failure_reason: str | None

    model_config = {"from_attributes": True}


class DriveFileOut(BaseModel):
    id: str
    name: str
    type: str
    updated_at: str
    url: str


class CalendarEventOut(BaseModel):
    id: str
    title: str
    start: str
    attendees: int


class ChatMessageOut(BaseModel):
    id: str
    author: str
    content: str
    created_at: str


class ChatMessageCreate(BaseModel):
    content: str


class MeetSessionOut(BaseModel):
    meet_url: str
    join_code: str
    status: str
    participants: int


class ToolHealthOut(BaseModel):
    tool_id: uuid.UUID
    healthy: bool
    connector_type: str
    message: str


class ToolSessionOut(BaseModel):
    tool_id: uuid.UUID
    tool_name: str
    tool_type: str
    launch_url: str
    status: str
    session: dict


class ConnectorTypeOut(BaseModel):
    type: str
    label: str
    capabilities: list[str]
