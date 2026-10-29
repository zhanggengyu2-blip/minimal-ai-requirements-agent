from datetime import datetime
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, JSON, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.db.models import new_id, utc_now

class KnowledgeCategory(Base):
    __tablename__ = 'knowledge_category'
    __table_args__ = (
        CheckConstraint("scope IN ('ENTERPRISE','PROJECT')", name='ck_knowledge_scope'),
        CheckConstraint("(scope='PROJECT' AND project_id IS NOT NULL AND department_id IS NULL) OR (scope='ENTERPRISE' AND project_id IS NULL)", name='ck_knowledge_scope_ids'),
    )
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    project_id: Mapped[str | None] = mapped_column(ForeignKey('project.id', ondelete='CASCADE'), index=True)
    department_id: Mapped[str | None] = mapped_column(ForeignKey('department.id', ondelete='RESTRICT'))
    created_by: Mapped[str] = mapped_column(ForeignKey('user_account.id'), nullable=False)
    created_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

class KnowledgeDocument(Base):
    __tablename__ = 'knowledge_document'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    category_id: Mapped[str] = mapped_column(ForeignKey('knowledge_category.id', ondelete='CASCADE'), index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey('user_account.id'), nullable=False)
    updated_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

class KnowledgeVersion(Base):
    __tablename__ = 'knowledge_version'
    __table_args__ = (UniqueConstraint('document_id','version'),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    document_id: Mapped[str] = mapped_column(ForeignKey('knowledge_document.id', ondelete='CASCADE'), index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default='DRAFT', nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    settings: Mapped[dict] = mapped_column(JSON, nullable=False)
    embedding_space: Mapped[str | None] = mapped_column(String(256))
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(String(300))
    created_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

class KnowledgeChunk(Base):
    __tablename__ = 'knowledge_chunk'
    __table_args__ = (UniqueConstraint('version_id','ordinal'),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    version_id: Mapped[str] = mapped_column(ForeignKey('knowledge_version.id', ondelete='CASCADE'), index=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list] = mapped_column(JSON, nullable=False)
