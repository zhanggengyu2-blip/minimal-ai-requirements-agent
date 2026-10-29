"""durable business outbox with deduplication and worker leases"""
from alembic import op
revision = "0010_coo_events"
down_revision = "0009_coo_runtime"
branch_labels = depends_on = None

def upgrade():
    op.execute('\nCREATE TABLE coo_business_event (\n\tid VARCHAR(32) NOT NULL, \n\tdedupe_key VARCHAR(200) NOT NULL, \n\tevent_type VARCHAR(50) NOT NULL, \n\tproject_id VARCHAR(32) NOT NULL, \n\tactor_id VARCHAR(32) NOT NULL, \n\torigin VARCHAR(20) NOT NULL, \n\tpayload JSON NOT NULL, \n\tstatus VARCHAR(24) NOT NULL, \n\tattempts INTEGER NOT NULL, \n\tclaim_token VARCHAR(32), \n\tlease_until DATETIME, \n\trun_id VARCHAR(32), \n\terror VARCHAR(500), \n\tcreated_time DATETIME NOT NULL, \n\tprocessed_time DATETIME, \n\tPRIMARY KEY (id), \n\tUNIQUE (dedupe_key), \n\tFOREIGN KEY(project_id) REFERENCES project (id) ON DELETE CASCADE, \n\tFOREIGN KEY(actor_id) REFERENCES user_account (id), \n\tFOREIGN KEY(run_id) REFERENCES coo_agent_run (id) ON DELETE SET NULL\n)\n\n')
    op.execute('CREATE INDEX ix_coo_business_event_project_id ON coo_business_event (project_id)')
    op.execute('CREATE INDEX ix_coo_business_event_status ON coo_business_event (status)')
    op.execute('CREATE INDEX ix_coo_business_event_actor_id ON coo_business_event (actor_id)')

def downgrade():
    op.drop_table('coo_business_event')
