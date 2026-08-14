# Backend Code Review Map：Schema

> 扫描范围：`app/schemas/` 全部文件，并通过 Router / Service 引用确认用途。本文中的 **Schema** 专指 Pydantic 数据对象；`DifyWorkflowResult` 与 `DifyInterviewWorkflowResult` 是 Service 层 dataclass，会单独标明，不把它们当作 Pydantic Schema。

## 术语与表格约定

- **Create Schema**：API 创建输入。
- **Update Schema**：API 修改输入。
- **Read Schema**：API 输出。
- **Service Result**：Service 内部结果对象。
- “必填”依据 Pydantic 是否声明默认值判断，不依据类型是否包含 `None`。因此 `str | None` 也可能是“必填但允许 `null`”。
- `ORMModel` 配置 `from_attributes=True`，支持从 SQLAlchemy ORM 属性构造 Schema。

## Schema Module Overview

| 模块 | Pydantic Schema / 类型 | 主要职责 |
|---|---|---|
| `common` | `ApiResponse[T]`、`PageData[T]`、`ORMModel` | 通用响应、分页和 ORM 转换基类 |
| `project` | `ProjectCreate`、`ProjectRead` | 项目输入与输出 |
| `organization` | `DepartmentCreate`、`DepartmentUpdate`、`DepartmentRead`、`InvitationCreate`、`InvitationRead` | 部门与邀请码 |
| `requirement` | `RequirementCreate`、`RequirementRead`、`BatchAnalyzeRequest`、`BatchAnalyzeAccepted` | 需求输入、输出及批量分析预留响应 |
| `dify` | `DifyAnalysisResult`、访谈字段/问题/结果 | Dify Workflow 严格输出契约 |
| `interview` | 访谈输入、读模型、确认结果、动作别名 | 访谈 API 边界 |

# common

## ApiResponse[T]

- 继承：`BaseModel`、`Generic[T]`
- 类型：Common / API Response Wrapper
- 用途：所有 Router 的统一响应外壳，`data` 的实际类型由泛型参数决定。

| 字段 | 类型 | 必填 | 默认值 | 限制 | 嵌套 Schema | 说明 |
|---|---|---|---|---|---|---|
| `code` | `str` | 否 | `"OK"` | - | - | 业务响应码 |
| `message` | `str` | 否 | `"success"` | - | - | 响应消息 |
| `data` | `T` | 是 | - | - | 取决于 `T` | 实际响应数据 |
| `request_id` | `str \| None` | 否 | `None` | - | - | 请求追踪 ID |

## PageData[T]

- 继承：`BaseModel`、`Generic[T]`
- 类型：Common / Pagination
- 用途：列表 API 的分页数据。

| 字段 | 类型 | 必填 | 默认值 | 限制 | 嵌套 Schema | 说明 |
|---|---|---|---|---|---|---|
| `items` | `list[T]` | 是 | - | - | 取决于 `T` | 当前页数据 |
| `total` | `int` | 是 | - | `>= 0` | - | 总数 |
| `page` | `int` | 是 | - | `>= 1` | - | 当前页 |
| `page_size` | `int` | 是 | - | `>= 1` | - | 每页条数 |

## ORMModel

- 继承：`BaseModel`
- 类型：Common / Schema Base
- 用途：为需要从 ORM 读取属性的 Schema 统一开启 `ConfigDict(from_attributes=True)`。
- 无业务字段。

# project

## ProjectCreate

- 继承：`ORMModel`
- 类型：Create Input
- 用途：创建项目的 API → Service 输入。

| 字段 | 类型 | 必填 | 默认值 | 限制 | 嵌套 Schema | 说明 |
|---|---|---|---|---|---|---|
| `name` | `str` | 是 | - | `1 <= length <= 100` | - | 去除首尾空白后不能为空 |
| `description` | `str` | 否 | `""` | `length <= 2000` | - | 项目描述 |
| `project_context` | `str` | 是 | - | `1 <= length <= 10000` | - | 去除首尾空白后不能为空 |
| `department_id` | `str \| None` | 否 | `None` | `length <= 32` | - | 部门逻辑 ID；Schema 不验证目标部门存在 |
| `created_by` | `str \| None` | 否 | `None` | `length <= 32` | - | 创建人逻辑 ID |

Validator：`name` 与 `project_context` 会先 `strip()`；全空白会报错。

## ProjectRead

- 继承：`ORMModel`
- 类型：Read/Response
- 用途：项目创建和项目列表的输出。

