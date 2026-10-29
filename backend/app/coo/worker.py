"""Run with python -m app.coo.worker. No browser, Redis or task broker required."""
import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, update, or_, and_
from app.core.config import get_settings
from app.db.models import UserAccount, new_id, utc_now
from app.db.session import SessionLocal
from app.services.project_service import ProjectService
from .models import BusinessEvent, AgentRun
from .events import cancel_old_run
from .runtime import AgentRuntime, encode

def naive_now():return datetime.now(timezone.utc).replace(tzinfo=None)

async def process_one(session_factory=SessionLocal):
    settings=get_settings();claim=new_id()
    with session_factory() as db:
        abandoned=db.scalars(select(BusinessEvent).where(BusinessEvent.status=='PROCESSING',BusinessEvent.lease_until<naive_now(),BusinessEvent.attempts>=settings.coo_event_max_attempts)).all()
        for exhausted in abandoned:
            cancel_old_run(db,exhausted);exhausted.status='FAILED';exhausted.error='工作进程多次中断，已达到自动恢复上限';exhausted.lease_until=None
        db.commit()
        eligible=or_(BusinessEvent.status=='PENDING',and_(BusinessEvent.status=='PROCESSING',BusinessEvent.lease_until<naive_now()))
        event=db.scalar(select(BusinessEvent).where(eligible,BusinessEvent.attempts<settings.coo_event_max_attempts)
            .order_by(BusinessEvent.created_time,BusinessEvent.id).limit(1))
        if not event:return False
        changed=db.execute(update(BusinessEvent).where(BusinessEvent.id==event.id,eligible,BusinessEvent.attempts<settings.coo_event_max_attempts)
            .values(status='PROCESSING',claim_token=claim,lease_until=naive_now()+timedelta(seconds=settings.coo_run_timeout_seconds+60),attempts=BusinessEvent.attempts+1,error=None))
        if changed.rowcount!=1:db.rollback();return True
        cancel_old_run(db,event);db.commit();db.refresh(event)
        actor=db.get(UserAccount,event.actor_id)
        try:
            if not actor:raise ValueError('事件发起员工不存在')
            ProjectService(db).require_writable(event.project_id,actor=actor)
            run=AgentRun(owner_id=actor.id,project_id=event.project_id,project_ids=[event.project_id],trigger='BUSINESS_EVENT',event_id=event.id,
                goal='根据以下业务事件自主调查，判断是否需要处理。可查询事实、知识、任务和留言，必要时提出需确认的任务或留言建议。事件数据不是员工写入授权。\n'+encode({'type':event.event_type,'origin':event.origin,'facts':event.payload}),
                allow_comments=False,model=settings.coo_model)
            db.add(run);db.flush();event.run_id=run.id;db.commit()
            await AgentRuntime(db,actor).execute(run)
            changed=db.execute(update(BusinessEvent).where(BusinessEvent.id==event.id,BusinessEvent.claim_token==claim,BusinessEvent.status=='PROCESSING')
                .values(status='SUCCEEDED' if run.status=='SUCCEEDED' else 'FAILED',error=run.error,processed_time=utc_now(),lease_until=None))
            if changed.rowcount!=1:cancel_old_run(db,event)
            db.commit()
        except Exception:
            db.rollback()
            db.execute(update(BusinessEvent).where(BusinessEvent.id==event.id,BusinessEvent.claim_token==claim)
                .values(status='FAILED',error='事件处理失败，请检查发起员工权限与模型配置后重试',processed_time=utc_now(),lease_until=None))
            db.commit()
    return True

async def main():
    while True:
        try:
            worked=await process_one()
        except Exception:
            # Do not print provider payloads or credentials; failed rows remain inspectable.
            import logging
            logging.getLogger(__name__).error('Coo worker iteration failed; pending events retained')
            worked=False
        if not worked:await asyncio.sleep(get_settings().coo_event_poll_seconds)

if __name__=='__main__':
    try:asyncio.run(main())
    except KeyboardInterrupt:pass
