"""record actual publication lease start and successful publication time"""
from alembic import op
import sqlalchemy as sa
revision='0011_knowledge_publish_times'
down_revision='0010_coo_events'
branch_labels=depends_on=None

def upgrade():
    op.add_column('knowledge_version',sa.Column('processing_started_time',sa.DateTime(timezone=True),nullable=True))
    op.add_column('knowledge_version',sa.Column('published_time',sa.DateTime(timezone=True),nullable=True))

def downgrade():
    # Native DROP COLUMN keeps referencing knowledge_chunk rows intact (SQLite >= 3.35).
    op.drop_column('knowledge_version','published_time')
    op.drop_column('knowledge_version','processing_started_time')