| 字段 | 类型 | 必填 | 默认值 | 限制 | 嵌套 Schema | 说明 |
|---|---|---|---|---|---|---|
| `id` | `str` | 是 | - | - | - | 项目 ID |
| `name` | `str` | 是 | - | - | - | 项目名称 |
| `description` | `str` | 是 | - | - | - | 项目描述 |
| `project_context` | `str` | 是 | - | - | - | 项目上下文 |
| `department_id` | `str \| None` | 是 | - | 可为 `null` | - | 部门逻辑 ID |
| `created_by` | `str \| None` | 是 | - | 可为 `null` | - | 创建人逻辑 ID |
| `status` | `ProjectStatus` | 是 | - | `ACTIVE` / `ARCHIVED` | - | 项目状态 |
| `requirement_count` | `int` | 否 | `0` | - | - | `ProjectService.list()` 查询后补充 |
| `created_time` | `datetime` | 是 | - | - | - | 创建时间 |
| `updated_time` | `datetime` | 是 | - | - | - | 更新时间 |

# organization

## DepartmentCreate

- 继承：`ORMModel`
- 类型：Create Input
- 用途：创建部门。

| 字段 | 类型 | 必填 | 默认值 | 限制 | 嵌套 Schema | 说明 |
|---|---|---|---|---|---|---|
| `name` | `str` | 是 | - | `1 <= length <= 100` | - | 去除首尾空白后不能为空 |

## DepartmentUpdate

- 继承：`ORMModel`
- 类型：Update Input
- 用途：修改部门名称或状态。

| 字段 | 类型 | 必填 | 默认值 | 限制 | 嵌套 Schema | 说明 |
|---|---|---|---|---|---|---|
| `name` | `str \| None` | 否 | `None` | 非空时 `1 <= length <= 100` | - | 非空时去除首尾空白；全空白报错 |
| `status` | `DepartmentStatus \| None` | 否 | `None` | `ACTIVE` / `DISABLED` | - | Service 使用 `exclude_none=True`，`null` 不会写入 ORM |

## DepartmentRead

- 继承：`ORMModel`
- 类型：Read/Response
- 用途：部门 API 输出。

| 字段 | 类型 | 必填 | 默认值 | 限制 | 嵌套 Schema | 说明 |
|---|---|---|---|---|---|---|
| `id` | `str` | 是 | - | - | - | 部门 ID |
| `name` | `str` | 是 | - | - | - | 部门名称 |
| `status` | `DepartmentStatus` | 是 | - | `ACTIVE` / `DISABLED` | - | 部门状态 |
| `created_time` | `datetime` | 是 | - | - | - | 创建时间 |
| `updated_time` | `datetime` | 是 | - | - | - | 更新时间 |
| `user_count` | `int` | 否 | `0` | - | - | 当前 Service 未统计，保持默认值 |
| `project_count` | `int` | 否 | `0` | - | - | `DepartmentService._to_read()` 按 `Project.department_id` 统计 |

## InvitationCreate

- 继承：`ORMModel`
- 类型：Create Input
- 用途：为指定部门生成邀请码。

| 字段 | 类型 | 必填 | 默认值 | 限制 | 嵌套 Schema | 说明 |
|---|---|---|---|---|---|---|
| `department_id` | `str` | 是 | - | `length = 32` | - | Department ORM ID |
| `user_name` | `str \| None` | 否 | `None` | `length <= 50` | - | 去除首尾空白；空字符串转为 `None` |

## InvitationRead

- 继承：`ORMModel`
- 类型：Read/Response
- 用途：邀请码创建、禁用和列表输出。

| 字段 | 类型 | 必填 | 默认值 | 限制 | 嵌套 Schema | 说明 |
|---|---|---|---|---|---|---|
| `id` | `str` | 是 | - | - | - | 记录 ID |
| `code` | `str` | 是 | - | - | - | 邀请码 |
| `department_id` | `str` | 是 | - | - | - | 部门 ID |
| `department_name` | `str` | 是 | - | - | - | Service 从 relationship 补充 |
| `user_name` | `str \| None` | 是 | - | 可为 `null` | - | 使用人姓名 |
| `status` | `InvitationStatus` | 是 | - | `UNUSED` / `USED` / `DISABLED` | - | 使用状态 |
| `created_time` | `datetime` | 是 | - | - | - | 创建时间 |
| `used_time` | `datetime \| None` | 是 | - | 可为 `null` | - | 使用时间；当前 Service 未赋值 |

# requirement

## RequirementCreate

- 继承：`ORMModel`
- 类型：Create Input
- 用途：管理端直接创建并触发分析的需求输入。

| 字段 | 类型 | 必填 | 默认值 | 限制 | 嵌套 Schema | 说明 |
|---|---|---|---|---|---|---|
| `project_id` | `str` | 是 | - | `length = 32` | - | 所属项目 ID |
| `raw_content` | `str` | 是 | - | `1 <= length <= 10000` | - | 去除首尾空白后不能为空 |
| `created_by` | `str \| None` | 否 | `None` | `length <= 32` | - | 创建人逻辑 ID |

## RequirementRead

