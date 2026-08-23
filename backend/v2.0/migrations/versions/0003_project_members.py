"""project members and visibility

Revision ID: 0003_project_members
Revises: 0002_identity_auth
Create Date: 2026-08-23
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0003_project_members"
down_revision: str | None = "0002_identity_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    legacy_project_count = bind.scalar(sa.text("SELECT COUNT(*) FROM project")) or 0
    admin_id = bind.scalar(
        sa.text(
            "SELECT id FROM user_account WHERE role = 'ADMIN' "
            "ORDER BY created_time ASC LIMIT 1"
        )
    )
    if legacy_project_count and admin_id is None:
        raise RuntimeError(
            "0003_project_members requires an administrator before migrating legacy projects"
        )

    if legacy_project_count:
        bind.execute(
            sa.text(
                "UPDATE project SET created_by = :admin_id "
                "WHERE created_by IS NULL OR created_by NOT IN (SELECT id FROM user_account)"
            ),
            {"admin_id": admin_id},
        )
        bind.execute(
            sa.text(
                "UPDATE project SET department_id = NULL "
                "WHERE department_id IS NOT NULL "
                "AND department_id NOT IN (SELECT id FROM department)"
            )
        )

    with op.batch_alter_table("project", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("revision", sa.Integer(), server_default="1", nullable=False)
        )
        batch_op.add_column(
            sa.Column("member_revision", sa.Integer(), server_default="1", nullable=False)
        )
        batch_op.create_foreign_key(
            "fk_project_department", "department", ["department_id"], ["id"], ondelete="RESTRICT"
        )
        batch_op.create_foreign_key(
            "fk_project_created_by", "user_account", ["created_by"], ["id"], ondelete="RESTRICT"
        )

    op.create_table(
        "project_member",
        sa.Column("project_id", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("added_by", sa.String(length=32), nullable=False),
        sa.Column("created_time", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["added_by"], ["user_account.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user_account.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("project_id", "user_id"),
    )
    op.create_index(
        "ix_project_member_user_project",
        "project_member",
        ["user_id", "project_id"],
        unique=False,
    )

    if legacy_project_count:
        bind.execute(
            sa.text(
                "INSERT INTO project_member (project_id, user_id, added_by, created_time) "
                "SELECT id, created_by, created_by, created_time FROM project"
            )
        )


def downgrade() -> None:
    op.drop_index("ix_project_member_user_project", table_name="project_member")
    op.drop_table("project_member")

    with op.batch_alter_table("project", schema=None) as batch_op:
        batch_op.drop_constraint("fk_project_created_by", type_="foreignkey")
        batch_op.drop_constraint("fk_project_department", type_="foreignkey")
        batch_op.drop_column("member_revision")
        batch_op.drop_column("revision")
