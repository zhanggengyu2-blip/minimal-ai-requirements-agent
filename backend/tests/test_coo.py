import json
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.coo.provider import ChatResult
from app.coo.models import CooAction, AgentRun
from tests.test_task_api import _admin, _member, _create_project, _create_task, authenticated_as

def tool(name,args):
    return ChatResult({'role':'assistant','content':None,'tool_calls':[{'id':'call_'+name,'type':'function','function':{'name':name,'arguments':json.dumps(args)}}]},100)
def answer(text='已完成调查，建议等待员工确认',sources=None):
    return ChatResult({'role':'assistant','content':json.dumps({'answer':text,'source_ids':sources or []})},50)
def session(c,p=None):
    r=c.post('/api/v1/coo/sessions',json={'project_id':p['id'] if p else None});assert r.status_code==201,r.text;return r.json()['data']
def send(c,s,**body):
    r=c.post(f"/api/v1/coo/sessions/{s['id']}/messages",json={'content':'调查履约风险并跟进',**body});assert r.status_code==200,r.text;return r.json()['data']

def test_model_selects_tools_task_confirmation_is_idempotent(db_session):
    admin=_admin(db_session)
    with TestClient(app) as c:
        p=_create_project(c,'Coo协作');s=session(c,p)
        replies=[tool('get_project_context',{'project_id':p['id']}),tool('create_task',{'project_id':p['id'],'name':'调查超时未发货','assignee_id':admin.id,'description':'核实模拟 ERP 的异常，联系仓库'}),answer()]
        mock=AsyncMock(side_effect=replies)
        with patch('app.coo.provider.ModelClient.complete',new=mock):run=send(c,s)
        assert run['status']=='SUCCEEDED',run
        assert len(run['tools'])==2 and run['actions'][0]['status']=='PENDING'
        assert c.get(f"/api/v1/projects/{p['id']}/tasks").json()['data']['total']==0
        action=run['actions'][0]
        result=c.post(f"/api/v1/coo/actions/{action['id']}/decision",json={'decision':'APPROVE'})
        assert result.status_code==200,result.text
        assert result.json()['data']['actions'][0]['status']=='SUCCEEDED'
        assert c.post(f"/api/v1/coo/actions/{action['id']}/decision",json={'decision':'APPROVE'}).status_code==200
        assert c.get(f"/api/v1/projects/{p['id']}/tasks").json()['data']['total']==1
        assert mock.await_count==3
    outsider=_member(db_session,'Coo其他员工')
    with authenticated_as(outsider) as c:
        assert c.get('/api/v1/coo/sessions/'+s['id']).status_code==404
        assert c.get('/api/v1/coo/runs/'+run['id']).status_code==404
        assert c.post(f"/api/v1/coo/actions/{action['id']}/decision",json={'decision':'APPROVE'}).status_code==404

def test_comments_require_explicit_run_authorization_and_keep_ai_identity(db_session):
    admin=_admin(db_session)
    with TestClient(app) as c:
        p=_create_project(c,'Coo留言');t=_create_task(c,p['id'],admin.id,'发货核查');s=session(c,p)
        args={'project_id':p['id'],'task_id':t['id'],'content':'请仓储核实发货时间'}
        with patch('app.coo.provider.ModelClient.complete',new=AsyncMock(side_effect=[tool('create_task_comment',args),answer()])):run=send(c,s)
        assert run['actions'][0]['status']=='PENDING'
        with patch('app.coo.provider.ModelClient.complete',new=AsyncMock(side_effect=[tool('create_task_comment',args),answer()])):run=send(c,s,allow_comments=True)
        assert run['actions'][0]['status']=='SUCCEEDED',run
        comments=c.get(f"/api/v1/projects/{p['id']}/tasks/{t['id']}/comments").json()['data']
        assert len(comments)==1 and comments[0]['actor_type']=='COO' and comments[0]['agent_run_id']==run['id']

def test_invalid_tool_cross_project_scope_and_citations_are_rejected(db_session):
    with TestClient(app) as c:
        p=_create_project(c,'Coo范围A');other=_create_project(c,'Coo范围B');s=session(c,p)
        with patch('app.coo.provider.ModelClient.complete',new=AsyncMock(side_effect=[tool('get_project_context',{'project_id':other['id']}),tool('execute_sql',{'sql':'select * from users'}),answer()])):run=send(c,s)
        assert [r['status'] for r in run['tools']]==['FAILED','FAILED']
        with patch('app.coo.provider.ModelClient.complete',new=AsyncMock(return_value=answer(sources=['fake']))):run=send(c,s)
        assert run['status']=='FAILED' and run['error_code']=='INVALID_CITATIONS'

def test_missing_model_is_explicit_and_requirement_survives(db_session):
    with TestClient(app) as c:
        p=_create_project(c,'模型缺失');s=session(c,p)
        run=send(c,s)
        assert run['status']=='FAILED' and run['error_code']=='COO_MODEL_NOT_CONFIGURED'
        r=c.post('/api/v1/requirements',json={'project_id':p['id'],'raw_content':'完整保留我的需求','analyze_with_ai':True})
        row=c.get('/api/v1/requirements/'+r.json()['data']['id']).json()['data']
        assert row['raw_content']=='完整保留我的需求' and row['analysis_status']=='FAILED'
        assert row['analysis_error_code']=='COO_MODEL_NOT_CONFIGURED'

def test_round_limit_and_requirement_analysis_candidate_validation(db_session,monkeypatch):
    from app.core.config import get_settings
    from app.coo import runtime
    settings=get_settings().model_copy(update={'coo_max_rounds':2})
    monkeypatch.setattr(runtime,'get_settings',lambda:settings)
    with TestClient(app) as c:
        p=_create_project(c,'轮次限制');s=session(c,p)
        with patch('app.coo.provider.ModelClient.complete',new=AsyncMock(return_value=tool('list_projects',{}))):run=send(c,s)
        assert run['status']=='FAILED' and run['error_code']=='COO_ROUND_LIMIT'
        from tests.test_api import VALID_ANALYSIS
        invalid=VALID_ANALYSIS.model_dump();invalid.update(is_duplicate=True,related_id='f'*32)
        with patch('app.coo.provider.ModelClient.complete',new=AsyncMock(return_value=ChatResult({'content':json.dumps(invalid)},10))):
            r=c.post('/api/v1/requirements',json={'project_id':p['id'],'raw_content':'需求分析候选校验','analyze_with_ai':True})
        row=c.get('/api/v1/requirements/'+r.json()['data']['id']).json()['data']
        assert row['analysis_status']=='FAILED' and row['analysis_error_code']=='COO_ANALYSIS_INVALID'
