"""Validated HTTP adapters adapted from foundation/providers.py. Apache-2.0."""
import hashlib
import math
import httpx
from app.core.config import get_settings
from app.core.exceptions import AppError

def fail(message, code='KNOWLEDGE_MODEL_ERROR'):
    raise AppError(message, code=code, status_code=503)

def space():
    s = get_settings()
    return hashlib.sha256(f'{s.knowledge_embedding_base_url}|{s.knowledge_embedding_model}'.encode()).hexdigest()

def post(base, path, key, payload):
    if not key: fail('知识模型未配置 API Key，请检查服务端环境变量', 'KNOWLEDGE_MODEL_NOT_CONFIGURED')
    try:
        with httpx.Client(timeout=30, follow_redirects=False) as client:
            r = client.post(base.rstrip('/')+path, headers={'Authorization': 'Bearer '+key}, json=payload)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, dict): raise ValueError()
        return data
    except (httpx.HTTPError, ValueError):
        fail('知识模型请求失败，请检查地址、模型与凭据')

def valid_vector(v):
    return isinstance(v,list) and 0 < len(v) <= 8192 and all(type(x) in (float,int) and math.isfinite(x) for x in v) and math.isfinite(sum(x*x for x in v)) and sum(x*x for x in v)>0

def embed(texts):
    s=get_settings(); vectors=[]
    if not s.knowledge_embedding_model: fail('请配置 KNOWLEDGE_EMBEDDING_MODEL', 'KNOWLEDGE_MODEL_NOT_CONFIGURED')
    for start in range(0,len(texts),10):
        batch=texts[start:start+10]
        data=post(s.knowledge_embedding_base_url,'/embeddings',s.knowledge_embedding_api_key,
                  {'model':s.knowledge_embedding_model,'input':batch,'encoding_format':'float'})
        try:
            items=sorted(data['data'],key=lambda row: row['index'])
            if [x['index'] for x in items]!=list(range(len(batch))) or any(type(x['index']) is not int for x in items): raise ValueError()
            result=[x['embedding'] for x in items]
            if not all(valid_vector(v) for v in result) or len({len(v) for v in [*vectors,*result]})!=1: raise ValueError()
            vectors.extend(result)
        except (KeyError, TypeError, ValueError): fail('Embedding 返回数量、维度或数值无效')
    return vectors

def rerank(query, documents):
    s=get_settings()
    if not s.knowledge_rerank_model or not s.knowledge_rerank_api_key: return None
    data=post(s.knowledge_rerank_base_url,'/rerank',s.knowledge_rerank_api_key,
              {'model':s.knowledge_rerank_model,'query':query,'documents':documents,'top_n':len(documents)})
    try:
        rows=data['results']; indices=[r['index'] for r in rows]
        if len(rows)!=len(documents) or len(set(indices))!=len(indices) or any(type(i) is not int or not 0<=i<len(documents) for i in indices): raise ValueError()
        if any(type(r['relevance_score']) not in (float,int) or not math.isfinite(r['relevance_score']) or not 0<=r['relevance_score']<=1 for r in rows): raise ValueError()
        return sorted(rows,key=lambda r:r['relevance_score'],reverse=True)
    except (KeyError,TypeError,ValueError): fail('Rerank 返回索引或相关度无效')
