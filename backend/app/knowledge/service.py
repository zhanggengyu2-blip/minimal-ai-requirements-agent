"""Scoped lifecycle adapted from foundation/knowledge.py. Apache-2.0."""
from datetime import datetime, timezone
from sqlalchemy import select, update, or_
from app.core.exceptions import AppError, ConflictError, NotFoundError, PermissionDeniedError
from app.db.models import UserRole, ProjectMember, utc_now
from app.services.project_service import ProjectService
from .models import KnowledgeCategory as Category, KnowledgeDocument as Document, KnowledgeVersion as Version, KnowledgeChunk as Chunk
from .schemas import DocumentSave, ChunkSettings
from .ingestion import split_text
from . import providers

def now(): return datetime.now(timezone.utc).replace(tzinfo=None)
def iso(value): return value.replace(tzinfo=timezone.utc).isoformat() if value else None

class KnowledgeService:
    def __init__(self, db, actor):
        self.db, self.actor = db, actor
        self.projects = ProjectService(db)

    def category(self, ident, *, write=False):
        c=self.db.get(Category,ident)
        if c is None: raise NotFoundError('知识分类不存在')
        if c.scope=='PROJECT':
            (self.projects.require_writable if write else self.projects.get_visible)(c.project_id,actor=self.actor)
        elif write and self.actor.role!=UserRole.ADMIN:
            raise PermissionDeniedError('企业知识仅由管理员维护')
        elif c.department_id and c.department_id!=self.actor.department_id and self.actor.role!=UserRole.ADMIN:
            raise NotFoundError('知识分类不存在')
        return c

    def categories(self, project_id=None):
        if project_id: self.projects.get_visible(project_id, actor=self.actor)
        enterprise=(Category.scope=='ENTERPRISE')
        if self.actor.role!=UserRole.ADMIN:
            enterprise=enterprise & or_(Category.department_id.is_(None),Category.department_id==self.actor.department_id)
        project=(Category.scope=='PROJECT')
        if project_id: project=project & (Category.project_id==project_id)
        elif self.actor.role!=UserRole.ADMIN:
            project=project & Category.project_id.in_(select(ProjectMember.project_id).where(ProjectMember.user_id==self.actor.id))
        return list(self.db.scalars(select(Category).where(or_(enterprise,project)).order_by(Category.created_time)))

    def create_category(self, body):
        if body.scope=='PROJECT': self.projects.require_writable(body.project_id,actor=self.actor)
        elif self.actor.role!=UserRole.ADMIN: raise PermissionDeniedError('企业知识仅由管理员维护')
        row=Category(**body.model_dump(exclude={'access_policy'}),created_by=self.actor.id)
        self.db.add(row);self.db.commit();self.db.refresh(row)
        return row

    def document(self, ident, *, write=False):
        doc=self.db.get(Document,ident)
        if not doc: raise NotFoundError('知识不存在')
        self.category(doc.category_id,write=write)
        return doc

    def versions(self, ident):
        return list(self.db.scalars(select(Version).where(Version.document_id==ident).order_by(Version.version.desc())))

    def active_version(self, doc):
        if not doc.enabled: return None
        # The newest already-effective publication supersedes all earlier publications.
        # Once it expires, do not silently resurrect an older policy.
        version=self.db.scalar(select(Version).where(Version.document_id==doc.id,Version.status=='PUBLISHED',
            or_(Version.effective_from.is_(None), Version.effective_from<=now())).order_by(Version.version.desc()).limit(1))
        return version if version and (version.effective_until is None or version.effective_until>now()) else None

    def view(self, doc, *, detail=False):
        versions=self.versions(doc.id); active=self.active_version(doc)
        result={'id':doc.id,'title':doc.title,'category_id':doc.category_id,'enabled':doc.enabled,'revision':doc.revision,
            'updated_time':iso(doc.updated_time),'active_version_id':active.id if active else None,
            'state':'已停用' if not doc.enabled else '已发布' if active else '未生效或已失效'}
        def view_version(v):
            row={'id':v.id,'version':v.version,'status':v.status,'error':v.error,'settings':v.settings,
                 'effective_from':iso(v.effective_from),'effective_until':iso(v.effective_until),'created_time':iso(v.created_time)}
            if detail: row['content']=v.content
            return row
        result['versions']=[view_version(v) for v in versions]
        return result

    def list(self, project_id=None):
        ids=[c.id for c in self.categories(project_id)]
        return [self.view(doc) for doc in self.db.scalars(select(Document).where(Document.category_id.in_(ids)).order_by(Document.updated_time.desc()))]

    def _claim(self, doc, expected_revision, **changes):
        changed=self.db.execute(update(Document).where(Document.id==doc.id,Document.revision==expected_revision)
            .values(revision=Document.revision+1,updated_time=utc_now(),**changes))
        if changed.rowcount!=1:
            self.db.rollback();raise ConflictError('知识已被修改，请刷新',code='DOCUMENT_CHANGED')

    def _no_processing(self, doc):
        processing=self.db.scalar(select(Version).where(Version.document_id==doc.id,Version.status=='PROCESSING'))
        if processing:
            if (now()-processing.created_time).total_seconds()>600:
                processing.status='FAILED';processing.error='发布进程中断，请重新发布';self.db.flush()
            else: raise ConflictError('知识正在发布，请稍后再编辑',code='PUBLISH_RUNNING')

    def save(self, body: DocumentSave, ident=None):
        self.category(body.category_id,write=True)
        split_text(body.content,body.settings)
        if ident:
            doc=self.document(ident,write=True); self._no_processing(doc)
            if doc.category_id!=body.category_id: raise AppError('请在原分类中编辑，避免改变访问范围',status_code=422,code='SCOPE_IMMUTABLE')
            self._claim(doc,body.expected_revision,title=body.title)
            number=self.versions(doc.id)[0].version+1
        else:
            if body.expected_revision!=0: raise ConflictError('新知识 revision 应为0')
            doc=Document(title=body.title,category_id=body.category_id,created_by=self.actor.id)
            self.db.add(doc);self.db.flush();number=1
        self.db.add(Version(document_id=doc.id,version=number,content=body.content,settings=body.settings.model_dump(),
            effective_from=body.effective_from,effective_until=body.effective_until,status='DRAFT'))
        self.db.commit();self.db.refresh(doc)
        return self.view(doc,detail=True)

    def publish(self, ident, expected_revision):
        doc=self.document(ident,write=True); self._no_processing(doc)
        version=self.versions(doc.id)[0]
        if version.status=='PUBLISHED': raise ConflictError('当前版本已经发布')
        chunks=split_text(version.content,ChunkSettings.model_validate(version.settings))
        self._claim(doc,expected_revision)
        version.status='PROCESSING';version.error=None
        self.db.commit()
        try:
            vectors=providers.embed(chunks)
            # Recheck permission after the potentially slow external request.
            self.document(ident,write=True)
            for i,(content,vector) in enumerate(zip(chunks,vectors)):
                self.db.add(Chunk(version_id=version.id,ordinal=i,content=content,embedding=vector))
            version.embedding_space=providers.space();version.status='PUBLISHED'
            self.db.commit()
        except AppError as exc:
            self.db.rollback();version=self.db.get(Version,version.id)
            version.status='FAILED';version.error=exc.message;self.db.commit()
        self.db.refresh(doc)
        return self.view(doc,detail=True)

    def enable(self, ident, body):
        doc=self.document(ident,write=True)
        self._no_processing(doc);self._claim(doc,body.expected_revision,enabled=body.enabled)
        self.db.commit();self.db.refresh(doc);return self.view(doc,detail=True)

    def restore(self, ident, expected_revision):
        doc=self.document(ident,write=True)
        published=[v for v in self.versions(doc.id) if v.status=='PUBLISHED']
        if len(published)<2: raise ConflictError('没有上一已发布版本')
        v=published[1]
        return self.save(DocumentSave(title=doc.title,category_id=doc.category_id,expected_revision=expected_revision,
            content=v.content,settings=v.settings,effective_from=v.effective_from,effective_until=v.effective_until),ident)
