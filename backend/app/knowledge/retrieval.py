"""Hybrid recall and RRF adapted from foundation/retrieval.py (Apache-2.0)."""
import math
import re
from sqlalchemy import select
from app.core.exceptions import AppError
from .service import KnowledgeService
from .models import KnowledgeDocument as Document, KnowledgeChunk as Chunk
from . import providers

def search(db, actor, body):
    service=KnowledgeService(db,actor)
    categories=[c for c in service.categories(body.project_id) if c.scope=='ENTERPRISE' or c.project_id==body.project_id]
    chunks=[]
    for doc in db.scalars(select(Document).where(Document.category_id.in_([c.id for c in categories]),Document.enabled.is_(True))):
        version=service.active_version(doc)
        if not version: continue
        for chunk in db.scalars(select(Chunk).where(Chunk.version_id==version.id)):
            chunks.append({'id':chunk.id,'content':chunk.content,'vector':chunk.embedding,'document_id':doc.id,
                           'document_title':doc.title,'version_id':version.id,'version':version.version,'space':version.embedding_space})
    chinese=re.findall(r'[\u4e00-\u9fff]',body.query)
    terms=set(re.findall(r'[a-z0-9_-]+',body.query.lower())+[''.join(chinese[i:i+2]) for i in range(len(chinese)-1)]+chinese)
    lexical=sorted([(c,sum(c['content'].lower().count(t) for t in terms)) for c in chunks],key=lambda r:r[1],reverse=True)
    lexical=[c for c,score in lexical if score>0][:30]
    vectors=[];warnings=[]
    if chunks:
        try:
            q=providers.embed([body.query])[0];norm=math.sqrt(sum(x*x for x in q))
            for c in chunks:
                v=c['vector']
                if c['space']!=providers.space() or not providers.valid_vector(v) or len(v)!=len(q): continue
                denominator=norm*math.sqrt(sum(x*x for x in v))
                if denominator: vectors.append((c,sum(x*y for x,y in zip(q,v))/denominator))
            vectors=[c for c,_ in sorted(vectors,key=lambda r:r[1],reverse=True)[:30]]
        except AppError as exc: warnings.append(exc.message+'；当前仅使用关键词检索')
    scores={}
    for group in (lexical,vectors):
        for position,c in enumerate(group,1): scores[c['id']]=scores.get(c['id'],0)+1/(60+position)
    by_id={c['id']:c for c in chunks}
    merged=[by_id[cid] for cid in sorted(scores,key=scores.get,reverse=True)[:20]]
    reranked=providers.rerank(body.query,[c['content'] for c in merged]) if merged else None
    if reranked is None:
        warnings.append('未配置 Rerank，结果按 RRF 融合排序；不应用相关度阈值')
        results=[dict(c,score=scores[c['id']]) for c in merged]
    else: results=[dict(merged[r['index']],score=r['relevance_score']) for r in reranked if r['relevance_score']>=body.min_score]
    results=[{k:v for k,v in c.items() if k not in ('vector','space')} for c in results[:body.top_k]]
    return {'results':results,'warnings':warnings,'rerank_applied':reranked is not None,'score_kind':'rerank_relevance' if reranked is not None else 'rrf',
            'recall':{'keyword_ids':[c['id'] for c in lexical],'vector_ids':[c['id'] for c in vectors]}}

def validate_citations(source_ids, results):
    allowed={row['id'] for row in results}
    if any(type(i) is not str or i not in allowed for i in source_ids):
        raise AppError('引用不属于本次授权检索结果',code='INVALID_CITATIONS',status_code=422)
    return [row for row in results if row['id'] in source_ids]
