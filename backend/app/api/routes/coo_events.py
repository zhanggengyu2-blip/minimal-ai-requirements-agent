from fastapi import APIRouter
from sqlalchemy import select
from app.api.deps import DbSession, AuthenticatedUser
from app.schemas.common import ApiResponse
from app.coo.models import AgentRun
from app.coo.schemas import SimulatedOrderEvent
from app.coo.events import EventService
from app.coo.runtime import CooService
from app.core.exceptions import NotFoundError
router=APIRouter()

@router.get('/events')
def events(db:DbSession,actor:AuthenticatedUser):return ApiResponse(data=EventService(db,actor).list())

@router.post('/events/simulated-order',status_code=201)
def simulate(body:SimulatedOrderEvent,db:DbSession,actor:AuthenticatedUser):return ApiResponse(data=EventService(db,actor).simulate(body))

@router.post('/events/{ident}/retry')
def retry(ident:str,db:DbSession,actor:AuthenticatedUser):return ApiResponse(data=EventService(db,actor).retry(ident))

@router.get('/runs')
def runs(db:DbSession,actor:AuthenticatedUser):
    rows=db.scalars(select(AgentRun).where(AgentRun.owner_id==actor.id).order_by(AgentRun.created_time.desc()).limit(50)).all()
    result=[];service=CooService(db,actor)
    for row in rows:
        try:result.append(service.run_summary(row))
        except NotFoundError:continue
    return ApiResponse(data=result)
