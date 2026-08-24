from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.db.models import (
    Department,
    Project,
    ProjectMember,
    ProjectStatus,
    Requirement,
    Task,
    TaskLane,
    UserAccount,
    UserRole,
    utc_now,
)
from app.schemas.project import (
    ProjectCreate,
    ProjectMemberList,
    ProjectMemberRead,
    ProjectMembersUpdate,
    ProjectRead,
    ProjectUpdate,
)


class ProjectService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: ProjectCreate, *, actor: UserAccount) -> ProjectRead:
        self._validate_department(payload.department_id)
        ordered_member_ids = [
            actor.id,
            *(user_id for user_id in payload.member_ids if user_id != actor.id),
        ]
        found_member_ids = set(
            self.db.scalars(
                select(UserAccount.id).where(UserAccount.id.in_(ordered_member_ids))
            )
        )
        if found_member_ids != set(ordered_member_ids):
            raise NotFoundError("成员列表中存在未注册用户")

        project = Project(
            **payload.model_dump(exclude={"member_ids"}),
            created_by=actor.id,
        )
        self.db.add(project)
        try:
            self.db.flush()
            for sort_order, user_id in enumerate(ordered_member_ids, start=1):
                self.db.add(
                    ProjectMember(
                        project_id=project.id,
                        user_id=user_id,
                        added_by=actor.id,
                        sort_order=sort_order,
                    )
                )
                self.db.add(TaskLane(project_id=project.id, assignee_id=user_id))
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError("项目名称已存在") from exc
        self.db.refresh(project)
        return self._to_read(project)

    def list(
        self,
        *,
        actor: UserAccount,
        page: int,
        page_size: int,
        status: str | None,
    ) -> tuple[list[ProjectRead], int]:
        requirement_count = (
            select(func.count())
            .select_from(Requirement)
            .where(Requirement.project_id == Project.id)
            .correlate(Project)
            .scalar_subquery()
        )
        member_count = (
            select(func.count())
            .select_from(ProjectMember)
            .where(ProjectMember.project_id == Project.id)
            .correlate(Project)
            .scalar_subquery()
        )
        query = select(Project, requirement_count, member_count)
        count_query = select(func.count()).select_from(Project)
        if actor.role != UserRole.ADMIN:
            visible_project_ids = select(ProjectMember.project_id).where(
                ProjectMember.user_id == actor.id
            )
            query = query.where(Project.id.in_(visible_project_ids))
            count_query = count_query.where(Project.id.in_(visible_project_ids))
        if status:
            query = query.where(Project.status == status)
            count_query = count_query.where(Project.status == status)

        total = self.db.scalar(count_query) or 0
        rows = self.db.execute(
            query.order_by(Project.created_time.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        items: list[ProjectRead] = []
        for project, requirements, members in rows:
            item = ProjectRead.model_validate(project)
            item.requirement_count = requirements
            item.member_count = members
            items.append(item)
        return items, total

    def get_visible(self, project_id: str, *, actor: UserAccount) -> Project:
        project = self.db.get(Project, project_id)
        if project is None:
            raise NotFoundError("项目不存在")
        if actor.role == UserRole.ADMIN or self._is_member(project.id, actor.id):
            return project
        raise NotFoundError("项目不存在")

    def require_member(self, project_id: str, *, actor: UserAccount) -> Project:
        project = self.db.get(Project, project_id)
        if project is None:
            raise NotFoundError("项目不存在")
        if self._is_member(project.id, actor.id):
            return project
        if actor.role == UserRole.ADMIN:
            raise PermissionDeniedError("请先将自己加入项目成员后再修改项目")
        raise NotFoundError("项目不存在")

    def require_writable(self, project_id: str, *, actor: UserAccount) -> Project:
        project = self.require_member(project_id, actor=actor)
        if project.status != ProjectStatus.ACTIVE:
            raise PermissionDeniedError("归档项目为只读状态", code="PROJECT_ARCHIVED")
        return project

    def get(self, project_id: str, *, actor: UserAccount) -> ProjectRead:
        return self._to_read(self.get_visible(project_id, actor=actor))

    def update(
        self,
        project_id: str,
        payload: ProjectUpdate,
        *,
        actor: UserAccount,
    ) -> ProjectRead:
        project = self.require_member(project_id, actor=actor)
        changes = payload.model_dump(exclude_unset=True, exclude={"expected_revision"})
        if project.status == ProjectStatus.ARCHIVED:
            if changes != {"status": ProjectStatus.ACTIVE}:
                raise PermissionDeniedError(
                    "归档项目只能重新打开，不能修改其他信息",
                    code="PROJECT_ARCHIVED",
                )
        self._validate_department(changes.get("department_id"), supplied="department_id" in changes)

        changes["updated_time"] = utc_now()
        changes["revision"] = Project.revision + 1
        try:
            result = self.db.execute(
                update(Project)
                .where(Project.id == project.id, Project.revision == payload.expected_revision)
                .values(**changes)
            )
            if result.rowcount != 1:
                self.db.rollback()
                self._raise_revision_conflict(project.id, payload.expected_revision)
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError("项目名称已存在") from exc
        refreshed = self.db.get(Project, project.id)
        if refreshed is None:
            raise NotFoundError("项目不存在")
        return self._to_read(refreshed)

    def list_members(self, project_id: str, *, actor: UserAccount) -> ProjectMemberList:
        project = self.get_visible(project_id, actor=actor)
        rows = self.db.execute(
            select(ProjectMember, UserAccount, Department)
            .join(UserAccount, UserAccount.id == ProjectMember.user_id)
            .join(Department, Department.id == UserAccount.department_id)
            .where(ProjectMember.project_id == project.id)
            .order_by(ProjectMember.sort_order, UserAccount.id)
        ).all()
        task_counts = self._assigned_task_counts(project.id)
        return ProjectMemberList(
            items=[
                ProjectMemberRead(
                    user_id=user.id,
                    name=user.name,
                    department_id=department.id,
                    department_name=department.name,
                    role=user.role,
                    sort_order=membership.sort_order,
                    task_count=task_counts.get(user.id, 0),
                    created_time=membership.created_time,
                )
                for membership, user, department in rows
            ],
            member_revision=project.member_revision,
        )

    def save_members(
        self,
        project_id: str,
        payload: ProjectMembersUpdate,
        *,
        actor: UserAccount,
    ) -> ProjectMemberList:
        project = self.get_visible(project_id, actor=actor)
        if project.status != ProjectStatus.ACTIVE:
            raise PermissionDeniedError("归档项目为只读状态", code="PROJECT_ARCHIVED")

        ordered_ids = payload.user_ids
        requested_ids = set(ordered_ids)
        users = list(self.db.scalars(select(UserAccount).where(UserAccount.id.in_(requested_ids))))
        found_ids = {user.id for user in users}
        if found_ids != requested_ids:
            raise NotFoundError("成员列表中存在未注册用户")

        current_memberships = list(
            self.db.scalars(
                select(ProjectMember).where(ProjectMember.project_id == project.id)
            )
        )
        membership_by_user_id = {
            membership.user_id: membership for membership in current_memberships
        }
        current_ids = set(membership_by_user_id)
        removed_ids = current_ids - requested_ids
        assigned_counts = self._assigned_task_counts(project.id, user_ids=removed_ids)
        blocked = {user_id: count for user_id, count in assigned_counts.items() if count > 0}
        if blocked:
            raise ConflictError(
                "仍负责任务的成员不能移除，请先转交任务",
                code="PROJECT_MEMBER_HAS_TASKS",
                details={"task_counts": blocked},
            )

        revision_result = self.db.execute(
            update(Project)
            .where(
                Project.id == project.id,
                Project.member_revision == payload.expected_member_revision,
            )
            .values(member_revision=Project.member_revision + 1, updated_time=utc_now())
        )
        if revision_result.rowcount != 1:
            self.db.rollback()
            current_revision = self.db.scalar(
                select(Project.member_revision).where(Project.id == project.id)
            )
            raise ConflictError(
                "项目成员已被其他人修改，请刷新后重试",
                code="PROJECT_MEMBER_REVISION_CONFLICT",
                details={
                    "project_id": project.id,
                    "expected_member_revision": payload.expected_member_revision,
                    "current_member_revision": current_revision,
                },
            )

        if removed_ids:
            self.db.execute(
                delete(TaskLane).where(
                    TaskLane.project_id == project.id,
                    TaskLane.assignee_id.in_(removed_ids),
                )
            )
            self.db.execute(
                delete(ProjectMember).where(
                    ProjectMember.project_id == project.id,
                    ProjectMember.user_id.in_(removed_ids),
                )
            )
        for sort_order, user_id in enumerate(ordered_ids, start=1):
            membership = membership_by_user_id.get(user_id)
            if membership is None:
                self.db.add(
                    ProjectMember(
                        project_id=project.id,
                        user_id=user_id,
                        added_by=actor.id,
                        sort_order=sort_order,
                    )
                )
                self.db.add(TaskLane(project_id=project.id, assignee_id=user_id))
            else:
                membership.sort_order = sort_order
        self.db.commit()
        return self.list_members(project.id, actor=actor)

    def visible_project_ids(self, *, actor: UserAccount):
        if actor.role == UserRole.ADMIN:
            return select(Project.id)
        return select(ProjectMember.project_id).where(ProjectMember.user_id == actor.id)

    def _to_read(self, project: Project) -> ProjectRead:
        item = ProjectRead.model_validate(project)
        item.requirement_count = self.db.scalar(
            select(func.count()).select_from(Requirement).where(Requirement.project_id == project.id)
        ) or 0
        item.member_count = self.db.scalar(
            select(func.count()).select_from(ProjectMember).where(ProjectMember.project_id == project.id)
        ) or 0
        return item

    def _is_member(self, project_id: str, user_id: str) -> bool:
        return self.db.get(ProjectMember, (project_id, user_id)) is not None

    def _validate_department(self, department_id: str | None, *, supplied: bool = True) -> None:
        if not supplied or department_id is None:
            return
        if self.db.get(Department, department_id) is None:
            raise NotFoundError("部门不存在")

    def _raise_revision_conflict(self, project_id: str, expected_revision: int) -> None:
        current_revision = self.db.scalar(select(Project.revision).where(Project.id == project_id))
        raise ConflictError(
            "项目已被其他人修改，请刷新后重试",
            code="PROJECT_REVISION_CONFLICT",
            details={
                "project_id": project_id,
                "expected_revision": expected_revision,
                "current_revision": current_revision,
            },
        )

    def _assigned_task_counts(
        self,
        project_id: str,
        *,
        user_ids: set[str] | None = None,
    ) -> dict[str, int]:
        query = (
            select(Task.assignee_id, func.count(Task.id))
            .where(Task.project_id == project_id)
            .group_by(Task.assignee_id)
        )
        if user_ids is not None:
            if not user_ids:
                return {}
            query = query.where(Task.assignee_id.in_(user_ids))
        rows = self.db.execute(query).all()
        return {assignee_id: task_count for assignee_id, task_count in rows}
