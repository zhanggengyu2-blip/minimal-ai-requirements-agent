import json
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.db.models import ProjectMember
from app.coo.provider import ModelClient, ChatResult
from app.core.config import get_settings
from app.core.exceptions import AppError
from tests.test_coo import tool, answer, session, send
from tests.test_task_api import _admin, _member, _create_project, _add_member, authenticated_as

def test_confirmation_rechecks_removed_membership(db_session):
    admin=_admin(db_session);member=_member(db_session,'将被移除成员')
    with TestClient(app) as c:
        p=_create_project(c,'确认时重验权限');_add_member(c,p,admin,member)
    with authenticated_as(member) as c:
        s=session(c,p)
        with patch('app.coo.provider.ModelClient.complete',new=AsyncMock(side_effect=[tool('create_task',{'project_id':p['id'],'name':'应被拒绝','assignee_id':member.id}),answer()])):run=send(c,s)
    membership=db_session.get(ProjectMember,(p['id'],member.id));db_session.delete(membership);db_session.commit()
    with authenticated_as(member) as c:
        assert c.post('/api/v1/coo/actions/'+run['actions'][0]['id']+'/decision',json={'decision':'APPROVE'}).status_code==404
        assert c.get('/api/v1/coo/sessions/'+s['id']).status_code==404

@pytest.mark.asyncio
async def test_real_http_adapter_sends_tool_schema_and_hides_credentials():
    import httpx
    s=get_settings().model_copy(update={'coo_api_key':'server-secret','coo_model':'fixture','coo_base_url':'https://fixture.invalid/v1'})
    captured=[]
    def transport(request):
        captured.append(request)
        return httpx.Response(200,json={'choices':[{'finish_reason':'tool_calls','message':{'role':'assistant','content':None,'tool_calls':[{'id':'c1','type':'function','function':{'name':'list_projects','arguments':'{}'}}]}}],'usage':{'total_tokens':123}})
    original=httpx.AsyncClient
    with patch('app.coo.provider.httpx.AsyncClient',side_effect=lambda **kwargs:original(transport=httpx.MockTransport(transport),**kwargs)):
        result=await ModelClient(s).complete([{'role':'user','content':'查询项目'}],tools=[{'type':'function','function':{'name':'list_projects','parameters':{'type':'object'}}}])
    assert result.token_usage==123 and result.message['tool_calls'][0]['function']['name']=='list_projects'
    assert captured[0].url.path=='/v1/chat/completions'
    assert json.loads(captured[0].content)['tools'][0]['function']['name']=='list_projects'
    assert 'server-secret' not in repr(result)

@pytest.mark.asyncio
async def test_real_http_adapter_does_not_leak_provider_error_body():
    import httpx
    s=get_settings().model_copy(update={'coo_api_key':'server-secret','coo_model':'fixture'})
    original=httpx.AsyncClient
    with patch('app.coo.provider.httpx.AsyncClient',side_effect=lambda **kwargs:original(transport=httpx.MockTransport(lambda request:httpx.Response(401,text='server-secret')),**kwargs)):
        with pytest.raises(AppError) as exc:await ModelClient(s).complete([{'role':'user','content':'hi'}])
    assert 'server-secret' not in str(exc.value)


def test_knowledge_disabled_during_model_generation_invalidates_citation(db_session):
    from tests.test_knowledge import category,save,publish
    from app.knowledge.models import KnowledgeDocument
    from app.db.session import SessionLocal
    with TestClient(app) as c,patch('app.knowledge.providers.embed',side_effect=lambda texts:[[1.,0.] for _ in texts]):
        p=_create_project(c,'引用时重验知识');cat=category(c,p);doc=publish(c,save(c,cat)).json()['data'];s=session(c,p)
        count=0
        async def respond(messages,**kwargs):
            nonlocal count
            count+=1
            if count==1:return tool('search_knowledge',{'project_id':p['id'],'query':'订单超时'})
            sources=json.loads(messages[-1]['content'])['results']
            with SessionLocal() as db:
                d=db.get(KnowledgeDocument,doc['id']);d.enabled=False;db.commit()
            return answer(sources=[sources[0]['id']])
        with patch('app.coo.provider.ModelClient.complete',new=AsyncMock(side_effect=respond)):run=send(c,s)
        assert run['status']=='FAILED' and run['error_code']=='STALE_CITATIONS',run

def test_token_budget_counts_tool_schemas_before_request(db_session,monkeypatch):
    from app.coo import runtime
    monkeypatch.setattr(runtime,'get_settings',lambda:get_settings().model_copy(update={'coo_token_budget':2000}))
    with TestClient(app) as c:
        p=_create_project(c,'预算限制');s=session(c,p)
        with patch('app.coo.provider.ModelClient.complete',new=AsyncMock()) as mocked:run=send(c,s)
        assert run['error_code']=='COO_TOKEN_LIMIT'
        mocked.assert_not_awaited()

def test_historical_run_respects_current_enterprise_department_acl(db_session):
    from app.db.models import Department,UserAccount
    from tests.test_knowledge import save,publish
    admin=_admin(db_session);member=_member(db_session,'部门知识使用者')
    with TestClient(app) as c:
        p=_create_project(c,'企业知识历史权限');_add_member(c,p,admin,member)
        cat=c.post('/api/v1/knowledge/categories',json={'name':'本部门规范','scope':'ENTERPRISE','access_policy':'DEPARTMENT','department_id':member.department_id}).json()['data']
        with patch('app.knowledge.providers.embed',side_effect=lambda texts:[[1.,0.] for _ in texts]):doc=publish(c,save(c,cat)).json()['data']
    with authenticated_as(member) as c,patch('app.knowledge.providers.embed',side_effect=lambda texts:[[1.,0.] for _ in texts]):
        s=session(c,p)
        async def respond(messages,**kwargs):
            if messages[-1]['role']=='user':return tool('search_knowledge',{'project_id':p['id'],'query':'订单超时'})
            return answer(sources=[json.loads(messages[-1]['content'])['results'][0]['id']])
        with patch('app.coo.provider.ModelClient.complete',new=AsyncMock(side_effect=respond)):run=send(c,s)
        assert run['status']=='SUCCEEDED',run
    department=Department(name='调任部门');db_session.add(department);db_session.flush();member.department_id=department.id;db_session.commit()
    with authenticated_as(member) as c:
        assert c.get('/api/v1/coo/runs/'+run['id']).status_code==404
