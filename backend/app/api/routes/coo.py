from fastapi import APIRouter
from app.api.deps import DbSession, AuthenticatedUser
from app.schemas.common import ApiResponse
from app.core.config import get_settings
from app.coo.schemas import SessionCreate, MessageCreate, Decision
from app.coo.runtime import CooService
router=APIRouter()

@router.get('/status')
def status(actor: AuthenticatedUser):
    s=get_settings();return ApiResponse(data={'model_configured':bool(s.coo_api_key and s.coo_model),'model':s.coo_model,'mode':'LLM_TOOL_CALLING'})

@router.get('/sessions')
def sessions(db: DbSession,actor: AuthenticatedUser):return ApiResponse(data=CooService(db,actor).sessions())

@router.post('/sessions',status_code=201)
def create_session(body:SessionCreate,db:DbSession,actor:AuthenticatedUser):return ApiResponse(data=CooService(db,actor).create_session(body))

@router.get('/sessions/{ident}')
def history(ident:str,db:DbSession,actor:AuthenticatedUser):return ApiResponse(data=CooService(db,actor).history(ident))

@router.post('/sessions/{ident}/messages')
async def send(ident:str,body:MessageCreate,db:DbSession,actor:AuthenticatedUser):return ApiResponse(data=await CooService(db,actor).send(ident,body))

@router.get('/runs/{ident}')
def run(ident:str,db:DbSession,actor:AuthenticatedUser):
    s=CooService(db,actor);return ApiResponse(data=s.run_view(s.check_run(ident)))

@router.post('/actions/{ident}/decision')
async def decide(ident:str,body:Decision,db:DbSession,actor:AuthenticatedUser):return ApiResponse(data=await CooService(db,actor).decide(ident,body.decision))
