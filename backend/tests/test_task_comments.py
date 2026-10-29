from fastapi.testclient import TestClient
from app.main import app
from tests.test_task_api import _admin, _member, _create_project, _create_task, authenticated_as

def test_comments_reply_history_and_no_ai_impersonation(db_session):
    admin = _admin(db_session)
    with TestClient(app) as c:
        p = _create_project(c, '留言项目')
        t = _create_task(c, p['id'], admin.id, '履约调查')
        url = f"/api/v1/projects/{p['id']}/tasks/{t['id']}/comments"
        first = c.post(url, json={'content': '  请仓储调查  '})
        assert first.status_code == 201
        root = first.json()['data']
        assert root['content'] == '请仓储调查' and root['actor_type'] == 'HUMAN'
        assert c.post(url, json={'content': '已经联系', 'parent_id': root['id']}).status_code == 201
        assert len(c.get(url).json()['data']) == 2
        assert c.post(url, json={'content': '  '}).status_code == 422
        assert c.post(url, json={'content': '伪装', 'actor_type': 'COO'}).status_code == 422
        assert c.get(f"/api/v1/projects/{p['id']}/tasks/{t['id']}").json()['data']['revision'] == 1
        other = _create_task(c, p['id'], admin.id, '另一任务')
        assert c.post(f"/api/v1/projects/{p['id']}/tasks/{other['id']}/comments", json={'content': '非法回复', 'parent_id': root['id']}).status_code == 404
    outsider = _member(db_session, '无权限留言人')
    with authenticated_as(outsider) as c:
        assert c.get(url).status_code == 404
        assert c.post(url, json={'content': '越权'}).status_code == 404

def test_interviews_are_offline_but_historical_tables_remain(db_session):
    from sqlalchemy import inspect
    with TestClient(app) as c:
        assert c.post('/api/v1/interviews', json={}).status_code == 404
        assert not any('/interview' in path for path in app.openapi()['paths'])
    assert 'interview_session' in inspect(db_session.bind).get_table_names()

def test_archived_project_is_read_only_and_task_deletion_cascades_comments(db_session):
    from sqlalchemy import select,func
    from app.db.models import TaskComment
    admin=_admin(db_session)
    with TestClient(app) as c:
        p=_create_project(c,'留言生命周期');t=_create_task(c,p['id'],admin.id,'旧任务')
        url=f"/api/v1/projects/{p['id']}/tasks/{t['id']}/comments"
        row=c.post(url,json={'content':'保留留言'}).json()['data']
        assert row['created_time'].endswith(('Z','+00:00'))
        assert c.patch(f"/api/v1/projects/{p['id']}",json={'expected_revision':p['revision'],'status':'ARCHIVED'}).status_code==200
        assert c.get(url).status_code==200
        assert c.post(url,json={'content':'应拒绝'}).status_code==403
        assert c.patch(f"/api/v1/projects/{p['id']}",json={'expected_revision':2,'status':'ACTIVE'}).status_code==200
        assert c.delete(f"/api/v1/projects/{p['id']}/tasks/{t['id']}?expected_revision=1").status_code==200
        assert db_session.scalar(select(func.count()).select_from(TaskComment))==0
