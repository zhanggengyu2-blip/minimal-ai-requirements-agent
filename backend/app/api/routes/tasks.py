from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.task import (
    TaskCreate,
    TaskLaneOrderRead,
    TaskLaneOrderUpdate,
    TaskList,
    TaskRead,
    TaskStatusFilter,
    TaskUpdate,
)
from app.services.task_service import TaskService


router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/{project_id}/tasks", response_model=ApiResponse[TaskList])
def list_tasks(
    project_id: str,
    request: Request,
    db: DbSession,
    keyword: Annotated[str | None, Query(max_length=100)] = None,
    task_status: Annotated[TaskStatusFilter, Query(alias="status")] = TaskStatusFilter.ALL,
    version_id: Annotated[str | None, Query(min_length=32, max_length=32)] = None,
) -> ApiResponse[TaskList]:
    tasks = TaskService(db).list(
        project_id,
        actor=request.state.current_user,
        keyword=keyword.strip() if keyword else None,
        status_filter=task_status,
        version_id=version_id,
    )
    return ApiResponse(data=tasks, request_id=request.state.request_id)


@router.post(
    "/{project_id}/tasks",
    response_model=ApiResponse[TaskRead],
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    project_id: str,
    payload: TaskCreate,
    request: Request,
    db: DbSession,
) -> ApiResponse[TaskRead]:
    task = TaskService(db).create(
        project_id, payload, actor=request.state.current_user
    )
    return ApiResponse(
        message="任务已创建",
        data=TaskRead.model_validate(task),
        request_id=request.state.request_id,
    )


@router.get("/{project_id}/tasks/{task_id}", response_model=ApiResponse[TaskRead])
def get_task(
    project_id: str, task_id: str, request: Request, db: DbSession
) -> ApiResponse[TaskRead]:
    task = TaskService(db).get(project_id, task_id, actor=request.state.current_user)
    return ApiResponse(data=TaskRead.model_validate(task), request_id=request.state.request_id)


@router.patch("/{project_id}/tasks/{task_id}", response_model=ApiResponse[TaskRead])
def update_task(
    project_id: str,
    task_id: str,
    payload: TaskUpdate,
    request: Request,
    db: DbSession,
) -> ApiResponse[TaskRead]:
    task = TaskService(db).update(
        project_id, task_id, payload, actor=request.state.current_user
    )
    return ApiResponse(
        message="任务已更新",
        data=TaskRead.model_validate(task),
        request_id=request.state.request_id,
    )


@router.delete("/{project_id}/tasks/{task_id}", response_model=ApiResponse[None])
def delete_task(
    project_id: str,
    task_id: str,
    request: Request,
    db: DbSession,
    expected_revision: Annotated[int, Query(ge=1)],
) -> ApiResponse[None]:
    TaskService(db).delete(
        project_id,
        task_id,
        expected_revision=expected_revision,
        actor=request.state.current_user,
    )
    return ApiResponse(message="任务已永久删除", data=None, request_id=request.state.request_id)


@router.get(
    "/{project_id}/task-lanes/{assignee_id}/order",
    response_model=ApiResponse[TaskLaneOrderRead],
)
def get_task_lane_order(
    project_id: str,
    assignee_id: str,
    request: Request,
    db: DbSession,
) -> ApiResponse[TaskLaneOrderRead]:
    order = TaskService(db).get_lane_order(
        project_id, assignee_id, actor=request.state.current_user
    )
    return ApiResponse(data=order, request_id=request.state.request_id)


@router.put(
    "/{project_id}/task-lanes/{assignee_id}/order",
    response_model=ApiResponse[TaskLaneOrderRead],
)
def reorder_task_lane(
    project_id: str,
    assignee_id: str,
    payload: TaskLaneOrderUpdate,
    request: Request,
    db: DbSession,
) -> ApiResponse[TaskLaneOrderRead]:
    order = TaskService(db).reorder_lane(
        project_id,
        assignee_id,
        payload,
        actor=request.state.current_user,
    )
    return ApiResponse(message="任务顺序已更新", data=order, request_id=request.state.request_id)
