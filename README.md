# 极简 AI 团队需求管理智能体

当前下一版本暂定为 **V4.0：留言 + 项目知识库 + LangGraph 技术迁移**，优先推进已有知识库的迁移复用。版本讨论请先查看[当前版本计划](product/当前版本计划.md)（更新于 2026-10-19）；V3.0 团队任务与版本排期属于已有版本范围。

前后端使用稳定的职能目录持续迭代，产品、设计和技术文档保留各版本基线。当前代码包含需求分析、访谈后端，以及 V3.0 身份、项目成员、团队任务、版本排期和甘特图；访谈工作台仍为界面原型。

## 目录导航

```text
frontend/
├── src/                   # Vue 3 页面、组件、路由与接口
└── e2e/                   # 前后端闭环验收
backend/
├── app/                   # FastAPI 后端
├── migrations/            # Alembic 数据库迁移
├── tests/                 # 后端测试
├── docs/                  # 运行、接口与代码说明
└── data/                  # 本地数据库与附件，不纳入 Git
product/v3.0/              # V3.0 产品基线
design/v3.0/               # V3.0 设计基线
technical/v3.0/            # V3.0 技术基线
dify-rag/                  # 通用需求分析规则与输出契约
```

早期 PRD、Dify 设计文档与业务流程保留在仓库根目录。

## 启动后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env
python -m alembic upgrade head
python -m app.db.seed
python scripts/bootstrap_admin.py --department 产品部 --name 管理员姓名
python -m uvicorn app.main:app --reload
```

`.env` 已随项目移动到 `backend/`。Python 虚拟环境在移动目录后建议重新创建，避免入口脚本保留旧的绝对路径。

默认 SQLite 数据库和访谈图片目录也固定在 `backend/data/` 下，不会因为从其他目录调用后端而改变。若确实需要从仓库根目录启动，可使用：

```bash
python -m uvicorn app.main:app --app-dir backend --reload
```

## 启动前端

```bash
cd frontend
pnpm install
pnpm run generate:api
pnpm run dev
```

Apifox 优先导入 `backend/docs/openapi-v3.0-apifox.json`，或在后端启动后通过 `http://127.0.0.1:8000/openapi.json` 导入。

更详细的运行与接口说明见：

- `frontend/README.md`
- `backend/README.md`
- `backend/docs/`

## 版本归档约定

- 已确定版本的产品文档、设计稿和 Agent 配置放入对应版本目录。
- 当前代码始终放在 `backend/`、`frontend/`，不随产品版本移动或复制。
- 新版本立项时，为产品、设计和技术基线新增对应版本目录；不要覆盖旧版本资料。
- 代码发布版本通过 Git 标签与发布说明记录；历史文档版本、数据库迁移编号和 API 路径按各自用途维护。
