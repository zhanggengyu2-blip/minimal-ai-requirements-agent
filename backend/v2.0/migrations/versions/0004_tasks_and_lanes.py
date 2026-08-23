"""tasks and task lanes

Revision ID: 0004_tasks_and_lanes
Revises: 0003_project_members
Create Date: 2026-08-23
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0004_tasks_and_lanes"
down_revision: str | None = "0003_project_members"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "task_lane",
        sa.Column("project_id", sa.String(length=32), nullable=False),
        sa.Column("assignee_id", sa.String(length=32), nullable=False),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        sa.Column("updated_time", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["assignee_id"], ["user_account.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("project_id", "assignee_id"),
    )
    op.execute(
        sa.text(
            "INSERT INTO task_lane (project_id, assignee_id, revision, updated_time) "
            "SELECT project_id, user_id, 1, created_time FROM project_member"
        )
    )

    op.create_table(
        "task",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("project_id", sa.String(length=32), nullable=False),
        sa.Column("assignee_id", sa.String(length=32), nullable=False),
        sa.Column("version_id", sa.String(length=32), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "NOT_STARTED",
                "IN_PROGRESS",
                "COMPLETED",
                "CANCELED",
                name="taskstatus",
                native_enum=False,
            ),
            server_default="NOT_STARTED",
            nullable=False,
        ),
        sa.Column(
            "priority",
            sa.Enum("P0", "P1", "P2", "P3", name="taskpriority", native_enum=False),
            server_default="P1",
            nullable=False,
        ),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_by", sa.String(length=32), nullable=False),
        sa.Column("updated_by", sa.String(length=32), nullable=False),
        sa.Column("created_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_time", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "due_date IS NULL OR start_date IS NULL OR due_date >= start_date",
            name="ck_task_date_order",
        ),
        sa.ForeignKeyConstraint(["assignee_id"], ["user_account.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["user_account.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["project_id", "assignee_id"],
            ["project_member.project_id", "project_member.user_id"],
            name="fk_task_project_member",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by"], ["user_account.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_task_project_assignee_sort",
        "task",
        ["project_id", "assignee_id", "sort_order"],
        unique=False,
    )
    op.create_index(
        "ix_task_project_status_sort",
        "task",
        ["project_id", "status", "sort_order"],
        unique=False,
    )
    op.create_index(
        "ix_task_version_assignee_sort",
        "task",
        ["version_id", "assignee_id", "sort_order"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_task_version_assignee_sort", table_name="task")
    op.drop_index("ix_task_project_status_sort", table_name="task")
    op.drop_index("ix_task_project_assignee_sort", table_name="task")
    op.drop_table("task")
    op.drop_table("task_lane")