- 继承：`ORMModel`
- 类型：Read/Response
- 用途：需求创建、查询、列表与重新分析输出。

| 字段 | 类型 | 必填 | 默认值 | 限制 / 允许值 | 嵌套 Schema | 说明 |
|---|---|---|---|---|---|---|
| `id` | `str` | 是 | - | - | - | 需求 ID |
| `project_id` | `str` | 是 | - | - | - | 项目 ID |
| `raw_content` | `str` | 是 | - | - | - | 原始内容 |
| `interview_session_id` | `str \| None` | 是 | - | 可为 `null` | - | 来源访谈会话逻辑 ID |
| `clarified_content` | `str \| None` | 是 | - | 可为 `null` | - | 访谈澄清内容 |
| `interview_rounds` | `int` | 是 | - | - | - | 访谈轮数 |
| `completeness_score` | `int \| None` | 是 | - | 可为 `null` | - | 完整度 |
| `standard_content` | `str \| None` | 是 | - | 可为 `null` | - | AI 标准化内容 |
| `business_goal` | `str \| None` | 是 | - | 可为 `null` | - | AI 业务目标 |
| `type` | `RequirementType \| None` | 是 | - | `NEW_FEATURE` / `BUG` / `OPTIMIZATION` / `null` | - | AI 需求类型 |
| `priority` | `RequirementPriority \| None` | 是 | - | `P0` / `P1` / `P2` / `P3` / `null` | - | AI 优先级 |
| `is_fake` | `bool \| None` | 是 | - | 可为 `null` | - | 伪需求判断 |
| `fake_reason` | `str \| None` | 是 | - | 可为 `null` | - | 判断原因 |
| `is_duplicate` | `bool \| None` | 是 | - | 可为 `null` | - | 重复判断 |
| `related_id` | `str` | 是 | - | - | - | 关联需求 ID 或空字符串 |
| `reference_rule` | `str \| None` | 是 | - | 可为 `null` | - | 参考规则 |
| `analysis_summary` | `str \| None` | 是 | - | 可为 `null` | - | 分析摘要 |
| `analysis_status` | `AnalysisStatus` | 是 | - | `PENDING` / `ANALYZING` / `ANALYZED` / `FAILED` | - | 分析状态 |
| `analysis_error_code` | `str \| None` | 是 | - | 可为 `null` | - | 错误码 |
| `analysis_error_message` | `str \| None` | 是 | - | 可为 `null` | - | 错误信息 |
| `dify_workflow_run_id` | `str \| None` | 是 | - | 可为 `null` | - | Dify Workflow Run ID |
| `manual_modify` | `bool` | 是 | - | - | - | 人工修改标记 |
| `created_by` | `str \| None` | 是 | - | 可为 `null` | - | 创建人逻辑 ID |
| `created_time` | `datetime` | 是 | - | - | - | 创建时间 |
| `updated_time` | `datetime` | 是 | - | - | - | 更新时间 |

## BatchAnalyzeRequest

- 继承：`ORMModel`
- 类型：Action Input
- 用途：批量分析预留接口的请求体。

| 字段 | 类型 | 必填 | 默认值 | 限制 | 嵌套 Schema | 说明 |
|---|---|---|---|---|---|---|
| `requirement_ids` | `list[str]` | 是 | - | `1 <= items <= 50`；不可重复；每项 `length = 32` | - | 待分析需求 ID |

## BatchAnalyzeAccepted

- 继承：`ORMModel`
- 类型：Action Response / Reserved
- 用途：批量分析预留接口返回“已接受”信息；当前 Router 直接构造，不进入 Service。

| 字段 | 类型 | 必填 | 默认值 | 限制 | 嵌套 Schema | 说明 |
|---|---|---|---|---|---|---|
| `task_id` | `str` | 是 | - | - | - | Router 生成 UUID |
| `total` | `int` | 是 | - | - | - | 请求 ID 数量 |
| `status` | `str` | 否 | `"RESERVED"` | 固定默认语义 | - | 表明功能预留 |
| `message` | `str` | 否 | `"批量分析接口已预留，任务尚未执行"` | - | - | 明确当前不会执行任务 |

# dify

本模块中的 Schema 均使用严格模式；`DifyAnalysisResult`、`DifyInterviewField`、`DifyInterviewFields`、`DifyInterviewQuestion`、`DifyInterviewResult` 禁止额外字段（`extra="forbid"`）。

## DifyAnalysisResult

- 继承：`BaseModel`
- 类型：AI/Dify Result
- 用途：需求分析 Workflow 的严格输出契约。

