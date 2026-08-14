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
python -m uvicorn app.main:app --reload
```

启动后访问：

- Swagger：<http://127.0.0.1:8000/docs>
- 健康检查：<http://127.0.0.1:8000/api/v1/health>

首次启动会自动创建 `backend/v2.0/data/requirements.db` 和数据表。`.env`、默认数据库和访谈图片目录均以 `backend/v2.0` 为固定基准，不依赖启动命令的当前目录。实际部署建议下一阶段接入 Alembic 管理迁移。

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
