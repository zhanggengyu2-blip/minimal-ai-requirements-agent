# 极简 AI 团队需求管理智能体后端 V2.0

FastAPI + SQLite 的后端实现。V2.0 新增对话式需求访谈，并继续兼容 V1.1 项目、需求、部门和邀请码管理能力。业务数据只写入本地 SQLite，Dify Workflow 只负责 AI 推理。

## 目录结构

```text
app/
├── api/routes/              # 路由层
├── core/                   # 配置、业务异常
├── db/                     # SQLAlchemy 连接与数据库模型层
├── schemas/                # Pydantic 请求、响应、Dify 输出校验
├── services/               # 项目、需求、Dify 业务服务层
└── main.py                 # FastAPI 入口与统一异常处理
tests/                      # 核心流程测试
```

## 启动

以下命令均在 `backend/v2.0` 目录执行：

```bash
cd backend/v2.0
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env
python -m alembic upgrade head
python -m app.db.seed
python scripts/bootstrap_admin.py --department 产品部 --name 管理员姓名
python -m uvicorn app.main:app --reload
```

启动后访问：

- Swagger：<http://127.0.0.1:8000/docs>
- 健康检查：<http://127.0.0.1:8000/api/v1/health>

数据库结构由 Alembic 管理，应用启动不会自动建表或修改表结构。首次启动及每次拉取包含迁移的代码后，应先执行 `python -m alembic upgrade head`。默认部门通过独立的幂等命令 `python -m app.db.seed` 初始化，可安全重复执行。

`.env`、默认数据库和访谈图片目录均以 `backend/v2.0` 为固定基准，不依赖启动命令的当前目录。

## 数据库迁移

以下命令均在 `backend/v2.0` 目录执行：

```bash
# 升级到最新结构
python -m alembic upgrade head

# 查看当前版本
python -m alembic current

# 检查 ORM 模型是否存在未生成的结构变化
python -m alembic check

# 初始化默认部门；重复执行不会重复插入
python -m app.db.seed
```

创建后续迁移时使用 `python -m alembic revision --autogenerate -m "变更说明"`，并在提交前人工审查升级和降级内容。不要在应用启动代码中恢复 `create_all()` 或手写 `ALTER TABLE`。

## 身份与管理员初始化

首次运行前必须在 `.env` 配置：

```dotenv
SHARED_PASSWORD=公司统一密码
AUTH_HMAC_KEY=至少32位随机字符串
INVITATION_ENCRYPTION_KEY=另一条至少32位随机字符串
SESSION_COOKIE_SECURE=false
```

- `SHARED_PASSWORD` 只用于注册后的统一登录，不写入数据库；
- `AUTH_HMAC_KEY` 用于邀请码和会话令牌摘要；
- `INVITATION_ENCRYPTION_KEY` 用于管理员列表中的邀请码解密展示；
- 正式 HTTPS 环境必须将 `SESSION_COOKIE_SECURE` 改为 `true`；
- 三个密钥或密码不得提交到 Git，也不得写入日志、URL 或前端持久化存储。

数据库迁移和默认部门 seed 完成后，执行一次：

```bash
python scripts/bootstrap_admin.py --department 产品部 --name 管理员姓名
```

该命令只允许在系统不存在管理员时执行。管理员随后使用“部门＋姓名＋公司统一密码”登录，并通过管理接口生成普通成员首次注册邀请码。

身份接口：

| 方法 | 地址 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/auth/departments` | 公开的登录部门选项 |
| POST | `/api/v1/auth/registrations` | 部门、姓名、邀请码首次注册 |
| POST | `/api/v1/auth/sessions` | 部门、姓名、统一密码登录 |
| GET | `/api/v1/auth/me` | 当前用户和 CSRF 令牌 |
| DELETE | `/api/v1/auth/session` | 撤销当前会话并退出 |

登录 Cookie 使用 `HttpOnly` 和 `SameSite=Lax`。除登录、注册和健康检查外，所有业务接口都要求登录；所有写请求还必须使用 `X-CSRF-Token` 请求头携带 `/auth/me` 返回的 CSRF 令牌。

## 项目成员与可见性

- 创建项目时，当前用户自动成为首位项目成员；
- 普通成员只能查看自己加入的项目，直接访问其他项目及其需求、访谈会返回 `404`；
- 管理员可以查看全部项目并协助维护成员，但修改项目业务数据前也必须加入项目；
- 项目成员使用完整用户 ID 集合保存成员，至少保留一名成员；
- 任意项目成员可以归档或重新打开项目，归档项目除重新打开外均为只读；
- 项目基础信息和成员集合分别使用 `revision`、`member_revision` 防止并发覆盖。

项目与成员接口：

| 方法 | 地址 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/projects` | 普通成员查询本人项目，管理员查询全部项目 |
| POST | `/api/v1/projects` | 创建项目并自动加入创建者 |
| GET | `/api/v1/projects/{project_id}` | 查询可见项目详情 |
| PATCH | `/api/v1/projects/{project_id}` | 编辑、归档或重新打开项目 |
| GET | `/api/v1/projects/{project_id}/members` | 查询项目成员及成员修订号 |
| PUT | `/api/v1/projects/{project_id}/members` | 使用完整用户 ID 集合保存成员 |