| 字段 | 类型 | 必填 | 默认值 | 限制 / 允许值 | 嵌套 Schema | 说明 |
|---|---|---|---|---|---|---|
| `standard_content` | `str` | 是 | - | `1 <= length <= 4000` | - | 标准化需求 |
| `business_goal` | `str` | 是 | - | `1 <= length <= 2000` | - | 业务目标 |
| `type` | `Literal` | 是 | - | `NEW_FEATURE` / `BUG` / `OPTIMIZATION` | - | 需求类型 |
| `priority` | `Literal` | 是 | - | `P0` / `P1` / `P2` / `P3` | - | 优先级 |
| `is_fake` | `bool` | 是 | - | 严格布尔值 | - | 是否伪需求 |
| `fake_reason` | `str` | 是 | - | `1 <= length <= 2000` | - | 伪需求解释 |
| `is_duplicate` | `bool` | 是 | - | 严格布尔值 | - | 是否重复 |
| `related_id` | `str` | 是 | - | `length <= 32` | - | 关联候选需求 ID 或空字符串 |
| `reference_rule` | `str` | 是 | - | `1 <= length <= 2000` | - | 分析参考规则 |
| `analysis_summary` | `str` | 是 | - | `1 <= length <= 500` | - | 分析摘要 |

业务校验：

- `is_duplicate=True` → `related_id` 去空白后必须有值。
- `is_duplicate=False` → `related_id` 必须为空字符串。
- 此外，`DifyService` 会验证重复需求的 `related_id` 必须属于本次传给 Dify 的候选需求集合。

## InterviewFieldName

- 类型：`TypeAlias` / `Literal`
- 用途：统一访谈字段名。
- 允许值：`target_user` / `usage_scenario` / `user_goal` / `current_problem` / `expected_result` / `proposed_solution` / `frequency` / `impact_scope` / `bug_steps` / `actual_result` / `environment`。

## DifyInterviewField

- 继承：`BaseModel`
- 类型：AI/Dify Nested Result
- 用途：一个结构化访谈字段及其证据。

| 字段 | 类型 | 必填 | 默认值 | 限制 / 允许值 | 嵌套 Schema | 说明 |
|---|---|---|---|---|---|---|
| `value` | `str` | 是 | - | `1 <= length <= 2000` | - | 字段值 |
| `evidence_message_ids` | `list[str]` | 是 | - | `items <= 20` | - | 支撑该字段的消息 ID |
| `source` | `Literal` | 是 | - | `USER_INPUT` / `USER_EDIT` | - | 信息来源 |

## DifyInterviewFields

- 继承：`BaseModel`
- 类型：AI/Dify Nested Result
- 用途：承载全部 11 个访谈字段。

| 字段 | 类型 | 必填 | 默认值 | 限制 | 嵌套 Schema | 说明 |
|---|---|---|---|---|---|---|
| `target_user` | `DifyInterviewField \| None` | 是 | - | 可为 `null` | `DifyInterviewField` | 目标用户 |
| `usage_scenario` | 同上 | 是 | - | 可为 `null` | `DifyInterviewField` | 使用场景 |
| `user_goal` | 同上 | 是 | - | 可为 `null` | `DifyInterviewField` | 用户目标 |
| `current_problem` | 同上 | 是 | - | 可为 `null` | `DifyInterviewField` | 当前问题 |
| `expected_result` | 同上 | 是 | - | 可为 `null` | `DifyInterviewField` | 期望结果 |
| `proposed_solution` | 同上 | 是 | - | 可为 `null` | `DifyInterviewField` | 用户提出的方案 |
| `frequency` | 同上 | 是 | - | 可为 `null` | `DifyInterviewField` | 发生频率 |
| `impact_scope` | 同上 | 是 | - | 可为 `null` | `DifyInterviewField` | 影响范围 |
| `bug_steps` | 同上 | 是 | - | 可为 `null` | `DifyInterviewField` | Bug 复现步骤 |
| `actual_result` | 同上 | 是 | - | 可为 `null` | `DifyInterviewField` | 实际结果 |
| `environment` | 同上 | 是 | - | 可为 `null` | `DifyInterviewField` | 环境信息 |

注意：11 个键均没有默认值，所以 Dify 输出必须提供全部键；每个键的值可以是 `null`。

## DifyInterviewQuestion

- 继承：`BaseModel`
- 类型：AI/Dify Nested Result
- 用途：下一轮访谈问题。

| 字段 | 类型 | 必填 | 默认值 | 限制 / 允许值 | 嵌套 Schema | 说明 |
|---|---|---|---|---|---|---|
| `text` | `str` | 是 | - | `1 <= length <= 120` | - | 问题文本 |
| `target_field` | `InterviewFieldName` | 是 | - | 11 个访谈字段名 | - | 本轮目标字段 |
| `reason_code` | `Literal` | 是 | - | `MISSING_CORE_FIELD` / `MISSING_BUG_FIELD` / `CLARIFY_CONFLICT` / `SEPARATE_PROBLEM_FROM_SOLUTION` / `CLARIFY_MULTIPLE_REQUESTS` / `MISSING_RECOMMENDED_FIELD` | - | 提问原因 |

