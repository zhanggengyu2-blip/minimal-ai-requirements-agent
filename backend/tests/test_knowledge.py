from unittest.mock import patch
from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.exceptions import AppError
from app.knowledge.retrieval import validate_citations
from app.knowledge.service import now
from tests.test_task_api import _admin, _member, _create_project, authenticated_as

def category(c, project, name='项目规则'):
    r=c.post('/api/v1/knowledge/categories',json={'name':name,'scope':'PROJECT','project_id':project['id'],'access_policy':'PROJECT_MEMBERS'})
    assert r.status_code==201,r.text
    return r.json()['data']

def save(c, cat, ident=None, revision=0, **extra):
    body={'title':'履约处理规范','category_id':cat['id'],'content':'订单超时未发货，需要联系仓储核查库存，并记录跟进任务。','expected_revision':revision,**extra}
    r=c.put('/api/v1/knowledge/documents/'+ident,json=body) if ident else c.post('/api/v1/knowledge/documents',json=body)
    assert r.status_code in (200,201),r.text
    return r.json()['data']

def publish(c, doc):
    return c.post(f"/api/v1/knowledge/documents/{doc['id']}/publish",json={'expected_revision':doc['revision']})

def test_publication_failure_retains_old_version_and_scope_filters(db_session):
    with TestClient(app) as c, patch('app.knowledge.providers.embed',side_effect=lambda texts:[[1.,0.] for _ in texts]):
        p=_create_project(c,'履约项目');cat=category(c,p);doc=save(c,cat)
        assert doc['versions'][0]['status']=='DRAFT'
        published=publish(c,doc);assert published.status_code==200,published.text
        doc=published.json()['data'];old=doc['active_version_id'];assert old
        draft=save(c,cat,doc['id'],doc['revision'],content='未验证的新政策')
        with patch('app.knowledge.providers.embed',side_effect=AppError('配置失效',code='MODEL_ERROR')):
            failed=publish(c,draft).json()['data']
        assert failed['active_version_id']==old and failed['versions'][0]['status']=='FAILED'
        assert publish(c,draft).status_code==409
        result=c.post('/api/v1/knowledge/search',json={'query':'订单超时','project_id':p['id']}).json()['data']
        assert result['results'] and result['results'][0]['version_id']==old
        assert validate_citations([result['results'][0]['id']],result['results'])
        with pytest.raises(AppError):validate_citations(['fabricated'],result['results'])
        assert c.post('/api/v1/knowledge/search',json={'query':'订单超时'}).json()['data']['results']==[]
        # Re-publish the failed version, then ensure expiry never resurrects the old policy.
        expired=save(c,cat,doc['id'],failed['revision'],effective_until=(now()-timedelta(seconds=1)).isoformat())
        doc=publish(c,expired).json()['data'];assert doc['active_version_id'] is None
        assert c.post('/api/v1/knowledge/search',json={'query':'订单超时','project_id':p['id']}).json()['data']['results']==[]
    outsider=_member(db_session,'无权限知识访问者')
    with authenticated_as(outsider) as c:
        assert c.get('/api/v1/knowledge/documents/'+doc['id']).status_code==404
        assert c.get('/api/v1/knowledge/documents').json()['data']==[]
        assert c.post('/api/v1/knowledge/search',json={'query':'超时','project_id':p['id']}).status_code==404

def test_enterprise_policy_upload_and_chunk_boundaries(db_session):
    from app.db.models import Department
    other_department=Department(name='保密部门');db_session.add(other_department);db_session.commit()
    with TestClient(app) as c:
        assert c.post('/api/v1/knowledge/categories',json={'name':'缺少策略','scope':'ENTERPRISE'}).status_code==422
        cat=c.post('/api/v1/knowledge/categories',json={'name':'敏感政策','scope':'ENTERPRISE','access_policy':'DEPARTMENT','department_id':other_department.id}).json()['data']
        assert cat['department_id']==other_department.id
        r=c.post('/api/v1/knowledge/upload',files={'file':('规则.txt','联系仓库'.encode(),'text/plain')})
        assert r.json()['data']['content']=='联系仓库'
        assert c.post('/api/v1/knowledge/upload',files={'file':('a.txt',b'\xff','text/plain')}).status_code==422
        assert c.post('/api/v1/knowledge/preview',json={'content':'x'*230,'settings':{'target_chars':100,'overlap_chars':20}}).json()['data']['chunks']==['x'*100,'x'*100,'x'*70]
        assert c.post('/api/v1/knowledge/preview',json={'content':'a','settings':{'target_chars':100,'overlap_chars':100}}).status_code==422
    member=_member(db_session,'普通企业员工')
    with authenticated_as(member) as c:
        assert c.get('/api/v1/knowledge/categories').json()['data']==[]
        assert c.post('/api/v1/knowledge/categories',json={'name':'企业','scope':'ENTERPRISE','access_policy':'ALL_MEMBERS'}).status_code==403

def test_provider_rejects_invalid_vectors_and_rerank_indices(monkeypatch):
    from app.knowledge import providers
    settings=providers.get_settings().model_copy(update={'knowledge_embedding_model':'embedding','knowledge_rerank_model':'rerank','knowledge_rerank_api_key':'secret'})
    monkeypatch.setattr(providers,'get_settings',lambda:settings)
    monkeypatch.setattr(providers,'post',lambda *a:{'data':[{'index':0,'embedding':[float('nan')]}]})
    with pytest.raises(AppError):providers.embed(['a'])
    monkeypatch.setattr(providers,'post',lambda *a:{'results':[{'index':2,'relevance_score':.9}]})
    with pytest.raises(AppError):providers.rerank('a',['b'])
