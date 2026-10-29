from alembic import command
from sqlalchemy import create_engine, func, select, text

from app.db.migrations import build_alembic_config, current_revision, upgrade_database
from app.db.models import Department
from app.db.seed import DEFAULT_DEPARTMENTS, seed_default_departments
from app.db.session import SessionLocal, engine


def test_database_is_at_v3_baseline() -> None:
    from alembic.script import ScriptDirectory
    assert current_revision() == ScriptDirectory.from_config(build_alembic_config()).get_current_head()


def test_repeated_upgrade_preserves_seed_data() -> None:
    with SessionLocal() as db:
        before = db.scalar(select(func.count()).select_from(Department))

    upgrade_database()

    with SessionLocal() as db:
        after = db.scalar(select(func.count()).select_from(Department))
    assert before == after == len(DEFAULT_DEPARTMENTS)


def test_project_member_order_migration_backfills_existing_members(tmp_path) -> None:
    database_path = tmp_path / "member-order.db"
    database_url = f"sqlite:///{database_path}"
    config = build_alembic_config(database_url)
    command.upgrade(config, "0004_tasks_and_lanes")

    legacy_engine = create_engine(database_url)
    created_time = "2026-08-24 08:00:00"
    department_id = "d" * 32
    project_id = "p" * 32
    creator_user_id = "b" * 32
    other_user_id = "a" * 32
    with legacy_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO department (id, name, created_time, updated_time) "
                "VALUES (:id, :name, :created_time, :updated_time)"
            ),
            {
                "id": department_id,
                "name": "迁移测试部门",
                "created_time": created_time,
                "updated_time": created_time,
            },
        )
        for user_id, name in [(other_user_id, "甲"), (creator_user_id, "乙")]:
            connection.execute(
                text(
                    "INSERT INTO user_account "
                    "(id, department_id, name, normalized_name, role, invitation_id, "
                    "created_time, updated_time) "
                    "VALUES (:id, :department_id, :name, :normalized_name, 'MEMBER', NULL, "
                    ":created_time, :updated_time)"
                ),
                {
                    "id": user_id,
                    "department_id": department_id,
                    "name": name,
                    "normalized_name": name,
                    "created_time": created_time,
                    "updated_time": created_time,
                },
            )
        connection.execute(
            text(
                "INSERT INTO project "
                "(id, name, description, project_context, department_id, created_by, status, "
                "revision, member_revision, created_time, updated_time) "
                "VALUES (:id, :name, '', :project_context, :department_id, :created_by, "
                "'ACTIVE', 1, 1, :created_time, :updated_time)"
            ),
            {
                "id": project_id,
                "name": "成员顺序迁移项目",
                "project_context": "迁移前已有项目成员",
                "department_id": department_id,
                "created_by": creator_user_id,
                "created_time": created_time,
                "updated_time": created_time,
            },
        )
        for user_id in [other_user_id, creator_user_id]:
            connection.execute(
                text(
                    "INSERT INTO project_member (project_id, user_id, added_by, created_time) "
                    "VALUES (:project_id, :user_id, :added_by, :created_time)"
                ),
                {
                    "project_id": project_id,
                    "user_id": user_id,
                    "added_by": creator_user_id,
                    "created_time": created_time,
                },
            )
    legacy_engine.dispose()

    command.upgrade(config, "head")
    migrated_engine = create_engine(database_url)
    try:
        with migrated_engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT user_id, sort_order FROM project_member "
                    "WHERE project_id = :project_id ORDER BY sort_order"
                ),
                {"project_id": project_id},
            ).all()
        assert rows == [(creator_user_id, 1), (other_user_id, 2)]
    finally:
        migrated_engine.dispose()


def test_default_department_seed_is_idempotent() -> None:
    assert seed_default_departments() == 0
    with SessionLocal() as db:
        names = set(db.scalars(select(Department.name)).all())
    assert names == set(DEFAULT_DEPARTMENTS)


def test_sqlite_runtime_pragmas_are_enabled() -> None:
    with engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        assert connection.exec_driver_sql("PRAGMA busy_timeout").scalar_one() == 5000
        assert connection.exec_driver_sql("PRAGMA journal_mode").scalar_one().lower() == "wal"
        assert connection.exec_driver_sql("PRAGMA synchronous").scalar_one() == 1
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []

def test_v4_upgrade_preserves_existing_business_and_interview_tables(tmp_path):
    from sqlalchemy import inspect
    database_url=f"sqlite:///{tmp_path/'v3-to-v4.db'}"
    config=build_alembic_config(database_url)
    command.upgrade(config,'0006_project_versions')
    old_engine=create_engine(database_url)
    with old_engine.begin() as connection:
        connection.execute(text("INSERT INTO department (id,name,created_time,updated_time) VALUES (:id,:name,:created,:created)"),{'id':'e'*32,'name':'已有部门','created':'2026-01-01 00:00:00'})
    command.upgrade(config,'head');command.upgrade(config,'head')
    with old_engine.connect() as connection:
        assert connection.scalar(text('SELECT name FROM department WHERE id=:id'),{'id':'e'*32})=='已有部门'
        assert {'interview_session','task_comment','knowledge_chunk','coo_business_event'}<=set(inspect(connection).get_table_names())
        assert connection.exec_driver_sql('PRAGMA foreign_key_check').all()==[]
    old_engine.dispose()

def test_publish_metadata_downgrade_preserves_published_chunks(tmp_path):
    from sqlalchemy.orm import Session
    from app.db.models import UserAccount,UserRole
    from app.knowledge.models import KnowledgeCategory,KnowledgeDocument,KnowledgeVersion,KnowledgeChunk
    url=f"sqlite:///{tmp_path/'publish-metadata.db'}";config=build_alembic_config(url)
    command.upgrade(config,'head');local_engine=create_engine(url)
    with Session(local_engine) as db:
        department=Department(name='回退检查');db.add(department);db.flush()
        user=UserAccount(name='测试成员',normalized_name='测试成员',department_id=department.id,role=UserRole.MEMBER);db.add(user);db.flush()
        category=KnowledgeCategory(name='公开规范',scope='ENTERPRISE',created_by=user.id);db.add(category);db.flush()
        doc=KnowledgeDocument(title='已发布政策',category_id=category.id,created_by=user.id);db.add(doc);db.flush()
        version=KnowledgeVersion(document_id=doc.id,version=1,status='PUBLISHED',content='保留正文',settings={});db.add(version);db.flush()
        chunk=KnowledgeChunk(version_id=version.id,ordinal=0,content='保留片段',embedding=[1.,0.]);db.add(chunk);db.commit()
    command.downgrade(config,'0010_coo_events')
    with local_engine.connect() as connection:
        assert connection.scalar(text('SELECT content FROM knowledge_chunk'))=='保留片段'
        assert connection.scalar(text('SELECT content FROM knowledge_version'))=='保留正文'
    command.upgrade(config,'head');local_engine.dispose()