## DifyInterviewResult

- 继承：`BaseModel`
- 类型：AI/Dify Result
- 用途：访谈 Workflow 单轮完整输出。

| 字段 | 类型 | 必填 | 默认值 | 限制 / 允许值 | 嵌套 Schema | 说明 |
|---|---|---|---|---|---|---|
| `request_type` | `Literal \| None` | 是 | - | `NEW_FEATURE` / `BUG` / `OPTIMIZATION` / `null` | - | 当前识别的需求类型 |
| `extracted_fields` | `DifyInterviewFields` | 是 | - | - | `DifyInterviewFields` | 本轮提取结果 |
| `next_question` | `DifyInterviewQuestion \| None` | 是 | - | 可为 `null` | `DifyInterviewQuestion` | 下一问题 |
| `summary_title` | `str` | 是 | - | `1 <= length <= 100` | - | 摘要标题 |
| `validation_ok` | `bool` | 否 | `True` | 严格布尔值 | - | Dify 自检结果 |
| `validation_errors` | `list[str]` | 否 | `[]` | `items <= 50` | - | Dify 自检错误 |

业务校验：`validation_ok=False` 时整个 Schema 校验失败，错误信息由 `validation_errors` 合并形成。

## Dify Schema 嵌套关系

```text
DifyInterviewResult Schema
├── request_type
├── extracted_fields: DifyInterviewFields Schema
│   ├── target_user: DifyInterviewField Schema | null
│   ├── usage_scenario: DifyInterviewField Schema | null
│   ├── user_goal: DifyInterviewField Schema | null
│   ├── current_problem: DifyInterviewField Schema | null
│   ├── expected_result: DifyInterviewField Schema | null
│   ├── proposed_solution: DifyInterviewField Schema | null
│   ├── frequency: DifyInterviewField Schema | null
│   ├── impact_scope: DifyInterviewField Schema | null
│   ├── bug_steps: DifyInterviewField Schema | null
│   ├── actual_result: DifyInterviewField Schema | null
│   └── environment: DifyInterviewField Schema | null
├── next_question: DifyInterviewQuestion Schema | null
├── summary_title
├── validation_ok
└── validation_errors

DifyAnalysisResult Schema
└── 十个扁平分析字段；无嵌套 Schema
```

# interview

## InterviewCreate

- 继承：`ORMModel`
- 类型：Create Input
- 用途：创建访谈会话并提交第一条用户消息/图片。

| 字段 | 类型 | 必填 | 默认值 | 限制 | 嵌套 Schema | 说明 |
|---|---|---|---|---|---|---|
| `project_id` | `str` | 是 | - | `length = 32` | - | 项目 ID |
| `raw_content` | `str` | 否 | `""` | `length <= 10000` | - | 去除首尾空白 |
| `created_by` | `str \| None` | 否 | `None` | `length <= 32` | - | 创建人逻辑 ID |
| `client_message_id` | `str` | 是 | - | `1 <= length <= 64` | - | 创建幂等键，同时成为首条消息的客户端 ID |
| `attachment_ids` | `list[str]` | 否 | `[]` | `items <= 5`；不可重复；每项 `length = 32` | - | 预上传附件 ID |

业务校验：`raw_content` 与 `attachment_ids` 至少有一个非空。

## InterviewMessageCreate

- 继承：`ORMModel`
- 类型：Action Input
- 用途：继续回答访谈问题。

| 字段 | 类型 | 必填 | 默认值 | 限制 | 嵌套 Schema | 说明 |
|---|---|---|---|---|---|---|
| `content` | `str` | 否 | `""` | `length <= 10000` | - | 去除首尾空白 |
| `client_message_id` | `str` | 是 | - | `1 <= length <= 64` | - | 会话内幂等键 |
| `attachment_ids` | `list[str]` | 否 | `[]` | `items <= 5`；不可重复；每项 `length = 32` | - | 预上传附件 ID |

业务校验：`content` 与 `attachment_ids` 至少有一个非空。

## InterviewActionRequest

- 继承：`ORMModel`
- 类型：Action Input
- 用途：跳过或“不知道”动作的幂等请求。

| 字段 | 类型 | 必填 | 默认值 | 限制 | 嵌套 Schema | 说明 |
|---|---|---|---|---|---|---|
| `client_message_id` | `str` | 是 | - | `1 <= length <= 64` | - | 会话内幂等键 |

## InterviewSummaryUpdate

- 继承：`ORMModel`
- 配置：`extra="forbid"`
- 类型：Update Input
- 用途：确认前人工编辑结构化摘要。

