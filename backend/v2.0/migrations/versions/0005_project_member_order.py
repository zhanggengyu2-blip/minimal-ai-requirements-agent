"""project member order

Revision ID: 0005_project_member_order
Revises: 0004_tasks_and_lanes
Create Date: 2026-08-24
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0005_project_member_order"
down_revision: str | None = "0004_tasks_and_lanes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "project_member",
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
    )
    op.execute(
        sa.text(
            "UPDATE project_member AS current_member "
            "SET sort_order = ("
            "SELECT COUNT(*) FROM project_member AS earlier_member "
            "WHERE earlier_member.project_id = current_member.project_id "
            "AND ("
            "CASE WHEN earlier_member.user_id = ("
            "SELECT created_by FROM project WHERE id = current_member.project_id"
            ") THEN 0 ELSE 1 END < "
            "CASE WHEN current_member.user_id = ("
            "SELECT created_by FROM project WHERE id = current_member.project_id"
            ") THEN 0 ELSE 1 END "
            "OR ("
            "CASE WHEN earlier_member.user_id = ("
            "SELECT created_by FROM project WHERE id = current_member.project_id"
            ") THEN 0 ELSE 1 END = "
            "CASE WHEN current_member.user_id = ("
            "SELECT created_by FROM project WHERE id = current_member.project_id"
            ") THEN 0 ELSE 1 END "
            "AND (earlier_member.created_time < current_member.created_time "
            "OR (earlier_member.created_time = current_member.created_time "
            "AND earlier_member.user_id <= current_member.user_id))"
            ")"
            ")"
            ")"
        )
    )
    with op.batch_alter_table("project_member") as batch_op:
        batch_op.alter_column("sort_order", server_default=None)
    op.create_index(
        "ix_project_member_project_sort",
        "project_member",
        ["project_id", "sort_order"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_project_member_project_sort", table_name="project_member")
    with op.batch_alter_table("project_member") as batch_op:
        batch_op.drop_column("sort_order")
