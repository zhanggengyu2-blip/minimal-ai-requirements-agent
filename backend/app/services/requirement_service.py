from __future__ import annotations

from datetime import datetime, timezone, timedelta
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppError, NotFoundError, ConflictError
from app.db.models import (
    AnalysisStatus,
    Project,
    ProjectMember,
    Requirement,
    RequirementPriority,
    RequirementType,
    UserAccount,
    UserRole,
)
from app.schemas.requirement import RequirementCreate
from app.coo.analysis import RequirementAnalysisWorkflow
from app.schemas.analysis import AnalysisResult
from pydantic import ValidationError


class RequirementService:
    def __init__(self, db: Session, analyzer=None, *, dify=None) -> None:
        self.db = db
        self.analyzer = analyzer or dify or RequirementAnalysisWorkflow(db)
        self.settings = get_settings()

    def create(
        self, payload: RequirementCreate, *, created_by: str
    ) -> Requirement:
        """先保存需求；仅显式开启 AI 时进入等待分析状态，不在此调用模型。"""
        project = self.db.get(Project, payload.project_id)
        if project is None:
            raise NotFoundError("项目不存在")

        requirement = Requirement(
            **payload.model_dump(exclude={"analyze_with_ai"}),
            created_by=created_by,
            analysis_status=(
                AnalysisStatus.PENDING if payload.analyze_with_ai else AnalysisStatus.NOT_RUN
            ),
        )
        self.db.add(requirement)
        self.db.flush()
        from app.coo.events import enqueue
        # Legacy service fixtures can have non-account author IDs; public APIs always use authenticated accounts.
        if self.db.get(UserAccount, created_by):
            enqueue(self.db, key=f'requirement.created:{requirement.id}', event_type='REQUIREMENT_CREATED',
                project_id=requirement.project_id, actor_id=created_by,
                payload={'requirement_id':requirement.id,'analysis_requested':payload.analyze_with_ai})
        self.db.commit()
        self.db.refresh(requirement)

        return requirement

    async def create_and_analyze(
        self, payload: RequirementCreate, *, created_by: str
    ) -> Requirement:
        """供需要同步结果的调用方使用；未开启 AI 时只保存。"""
        requirement = self.create(payload, created_by=created_by)
        if not payload.analyze_with_ai:
            return requirement
        return await self.analyze_existing(requirement, user=created_by)

    async def create_from_interview(
        self,
        *,
        project_id: str,
        raw_content: str,
        clarified_content: str,
        interview_session_id: str,
        interview_rounds: int,
        completeness_score: int,
        created_by: str | None,
    ) -> Requirement:
        project = self.db.get(Project, project_id)
        if project is None:
            raise NotFoundError("项目不存在")

        requirement = Requirement(
            project_id=project_id,
            raw_content=raw_content,
            clarified_content=clarified_content,
            interview_session_id=interview_session_id,
            interview_rounds=interview_rounds,
            completeness_score=completeness_score,
            created_by=created_by,
            analysis_status=AnalysisStatus.PENDING,
        )
        self.db.add(requirement)
        self.db.commit()
        self.db.refresh(requirement)
        return await self.analyze_existing(
            requirement, user=created_by or f"interview:{interview_session_id}"
        )

    async def analyze_existing(self, requirement: Requirement, *, user: str) -> Requirement:
        """保存分析中状态，调用共用 Coo 工作流，校验十字段与候选范围后持久化。

        模型失败时仅标记 FAILED，保留原始输入。默认适配器在分析前后重验成员写权限；
        并发请求通过状态条件更新互斥，超过运行时限的中断分析可以重新启动。
        """
        project = self.db.get(Project, requirement.project_id)
        if project is None:
            raise NotFoundError("项目不存在")

        if isinstance(self.analyzer, RequirementAnalysisWorkflow):
            from app.services.project_service import ProjectService
            actor = self.db.get(UserAccount, user, populate_existing=True)
            if not actor: raise NotFoundError("分析员工不存在")
            ProjectService(self.db).require_writable(project.id, actor=actor)
        stale_before = datetime.now(timezone.utc) - timedelta(seconds=self.settings.coo_run_timeout_seconds+30)
        claimed = self.db.execute(update(Requirement).where(Requirement.id==requirement.id,
            or_(Requirement.analysis_status!=AnalysisStatus.ANALYZING, Requirement.updated_time<stale_before))
            .values(analysis_status=AnalysisStatus.ANALYZING, analysis_error_code=None, analysis_error_message=None))
        if claimed.rowcount!=1:
            self.db.rollback()
            raise ConflictError("该需求正在分析，请稍后刷新")
        self.db.commit()

        candidates = self._candidate_requirements(project.id, exclude_id=requirement.id)
        try:
            result = await self.analyzer.analyze_requirement(
                project_name=project.name,
                project_context=project.project_context,
                raw_content=requirement.clarified_content or requirement.raw_content,
                candidates=candidates,
                user=user,
                **({"project_id": project.id, "requirement_id": requirement.id} if isinstance(self.analyzer, RequirementAnalysisWorkflow) else {}),
            )
            if isinstance(self.analyzer, RequirementAnalysisWorkflow):
                self.db.expire_all()
                actor = self.db.get(UserAccount, user, populate_existing=True)
                ProjectService(self.db).require_writable(project.id, actor=actor)
            validated = AnalysisResult.model_validate(result.analysis.model_dump())
            if validated.is_duplicate and validated.related_id not in {item["id"] for item in candidates}:
                raise AppError("关联需求不属于当前项目候选范围", code="COO_ANALYSIS_INVALID", status_code=422)
        except (ValidationError, ValueError):
            requirement.analysis_status = AnalysisStatus.FAILED
            requirement.analysis_error_code = "COO_ANALYSIS_INVALID"
            requirement.analysis_error_message = "分析结果未通过结构校验，原始需求已保存"
            self.db.commit()
            return requirement
        except AppError as exc:
            requirement.analysis_status = AnalysisStatus.FAILED
            requirement.analysis_error_code = exc.code
            requirement.analysis_error_message = exc.message
            self.db.commit()
            self.db.refresh(requirement)
            return requirement

        analysis = validated
        for field, value in analysis.model_dump().items():
            if field == "type":
                value = RequirementType(value)
            elif field == "priority":
                value = RequirementPriority(value)
            setattr(requirement, field, value)
        requirement.analysis_status = AnalysisStatus.ANALYZED
        requirement.analysis_error_code = None
        requirement.analysis_error_message = None
        requirement.dify_workflow_run_id = result.workflow_run_id
        self.db.commit()
        self.db.refresh(requirement)
        return requirement

    def get(self, requirement_id: str) -> Requirement:
        requirement = self.db.get(Requirement, requirement_id)
        if requirement is None:
            raise NotFoundError("需求不存在")
        return requirement

    def get_visible(self, requirement_id: str, *, actor: UserAccount) -> Requirement:
        requirement = self.get(requirement_id)
        if actor.role == UserRole.ADMIN:
            return requirement
        membership = self.db.get(ProjectMember, (requirement.project_id, actor.id))
        if membership is None:
            raise NotFoundError("需求不存在")
        return requirement

    def list(
        self,
        *,
        project_id: str | None,
        page: int,
        page_size: int,
        keyword: str | None,
        priority: RequirementPriority | None,
        requirement_type: RequirementType | None,
        analysis_status: AnalysisStatus | None,
        is_fake: bool | None,
        actor: UserAccount | None = None,
    ) -> tuple[list[Requirement], int]: 
        filters = []
        if project_id:
            if actor is not None and self.db.get(Project, project_id) is None:
                raise NotFoundError("项目不存在")
            if actor is not None and actor.role != UserRole.ADMIN:
                membership = self.db.get(ProjectMember, (project_id, actor.id))
                if membership is None:
                    raise NotFoundError("项目不存在")
            filters.append(Requirement.project_id == project_id)
        elif actor is not None and actor.role != UserRole.ADMIN:
            visible_project_ids = select(ProjectMember.project_id).where(
                ProjectMember.user_id == actor.id
            )
            filters.append(Requirement.project_id.in_(visible_project_ids))
        if keyword:
            escaped = keyword.replace("%", r"\%").replace("_", r"\_")
            pattern = f"%{escaped}%"
            filters.append(
                or_(
                    Requirement.raw_content.ilike(pattern, escape="\\"),
                    Requirement.standard_content.ilike(pattern, escape="\\"),
                    Requirement.business_goal.ilike(pattern, escape="\\"),
                )
            )
        if priority:
            filters.append(Requirement.priority == priority)
        if requirement_type:
            filters.append(Requirement.type == requirement_type)
        if analysis_status:
            filters.append(Requirement.analysis_status == analysis_status)
        if is_fake is not None:
            filters.append(Requirement.is_fake == is_fake)

        query = select(Requirement).where(*filters)
        count_query = select(func.count()).select_from(Requirement).where(*filters)
        total = self.db.scalar(count_query) or 0
        items = list(
            self.db.scalars(
                query.order_by(Requirement.created_time.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return items, total

    def _candidate_requirements(self, project_id: str, *, exclude_id: str) -> list[dict[str, str]]:
        """
        Responsibility：
            为需求分析读取同项目的候选需求，排除当前需求。
        Process：
            仅选取 ANALYZED 且标准内容非 NULL 的记录，按更新时间倒序读取，数量受 coo_candidate_limit 限制。
        Output：
            返回仅包含 id 和 standard_content 的字典列表；上限为 0 时直接返回空列表。
        Dependency：
            直接使用数据库 Session 和已加载的配置；只读取数据库，不提交修改或调用外部服务。
        """
        limit = self.settings.coo_candidate_limit
        if limit == 0:
            return []
        rows = self.db.execute(
            select(Requirement.id, Requirement.standard_content)
            .where(
                Requirement.project_id == project_id,
                Requirement.id != exclude_id,
                Requirement.analysis_status == AnalysisStatus.ANALYZED,
                Requirement.standard_content.is_not(None),
            )
            .order_by(Requirement.updated_time.desc())
            .limit(limit)
        ).all()
        return [{"id": row.id, "standard_content": row.standard_content} for row in rows]
