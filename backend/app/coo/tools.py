"""Typed registry: models select calls; services own business rules and authority."""
from dataclasses import dataclass
from pydantic import Field
from app.core.exceptions import AppError
from app.schemas.task import TaskCreate, TaskStatusFilter
from app.schemas.task_comment import TaskCommentCreate
from app.schemas.requirement import RequirementRead
from app.schemas.project import ProjectRead
from app.schemas.task import TaskRead
from app.services.project_service import ProjectService
from app.services.requirement_service import RequirementService
from app.services.task_service import TaskService
from app.services.task_comment_service import TaskCommentService
from app.knowledge.schemas import SearchInput
from app.knowledge.retrieval import search
from .schemas import Input

class Empty(Input): pass
class ProjectArgs(Input): project_id: str=Field(min_length=32,max_length=32)
class RequirementListArgs(ProjectArgs): keyword: str|None=Field(default=None,max_length=100)
class RequirementArgs(Input): requirement_id: str=Field(min_length=32,max_length=32)
class TaskListArgs(ProjectArgs): keyword: str|None=Field(default=None,max_length=100)
class TaskArgs(ProjectArgs): task_id: str=Field(min_length=32,max_length=32)
class CommentArgs(TaskArgs):
    content: str=Field(min_length=1,max_length=4000)
    parent_id: str|None=Field(default=None,min_length=32,max_length=32)
class CreateTaskArgs(ProjectArgs):
    name: str=Field(min_length=1,max_length=200)
    assignee_id: str=Field(min_length=32,max_length=32)
    description: str=Field(default='',max_length=500)
    priority: str=Field(default='P1',pattern='^P[0-3]$')

@dataclass(frozen=True)
class Tool:
    schema: type[Input]
    description: str
    risk: str='READ'

REGISTRY={
 'list_projects':Tool(Empty,'查询当前员工可访问的项目，最多30个。'),
 'get_project_context':Tool(ProjectArgs,'查询项目业务上下文和真实成员，创建任务前用此获取负责人ID。'),
 'list_requirements':Tool(RequirementListArgs,'查询一个项目最近20条需求，可按关键词筛选。'),
 'get_requirement':Tool(RequirementArgs,'查询有权限访问的需求原文和分析结果。'),
 'analyze_requirement':Tool(RequirementArgs,'运行确定性十字段需求分析工作流。需要确认，因为会写入分析结果。','CONFIRM'),
 'list_tasks':Tool(TaskListArgs,'查询项目任务，返回最近最多30条；需要更多信息时缩小关键词。'),
 'get_task':Tool(TaskArgs,'查询任务详情。'),
 'list_task_comments':Tool(TaskArgs,'查询任务最近100条留言。'),
 'create_task_comment':Tool(CommentArgs,'以明确的 Coo AI 身份留言；仅员工本轮勾选授权后可自动执行，否则需确认。','COMMENT'),
 'create_task':Tool(CreateTaskArgs,'提出创建任务建议；永远需要人工确认，不会立即创建。','CONFIRM'),
 'search_knowledge':Tool(SearchInput,'检索当前可访问企业知识和指定项目有效知识，返回可引用片段。'),
}

def definitions():
    return [{'type':'function','function':{'name':name,'description':tool.description,'parameters':tool.schema.model_json_schema()}} for name,tool in REGISTRY.items()]

class BusinessTools:
    def __init__(self, db, actor): self.db,self.actor=db,actor

    def project_for(self,name,args):
        if 'project_id' in args and args['project_id']:
            ProjectService(self.db).get_visible(args['project_id'],actor=self.actor)
            return args['project_id']
        if 'requirement_id' in args:
            return RequirementService(self.db).get_visible(args['requirement_id'],actor=self.actor).project_id
        return None

    async def execute(self,name,args,*,run_id=None,commit=True):
        db,actor=self.db,self.actor
        if name=='list_projects':
            items,total=ProjectService(db).list(actor=actor,page=1,page_size=30,status=None)
            return {'items':[v.model_dump(mode='json') for v in items],'total':total}
        if name=='get_project_context':
            service=ProjectService(db)
            return {'project':service.get(args['project_id'],actor=actor).model_dump(mode='json'),
                    'members':service.list_members(args['project_id'],actor=actor).model_dump(mode='json')}
        if name=='list_requirements':
            items,total=RequirementService(db).list(project_id=args['project_id'],keyword=args.get('keyword'),page=1,page_size=20,
                priority=None,requirement_type=None,analysis_status=None,is_fake=None,actor=actor)
            return {'items':[RequirementRead.model_validate(v).model_dump(mode='json') for v in items],'total':total}
        if name in ('get_requirement','analyze_requirement'):
            service=RequirementService(db);row=service.get_visible(args['requirement_id'],actor=actor)
            if name=='analyze_requirement':
                ProjectService(db).require_writable(row.project_id,actor=actor)
                row=await service.analyze_existing(row,user=actor.id)
            return RequirementRead.model_validate(row).model_dump(mode='json')
        if name=='list_tasks':
            result=TaskService(db).list(args['project_id'],actor=actor,keyword=args.get('keyword'),status_filter=TaskStatusFilter.ALL,version_id=None)
            return {'items':[v.model_dump(mode='json') for v in result.items[:30]],'total':result.total}
        if name=='get_task': return TaskRead.model_validate(TaskService(db).get(args['project_id'],args['task_id'],actor=actor)).model_dump(mode='json')
        if name=='list_task_comments': return {'items':[v.model_dump(mode='json') for v in TaskCommentService(db).list(args['project_id'],args['task_id'],actor=actor)]}
        if name=='create_task_comment':
            body=TaskCommentCreate.model_validate({k:v for k,v in args.items() if k in ('content','parent_id')})
            return TaskCommentService(db).create(args['project_id'],args['task_id'],body,actor=actor,agent_run_id=run_id,commit=commit).model_dump(mode='json')
        if name=='create_task':
            body=TaskCreate.model_validate({k:v for k,v in args.items() if k!='project_id'})
            row=TaskService(db).create(args['project_id'],body,actor=actor,commit=commit)
            return TaskRead.model_validate(row).model_dump(mode='json')
        if name=='search_knowledge': return search(db,actor,SearchInput.model_validate(args))
        raise AppError('未知工具',code='UNKNOWN_TOOL',status_code=422)
