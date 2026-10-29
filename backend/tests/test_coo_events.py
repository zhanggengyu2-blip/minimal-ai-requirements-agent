import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from app.main import app
from app.db.models import utc_now
from app.coo.models import BusinessEvent
from app.coo.worker import process_one
from app.db.session import SessionLocal
from tests.test_task_api import _admin, _create_project, _create_task
from tests.test_coo import tool, answer, session, send

def test_simulated_event_investigation_confirmation_and_followup(db_session):
    admin=_admin(db_session)
    with TestClient(app) as c:
        p=_create_project(c,'电商履约协作')
        body={'project_id':p['id'],'order_id':'DEMO-001','hours_waiting':72}
        first=c.post('/api/v1/coo/events/simulated-order',json=body)
        assert first.status_code==201,first.text
        event=first.json()['data'];assert event['origin']=='SIMULATED_ERP'
        assert c.post('/api/v1/coo/events/simulated-order',json=body).json()['data']['id']==event['id']
        steps=[tool('get_simulated_order',{'project_id':p['id'],'order_id':'DEMO-001'}),tool('get_project_context',{'project_id':p['id']}),
            tool('create_task',{'project_id':p['id'],'name':'调查模拟订单超时未发货','assignee_id':admin.id}),answer('已核实模拟订单异常，请确认创建仓储跟进任务')]
        with patch('app.coo.provider.ModelClient.complete',new=AsyncMock(side_effect=steps)):
            assert asyncio.run(process_one(SessionLocal)) is True
        event=c.get('/api/v1/coo/events').json()['data'][0]
        assert event['status']=='SUCCEEDED' and event['attempts']==1
        run=c.get('/api/v1/coo/runs/'+event['run_id']).json()['data']
        assert len(run['tools'])==3 and run['actions'][0]['status']=='PENDING'
        assert asyncio.run(process_one(SessionLocal)) is False
        action=run['actions'][0]
        confirmed=c.post(f"/api/v1/coo/actions/{action['id']}/decision",json={'decision':'APPROVE'}).json()['data']
        task=confirmed['actions'][0]['result']
        assert task['name']=='调查模拟订单超时未发货'
        # Employee changes are durable new events.
        assert c.patch(f"/api/v1/projects/{p['id']}/tasks/{task['id']}",json={'expected_revision':task['revision'],'status':'IN_PROGRESS'}).status_code==200
        assert c.post(f"/api/v1/projects/{p['id']}/tasks/{task['id']}/comments",json={'content':'已联系仓库，核查中'}).status_code==201
        assert len(c.get('/api/v1/coo/events').json()['data'])==3
        with patch('app.coo.provider.ModelClient.complete',new=AsyncMock(side_effect=[tool('list_task_comments',{'project_id':p['id'],'task_id':task['id']}),answer('员工已联系仓库，建议待反馈后更新任务')])):
            assert asyncio.run(process_one(SessionLocal))
        assert len(c.get('/api/v1/coo/events').json()['data'])==3

def test_worker_failure_retry_and_no_self_comment_loop(db_session):
    admin=_admin(db_session)
    with TestClient(app) as c:
        p=_create_project(c,'事件重试');t=_create_task(c,p['id'],admin.id,'异常跟进')
        e=c.post('/api/v1/coo/events/simulated-order',json={'project_id':p['id'],'order_id':'DEMO-FAIL'}).json()['data']
        assert asyncio.run(process_one(SessionLocal))
        event=c.get('/api/v1/coo/events').json()['data'][0];assert event['status']=='FAILED'
        assert c.post(f"/api/v1/coo/events/{e['id']}/retry").status_code==200
        with patch('app.coo.provider.ModelClient.complete',new=AsyncMock(return_value=answer())):assert asyncio.run(process_one(SessionLocal))
        event=c.get('/api/v1/coo/events').json()['data'][0];assert event['status']=='SUCCEEDED' and event['attempts']==2
        s=session(c,p)
        with patch('app.coo.provider.ModelClient.complete',new=AsyncMock(side_effect=[tool('create_task_comment',{'project_id':p['id'],'task_id':t['id'],'content':'Coo已检查当前任务'}),answer()])):
            run=send(c,s,allow_comments=True)
        assert run['actions'][0]['status']=='SUCCEEDED'
        assert len(c.get('/api/v1/coo/events').json()['data'])==1

def test_expired_lease_is_recovered_and_exhaustion_is_visible(db_session):
    from app.coo.models import BusinessEvent
    with TestClient(app) as c:
        p=_create_project(c,'租约恢复');event=c.post('/api/v1/coo/events/simulated-order',json={'project_id':p['id'],'order_id':'LEASE-001'}).json()['data']
        row=db_session.get(BusinessEvent,event['id']);row.status='PROCESSING';row.claim_token='stale';row.lease_until=utc_now()-timedelta(minutes=5);row.attempts=1;db_session.commit()
        with patch('app.coo.provider.ModelClient.complete',new=AsyncMock(return_value=answer())):assert asyncio.run(process_one(SessionLocal))
        row=db_session.get(BusinessEvent,event['id']);db_session.refresh(row);assert row.status=='SUCCEEDED' and row.attempts==2
        row.status='PROCESSING';row.lease_until=utc_now()-timedelta(minutes=5);row.attempts=5;db_session.commit()
        assert not asyncio.run(process_one(SessionLocal));db_session.refresh(row);assert row.status=='FAILED'

def test_background_worker_runs_after_browser_client_closes_and_only_claims_once(db_session):
    with TestClient(app) as c:
        p=_create_project(c,'后台独立执行');event=c.post('/api/v1/coo/events/simulated-order',json={'project_id':p['id'],'order_id':'BACKGROUND-001'}).json()['data']
    async def delayed(*args,**kwargs):
        await asyncio.sleep(.02)
        return answer()
    async def two_workers():return await asyncio.gather(process_one(SessionLocal),process_one(SessionLocal))
    with patch('app.coo.provider.ModelClient.complete',new=AsyncMock(side_effect=delayed)) as mocked:
        results=asyncio.run(two_workers())
    assert results.count(True)==1 and mocked.await_count==1
    with TestClient(app) as c:
        record=next(r for r in c.get('/api/v1/coo/events').json()['data'] if r['id']==event['id'])
        assert record['status']=='SUCCEEDED' and record['attempts']==1
