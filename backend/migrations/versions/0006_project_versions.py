"""project versions and participants

Revision ID: 0006_project_versions
Revises: 0005_project_member_order
Create Date: 2026-08-24
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0006_project_versions"
down_revision: str | None = "0005_project_member_order"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "project_version",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("project_id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "NOT_STARTED",
                "IN_PROGRESS",
                "COMPLETED",
                name="versionstatus",
                native_enum=False,
            ),
            server_default="NOT_STARTED",
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_by", sa.String(length=32), nullable=False),
        sa.Column("updated_by", sa.String(length=32), nullable=False),
        sa.Column("created_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_time", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("end_date >= start_date", name="ck_project_version_date_order"),
        sa.ForeignKeyConstraint(["created_by"], ["user_account.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by"], ["user_account.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "name", name="uq_project_version_project_name"),
    )
    op.create_index(
        "ix_project_version_project_created",
        "project_version",
        ["project_id", "created_time"],
        unique=False,
    )
    op.create_table(
        "version_participant",
        sa.Column("version_id", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("created_time", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_account.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["version_id"], ["project_version.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("version_id", "user_id"),
    )


def downgrade() -> None:
    op.drop_table("version_participant")
    op.drop_index("ix_project_version_project_created", table_name="project_version")
    op.drop_table("project_version")