| 字段 | 类型 | 必填 | 默认值 | 限制 | 嵌套 Schema | 说明 |
|---|---|---|---|---|---|---|
| `fields` | `dict[InterviewFieldName, str \| None]` | 是 | - | `1 <= items <= 11`；非空值去空白后 `length <= 2000` | 值不是嵌套 Schema | `null` 表示清空该字段；未知键被类型拒绝 |
| `summary_title` | `str \| None` | 否 | `None` | 非空时 `1 <= length <= 100` | - | Service 去除首尾空白后写入 |

业务校验：字段值若不是 `null`，去除首尾空白后不得为空且长度不得超过 2000。

## InterviewConfirmRequest

- 继承：`ORMModel`
- 类型：Action Input
- 用途：确认摘要并创建最终需求。

| 字段 | 类型 | 必填 | 默认值 | 限制 | 嵌套 Schema | 说明 |
|---|---|---|---|---|---|---|
| `idempotency_key` | `str` | 是 | - | `1 <= length <= 64` | - | 写入会话；当前 Service 不按此键查询 |

## InterviewAttachmentRead

- 继承：`ORMModel`
- 类型：Read/Response
- 用途：附件上传结果及消息内附件输出。

| 字段 | 类型 | 必填 | 默认值 | 限制 | 嵌套 Schema | 说明 |
|---|---|---|---|---|---|---|
| `id` | `str` | 是 | - | - | - | 附件 ID |
| `session_id` | `str \| None` | 是 | - | 可为 `null` | - | 绑定会话 |
| `message_id` | `str \| None` | 是 | - | 可为 `null` | - | 绑定消息 |
| `uploaded_by` | `str \| None` | 是 | - | 可为 `null` | - | 上传人逻辑 ID |
| `original_name` | `str` | 是 | - | - | - | 原始文件名 |
| `mime_type` | `str` | 是 | - | - | - | MIME 类型 |
| `size_bytes` | `int` | 是 | - | - | - | 文件大小 |
| `sha256` | `str` | 是 | - | - | - | 文件摘要 |
| `preview_url` | `str` | 是 | - | - | - | 来自 ORM 计算属性，不是数据库列 |
| `created_time` | `datetime` | 是 | - | - | - | 创建时间 |

## InterviewMessageRead

- 继承：`ORMModel`
- 类型：Read/Response
- 用途：访谈会话中的消息输出。

| 字段 | 类型 | 必填 | 默认值 | 限制 | 嵌套 Schema | 说明 |
|---|---|---|---|---|---|---|
| `id` | `str` | 是 | - | - | - | 消息 ID |
| `session_id` | `str` | 是 | - | - | - | 会话 ID |
| `sequence_no` | `int` | 是 | - | - | - | 会话内序号 |
| `role` | `InterviewMessageRole` | 是 | - | `USER` / `AGENT` / `SYSTEM_EVENT` | - | 消息角色 |
| `content` | `str` | 是 | - | - | - | 消息内容 |
| `action_type` | `InterviewActionType \| None` | 是 | - | 五种动作或 `null` | - | 用户动作 |
| `target_field` | `str \| None` | 是 | - | 可为 `null` | - | 目标字段 |
| `reason_code` | `str \| None` | 是 | - | 可为 `null` | - | 原因代码 |
| `client_message_id` | `str \| None` | 是 | - | 可为 `null` | - | 客户端消息 ID |
| `agent_run_id` | `str \| None` | 是 | - | 可为 `null` | - | Dify Workflow Run ID |
| `attachments` | `list[InterviewAttachmentRead]` | 是 | - | - | `InterviewAttachmentRead` | 消息附件 |
| `created_time` | `datetime` | 是 | - | - | - | 创建时间 |

## InterviewSessionRead

- 继承：`ORMModel`
- 类型：Read/Response
- 用途：访谈详情和各动作后的当前状态输出；由 `InterviewService.to_read()` 显式组装。

