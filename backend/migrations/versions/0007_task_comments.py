"""task comments; historical interview tables remain intact"""
from alembic import op
import sqlalchemy as sa
revision = "0007_task_comments"
down_revision = "0006_project_versions"
branch_labels = depends_on = None

def upgrade():
    op.create_table("task_comment",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("project_id", sa.String(32), sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", sa.String(32), sa.ForeignKey("task.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", sa.String(32), sa.ForeignKey("user_account.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("actor_type", sa.String(10), nullable=False),
        sa.Column("parent_id", sa.String(32), sa.ForeignKey("task_comment.id", ondelete="CASCADE")),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("agent_run_id", sa.String(32)),
        sa.Column("created_time", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("actor_type IN ('HUMAN', 'COO')", name="ck_comment_actor"))
    op.create_index("ix_comment_task_time", "task_comment", ["task_id", "created_time"])

def downgrade():
    op.drop_table("task_comment")
