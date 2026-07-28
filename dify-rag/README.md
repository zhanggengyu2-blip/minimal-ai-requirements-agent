# Dify 需求分析知识库与固定输出

## 文件用途

- `01-需求优先级判定标准-P0-P3.md`：导入 Dify 知识库。
- `02-伪需求识别判定标准.md`：导入 Dify 知识库。
- `03-需求标准化整理规范.md`：导入 Dify 知识库。
- `04-Dify固定输出-JSON-Schema.json`：配置到 Dify 的结构化输出节点或 LLM JSON Schema。

## 数据库字段对应关系

Schema 的 10 个字段与 `requirement` 主表的 10 个 AI 分析字段完全同名：

| JSON 字段 | 数据库字段 |
| --- | --- |
| standard_content | requirement.standard_content |
| business_goal | requirement.business_goal |
| type | requirement.type |
| priority | requirement.priority |
| is_fake | requirement.is_fake |
| fake_reason | requirement.fake_reason |
| is_duplicate | requirement.is_duplicate |
| related_id | requirement.related_id |
| reference_rule | requirement.reference_rule |
| analysis_summary | requirement.analysis_summary |

以下字段不应由 Dify 输出：`id`、`raw_content`、`manual_modify`、`created_time`、`updated_time`。它们分别由后端生成、保存或维护，避免 AI 覆盖可信业务数据。

## Dify 输出指令

可将下面内容放入系统提示词末尾：

> 仅输出符合指定 JSON Schema 的 JSON 对象，不要输出 Markdown、代码围栏、解释文字或 Schema 之外的字段。所有 required 字段必须存在。布尔字段必须使用 true/false。没有相似需求时 related_id 输出空字符串。字段名不得翻译或改写。

## 后端校验建议

- 使用严格模型校验，拒绝未知字段。
- 枚举值严格区分大小写。
- `is_duplicate=false` 时，后端额外校验 `related_id==""`。
- `is_duplicate=true` 时，后端额外校验 `related_id` 非空且确实存在。
- `analysis_summary` 用于页面展示，建议限制在 80 至 200 个汉字，不展示内部推理过程。
- 校验失败时不覆盖旧分析结果，并记录失败原因以供重试。