| 字段 | 类型 | 必填 | 默认值 | 限制 / 允许值 | 嵌套 Schema | 说明 |
|---|---|---|---|---|---|---|
| `id` | `str` | 是 | - | - | - | 会话 ID |
| `project_id` | `str` | 是 | - | - | - | 项目 ID |
| `created_by` | `str \| None` | 是 | - | 可为 `null` | - | 创建人 |
| `source_channel` | `SourceChannel` | 是 | - | 七种来源渠道 | - | 来源渠道 |
| `project_resolve_mode` | `ProjectResolveMode` | 是 | - | 三种解析方式 | - | 项目解析方式 |
| `status` | `InterviewStatus` | 是 | - | 六种会话状态 | - | 当前状态 |
| `raw_content` | `str` | 是 | - | - | - | 首次原始输入 |
| `request_type` | `RequirementType \| None` | 是 | - | 三种类型或 `null` | - | 当前识别类型 |
| `current_card` | `dict[InterviewFieldName, DifyInterviewField \| None]` | 是 | - | 11 个字段键 | `DifyInterviewField` | Service 从 `structured_data` JSON 解析 |
| `skipped_fields` | `list[InterviewFieldName]` | 是 | - | - | - | Service 从 JSON 解析 |
| `completeness_score` | `int` | 是 | - | - | - | 当前完整度 |
| `round_count` | `int` | 是 | - | - | - | 当前轮数 |
| `consecutive_skip_count` | `int` | 是 | - | - | - | 连续跳过次数 |
| `stop_reason` | `str \| None` | 是 | - | 可为 `null` | - | 停止原因 |
| `summary_title` | `str \| None` | 是 | - | 可为 `null` | - | 摘要标题 |
| `clarified_content` | `str \| None` | 是 | - | 可为 `null` | - | 澄清内容 |
| `requirement_id` | `str \| None` | 是 | - | 可为 `null` | - | 最终需求 ID |
| `current_question` | `DifyInterviewQuestion \| None` | 是 | - | 可为 `null` | `DifyInterviewQuestion` | 从最新 Agent 消息元数据和正文重建 |
| `messages` | `list[InterviewMessageRead]` | 是 | - | - | `InterviewMessageRead` | 全部会话消息 |
| `agent_error_code` | `str \| None` | 是 | - | 可为 `null` | - | 最近 Agent 错误码 |
| `created_time` | `datetime` | 是 | - | - | - | 创建时间 |
| `updated_time` | `datetime` | 是 | - | - | - | 更新时间 |

该 Read Schema 有意不输出部分 ORM 字段：`source_user_id`、`source_message_id`、`entry_key`、`consecutive_agent_failures`、`confirm_idempotency_key`、`agent_error_message`、`prompt_version` 和会话级附件集合。是否需要暴露需由产品/API 契约决定，本文不补全。

## InterviewConfirmResult

- 继承：`ORMModel`
- 类型：Read/Response
- 用途：访谈确认接口的组合结果。

| 字段 | 类型 | 必填 | 默认值 | 限制 | 嵌套 Schema | 说明 |
|---|---|---|---|---|---|---|
| `session` | `InterviewSessionRead` | 是 | - | - | `InterviewSessionRead` | 提交后的会话 |
| `requirement` | `RequirementRead` | 是 | - | - | `RequirementRead` | 新建或已关联的需求 |

## InterviewDraftRead

- 继承：`ORMModel`
- 类型：Read/Response
- 用途：未完成访谈草稿列表。

| 字段 | 类型 | 必填 | 默认值 | 限制 | 嵌套 Schema | 说明 |
|---|---|---|---|---|---|---|
| `id` | `str` | 是 | - | - | - | 会话 ID |
| `project_id` | `str` | 是 | - | - | - | 项目 ID |
| `status` | `InterviewStatus` | 是 | - | - | - | 草稿当前状态 |
| `raw_content` | `str` | 是 | - | - | - | 原始内容 |
| `summary_title` | `str \| None` | 是 | - | 可为 `null` | - | 摘要标题 |
| `round_count` | `int` | 是 | - | - | - | 轮数 |
| `updated_time` | `datetime` | 是 | - | - | - | 最近更新时间 |

## InterviewActionName

- 类型：`TypeAlias` / `Literal`
- 允许值：`skip` / `unknown` / `summarize` / `abandon`。
- 当前扫描未发现 Router 或 Service 引用；各动作 Router 使用独立端点和具体方法。

## Interview Schema 嵌套关系

```text
InterviewConfirmResult Schema
├── session: InterviewSessionRead Schema
│   ├── current_card
│   │   └── 每个非空值: DifyInterviewField Schema
│   ├── current_question: DifyInterviewQuestion Schema | null
│   └── messages: list[InterviewMessageRead Schema]
│       └── attachments: list[InterviewAttachmentRead Schema]
└── requirement: RequirementRead Schema
```

# Service 内部结果对象（非 Pydantic Schema）

## DifyWorkflowResult

- 定义位置：`app/services/dify_service.py`
- 类型：`@dataclass(slots=True)` / Service Result
- 用途：`DifyService.analyze_requirement()` 向 `RequirementService` 返回已校验分析和运行 ID。

| 字段 | 类型 | 必填 | 默认值 | 嵌套对象 | 说明 |
|---|---|---|---|---|---|
| `analysis` | `DifyAnalysisResult` | 是 | - | `DifyAnalysisResult Schema` | 已通过严格校验的分析结果 |
| `workflow_run_id` | `str \| None` | 否 | `None` | - | Dify Workflow Run ID |

## DifyInterviewWorkflowResult

- 定义位置：`app/services/dify_interview_service.py`
- 类型：`@dataclass(slots=True)` / Service Result
- 用途：`DifyInterviewService.run_turn()` 向 `InterviewService` 返回已校验访谈结果、运行 ID 和附件上传映射。

