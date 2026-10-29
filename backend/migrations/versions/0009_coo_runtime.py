"""Coo sessions, runs, tools and confirmed operations"""
from alembic import op
revision = "0009_coo_runtime"
down_revision = "0008_knowledge"
branch_labels = depends_on = None

def upgrade():
    op.execute('\nCREATE TABLE coo_session (\n\tid VARCHAR(32) NOT NULL, \n\towner_id VARCHAR(32) NOT NULL, \n\tproject_id VARCHAR(32), \n\ttitle VARCHAR(100) NOT NULL, \n\tcreated_time DATETIME NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(owner_id) REFERENCES user_account (id), \n\tFOREIGN KEY(project_id) REFERENCES project (id) ON DELETE CASCADE\n)\n\n')
    op.execute('CREATE INDEX ix_coo_session_owner_id ON coo_session (owner_id)')
    op.execute('\nCREATE TABLE coo_agent_run (\n\tid VARCHAR(32) NOT NULL, \n\tsession_id VARCHAR(32), \n\towner_id VARCHAR(32) NOT NULL, \n\tproject_id VARCHAR(32), \n\t"trigger" VARCHAR(40) NOT NULL, \n\tevent_id VARCHAR(32), \n\tgoal TEXT NOT NULL, \n\tstatus VARCHAR(24) NOT NULL, \n\tanswer TEXT, \n\tsources JSON NOT NULL, \n\tproject_ids JSON NOT NULL, \n\tallow_comments BOOLEAN NOT NULL, \n\terror VARCHAR(500), \n\terror_code VARCHAR(50), \n\ttoken_usage INTEGER, \n\tmodel VARCHAR(100), \n\tcreated_time DATETIME NOT NULL, \n\tfinished_time DATETIME, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(session_id) REFERENCES coo_session (id) ON DELETE CASCADE, \n\tFOREIGN KEY(owner_id) REFERENCES user_account (id), \n\tFOREIGN KEY(project_id) REFERENCES project (id) ON DELETE CASCADE\n)\n\n')
    op.execute('CREATE INDEX ix_coo_agent_run_event_id ON coo_agent_run (event_id)')
    op.execute('CREATE INDEX ix_coo_agent_run_owner_id ON coo_agent_run (owner_id)')
    op.execute('CREATE INDEX ix_coo_agent_run_session_id ON coo_agent_run (session_id)')
    op.execute('\nCREATE TABLE coo_message (\n\tid VARCHAR(32) NOT NULL, \n\tsession_id VARCHAR(32) NOT NULL, \n\trun_id VARCHAR(32) NOT NULL, \n\trole VARCHAR(16) NOT NULL, \n\tcontent TEXT NOT NULL, \n\tcreated_time DATETIME NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(session_id) REFERENCES coo_session (id) ON DELETE CASCADE, \n\tFOREIGN KEY(run_id) REFERENCES coo_agent_run (id) ON DELETE CASCADE\n)\n\n')
    op.execute('CREATE INDEX ix_coo_message_session_id ON coo_message (session_id)')
    op.execute('\nCREATE TABLE coo_tool_call (\n\tid VARCHAR(32) NOT NULL, \n\trun_id VARCHAR(32) NOT NULL, \n\tsequence INTEGER NOT NULL, \n\tname VARCHAR(100) NOT NULL, \n\targuments JSON NOT NULL, \n\tstatus VARCHAR(24) NOT NULL, \n\tresult JSON, \n\terror VARCHAR(500), \n\tcreated_time DATETIME NOT NULL, \n\tfinished_time DATETIME, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(run_id) REFERENCES coo_agent_run (id) ON DELETE CASCADE\n)\n\n')
    op.execute('CREATE INDEX ix_coo_tool_call_run_id ON coo_tool_call (run_id)')
    op.execute('\nCREATE TABLE coo_action (\n\tid VARCHAR(32) NOT NULL, \n\trun_id VARCHAR(32) NOT NULL, \n\ttool_call_id VARCHAR(32) NOT NULL, \n\towner_id VARCHAR(32) NOT NULL, \n\tproject_id VARCHAR(32) NOT NULL, \n\tname VARCHAR(100) NOT NULL, \n\targuments JSON NOT NULL, \n\tstatus VARCHAR(24) NOT NULL, \n\tresult JSON, \n\terror VARCHAR(300), \n\tcreated_time DATETIME NOT NULL, \n\tdecided_time DATETIME, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(run_id) REFERENCES coo_agent_run (id) ON DELETE CASCADE, \n\tUNIQUE (tool_call_id), \n\tFOREIGN KEY(tool_call_id) REFERENCES coo_tool_call (id) ON DELETE CASCADE, \n\tFOREIGN KEY(owner_id) REFERENCES user_account (id), \n\tFOREIGN KEY(project_id) REFERENCES project (id) ON DELETE CASCADE\n)\n\n')
    op.execute('CREATE INDEX ix_coo_action_run_id ON coo_action (run_id)')

def downgrade():
    op.drop_table('coo_action')
    op.drop_table('coo_tool_call')
    op.drop_table('coo_message')
    op.drop_table('coo_agent_run')
    op.drop_table('coo_session')
