from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.db.models import Project, Requirement
from app.schemas.project import ProjectCreate, ProjectRead


class ProjectService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: ProjectCreate, *, created_by: str) -> ProjectRead:
        project = Project(**payload.model_dump(), created_by=created_by)
        self.db.add(project)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError("项目名称已存在") from exc
        self.db.refresh(project)
        return ProjectRead.model_validate(project)

    def list(self, *, page: int, page_size: int, status: str | None) -> tuple[list[ProjectRead], int]:
        requirement_count = func.count(Requirement.id).label("requirement_count")
        query = (
            select(Project, requirement_count)
            .outerjoin(Requirement, Requirement.project_id == Project.id)
            .group_by(Project.id)
        )
        count_query = select(func.count()).select_from(Project)
        if status:
            query = query.where(Project.status == status)
            count_query = count_query.where(Project.status == status)

        total = self.db.scalar(count_query) or 0
        rows = self.db.execute(
            query.order_by(Project.created_time.desc()).offset((page - 1) * page_size).limit(page_size)
        ).all()
        items = []
        for project, count in rows:
            item = ProjectRead.model_validate(project)
            item.requirement_count = count
            items.append(item)
        return items, total
