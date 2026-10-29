from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator

class Input(BaseModel):
    model_config = ConfigDict(extra='forbid')

class CategoryCreate(Input):
    name: str = Field(min_length=1, max_length=100)
    scope: Literal['ENTERPRISE','PROJECT']
    project_id: str | None = Field(default=None, min_length=32, max_length=32)
    access_policy: Literal['ALL_MEMBERS','DEPARTMENT','PROJECT_MEMBERS']
    department_id: str | None = Field(default=None, min_length=32, max_length=32)
    @model_validator(mode='after')
    def scope_ids(self):
        if self.scope == 'PROJECT':
            if not self.project_id or self.department_id or self.access_policy != 'PROJECT_MEMBERS':
                raise ValueError('项目知识必须选择项目成员访问策略')
        elif self.project_id or (self.access_policy == 'DEPARTMENT') != bool(self.department_id) or self.access_policy == 'PROJECT_MEMBERS':
            raise ValueError('企业知识必须明确选择全员或指定部门访问')
        if not self.name.strip(): raise ValueError('分类名称不能为空')
        self.name = self.name.strip()
        return self

class ChunkSettings(Input):
    separator: str = Field(default='\n\n', min_length=1, max_length=20)
    target_chars: int = Field(default=600, ge=100, le=4000)
    overlap_chars: int = Field(default=80, ge=0, le=1000)
    @model_validator(mode='after')
    def overlap(self):
        if self.overlap_chars >= self.target_chars: raise ValueError('重叠必须小于切片长度')
        return self

class Preview(Input):
    content: str = Field(min_length=1, max_length=500000)
    settings: ChunkSettings = Field(default_factory=ChunkSettings)

class DocumentSave(Preview):
    title: str = Field(min_length=1, max_length=200)
    category_id: str = Field(min_length=32, max_length=32)
    expected_revision: int = Field(default=0, ge=0)
    effective_from: datetime | None = None
    effective_until: datetime | None = None
    @field_validator('effective_from','effective_until')
    @classmethod
    def utc(cls, value):
        return value.astimezone(timezone.utc).replace(tzinfo=None) if value and value.tzinfo else value
    @model_validator(mode='after')
    def dates(self):
        if not self.title.strip(): raise ValueError('标题不能为空')
        self.title = self.title.strip()
        if self.effective_from and self.effective_until and self.effective_from >= self.effective_until:
            raise ValueError('失效时间必须晚于生效时间')
        return self

class RevisionInput(Input):
    expected_revision: int = Field(ge=1)

class EnableInput(RevisionInput):
    enabled: bool

class SearchInput(Input):
    query: str = Field(min_length=1, max_length=2000)
    project_id: str | None = Field(default=None, min_length=32, max_length=32)
    top_k: int = Field(default=5, ge=1, le=10)
    min_score: float = Field(default=0, ge=0, le=1)
