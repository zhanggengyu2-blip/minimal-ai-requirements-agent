# 极简 AI 团队需求管理智能体

项目按职能和版本两层组织。产品文档与设计资产保留 V1.1、V2.0 的独立目录；当前前后端代码为 V2.0 实现，并继续兼容 V1.1 能力。

## 目录导航

```text
product/
├── v1.1/                  # MVP PRD、组织管理需求、通用需求分析 Agent、业务流程
└── v2.0/                  # 对话式需求访谈 PRD 与 Agent 设计
design/
├── v1.1/                  # V1.1 UI 设计图与 Figma 插件
└── v2.0/                  # V2.0 需求访谈工作台设计图
frontend/
└── v2.0/                  # Vue 3 前端，兼容 V1.1 并新增 V2.0 访谈工作台
backend/
└── v2.0/                  # FastAPI 后端、测试、数据与技术文档
```

## 启动后端

```bash
cd backend/v2.0
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env
python -m uvicorn app.main:app --reload
```

`.env` 已随项目移动到 `backend/v2.0/`。Python 虚拟环境在移动目录后建议重新创建，避免入口脚本保留旧的绝对路径。

默认 SQLite 数据库和访谈图片目录也固定在 `backend/v2.0/data/` 下，不会因为从其他目录调用后端而改变。若确实需要从仓库根目录启动，可使用：

```bash
python -m uvicorn app.main:app --app-dir backend/v2.0 --reload
```

## 启动前端

```bash
cd frontend/v2.0
pnpm install
pnpm run generate:api
pnpm run dev
```

更详细的运行与接口说明见：

- `frontend/v2.0/README.md`
- `backend/v2.0/README.md`
- `backend/v2.0/docs/`

## 版本归档约定

- 已确定版本的产品文档、设计稿和 Agent 配置放入对应版本目录。
- 当前可运行代码放在最新版本目录中，通过兼容方式保留旧版能力，不复制两套源码。
- 新版本立项时，新增对应版本目录；不要覆盖旧版本产品和设计资料。
