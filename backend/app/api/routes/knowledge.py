from fastapi import APIRouter, UploadFile, File
from fastapi.encoders import jsonable_encoder
from app.api.deps import DbSession, AuthenticatedUser
from app.schemas.common import ApiResponse
from app.core.exceptions import AppError
from app.knowledge.schemas import CategoryCreate, DocumentSave, Preview, RevisionInput, EnableInput, SearchInput
from app.knowledge.service import KnowledgeService
from app.knowledge.ingestion import split_text
from app.knowledge.retrieval import search
router=APIRouter()

@router.get('/categories')
def categories(db: DbSession, actor: AuthenticatedUser, project_id: str | None = None):
    return ApiResponse(data=jsonable_encoder(KnowledgeService(db,actor).categories(project_id)))

@router.post('/categories',status_code=201)
def create_category(body: CategoryCreate, db: DbSession, actor: AuthenticatedUser):
    return ApiResponse(data=jsonable_encoder(KnowledgeService(db,actor).create_category(body)))

@router.post('/preview')
def preview(body: Preview, actor: AuthenticatedUser):
    return ApiResponse(data={'chunks':split_text(body.content,body.settings)})

@router.post('/upload')
async def upload(actor: AuthenticatedUser, file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(('.txt','.md')):
        raise AppError('仅支持 UTF-8 的 .txt / .md 文本',code='INVALID_TEXT_FILE',status_code=422)
    data=await file.read(1000001)
    if len(data)>1000000: raise AppError('文本不能超过1MB',code='FILE_TOO_LARGE',status_code=413)
    try: content=data.decode('utf-8-sig')
    except UnicodeDecodeError: raise AppError('请上传 UTF-8 编码文本',code='INVALID_ENCODING',status_code=422)
    return ApiResponse(data={'content':content})

@router.get('/documents')
def documents(db: DbSession, actor: AuthenticatedUser, project_id: str | None = None):
    return ApiResponse(data=KnowledgeService(db,actor).list(project_id))

@router.post('/documents',status_code=201)
def save_document(body: DocumentSave, db: DbSession, actor: AuthenticatedUser):
    return ApiResponse(data=KnowledgeService(db,actor).save(body))

@router.get('/documents/{ident}')
def document(ident: str, db: DbSession, actor: AuthenticatedUser):
    s=KnowledgeService(db,actor);return ApiResponse(data=s.view(s.document(ident),detail=True))

@router.put('/documents/{ident}')
def update_document(ident: str, body: DocumentSave, db: DbSession, actor: AuthenticatedUser):
    return ApiResponse(data=KnowledgeService(db,actor).save(body,ident))

@router.post('/documents/{ident}/publish')
def publish(ident: str, body: RevisionInput, db: DbSession, actor: AuthenticatedUser):
    return ApiResponse(data=KnowledgeService(db,actor).publish(ident,body.expected_revision))

@router.patch('/documents/{ident}/enabled')
def enable(ident: str, body: EnableInput, db: DbSession, actor: AuthenticatedUser):
    return ApiResponse(data=KnowledgeService(db,actor).enable(ident,body))

@router.post('/documents/{ident}/restore')
def restore(ident: str, body: RevisionInput, db: DbSession, actor: AuthenticatedUser):
    return ApiResponse(data=KnowledgeService(db,actor).restore(ident,body.expected_revision))

@router.post('/search')
def search_knowledge(body: SearchInput, db: DbSession, actor: AuthenticatedUser):
    return ApiResponse(data=search(db,actor,body))