| 字段 | 类型 | 必填 | 默认值 | 嵌套对象 | 说明 |
|---|---|---|---|---|---|
| `interview` | `DifyInterviewResult` | 是 | - | `DifyInterviewResult Schema` | 已通过严格校验的访谈结果 |
| `workflow_run_id` | `str \| None` | 否 | `None` | - | Dify Workflow Run ID |
| `uploaded_file_ids` | `dict[str, str]` | 否 | `{}` | - | `attachment_id -> Dify file_id` |

# Schema Usage

| Schema / 类型 | 主要使用位置 | 数据方向 |
|---|---|---|
| `ApiResponse[T]` | 全部 API Router | Router → Frontend |
| `PageData[T]` | 项目、部门、邀请码、需求列表 Router | Router → Frontend |
| `ProjectCreate` | `ProjectService.create()` | API → Service → Project ORM |
| `ProjectRead` | `ProjectService.create()` / `list()` | Project ORM → Service → API |
| `DepartmentCreate` | `DepartmentService.create()` | API → Service |
| `DepartmentUpdate` | `DepartmentService.update()` | API → Service → Department ORM |
| `DepartmentRead` | `DepartmentService` | Department ORM → Service → API |
| `InvitationCreate` | `InvitationService.create()` | API → Service |
| `InvitationRead` | `InvitationService` | InvitationCode ORM → Service → API |
| `RequirementCreate` | `RequirementService.create_and_analyze()` | API → Service → Requirement ORM |
| `RequirementRead` | requirements Router、`InterviewConfirmResult` | Requirement ORM → Schema → API |
| `BatchAnalyzeRequest` | requirements 批量分析预留 Router | API → Router；未进入 Service |
| `BatchAnalyzeAccepted` | requirements 批量分析预留 Router | Router → API |
| `DifyAnalysisResult` | `DifyService._extract_analysis()` / `analyze_requirement()` | Dify API → DifyService → RequirementService |
| `DifyInterviewResult` | `DifyInterviewService._extract_interview()` / `run_turn()` | Dify API → DifyInterviewService → InterviewService |
| `DifyInterviewField(s)` | Dify 结果、`InterviewService` 字段合并与会话读取 | Dify → Service → JSON 文本 / API |
| `DifyInterviewQuestion` | Dify 结果、`InterviewService` 问题验证/回退、会话读取 | Dify → Service → API |
| `InterviewCreate` | `InterviewService.create()` | API → Service → InterviewSession / Message ORM |
| `InterviewMessageCreate` | `InterviewService.answer()` | API → Service → InterviewMessage ORM |
| `InterviewActionRequest` | `InterviewService.skip_or_unknown()` | API → Service |
| `InterviewSummaryUpdate` | `InterviewService.update_summary()` | API → Service → JSON 文本 |
| `InterviewConfirmRequest` | `InterviewService.confirm()` | API → Service → InterviewSession ORM |
| `InterviewSessionRead` | `InterviewService.to_read()` | ORM / JSON → Service → API |
| `InterviewConfirmResult` | interviews Router | Service 返回的 ORM → 嵌套 Schema → API |
| `InterviewDraftRead` | interviews drafts Router | InterviewSession ORM → Schema → API |
| `InterviewAttachmentRead` | attachment Router、消息嵌套 | InterviewAttachment ORM → Schema → API |
| `DifyWorkflowResult` dataclass | `DifyService` → `RequirementService` | Service → Service |
| `DifyInterviewWorkflowResult` dataclass | `DifyInterviewService` → `InterviewService` | Service → Service |

# Review Notes

- `InterviewActionName` TypeAlias 已定义，但当前源码未发现使用位置。
- `BatchAnalyzeRequest` / `BatchAnalyzeAccepted` 已接入 Router，但接口明确为预留：只返回任务信息，不执行 Service 或后台任务。
- 多个 Read Schema 的字段类型允许 `None`，但因为没有默认值，它们仍是响应构造时的必填键；Review 时不要把“nullable”误读成“字段可缺失”。
- `DepartmentRead.user_count` 有默认值 `0`，当前 `DepartmentService` 只补充 `project_count`，未统计用户数。
- `InvitationRead.used_time` 对应 ORM 字段，但当前 Service 未设置邀请码为 `USED`，也未赋使用时间。
- `InterviewSessionRead` 是对 ORM 的选择性投影，不是一比一镜像；上述未输出 ORM 字段目前只能在 ORM/数据库层看到。
- `DifyWorkflowResult` 与 `DifyInterviewWorkflowResult` 名称像 Schema，但实际是 Service 文件内的 dataclass；其嵌套的 `DifyAnalysisResult` / `DifyInterviewResult` 才是 Pydantic Schema。
