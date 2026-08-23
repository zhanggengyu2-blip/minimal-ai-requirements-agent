import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return uuid.uuid4().hex


class ProjectStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class AnalysisStatus(str, enum.Enum):
    PENDING = "PENDING"
    ANALYZING = "ANALYZING"
    ANALYZED = "ANALYZED"
    FAILED = "FAILED"


class RequirementType(str, enum.Enum):
    NEW_FEATURE = "NEW_FEATURE"
    BUG = "BUG"
    OPTIMIZATION = "OPTIMIZATION"


class RequirementPriority(str, enum.Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class InvitationStatus(str, enum.Enum):
    UNUSED = "UNUSED"
    USED = "USED"
    DISABLED = "DISABLED"


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"


class InterviewStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    INTERVIEWING = "INTERVIEWING"
    CONFIRMING = "CONFIRMING"
    SUBMITTED = "SUBMITTED"
    ABANDONED = "ABANDONED"
    FAILED = "FAILED"


class InterviewMessageRole(str, enum.Enum):
    USER = "USER"
    AGENT = "AGENT"
    SYSTEM_EVENT = "SYSTEM_EVENT"


class InterviewActionType(str, enum.Enum):
    INITIAL = "INITIAL"
    ANSWER = "ANSWER"
    SKIP = "SKIP"
    UNKNOWN = "UNKNOWN"
    DIRECT_SUMMARY = "DIRECT_SUMMARY"


class SourceChannel(str, enum.Enum):
    MANAGEMENT_WEB = "MANAGEMENT_WEB"
    PRODUCT_WEB = "PRODUCT_WEB"
    MINI_PROGRAM = "MINI_PROGRAM"
    WECHAT = "WECHAT"
    WECOM = "WECOM"
    FEISHU = "FEISHU"
    OTHER = "OTHER"


class ProjectResolveMode(str, enum.Enum):
    USER_SELECTED = "USER_SELECTED"
    ENTRY_BOUND = "ENTRY_BOUND"
    CHANNEL_MAPPED = "CHANNEL_MAPPED"


class Department(Base):
    __tablename__ = "department"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    created_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    invitations: Mapped[list["InvitationCode"]] = relationship(back_populates="department")
    users: Mapped[list["UserAccount"]] = relationship(back_populates="department")


class UserAccount(Base):
    __tablename__ = "user_account"
    __table_args__ = (
        UniqueConstraint("department_id", "normalized_name", name="uq_user_department_name"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    department_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("department.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(50), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False), default=UserRole.MEMBER, nullable=False, index=True
    )
    invitation_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("invitation_code.id", ondelete="SET NULL"), nullable=True, unique=True
    )
    created_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    department: Mapped[Department] = relationship(back_populates="users")
    sessions: Mapped[list["AuthSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class AuthSession(Base):
    __tablename__ = "auth_session"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("user_account.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_digest: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    idle_expires_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    absolute_expires_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    last_seen_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    user: Mapped[UserAccount] = relationship(back_populates="sessions")


class InvitationCode(Base):
    __tablename__ = "invitation_code"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    code_digest: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    code_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    department_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("department.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    intended_user_name: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    status: Mapped[InvitationStatus] = mapped_column(
        Enum(InvitationStatus, native_enum=False),
        default=InvitationStatus.UNUSED,
        nullable=False,
        index=True,
    )
    used_by_user_id: Mapped[str | None] = mapped_column(
        String(32),
        ForeignKey(
            "user_account.id",
            ondelete="RESTRICT",
            name="fk_invitation_used_by_user",
            use_alter=True,
        ),
        nullable=True,
        unique=True,
    )
    created_by: Mapped[str | None] = mapped_column(
        String(32),
        ForeignKey(
            "user_account.id",
            ondelete="RESTRICT",
            name="fk_invitation_created_by_user",
            use_alter=True,
        ),
        nullable=True,
        index=True,
    )
    created_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    used_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disabled_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    department: Mapped[Department] = relationship(back_populates="invitations")


class Project(Base):
    __tablename__ = "project"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    project_context: Mapped[str] = mapped_column(Text, nullable=False)
    department_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    created_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, native_enum=False), default=ProjectStatus.ACTIVE, nullable=False, index=True
    )
    created_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    requirements: Mapped[list["Requirement"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    interview_sessions: Mapped[list["InterviewSession"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class InterviewSession(Base):
    __tablename__ = "interview_session"
    __table_args__ = (
        Index("ix_interview_creator_status_updated", "created_by", "status", "updated_time"),
        Index("ix_interview_project_status_created", "project_id", "status", "created_time"),
        UniqueConstraint(
            "source_channel", "source_message_id", name="uq_interview_source_message"
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    source_channel: Mapped[SourceChannel] = mapped_column(
        Enum(SourceChannel, native_enum=False), default=SourceChannel.MANAGEMENT_WEB, nullable=False
    )
    source_user_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_message_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    entry_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    project_resolve_mode: Mapped[ProjectResolveMode] = mapped_column(
        Enum(ProjectResolveMode, native_enum=False),
        default=ProjectResolveMode.USER_SELECTED,
        nullable=False,
    )
    status: Mapped[InterviewStatus] = mapped_column(
        Enum(InterviewStatus, native_enum=False),
        default=InterviewStatus.DRAFT,
        nullable=False,
        index=True,
    )
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    request_type: Mapped[RequirementType | None] = mapped_column(
        Enum(RequirementType, native_enum=False), nullable=True
    )
    structured_data: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    skipped_fields: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    completeness_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    round_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    consecutive_skip_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    consecutive_agent_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stop_reason: Mapped[str | None] = mapped_column(String(40), nullable=True)
    summary_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    clarified_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirement_id: Mapped[str | None] = mapped_column(String(32), nullable=True, unique=True)
    confirm_idempotency_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    agent_error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    agent_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    project: Mapped[Project] = relationship(back_populates="interview_sessions")
    messages: Mapped[list["InterviewMessage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="InterviewMessage.sequence_no",
    )
    attachments: Mapped[list["InterviewAttachment"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="InterviewAttachment.created_time",
    )


class InterviewMessage(Base):
    __tablename__ = "interview_message"
    __table_args__ = (
        UniqueConstraint("session_id", "sequence_no", name="uq_interview_message_sequence"),
        UniqueConstraint("session_id", "client_message_id", name="uq_interview_client_message"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("interview_session.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[InterviewMessageRole] = mapped_column(
        Enum(InterviewMessageRole, native_enum=False), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    action_type: Mapped[InterviewActionType | None] = mapped_column(
        Enum(InterviewActionType, native_enum=False), nullable=True
    )
    target_field: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    client_message_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    agent_run_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    session: Mapped[InterviewSession] = relationship(back_populates="messages")
    attachments: Mapped[list["InterviewAttachment"]] = relationship(
        back_populates="message",
        order_by="InterviewAttachment.created_time",
    )


class InterviewAttachment(Base):
    __tablename__ = "interview_attachment"
    __table_args__ = (
        Index("ix_interview_attachment_uploader_created", "uploaded_by", "created_time"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    session_id: Mapped[str | None] = mapped_column(
        String(32),
        ForeignKey("interview_session.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    message_id: Mapped[str | None] = mapped_column(
        String(32),
        ForeignKey("interview_message.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    uploaded_by: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(50), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dify_upload_file_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dify_user: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    session: Mapped[InterviewSession | None] = relationship(back_populates="attachments")
    message: Mapped[InterviewMessage | None] = relationship(back_populates="attachments")

    @property
    def preview_url(self) -> str:
        return f"/api/v1/interviews/attachments/{self.id}/content"


class Requirement(Base):
    __tablename__ = "requirement"
    __table_args__ = (
        Index("ix_requirement_project_created", "project_id", "created_time"),
        Index("ix_requirement_project_priority", "project_id", "priority"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    interview_session_id: Mapped[str | None] = mapped_column(String(32), nullable=True, unique=True)
    clarified_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    interview_rounds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completeness_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 以下 10 个字段与 Dify Workflow 固定输出严格同名。
    standard_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    business_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[RequirementType | None] = mapped_column(
        Enum(RequirementType, native_enum=False), nullable=True, index=True
    )
    priority: Mapped[RequirementPriority | None] = mapped_column(
        Enum(RequirementPriority, native_enum=False), nullable=True, index=True
    )
    is_fake: Mapped[bool | None] = mapped_column(Boolean, nullable=True, index=True)
    fake_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_duplicate: Mapped[bool | None] = mapped_column(Boolean, nullable=True, index=True)
    related_id: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    reference_rule: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    analysis_status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus, native_enum=False), default=AnalysisStatus.PENDING, nullable=False, index=True
    )
    analysis_error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    analysis_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    dify_workflow_run_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    manual_modify: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    project: Mapped[Project] = relationship(back_populates="requirements")
