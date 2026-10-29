# 企业 AI 协作系统 V4.0 — Coo 企业 AI 同事

基于原需求管理应用增量升级：保留项目、需求、团队任务、成员权限、版本排期与甘特图；新增任务留言/回复、企业与项目知识库、真实模型工具调用、私人 Coo 会话、操作确认和主动业务事件。

当前实际目录为 `backend/app` 与 `frontend/src`。不需要 Dify、Docker、Redis、Celery、OpenSearch。访谈入口与 API 已下线，源码、历史表和迁移保留。

## 启动

Python 3.12、Node.js 24 与 pnpm 11。后端依赖沿用现有项目，未引入 Agent 框架。

```bash
python3.12 -m venv backend/.venv
backend/.venv/bin/python -m pip install -e 'backend[dev]'
cp backend/.env.example backend/.env
```

已有 `.env` 和数据库请保留；不要执行覆盖命令。升级已有数据库前备份 `backend/data/`。在 `backend/.env` 中设置公司统一密码 `SHARED_PASSWORD`、独立随机 `AUTH_HMAC_KEY` 与 `INVITATION_ENCRYPTION_KEY`。例如可用 `python3 -c "import secrets; print(secrets.token_urlsafe(48))"` 分别生成密钥。

配置 `COO_BASE_URL`、`COO_API_KEY`、`COO_MODEL`。模型接口需要支持 Chat Completions、Tool Calling 与 JSON 输出；Key 仅由服务端读取。知识发布还需要 `KNOWLEDGE_EMBEDDING_*`；重排序使用可选 `KNOWLEDGE_RERANK_*`。未配置模型时系统明确报告错误，业务数据仍然保存，没有规则结果冒充 LLM 的演示模式。

```bash
# 自动执行增量迁移、部门初始化；同时启动 API 与主动事件后台进程
backend/.venv/bin/python backend/scripts/run_v4.py
```

首次使用另开终端创建管理员（已有管理员无需重复）：

```bash
backend/.venv/bin/python backend/scripts/bootstrap_admin.py --department 产品部 --name 演示管理员
```

原前端：

```bash
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend dev
```

打开 [应用](http://127.0.0.1:3000)、[接口文档](http://127.0.0.1:8000/docs)。管理员使用对应部门、姓名和公司统一密码登录，邀请员工、创建项目和添加项目成员。单独部署 API 时，可分别运行 `python -m uvicorn app.main:app` 与 `python -m app.coo.worker`（工作目录均为 backend）。关闭 Worker 仅暂停事件处理，队列仍保存在数据库。

## 功能与边界

- 任务留言/回复独立关联真实任务；保留 Task revision 并发控制。Coo 留言有 AI 身份与运行 ID，员工请求不能伪造该身份。
- 企业知识由管理员显式选择全员或指定部门可读；项目知识沿用项目权限。支持分类、UTF-8 `.txt/.md` 上传、分段预览、草稿、发布、版本恢复、有效期和停启用。新版本发布失败保留旧有效版本。
- SQLite 保存向量，Python 完成小规模关键词与向量混合检索、RRF 融合、可选 Rerank 和来源校验。未配置或失败的能力会说明降级情况。
- Coo 根据目标自主选择有 Schema 的业务工具；不允许任意 SQL。默认写入产生具体待确认建议，确认时重新检查权限。员工本轮明确授权的留言可自动执行。需求分析按钮调用确定性的十字段工作流，Coo 也复用它。
- 员工私人会话、执行日志及确认归属相互隔离；项目任务和留言是共享业务事实。当前是单企业部署，没有多企业租户管理。
- 新需求、员工任务修改/留言和模拟履约异常会保存事件，由后台进程主动调查；支持去重、租约恢复、失败原因与人工重试。Coo 留言不触发自回复循环。
- 模拟 ERP 适配器明确标记来源，未连接真实 ERPNext。未实现完整 Goal/Plan/长期 Memory、流式输出或生产规模检索。

## 验证与演示

```bash
cd backend && .venv/bin/python -m pytest -q
```

```bash
pnpm --dir frontend test
pnpm --dir frontend build
pnpm --dir frontend test:e2e
```

端到端测试需要独立临时数据库和测试管理员，参照 `.github/workflows/quality.yml`，不要对个人业务库运行。自动化模型测试使用受控响应；真实模型连通性与质量验证需要自行配置服务端 Key。

- [审计与实施计划](docs/v4/IMPLEMENTATION.md)
- [面试演示脚本](docs/v4/DEMO.md)
- [验收记录与已知限制](docs/v4/ACCEPTANCE.md)
- [第三方来源与许可](THIRD_PARTY_NOTICES.md)

知识库复用 [AI 电商智能客服](https://github.com/zhanggengyu2-blip/ai-ecommerce-customer-service) 的 foundation 实现与测试思路；其 AgentServe 上游 Apache 2.0 许可证随仓库保留，第三方原始实现不计作本项目原创。
