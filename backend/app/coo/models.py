from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.db.models import new_id, utc_now

class CooSession(Base):
    __tablename__='coo_session'
    id: Mapped[str]=mapped_column(String(32),primary_key=True,default=new_id)
    owner_id: Mapped[str]=mapped_column(ForeignKey('user_account.id'),nullable=False,index=True)
    project_id: Mapped[str|None]=mapped_column(ForeignKey('project.id',ondelete='CASCADE'))
    title: Mapped[str]=mapped_column(String(100),nullable=False,default='与 Coo 协作')
    created_time: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utc_now)

class AgentRun(Base):
    __tablename__='coo_agent_run'
    id: Mapped[str]=mapped_column(String(32),primary_key=True,default=new_id)
    session_id: Mapped[str|None]=mapped_column(ForeignKey('coo_session.id',ondelete='CASCADE'),index=True)
    owner_id: Mapped[str]=mapped_column(ForeignKey('user_account.id'),nullable=False,index=True)
    project_id: Mapped[str|None]=mapped_column(ForeignKey('project.id',ondelete='CASCADE'))
    trigger: Mapped[str]=mapped_column(String(40),nullable=False)
    event_id: Mapped[str|None]=mapped_column(String(32),index=True)
    goal: Mapped[str]=mapped_column(Text,nullable=False)
    status: Mapped[str]=mapped_column(String(24),default='RUNNING',nullable=False)
    answer: Mapped[str|None]=mapped_column(Text)
    sources: Mapped[list]=mapped_column(JSON,default=list,nullable=False)
    project_ids: Mapped[list]=mapped_column(JSON,default=list,nullable=False)
    allow_comments: Mapped[bool]=mapped_column(Boolean,default=False,nullable=False)
    error: Mapped[str|None]=mapped_column(String(500))
    error_code: Mapped[str|None]=mapped_column(String(50))
    token_usage: Mapped[int|None]=mapped_column(Integer)
    model: Mapped[str|None]=mapped_column(String(100))
    created_time: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utc_now)
    finished_time: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))

class CooMessage(Base):
    __tablename__='coo_message'
    id: Mapped[str]=mapped_column(String(32),primary_key=True,default=new_id)
    session_id: Mapped[str]=mapped_column(ForeignKey('coo_session.id',ondelete='CASCADE'),nullable=False,index=True)
    run_id: Mapped[str]=mapped_column(ForeignKey('coo_agent_run.id',ondelete='CASCADE'),nullable=False)
    role: Mapped[str]=mapped_column(String(16),nullable=False)
    content: Mapped[str]=mapped_column(Text,nullable=False)
    created_time: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utc_now)

class CooToolCall(Base):
    __tablename__='coo_tool_call'
    id: Mapped[str]=mapped_column(String(32),primary_key=True,default=new_id)
    run_id: Mapped[str]=mapped_column(ForeignKey('coo_agent_run.id',ondelete='CASCADE'),nullable=False,index=True)
    sequence: Mapped[int]=mapped_column(Integer,nullable=False)
    name: Mapped[str]=mapped_column(String(100),nullable=False)
    arguments: Mapped[dict]=mapped_column(JSON,nullable=False)
    status: Mapped[str]=mapped_column(String(24),nullable=False)
    result: Mapped[dict|list|None]=mapped_column(JSON)
    error: Mapped[str|None]=mapped_column(String(500))
    created_time: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utc_now)
    finished_time: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))

class CooAction(Base):
    __tablename__='coo_action'
    id: Mapped[str]=mapped_column(String(32),primary_key=True,default=new_id)
    run_id: Mapped[str]=mapped_column(ForeignKey('coo_agent_run.id',ondelete='CASCADE'),nullable=False,index=True)
    tool_call_id: Mapped[str]=mapped_column(ForeignKey('coo_tool_call.id',ondelete='CASCADE'),unique=True,nullable=False)
    owner_id: Mapped[str]=mapped_column(ForeignKey('user_account.id'),nullable=False)
    project_id: Mapped[str]=mapped_column(ForeignKey('project.id',ondelete='CASCADE'),nullable=False)
    name: Mapped[str]=mapped_column(String(100),nullable=False)
    arguments: Mapped[dict]=mapped_column(JSON,nullable=False)
    status: Mapped[str]=mapped_column(String(24),nullable=False,default='PENDING')
    result: Mapped[dict|None]=mapped_column(JSON)
    error: Mapped[str|None]=mapped_column(String(300))
    created_time: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utc_now)
    decided_time: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))

class BusinessEvent(Base):
    __tablename__='coo_business_event'
    id: Mapped[str]=mapped_column(String(32),primary_key=True,default=new_id)
    dedupe_key: Mapped[str]=mapped_column(String(200),nullable=False,unique=True)
    event_type: Mapped[str]=mapped_column(String(50),nullable=False)
    project_id: Mapped[str]=mapped_column(ForeignKey('project.id',ondelete='CASCADE'),nullable=False,index=True)
    actor_id: Mapped[str]=mapped_column(ForeignKey('user_account.id'),nullable=False,index=True)
    origin: Mapped[str]=mapped_column(String(20),nullable=False,default='HUMAN')
    payload: Mapped[dict]=mapped_column(JSON,nullable=False)
    status: Mapped[str]=mapped_column(String(24),nullable=False,default='PENDING',index=True)
    attempts: Mapped[int]=mapped_column(Integer,nullable=False,default=0)
    claim_token: Mapped[str|None]=mapped_column(String(32))
    lease_until: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    run_id: Mapped[str|None]=mapped_column(ForeignKey('coo_agent_run.id',ondelete='SET NULL'))
    error: Mapped[str|None]=mapped_column(String(500))
    created_time: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utc_now)
    processed_time: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
