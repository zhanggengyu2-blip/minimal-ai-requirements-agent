from sqlalchemy import select
from app.core.exceptions import NotFoundError
from app.db.models import TaskComment, UserAccount
from app.schemas.task_comment import TaskCommentCreate, TaskCommentRead
from app.services.task_service import TaskService

class TaskCommentService:
    def __init__(self, db):
        self.db = db
        self.tasks = TaskService(db)

    def _read(self, row):
        author = self.db.get(UserAccount, row.author_id)
        return TaskCommentRead(**{c.name: getattr(row, c.name) for c in row.__table__.columns},
            author_name="Coo · AI 同事" if row.actor_type == "COO" else author.name)

    def list(self, project_id, task_id, *, actor, limit=100, before=None):
        self.tasks.get(project_id, task_id, actor=actor)
        query = select(TaskComment).where(TaskComment.task_id == task_id, TaskComment.project_id == project_id)
        if before:
            anchor = self.db.get(TaskComment, before)
            if not anchor or anchor.task_id != task_id:
                raise NotFoundError("留言不存在")
            from sqlalchemy import or_, and_
            query = query.where(or_(TaskComment.created_time < anchor.created_time,
                and_(TaskComment.created_time == anchor.created_time, TaskComment.id < anchor.id)))
        rows = list(self.db.scalars(query.order_by(TaskComment.created_time.desc(), TaskComment.id.desc()).limit(limit)))
        return [self._read(row) for row in reversed(rows)]

    def create(self, project_id, task_id, payload: TaskCommentCreate, *, actor, agent_run_id=None, commit=True):
        self.tasks.projects.require_writable(project_id, actor=actor)
        self.tasks.get(project_id, task_id, actor=actor)
        if payload.parent_id:
            parent = self.db.get(TaskComment, payload.parent_id)
            if not parent or parent.task_id != task_id or parent.project_id != project_id:
                raise NotFoundError("回复目标不属于当前任务")
        row = TaskComment(project_id=project_id, task_id=task_id, author_id=actor.id,
            actor_type="COO" if agent_run_id else "HUMAN", agent_run_id=agent_run_id, **payload.model_dump())
        self.db.add(row)
        self.db.flush()
        if not agent_run_id:
            from app.coo.events import enqueue
            enqueue(self.db, key=f'task.comment:{row.id}', event_type='TASK_COMMENT_CREATED', project_id=project_id,
                actor_id=actor.id, payload={'task_id':task_id,'comment_id':row.id})
        if commit:
            self.db.commit()
        else:
            self.db.flush()
        self.db.refresh(row)
        return self._read(row)
