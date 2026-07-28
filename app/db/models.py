import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text
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


class DepartmentStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class InvitationStatus(str, enum.Enum):
    UNUSED = "UNUSED"
    USED = "USED"
    DISABLED = "DISABLED"


class Department(Base):
    __tablename__ = "department"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    status: Mapped[DepartmentStatus] = mapped_column(
        Enum(DepartmentStatus, native_enum=False),
        default=DepartmentStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    created_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    invitations: Mapped[list["InvitationCode"]] = relationship(
        back_populates="department", cascade="all, delete-orphan"
    )


class InvitationCode(Base):
    __tablename__ = "invitation_code"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    code: Mapped[str] = mapped_column(String(9), unique=True, nullable=False, index=True)
    department_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("department.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    user_name: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    status: Mapped[InvitationStatus] = mapped_column(
        Enum(InvitationStatus, native_enum=False),
        default=InvitationStatus.UNUSED,
        nullable=False,
        index=True,
    )
    created_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    used_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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
