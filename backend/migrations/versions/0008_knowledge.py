"""enterprise/project knowledge lifecycle"""
from alembic import op
revision = "0008_knowledge"
down_revision = "0007_task_comments"
branch_labels = depends_on = None

def upgrade():
    op.execute("\nCREATE TABLE knowledge_category (\n\tid VARCHAR(32) NOT NULL, \n\tname VARCHAR(100) NOT NULL, \n\tscope VARCHAR(16) NOT NULL, \n\tproject_id VARCHAR(32), \n\tdepartment_id VARCHAR(32), \n\tcreated_by VARCHAR(32) NOT NULL, \n\tcreated_time DATETIME NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT ck_knowledge_scope CHECK (scope IN ('ENTERPRISE','PROJECT')), \n\tCONSTRAINT ck_knowledge_scope_ids CHECK ((scope='PROJECT' AND project_id IS NOT NULL AND department_id IS NULL) OR (scope='ENTERPRISE' AND project_id IS NULL)), \n\tFOREIGN KEY(project_id) REFERENCES project (id) ON DELETE CASCADE, \n\tFOREIGN KEY(department_id) REFERENCES department (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(created_by) REFERENCES user_account (id)\n)\n\n")
    op.execute('CREATE INDEX ix_knowledge_category_project_id ON knowledge_category (project_id)')
    op.execute('\nCREATE TABLE knowledge_document (\n\tid VARCHAR(32) NOT NULL, \n\tcategory_id VARCHAR(32) NOT NULL, \n\ttitle VARCHAR(200) NOT NULL, \n\tenabled BOOLEAN NOT NULL, \n\trevision INTEGER NOT NULL, \n\tcreated_by VARCHAR(32) NOT NULL, \n\tupdated_time DATETIME NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(category_id) REFERENCES knowledge_category (id) ON DELETE CASCADE, \n\tFOREIGN KEY(created_by) REFERENCES user_account (id)\n)\n\n')
    op.execute('CREATE INDEX ix_knowledge_document_category_id ON knowledge_document (category_id)')
    op.execute('\nCREATE TABLE knowledge_version (\n\tid VARCHAR(32) NOT NULL, \n\tdocument_id VARCHAR(32) NOT NULL, \n\tversion INTEGER NOT NULL, \n\tstatus VARCHAR(16) NOT NULL, \n\tcontent TEXT NOT NULL, \n\tsettings JSON NOT NULL, \n\tembedding_space VARCHAR(256), \n\teffective_from DATETIME, \n\teffective_until DATETIME, \n\terror VARCHAR(300), \n\tcreated_time DATETIME NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (document_id, version), \n\tFOREIGN KEY(document_id) REFERENCES knowledge_document (id) ON DELETE CASCADE\n)\n\n')
    op.execute('CREATE INDEX ix_knowledge_version_document_id ON knowledge_version (document_id)')
    op.execute('\nCREATE TABLE knowledge_chunk (\n\tid VARCHAR(32) NOT NULL, \n\tversion_id VARCHAR(32) NOT NULL, \n\tordinal INTEGER NOT NULL, \n\tcontent TEXT NOT NULL, \n\tembedding JSON NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (version_id, ordinal), \n\tFOREIGN KEY(version_id) REFERENCES knowledge_version (id) ON DELETE CASCADE\n)\n\n')
    op.execute('CREATE INDEX ix_knowledge_chunk_version_id ON knowledge_chunk (version_id)')

def downgrade():
    op.drop_table('knowledge_chunk')
    op.drop_table('knowledge_version')
    op.drop_table('knowledge_document')
    op.drop_table('knowledge_category')
