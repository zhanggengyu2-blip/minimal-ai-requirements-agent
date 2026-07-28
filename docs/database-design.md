# SQLite 数据表设计

## `project` 项目表

| 字段 | 类型 | 约束/说明 |
| --- | --- | --- |
| `id` | VARCHAR(32) | 主键，UUID hex |
| `name` | VARCHAR(100) | 非空、唯一、索引 |
| `description` | TEXT | 项目简介 |
| `project_context` | TEXT | 非空，传给 Dify 的完整项目上下文 |
| `department_id` | VARCHAR(32) | 可空，预留部门关联 |
| `created_by` | VARCHAR(32) | 可空，预留用户关联 |
| `status` | VARCHAR | `ACTIVE/ARCHIVED` |
| `created_time` | DATETIME | UTC 创建时间 |
| `updated_time` | DATETIME | UTC 更新时间 |

## `requirement` 需求表

| 字段 | 类型 | 约束/说明 |
| --- | --- | --- |
| `id` | VARCHAR(32) | 主键，UUID hex |
| `project_id` | VARCHAR(32) | 非空，外键关联 `project.id` |
| `raw_content` | TEXT | 非空，用户原始输入 |
| `standard_content` | TEXT | Dify 字段 1 |
| `business_goal` | TEXT | Dify 字段 2 |
| `type` | VARCHAR | Dify 字段 3：`NEW_FEATURE/BUG/OPTIMIZATION` |
| `priority` | VARCHAR | Dify 字段 4：`P0/P1/P2/P3` |
| `is_fake` | BOOLEAN | Dify 字段 5 |
| `fake_reason` | TEXT | Dify 字段 6 |
| `is_duplicate` | BOOLEAN | Dify 字段 7 |
| `related_id` | VARCHAR(32) | Dify 字段 8，无重复固定为空字符串 |
| `reference_rule` | TEXT | Dify 字段 9，规则溯源 |
| `analysis_summary` | TEXT | Dify 字段 10，页面 AI 总结 |
| `analysis_status` | VARCHAR | `PENDING/ANALYZING/ANALYZED/FAILED` |
| `analysis_error_code` | VARCHAR(50) | 最近一次分析错误码 |
| `analysis_error_message` | TEXT | 可安全展示的失败原因 |
| `dify_workflow_run_id` | VARCHAR(100) | Dify 运行 ID，便于排障 |
| `manual_modify` | BOOLEAN | 是否人工修正，当前预留 |
| `created_by` | VARCHAR(32) | 可空，预留用户关联 |
| `created_time` | DATETIME | UTC 创建时间 |
| `updated_time` | DATETIME | UTC 更新时间 |

AI 字段允许为 NULL，因为原始需求必须先保存，AI 调用可能处于处理中或失败。只有 `DifyAnalysisResult` 完整校验通过后，10 个字段才会在同一事务中更新。

索引覆盖项目时间倒序、项目优先级、分析状态、类型、真伪和重复状态，满足项目列表与需求池组合筛选的 MVP 查询模式。

