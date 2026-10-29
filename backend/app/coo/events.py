"""Durable business outbox. Insertion shares the originating business transaction."""
from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert
from app.core.exceptions import ConflictError, NotFoundError
from app.core.config import get_settings
from app.db.models import new_id, utc_now
from app.services.project_service import ProjectService
from .models import BusinessEvent, CooAction, AgentRun


def enqueue(db, *, key, event_type, project_id, actor_id, payload, origin='HUMAN'):
    # SQLite's atomic unique conflict handling also deduplicates concurrent deliveries.
    ident=new_id()
    db.execute(insert(BusinessEvent).values(id=ident,dedupe_key=key,event_type=event_type,project_id=project_id,
        actor_id=actor_id,payload=payload,origin=origin,status='PENDING',attempts=0,created_time=utc_now()).on_conflict_do_nothing(index_elements=['dedupe_key']))
    return db.scalar(select(BusinessEvent).where(BusinessEvent.dedupe_key==key))


def cancel_old_run(db,event):
    if event.run_id:
        db.execute(update(CooAction).where(CooAction.run_id==event.run_id,CooAction.status=='PENDING')
            .values(status='CANCELED',error='事件已重新处理，本次建议失效'))
        run=db.get(AgentRun,event.run_id)
        if run and run.status=='RUNNING':
            run.status='FAILED';run.error='工作进程中断或租约过期';run.error_code='COO_INTERRUPTED';run.finished_time=utc_now()

class EventService:
    def __init__(self,db,actor):self.db,self.actor=db,actor

    def get(self,ident):
        event=self.db.get(BusinessEvent,ident)
        if not event or event.actor_id!=self.actor.id:raise NotFoundError('事件不存在')
        ProjectService(self.db).get_visible(event.project_id,actor=self.actor)
        return event

    def view(self,event):return {c.name:getattr(event,c.name) for c in event.__table__.columns if c.name!='claim_token'}

    def list(self):
        rows=self.db.scalars(select(BusinessEvent).where(BusinessEvent.actor_id==self.actor.id).order_by(BusinessEvent.created_time.desc()).limit(100)).all()
        result=[]
        for event in rows:
            try:self.get(event.id)
            except NotFoundError:continue
            result.append(self.view(event))
        return result

    def simulate(self,body):
        ProjectService(self.db).require_writable(body.project_id,actor=self.actor)
        payload={'source':'SIMULATED_ERP','simulation':True,'order_id':body.order_id,'payment_status':'PAID',
                 'shipping_status':'NOT_SHIPPED','hours_waiting':body.hours_waiting,'warehouse':body.warehouse,
                 'description':'模拟电商履约异常：已付款订单超时未发货，请调查处理规范、相关任务和可联系的项目成员，提出跟进建议。'}
        key=f'erp.simulated:{body.project_id}:{body.order_id}'
        existing=self.db.scalar(select(BusinessEvent).where(BusinessEvent.dedupe_key==key))
        if existing and existing.actor_id!=self.actor.id:raise ConflictError('该模拟订单已由其他员工发起')
        event=enqueue(self.db,key=key,event_type='FULFILLMENT_DELAY',project_id=body.project_id,actor_id=self.actor.id,payload=payload,origin='SIMULATED_ERP')
        self.db.commit();return self.view(event)

    def retry(self,ident):
        event=self.get(ident)
        ProjectService(self.db).require_writable(event.project_id,actor=self.actor)
        if event.status!='FAILED':raise ConflictError('仅失败事件可重试；运行中事件会由后台租约恢复')
        if event.attempts>=get_settings().coo_event_max_attempts:raise ConflictError('已达到重试上限，请检查模型与权限后创建新事件')
        cancel_old_run(self.db,event)
        event.status='PENDING';event.error=None;event.claim_token=None;event.lease_until=None
        self.db.commit();return self.view(event)

    def simulated_order(self,project_id,order_id):
        ProjectService(self.db).get_visible(project_id,actor=self.actor)
        event=self.db.scalar(select(BusinessEvent).where(BusinessEvent.project_id==project_id,
            BusinessEvent.dedupe_key==f'erp.simulated:{project_id}:{order_id}',BusinessEvent.origin=='SIMULATED_ERP'))
        if not event:raise NotFoundError('模拟订单不存在；此适配器尚未接入真实 ERP')
        return event.payload
