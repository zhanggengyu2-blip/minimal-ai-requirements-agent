from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class Input(BaseModel):
    model_config=ConfigDict(extra='forbid')

class SessionCreate(Input):
    project_id: str|None=Field(default=None,min_length=32,max_length=32)
    title: str=Field(default='与 Coo 协作',min_length=1,max_length=100)

class MessageCreate(Input):
    content: str=Field(min_length=1,max_length=6000)
    allow_comments: bool=False

class Decision(Input):
    decision: Literal['APPROVE','REJECT']

class FinalAnswer(Input):
    answer: str=Field(min_length=1,max_length=8000)
    source_ids: list[str]=Field(default_factory=list,max_length=20)

class SimulatedOrderEvent(Input):
    project_id: str=Field(min_length=32,max_length=32)
    order_id: str=Field(min_length=3,max_length=64,pattern=r'^[A-Za-z0-9_-]+$')
    hours_waiting: int=Field(default=72,ge=24,le=720)
    warehouse: str=Field(default='模拟杭州一号仓',min_length=1,max_length=100)
