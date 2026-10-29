# Coo V4 实施审计与计划

2026-10-29。开发分支 `codex/coo-v4`。已有未提交的目录迁移及产品文档保存在基线提交 9f087be；本次沿用 backend/ 与 frontend/，不恢复 v2.0 路径。

## 审计

- 原业务由 API → Service → SQLAlchemy 组成；ProjectService 统一控制可见性、成员写入和归档只读，TaskService 已有 revision/泳道并发保护，继续复用。
- 需求先保存再分析，十字段 Pydantic 严格契约和同项目候选范围校验保留。替换默认分析提供者，保留旧 Dify/访谈源码及历史迁移。
- 基线：在 backend 中 pytest 92 passed；frontend Vitest 39 passed。仓库根部 tests 为旧 V2 访谈测试，不属于当前后端测试配置。
- 参考客服项目 main 的 foundation/knowledge.py (3c8e53b)、retrieval.py (1b0a1fc)、providers.py (85a2e67)、model_runtime.py (a07db1b)、workers.py (84b4efe)、ai_api.py (398d046)、models/knowledge.py、LiveKnowledge.vue 和 tests/test_foundation.py、tests/test_models_knowledge.py。当前实际运行路径没有强制 Redis/Celery/OpenSearch。保留来源及 Apache 2.0 许可。

## 分阶段文件计划

1. Phase 1：api/router.py、routes/requirements.py 停止注册访谈；前端 router/index.ts、AppLayout.vue 移除入口；db/models.py、schemas/task_comment.py、services/task_comment_service.py、routes/task_comments.py、0007 迁移新增评论；TaskComments.vue 接入 TaskDialog；后端权限/回复测试和前端交互测试。
2. Phase 2：knowledge/{models,schemas,ingestion,retrieval,service,providers}.py、routes/knowledge.py、0008 迁移；企业知识显式选择全员或部门 ACL，项目知识复用成员可见权限；发布新版本成功后才替换可检索版本；KnowledgeView.vue；THIRD_PARTY_NOTICES 与许可证。
3. Phase 3：coo/{models,schemas,provider,tools,runtime,analysis}.py、routes/coo.py、0009 迁移；确定性分析 Workflow 共用十字段契约；受限 Tool Calling 循环、私人会话、运行/工具记录、写入确认、CooView.vue。
4. Phase 4：coo/events.py、coo/worker.py、业务事件写入、0010 迁移；数据库事件队列/租约/重试；模拟 ERP 事件；确认后经 TaskService 写入；更新 README、环境示例、演示脚本与验收记录。

## 工程决策

不引入 Agent 框架，使用现有 httpx 与兼容 Chat Completions 的模型接口。知识 Embedding 与 Rerank 分开配置。没有 Key 时明确报错，不用规则结果冒充 LLM。独立本机 Worker 无需浏览器在线。写操作默认生成待确认建议，确认时重新校验会话所有者、项目成员与业务参数；低风险自动留言须员工在本次运行明确授权。所有新增数据采用增量迁移；历史访谈表不删除。

验收包含已有业务回归、跨项目/跨会话拒绝、失败版本保护、过期过滤、引用白名单、非法工具参数、写入幂等、事件去重与失败重试。受控模型响应测试与真实付费模型验证分别记录。

## 实施完成记录

- Phase 1：520ea5c，访谈停止注册；任务评论、回复、权限与前端交互。
- Phase 2：f1473ee，知识业务模块、权限、版本保护、检索与许可。
- Phase 3：409ecb4，Coo 模型适配器、注册表、运行记录、私有会话、确认与共用需求分析。
- Phase 4：760caf0，持久业务事件、后台 Worker、模拟订单适配器、主动调查及协作闭环。
- 追加验收修复：发布处理起点/超时、Token 预算含工具 Schema、分析并发互斥与写入前权限复验、UTC 时间输出、执行列表只返回摘要、迁移兼容与运行中撤权测试。最新验证数据见 ACCEPTANCE.md。

## 依赖来源与影响传播

原 ProjectService 的权限来自登录员工与 ProjectMember，向 TaskService、TaskCommentService、KnowledgeService 和 Coo 工具传播。Runtime 不能替换员工角色；确认时再次调用原业务服务。原 TaskService 的事务默认行为保留，仅增加 `commit=False` 供 Coo 创建/更新确认与业务写入一次提交，防止重复确认创建两个任务。业务 Service 在原提交之前插入 Outbox 事件，失败会和业务事务一起回滚；后台 Worker 只读取持久事件，以原员工身份调用 Runtime，不依赖 Web 请求或浏览器。

知识切分/召回/版本保护来自客服 foundation；改造后的业务存储、企业/项目 ACL 和服务接口位于 knowledge 模块。Coo 只通过 search_knowledge 调用它，查询上下文不复制整个知识库。需求分析 Schema 来自原十字段契约，移至 schemas/analysis.py；历史 Dify Schema 保留兼容导入，默认适配器改为 Coo 工作流。

最终验收补齐 `update_task`（任务状态变更工具），经原 TaskService 的 revision 校验与人工确认执行；Coo 自身更新不再投递同源跟进事件。知识发布增加处理起点与条件提交保护，超时恢复后的迟到模型结果不会重新发布旧候选。0011 使用原生 DROP COLUMN 回退新增元数据，验证已发布正文和片段不丢失。
