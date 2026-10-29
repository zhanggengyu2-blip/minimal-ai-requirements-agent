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
