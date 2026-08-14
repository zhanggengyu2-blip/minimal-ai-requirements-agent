from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppError, NotFoundError
from app.db.models import (
    AnalysisStatus,
    Project,
    Requirement,
    RequirementPriority,
    RequirementType,
)
from app.schemas.requirement import RequirementCreate
from app.services.dify_service import DifyService


class RequirementService:
    def __init__(self, db: Session, dify: DifyService | None = None) -> None:
        self.db = db
        self.dify = dify or DifyService()
        self.settings = get_settings()

    async def create_and_analyze(self, payload: RequirementCreate) -> Requirement:
        project = self.db.get(Project, payload.project_id)
        if project is None:
            raise NotFoundError("项目不存在")

        requirement = Requirement(**payload.model_dump(), analysis_status=AnalysisStatus.PENDING)
        self.db.add(requirement)
        self.db.commit()
        self.db.refresh(requirement)

        return await self.analyze_existing(
            requirement, user=payload.created_by or "anonymous"
        )

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
        project = self.db.get(Project, requirement.project_id)
        if project is None:
            raise NotFoundError("项目不存在")

        requirement.analysis_status = AnalysisStatus.ANALYZING
        requirement.analysis_error_code = None
        requirement.analysis_error_message = None
        self.db.commit()

        candidates = self._candidate_requirements(project.id, exclude_id=requirement.id)
        try:
            result = await self.dify.analyze_requirement(
                project_name=project.name,
                project_context=project.project_context,
                raw_content=requirement.clarified_content or requirement.raw_content,
                candidates=candidates,
                user=user,
            )
        except AppError as exc:
            requirement.analysis_status = AnalysisStatus.FAILED
            requirement.analysis_error_code = exc.code
            requirement.analysis_error_message = exc.message
            self.db.commit()
            self.db.refresh(requirement)
            return requirement

        analysis = result.analysis
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
    ) -> tuple[list[Requirement], int]: 
        filters = []
        if project_id:
            filters.append(Requirement.project_id == project_id)
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
        limit = self.settings.dify_candidate_limit
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
