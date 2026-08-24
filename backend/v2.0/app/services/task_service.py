from datetime import date

from sqlalchemy import case, delete, func, inspect, select, text, update
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.db.models import (
    ProjectMember,
    Task,
    TaskLane,
    TaskStatus,
    UserAccount,
    utc_now,
)
from app.schemas.task import (
    TaskCreate,
    TaskLaneOrderRead,
    TaskLaneOrderUpdate,
    TaskLaneRevision,
    TaskList,
    TaskRead,
    TaskStatusFilter,
    TaskUpdate,
)
from app.services.project_service import ProjectService


TASKS_PER_ASSIGNEE_LIMIT = 200


class TaskService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.projects = ProjectService(db)

    def list(
        self,
        project_id: str,
        *,
        actor: UserAccount,
        keyword: str | None,
        status_filter: TaskStatusFilter,
        version_id: str | None,
    ) -> TaskList:
        self.projects.get_visible(project_id, actor=actor)
        if version_id is not None:
            self._validate_version(project_id, version_id)

        filters = [Task.project_id == project_id]
        if keyword:
            escaped = keyword.replace("%", r"\%").replace("_", r"\_")
            filters.append(Task.name.ilike(f"%{escaped}%", escape="\\"))
        if status_filter == TaskStatusFilter.UNFINISHED:
            filters.append(Task.status.in_([TaskStatus.NOT_STARTED, TaskStatus.IN_PROGRESS]))
        elif status_filter != TaskStatusFilter.ALL:
            filters.append(Task.status == TaskStatus(status_filter.value))
        if version_id is not None:
            filters.append(Task.version_id == version_id)

        total = self.db.scalar(select(func.count()).select_from(Task).where(*filters)) or 0
        tasks = list(
            self.db.scalars(
                select(Task)
                .join(
                    ProjectMember,
                    (ProjectMember.project_id == Task.project_id)
                    & (ProjectMember.user_id == Task.assignee_id),
                )
                .where(*filters)
                .order_by(
                    ProjectMember.sort_order,
                    Task.sort_order,
                    Task.created_time,
                    Task.id,
                )
            )
        )
        lane_rows = self.db.execute(
            select(ProjectMember.user_id, TaskLane.revision)
            .outerjoin(
                TaskLane,
                (TaskLane.project_id == ProjectMember.project_id)
                & (TaskLane.assignee_id == ProjectMember.user_id),
            )
            .where(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.sort_order, ProjectMember.user_id)
        ).all()
        return TaskList(
            items=[TaskRead.model_validate(task) for task in tasks],
            total=total,
            lanes=[
                TaskLaneRevision(assignee_id=row.user_id, revision=row.revision or 1)
                for row in lane_rows
            ],
        )

    def create(
        self,
        project_id: str,
        payload: TaskCreate,
        *,
        actor: UserAccount,
    ) -> Task:
        self.projects.require_writable(project_id, actor=actor)
        self._validate_assignee(project_id, payload.assignee_id)
        self._validate_version(project_id, payload.version_id)
        self._validate_dates(payload.start_date, payload.due_date)

        self._bump_lane(project_id, payload.assignee_id)
        self._validate_lane_capacity(project_id, payload.assignee_id)
        sort_order = self._next_sort_order(project_id, payload.assignee_id)
        task = Task(
            project_id=project_id,
            **payload.model_dump(),
            sort_order=sort_order,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.db.add(task)
        self._ensure_version_participant(payload.version_id, payload.assignee_id)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get(self, project_id: str, task_id: str, *, actor: UserAccount) -> Task:
        self.projects.get_visible(project_id, actor=actor)
        return self._get_in_project(project_id, task_id)

    def update(
        self,
        project_id: str,
        task_id: str,
        payload: TaskUpdate,
        *,
        actor: UserAccount,
    ) -> Task:
        self.projects.require_writable(project_id, actor=actor)
        task = self._get_in_project(project_id, task_id)
        changes = payload.model_dump(exclude_unset=True, exclude={"expected_revision"})

        assignee_id = changes.get("assignee_id", task.assignee_id)
        version_id = changes.get("version_id", task.version_id)
        start_date = changes.get("start_date", task.start_date)
        due_date = changes.get("due_date", task.due_date)
        self._validate_assignee(project_id, assignee_id)
        self._validate_version(project_id, version_id)
        self._validate_dates(start_date, due_date)

        moved = assignee_id != task.assignee_id
        if moved:
            self._bump_lane(project_id, task.assignee_id)
            self._bump_lane(project_id, assignee_id)
            self._validate_lane_capacity(project_id, assignee_id)
            changes["sort_order"] = self._next_sort_order(project_id, assignee_id)

        changes.update(
            revision=Task.revision + 1,
            updated_by=actor.id,
            updated_time=utc_now(),
        )
        result = self.db.execute(
            update(Task)
            .where(
                Task.id == task.id,
                Task.project_id == project_id,
                Task.revision == payload.expected_revision,
            )
            .values(**changes)
        )
        if result.rowcount != 1:
            self.db.rollback()
            self._raise_revision_conflict(project_id, task.id, payload.expected_revision)
        self._ensure_version_participant(version_id, assignee_id)
        self.db.commit()
        refreshed = self.db.get(Task, task.id)
        if refreshed is None:
            raise NotFoundError("任务不存在")
        return refreshed

    def delete(
        self,
        project_id: str,
        task_id: str,
        *,
        expected_revision: int,
        actor: UserAccount,
    ) -> None:
        self.projects.require_writable(project_id, actor=actor)
        task = self._get_in_project(project_id, task_id)
        result = self.db.execute(
            delete(Task).where(
                Task.id == task.id,
                Task.project_id == project_id,
                Task.revision == expected_revision,
            )
        )
        if result.rowcount != 1:
            self.db.rollback()
            self._raise_revision_conflict(project_id, task.id, expected_revision)
        self._bump_lane(project_id, task.assignee_id)
        self.db.commit()

    def get_lane_order(
        self,
        project_id: str,
        assignee_id: str,
        *,
        actor: UserAccount,
    ) -> TaskLaneOrderRead:
        self.projects.get_visible(project_id, actor=actor)
        self._validate_assignee(project_id, assignee_id)
        lane = self.db.get(TaskLane, (project_id, assignee_id))
        task_ids = list(
            self.db.scalars(
                select(Task.id)
                .where(Task.project_id == project_id, Task.assignee_id == assignee_id)
                .order_by(Task.sort_order, Task.created_time, Task.id)
            )
        )
        return TaskLaneOrderRead(
            assignee_id=assignee_id,
            ordered_task_ids=task_ids,
            lane_revision=lane.revision if lane else 1,
        )

    def reorder_lane(
        self,
        project_id: str,
        assignee_id: str,
        payload: TaskLaneOrderUpdate,
        *,
        actor: UserAccount,
    ) -> TaskLaneOrderRead:
        self.projects.require_writable(project_id, actor=actor)
        self._validate_assignee(project_id, assignee_id)
        lane = self._ensure_lane(project_id, assignee_id)
        if lane.revision != payload.expected_lane_revision:
            self._raise_lane_revision_conflict(
                project_id, assignee_id, payload.expected_lane_revision
            )

        current_ids = list(
            self.db.scalars(
                select(Task.id)
                .where(Task.project_id == project_id, Task.assignee_id == assignee_id)
                .order_by(Task.sort_order, Task.created_time, Task.id)
            )
        )
        if len(current_ids) != len(payload.ordered_task_ids) or set(current_ids) != set(
            payload.ordered_task_ids
        ):
            raise ConflictError(
                "必须提交该负责人完整且准确的任务顺序",
                code="TASK_LANE_ORDER_INVALID",
                details={
                    "assignee_id": assignee_id,
                    "expected_task_count": len(current_ids),
                    "submitted_task_count": len(payload.ordered_task_ids),
                },
            )

        revision_result = self.db.execute(
            update(TaskLane)
            .where(
                TaskLane.project_id == project_id,
                TaskLane.assignee_id == assignee_id,
                TaskLane.revision == payload.expected_lane_revision,
            )
            .values(revision=TaskLane.revision + 1, updated_time=utc_now())
        )
        if revision_result.rowcount != 1:
            self.db.rollback()
            self._raise_lane_revision_conflict(
                project_id, assignee_id, payload.expected_lane_revision
            )
        if payload.ordered_task_ids:
            order_values = {
                task_id: index
                for index, task_id in enumerate(payload.ordered_task_ids, start=1)
            }
            self.db.execute(
                update(Task)
                .where(Task.project_id == project_id, Task.assignee_id == assignee_id)
                .values(sort_order=case(order_values, value=Task.id))
            )
        self.db.commit()
        return TaskLaneOrderRead(
            assignee_id=assignee_id,
            ordered_task_ids=payload.ordered_task_ids,
            lane_revision=payload.expected_lane_revision + 1,
        )

    def _get_in_project(self, project_id: str, task_id: str) -> Task:
        task = self.db.scalar(
            select(Task).where(Task.id == task_id, Task.project_id == project_id)
        )
        if task is None:
            raise NotFoundError("任务不存在")
        return task

    def _validate_assignee(self, project_id: str, assignee_id: str) -> None:
        if self.db.get(ProjectMember, (project_id, assignee_id)) is None:
            raise ConflictError(
                "任务负责人必须是当前项目成员",
                code="TASK_ASSIGNEE_NOT_PROJECT_MEMBER",
                details={"assignee_id": assignee_id},
            )

    def _validate_version(self, project_id: str, version_id: str | None) -> None:
        if version_id is None:
            return
        bind = self.db.get_bind()
        if not inspect(bind).has_table("project_version"):
            raise NotFoundError("版本不存在")
        row = self.db.execute(
            text("SELECT project_id FROM project_version WHERE id = :version_id"),
            {"version_id": version_id},
        ).first()
        if row is None or row.project_id != project_id:
            raise NotFoundError("版本不存在")

    def _ensure_version_participant(
        self, version_id: str | None, assignee_id: str
    ) -> None:
        if version_id is None or not inspect(self.db.get_bind()).has_table(
            "version_participant"
        ):
            return
        self.db.execute(
            text(
                "INSERT OR IGNORE INTO version_participant "
                "(version_id, user_id, created_time) "
                "VALUES (:version_id, :user_id, :created_time)"
            ),
            {
                "version_id": version_id,
                "user_id": assignee_id,
                "created_time": utc_now(),
            },
        )

    @staticmethod
    def _validate_dates(start_date: date | None, due_date: date | None) -> None:
        if start_date and due_date and due_date < start_date:
            raise AppError(
                "预计完成日期不能早于开始日期",
                code="TASK_DATE_INVALID",
                status_code=422,
            )

    def _ensure_lane(self, project_id: str, assignee_id: str) -> TaskLane:
        lane = self.db.get(TaskLane, (project_id, assignee_id))
        if lane is None:
            lane = TaskLane(project_id=project_id, assignee_id=assignee_id)
            self.db.add(lane)
            self.db.flush()
        return lane

    def _bump_lane(self, project_id: str, assignee_id: str) -> None:
        lane = self.db.get(TaskLane, (project_id, assignee_id))
        if lane is None:
            self.db.add(
                TaskLane(
                    project_id=project_id,
                    assignee_id=assignee_id,
                    revision=2,
                    updated_time=utc_now(),
                )
            )
            self.db.flush()
            return
        lane.revision += 1
        lane.updated_time = utc_now()
        self.db.flush()

    def _next_sort_order(self, project_id: str, assignee_id: str) -> int:
        current_max = self.db.scalar(
            select(func.max(Task.sort_order)).where(
                Task.project_id == project_id, Task.assignee_id == assignee_id
            )
        )
        return (current_max or 0) + 1

    def _validate_lane_capacity(self, project_id: str, assignee_id: str) -> None:
        current_count = self.db.scalar(
            select(func.count())
            .select_from(Task)
            .where(Task.project_id == project_id, Task.assignee_id == assignee_id)
        ) or 0
        if current_count >= TASKS_PER_ASSIGNEE_LIMIT:
            self.db.rollback()
            raise ConflictError(
                "该成员在当前项目中的任务已达到 200 条上限",
                code="TASK_ASSIGNEE_LIMIT_REACHED",
                details={
                    "assignee_id": assignee_id,
                    "current_task_count": current_count,
                    "task_limit": TASKS_PER_ASSIGNEE_LIMIT,
                },
            )

    def _raise_revision_conflict(
        self, project_id: str, task_id: str, expected_revision: int
    ) -> None:
        current_revision = self.db.scalar(
            select(Task.revision).where(Task.id == task_id, Task.project_id == project_id)
        )
        raise ConflictError(
            "任务已被其他人修改，请刷新后重试",
            code="TASK_REVISION_CONFLICT",
            details={
                "task_id": task_id,
                "expected_revision": expected_revision,
                "current_revision": current_revision,
            },
        )

    def _raise_lane_revision_conflict(
        self, project_id: str, assignee_id: str, expected_revision: int
    ) -> None:
        current_revision = self.db.scalar(
            select(TaskLane.revision).where(
                TaskLane.project_id == project_id,
                TaskLane.assignee_id == assignee_id,
            )
        )
        raise ConflictError(
            "任务顺序已被其他人修改，请刷新后重试",
            code="LANE_REVISION_CONFLICT",
            details={
                "assignee_id": assignee_id,
                "expected_lane_revision": expected_revision,
                "current_lane_revision": current_revision,
            },
        )
