from __future__ import annotations

from sqlalchemy import case, delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.db.models import (
    Department,
    ProjectMember,
    ProjectVersion,
    Task,
    TaskStatus,
    UserAccount,
    VersionParticipant,
    utc_now,
)
from app.schemas.version import (
    VersionCompletionImpact,
    VersionCreate,
    VersionDeleteResult,
    VersionList,
    VersionParticipantRead,
    VersionRead,
    VersionSummaryRead,
    VersionUpdate,
)
from app.services.project_service import ProjectService


UNFINISHED_TASK_STATUSES = (TaskStatus.NOT_STARTED, TaskStatus.IN_PROGRESS)


class VersionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.projects = ProjectService(db)

    def list(self, project_id: str, *, actor: UserAccount) -> VersionList:
        self.projects.get_visible(project_id, actor=actor)
        versions = list(
            self.db.scalars(
                select(ProjectVersion)
                .where(ProjectVersion.project_id == project_id)
                .order_by(ProjectVersion.created_time.desc(), ProjectVersion.id.desc())
            )
        )
        task_counts = self._version_task_counts(project_id)
        return VersionList(
            items=[self._to_summary(version, task_counts) for version in versions],
            total=len(versions),
        )

    def create(
        self,
        project_id: str,
        payload: VersionCreate,
        *,
        actor: UserAccount,
    ) -> VersionRead:
        self.projects.require_writable(project_id, actor=actor)
        self._validate_participants(project_id, payload.participant_ids)
        version = ProjectVersion(
            project_id=project_id,
            name=payload.name,
            start_date=payload.start_date,
            end_date=payload.end_date,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.db.add(version)
        try:
            self.db.flush()
            self.db.add_all(
                VersionParticipant(version_id=version.id, user_id=user_id)
                for user_id in payload.participant_ids
            )
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError(
                "同一项目中版本名称不能重复",
                code="VERSION_NAME_ALREADY_EXISTS",
            ) from exc
        return self.get(project_id, version.id, actor=actor)

    def get(
        self,
        project_id: str,
        version_id: str,
        *,
        actor: UserAccount,
    ) -> VersionRead:
        self.projects.get_visible(project_id, actor=actor)
        version = self._get_in_project(project_id, version_id)
        summary = self._to_summary(version, self._version_task_counts(project_id))
        task_counts = dict(
            self.db.execute(
                select(Task.assignee_id, func.count(Task.id))
                .where(Task.version_id == version.id)
                .group_by(Task.assignee_id)
            ).all()
        )
        rows = self.db.execute(
            select(VersionParticipant, ProjectMember, UserAccount, Department)
            .select_from(VersionParticipant)
            .join(
                ProjectVersion,
                ProjectVersion.id == VersionParticipant.version_id,
            )
            .join(
                ProjectMember,
                (ProjectMember.user_id == VersionParticipant.user_id)
                & (ProjectMember.project_id == ProjectVersion.project_id),
            )
            .join(UserAccount, UserAccount.id == VersionParticipant.user_id)
            .join(Department, Department.id == UserAccount.department_id)
            .where(VersionParticipant.version_id == version.id)
            .order_by(ProjectMember.sort_order, UserAccount.id)
        ).all()
        return VersionRead(
            **summary.model_dump(),
            participants=[
                VersionParticipantRead(
                    user_id=user.id,
                    name=user.name,
                    department_id=department.id,
                    department_name=department.name,
                    role=user.role,
                    sort_order=membership.sort_order,
                    task_count=task_counts.get(user.id, 0),
                    created_time=participant.created_time,
                )
                for participant, membership, user, department in rows
            ],
        )

    def update(
        self,
        project_id: str,
        version_id: str,
        payload: VersionUpdate,
        *,
        actor: UserAccount,
    ) -> VersionRead:
        self.projects.require_writable(project_id, actor=actor)
        version = self._get_in_project(project_id, version_id)
        changes = payload.model_dump(
            exclude_unset=True,
            exclude={"expected_revision", "participant_ids"},
        )
        start_date = changes.get("start_date", version.start_date)
        end_date = changes.get("end_date", version.end_date)
        if end_date < start_date:
            raise ConflictError(
                "版本结束日期不能早于开始日期",
                code="VERSION_DATE_ORDER_INVALID",
            )

        participant_ids = payload.participant_ids if "participant_ids" in payload.model_fields_set else None
        current_participant_ids = set(
            self.db.scalars(
                select(VersionParticipant.user_id).where(
                    VersionParticipant.version_id == version.id
                )
            )
        )
        if participant_ids is not None:
            self._validate_participants(project_id, participant_ids)
            removed_ids = current_participant_ids - set(participant_ids)
            self._validate_participant_removal(version.id, removed_ids)

        result = self.db.execute(
            update(ProjectVersion)
            .where(
                ProjectVersion.id == version.id,
                ProjectVersion.project_id == project_id,
                ProjectVersion.revision == payload.expected_revision,
            )
            .values(
                **changes,
                revision=ProjectVersion.revision + 1,
                updated_by=actor.id,
                updated_time=utc_now(),
            )
        )
        if result.rowcount != 1:
            self.db.rollback()
            self._raise_revision_conflict(project_id, version.id, payload.expected_revision)

        if participant_ids is not None:
            requested_ids = set(participant_ids)
            removed_ids = current_participant_ids - requested_ids
            added_ids = requested_ids - current_participant_ids
            if removed_ids:
                self.db.execute(
                    delete(VersionParticipant).where(
                        VersionParticipant.version_id == version.id,
                        VersionParticipant.user_id.in_(removed_ids),
                    )
                )
            self.db.add_all(
                VersionParticipant(version_id=version.id, user_id=user_id)
                for user_id in added_ids
            )
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError(
                "同一项目中版本名称不能重复",
                code="VERSION_NAME_ALREADY_EXISTS",
            ) from exc
        return self.get(project_id, version.id, actor=actor)

    def completion_impact(
        self,
        project_id: str,
        version_id: str,
        *,
        actor: UserAccount,
    ) -> VersionCompletionImpact:
        self.projects.get_visible(project_id, actor=actor)
        version = self._get_in_project(project_id, version_id)
        task_count, unfinished_task_count = self._task_impact(version.id)
        return VersionCompletionImpact(
            version_id=version.id,
            task_count=task_count,
            unfinished_task_count=unfinished_task_count,
        )

    def delete(
        self,
        project_id: str,
        version_id: str,
        *,
        expected_revision: int,
        actor: UserAccount,
    ) -> VersionDeleteResult:
        self.projects.require_writable(project_id, actor=actor)
        version = self._get_in_project(project_id, version_id)
        result = self.db.execute(
            delete(ProjectVersion).where(
                ProjectVersion.id == version.id,
                ProjectVersion.project_id == project_id,
                ProjectVersion.revision == expected_revision,
            )
        )
        if result.rowcount != 1:
            self.db.rollback()
            self._raise_revision_conflict(project_id, version.id, expected_revision)
        unlinked = self.db.execute(
            update(Task)
            .where(Task.project_id == project_id, Task.version_id == version.id)
            .values(
                version_id=None,
                revision=Task.revision + 1,
                updated_by=actor.id,
                updated_time=utc_now(),
            )
        ).rowcount
        next_version_id = self.db.scalar(
            select(ProjectVersion.id)
            .where(ProjectVersion.project_id == project_id)
            .order_by(ProjectVersion.created_time.desc(), ProjectVersion.id.desc())
            .limit(1)
        )
        self.db.commit()
        return VersionDeleteResult(
            unlinked_task_count=unlinked or 0,
            next_version_id=next_version_id,
        )

    def _get_in_project(self, project_id: str, version_id: str) -> ProjectVersion:
        version = self.db.scalar(
            select(ProjectVersion).where(
                ProjectVersion.id == version_id,
                ProjectVersion.project_id == project_id,
            )
        )
        if version is None:
            raise NotFoundError("版本不存在")
        return version

    def _validate_participants(self, project_id: str, participant_ids: list[str]) -> None:
        requested_ids = set(participant_ids)
        found_ids = set(
            self.db.scalars(
                select(ProjectMember.user_id).where(
                    ProjectMember.project_id == project_id,
                    ProjectMember.user_id.in_(requested_ids),
                )
            )
        )
        if found_ids != requested_ids:
            raise ConflictError(
                "版本参与人员必须是当前项目成员",
                code="VERSION_PARTICIPANT_NOT_PROJECT_MEMBER",
                details={"invalid_user_ids": sorted(requested_ids - found_ids)},
            )

    def _validate_participant_removal(self, version_id: str, removed_ids: set[str]) -> None:
        if not removed_ids:
            return
        task_counts = dict(
            self.db.execute(
                select(Task.assignee_id, func.count(Task.id))
                .where(
                    Task.version_id == version_id,
                    Task.assignee_id.in_(removed_ids),
                )
                .group_by(Task.assignee_id)
            ).all()
        )
        if task_counts:
            raise ConflictError(
                "仍负责当前版本任务的参与人员不能移除",
                code="VERSION_PARTICIPANT_HAS_TASKS",
                details={"task_counts": task_counts},
            )

    def _version_task_counts(self, project_id: str) -> dict[str, tuple[int, int]]:
        rows = self.db.execute(
            select(
                Task.version_id,
                func.count(Task.id),
                func.sum(case((Task.status.in_(UNFINISHED_TASK_STATUSES), 1), else_=0)),
            )
            .where(Task.project_id == project_id, Task.version_id.is_not(None))
            .group_by(Task.version_id)
        ).all()
        return {
            version_id: (task_count, unfinished_task_count or 0)
            for version_id, task_count, unfinished_task_count in rows
        }

    def _task_impact(self, version_id: str) -> tuple[int, int]:
        row = self.db.execute(
            select(
                func.count(Task.id),
                func.sum(case((Task.status.in_(UNFINISHED_TASK_STATUSES), 1), else_=0)),
            ).where(Task.version_id == version_id)
        ).one()
        return row[0] or 0, row[1] or 0

    def _to_summary(
        self,
        version: ProjectVersion,
        task_counts: dict[str, tuple[int, int]],
    ) -> VersionSummaryRead:
        task_count, unfinished_task_count = task_counts.get(version.id, (0, 0))
        item = VersionSummaryRead.model_validate(version)
        item.task_count = task_count
        item.unfinished_task_count = unfinished_task_count
        return item

    def _raise_revision_conflict(
        self,
        project_id: str,
        version_id: str,
        expected_revision: int,
    ) -> None:
        current_revision = self.db.scalar(
            select(ProjectVersion.revision).where(
                ProjectVersion.id == version_id,
                ProjectVersion.project_id == project_id,
            )
        )
        raise ConflictError(
            "版本已被其他人修改，请刷新后重试",
            code="VERSION_REVISION_CONFLICT",
            details={
                "version_id": version_id,
                "expected_revision": expected_revision,
                "current_revision": current_revision,
            },
        )
