from fastapi import APIRouter, Query
from app.api.deps import DbSession, AuthenticatedUser
from app.schemas.common import ApiResponse
from app.schemas.task_comment import TaskCommentCreate, TaskCommentRead
from app.services.task_comment_service import TaskCommentService
router = APIRouter()

@router.get("/{project_id}/tasks/{task_id}/comments", response_model=ApiResponse[list[TaskCommentRead]])
def list_comments(project_id: str, task_id: str, db: DbSession, actor: AuthenticatedUser,
                  limit: int = Query(100, ge=1, le=100), before: str | None = None):
    return ApiResponse(data=TaskCommentService(db).list(project_id, task_id, actor=actor, limit=limit, before=before))

@router.post("/{project_id}/tasks/{task_id}/comments", response_model=ApiResponse[TaskCommentRead], status_code=201)
def create_comment(project_id: str, task_id: str, payload: TaskCommentCreate, db: DbSession, actor: AuthenticatedUser):
    return ApiResponse(data=TaskCommentService(db).create(project_id, task_id, payload, actor=actor))