## 团队任务与泳道

- 任务名称、负责人、状态和优先级必填；默认状态为 `NOT_STARTED`，默认优先级为 `P1`；
- 负责人必须是当前项目成员，新建任务和更换负责人后均放到对应泳道底部；
- 状态支持全部、未完成及四种具体状态筛选，搜索只匹配任务名称；
- 单次最多返回 1000 条，响应使用 `total` 和 `truncated` 明确是否被截断；
- 任务基础字段使用 `revision` 防止并发覆盖，完整泳道排序使用独立 `lane_revision`；
- 排序请求必须提交负责人泳道中的完整任务 ID 集合；
- 归档项目允许读取和筛选任务，但拒绝创建、编辑、删除及排序；
- 删除任务为永久删除，不提供回收站或恢复记录。

任务接口：

| 方法 | 地址 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/projects/{project_id}/tasks` | 搜索、筛选并查询任务和泳道修订号 |
| POST | `/api/v1/projects/{project_id}/tasks` | 创建任务 |
| GET | `/api/v1/projects/{project_id}/tasks/{task_id}` | 查询任务详情 |
| PATCH | `/api/v1/projects/{project_id}/tasks/{task_id}` | 使用任务修订号更新任务 |
| DELETE | `/api/v1/projects/{project_id}/tasks/{task_id}` | 使用任务修订号永久删除任务 |
| GET | `/api/v1/projects/{project_id}/task-lanes/{assignee_id}/order` | 查询完整泳道顺序 |
| PUT | `/api/v1/projects/{project_id}/task-lanes/{assignee_id}/order` | 使用泳道修订号保存完整顺序 |

`version_id` 已进入任务模型和接口，但项目版本表属于 T6。在 T6 完成前仅支持 `null`，传入非空版本 ID 会返回“版本不存在”。

## Dify 配置

将本地 Dify Workflow 的 API 基础地址和密钥写入 `.env`：

```dotenv
DIFY_BASE_URL=http://127.0.0.1/v1
DIFY_API_KEY=app-xxxxxxxx
DIFY_TIMEOUT_SECONDS=8
```

后端调用 `POST {DIFY_BASE_URL}/workflows/run`，采用 `blocking` 模式，输入为：

```json
{
  "project_name": "项目名称",
  "project_context": "项目上下文",
  "raw_content": "用户原始需求",
  "candidate_requirements": "[{\"id\":\"...\",\"standard_content\":\"...\"}]"
}
```

`candidate_requirements` 按 Dify 设计文档传 JSON 数组字符串，且只包含当前项目最近的已分析需求。Dify 的 `data.outputs` 必须返回固定 10 字段；后端会再次执行严格类型、枚举、未知字段和关联 ID 校验。

## API

所有成功响应统一为：

```json
{
  "code": "OK",
  "message": "success",
  "data": {},
  "request_id": "..."
}
```

所有异常同样返回 `code/message/data/request_id`，并按需增加 `details`。

| 方法 | 地址 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/projects` | 创建项目（支撑新建需求的最小必要接口） |
| GET | `/api/v1/projects` | 分页查询项目列表与需求数量 |
| POST | `/api/v1/requirements` | 保存原始需求并同步触发 AI 分析 |
| GET | `/api/v1/requirements` | 分页、搜索及组合筛选需求 |
| GET | `/api/v1/requirements/{id}` | 获取需求详情 |
| POST | `/api/v1/requirements/batch-analyze` | 批量 AI 分析预留接口，最多 50 条 |

创建项目：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/projects \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "极简AI团队需求管理智能体",
    "description": "AI 原生需求管理 MVP",
    "project_context": "面向小型研发团队，收集、分析并管理需求；当前处于 MVP 阶段。"
  }'
```

创建需求：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/requirements \
  -H 'Content-Type: application/json' \
  -d '{"project_id":"替换为32位项目ID","raw_content":"希望支持批量导入客户需求"}'
```

Dify 超时、不可连接、鉴权失败或输出非法时，接口仍返回已保存的需求，`code` 为 `AI_ANALYSIS_FAILED`，记录状态为 `FAILED`，不会用非法结果覆盖 AI 字段。

## 测试

```bash
python -m pytest -q
```
