# 极简 AI 团队需求管理智能体：中文接口文档与 Apifox 调试指南

文档版本：V2.0（合并保留 V1.1 测试内容）
版本标识规则：接口标题中的 `【V1.1】` 表示原有能力，`【V2.0】` 表示本次新增的对话式需求访谈能力。
本地后端默认地址：`http://127.0.0.1:8000`
接口统一前缀：`/api/v1`
数据格式：JSON
当前鉴权：未实现，测试接口不需要登录 Token。

---

## 一、开始前检查

必须先启动 FastAPI：

```bash
cd '<仓库目录>/backend/v2.0'
source .venv/bin/activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

浏览器访问：

```text
http://127.0.0.1:8000/api/v1/health
```

正常后再打开 Apifox。

---

## 二、接口总览

下表顺序和文件夹名称与 Apifox 导入后的左侧列表一致。测试文档中的“Apifox 位置”也使用同一名称，方便直接查找。

| Apifox 文件夹    | 接口名称                          | 方法  | 路径                                                  |
| ---------------- | --------------------------------- | ----- | ----------------------------------------------------- |
| `health`       | `【V1.1】 健康检查`             | GET   | `/api/v1/health`                                    |
| `projects`     | `【V1.1】 创建项目`             | POST  | `/api/v1/projects`                                  |
| `projects`     | `【V1.1】 查询项目列表`         | GET   | `/api/v1/projects`                                  |
| `requirements` | `【V1.1】 直接创建并分析需求`   | POST  | `/api/v1/requirements`                              |
| `requirements` | `【V1.1】 查询需求列表`         | GET   | `/api/v1/requirements`                              |
| `requirements` | `【V1.1】 查询需求详情`         | GET   | `/api/v1/requirements/{requirement_id}`             |
| `requirements` | `【V1.1】 批量分析需求（预留）` | POST  | `/api/v1/requirements/batch-analyze`                |
| `requirements` | `【V2.0】 查询需求关联访谈`     | GET   | `/api/v1/requirements/{requirement_id}/interview`   |
| `interviews`   | `【V2.0】 创建访谈会话`         | POST  | `/api/v1/interviews`                                |
| `interviews`   | `【V2.0】 查询未完成访谈`       | GET   | `/api/v1/interviews/drafts`                         |
| `interviews`   | `【V2.0】 查询访谈详情`         | GET   | `/api/v1/interviews/{session_id}`                   |
| `interviews`   | `【V2.0】 回答访谈问题`         | POST  | `/api/v1/interviews/{session_id}/messages`          |
| `interviews`   | `【V2.0】 跳过当前问题`         | POST  | `/api/v1/interviews/{session_id}/actions/skip`      |
| `interviews`   | `【V2.0】 标记为不清楚`         | POST  | `/api/v1/interviews/{session_id}/actions/unknown`   |
| `interviews`   | `【V2.0】 按当前信息整理`       | POST  | `/api/v1/interviews/{session_id}/actions/summarize` |
| `interviews`   | `【V2.0】 编辑需求总结`         | PATCH | `/api/v1/interviews/{session_id}/summary`           |
| `interviews`   | `【V2.0】 确认并创建需求`       | POST  | `/api/v1/interviews/{session_id}/confirm`           |
| `interviews`   | `【V2.0】 放弃访谈`             | POST  | `/api/v1/interviews/{session_id}/abandon`           |
| `departments`  | `【V1.1】 创建部门`             | POST  | `/api/v1/departments`                               |
| `departments`  | `【V1.1】 查询部门列表`         | GET   | `/api/v1/departments`                               |
| `departments`  | `【V1.1】 更新部门`             | PATCH | `/api/v1/departments/{department_id}`               |
| `invitations`  | `【V1.1】 生成邀请码`           | POST  | `/api/v1/invitations`                               |
| `invitations`  | `【V1.1】 查询邀请码列表`       | GET   | `/api/v1/invitations`                               |
| `invitations`  | `【V1.1】 停用邀请码`           | POST  | `/api/v1/invitations/{invitation_id}/disable`       |

辅助地址：

| 地址              | 作用                         |
| ----------------- | ---------------------------- |
| `/docs`         | Swagger 可视化接口文档       |
| `/openapi.json` | OpenAPI JSON，供 Apifox 导入 |

离线导入文件：

```text
docs/openapi-v2.0-apifox.json
```

---

## 三、统一响应格式

### 1. 正常响应

```json
{
  "code": "OK",
  "message": "success",
  "data": {},
  "request_id": "6e761c15e19f442c891f9005345ade57"
}
```

| 字段           | 类型         | 作用            |
| -------------- | ------------ | --------------- |
| `code`       | String       | 业务结果码      |
| `message`    | String       | 结果说明        |
| `data`       | Object/Array | 实际业务数据    |
| `request_id` | String/Null  | 本次请求追踪 ID |

### 2. 参数校验失败

```json
{
  "code": "VALIDATION_ERROR",
  "message": "请求参数校验失败",
  "data": null,
  "details": [
    {
      "type": "string_too_short",
      "loc": ["body", "project_id"],
      "msg": "String should have at least 32 characters",
      "input": "bad"
    }
  ],
  "request_id": "6e761c15e19f442c891f9005345ade57"
}
```

### 3. 业务异常

```json
{
  "code": "NOT_FOUND",
  "message": "项目不存在",
  "data": null,
  "details": null,
  "request_id": "6e761c15e19f442c891f9005345ade57"
}
```

### 4. HTTP 状态码与业务码

| HTTP 状态 | 常见业务码             | 含义                                                                                 |
| --------- | ---------------------- | ------------------------------------------------------------------------------------ |
| 200       | `OK`                 | 查询成功                                                                             |
| 201       | `OK`                 | 数据创建成功                                                                         |
| 201       | `AI_ANALYSIS_FAILED` | 原始需求创建成功，但 AI 分析失败                                                     |
| 202       | `ACCEPTED`           | 批量接口已接受预留请求                                                               |
| 404       | `NOT_FOUND`          | 项目或需求不存在                                                                     |
| 409       | `CONFLICT`           | 项目名称冲突                                                                         |
| 422       | `VALIDATION_ERROR`   | 请求字段不符合规则                                                                   |
| 502       | `DIFY_*`             | 直接向上抛出的 Dify 网关异常；当前创建需求流程通常会转为 201 +`AI_ANALYSIS_FAILED` |

重要：

> HTTP 201 只说明需求原始数据已经创建成功。判断 AI 是否成功，还要检查 `code` 和 `data.analysis_status`。

---

## 四、固定枚举值

### 1. 项目状态

```text
ACTIVE
ARCHIVED
```

### 2. AI 分析状态

```text
PENDING
ANALYZING
ANALYZED
FAILED
```

### 3. 需求类型

```text
NEW_FEATURE
BUG
OPTIMIZATION
```

### 4. 需求优先级

```text
P0
P1
P2
P3
```

---

# 接口一：健康检查

## 五、GET `/api/v1/health`

### 作用

检查 FastAPI 是否已经启动。

它不检查：

- Dify 是否可用；
- API Key 是否正确；
- SQLite 是否能正常写入。

### 请求地址

```text
http://127.0.0.1:8000/api/v1/health
```

### Headers

无特殊 Header。

### Query 参数

无。

### JSON 请求体

无。GET 接口不要填写 JSON Body。

### Apifox 配置

```text
方法：GET
Path：/api/v1/health
```

### 成功响应

HTTP 200：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "status": "ok"
  },
  "request_id": "6e761c15e19f442c891f9005345ade57"
}
```

### 建议断言

| 位置              | 规则 | 期望值 |
| ----------------- | ---- | ------ |
| HTTP 状态码       | 等于 | 200    |
| `$.code`        | 等于 | `OK` |
| `$.data.status` | 等于 | `ok` |

---

# 接口二：创建项目

## 六、POST `/api/v1/projects`

### 作用

创建一个新的需求管理项目。创建需求之前必须先有项目。

### Headers

```text
Content-Type: application/json
```

Apifox 选择 JSON Body 后通常会自动添加。

### 请求字段

| 字段                | 类型        | 必填 | 限制                                     | 说明                   |
| ------------------- | ----------- | ---- | ---------------------------------------- | ---------------------- |
| `name`            | String      | 是   | 1～100，不能全为空格，不能与已有项目重名 | 项目名称               |
| `description`     | String      | 否   | 最长 2000                                | 页面展示用简介         |
| `project_context` | String      | 是   | 1～10000，不能全为空格                   | 给 Dify 使用的项目背景 |
| `department_id`   | String/Null | 否   | 最长 32                                  | 预留部门 ID            |
| `created_by`      | String/Null | 否   | 最长 32                                  | 预留创建人 ID          |

### 可直接复制的标准 JSON

每次重复测试时请修改项目名称，避免 409 冲突。

```json
{
  "name": "Apifox本地测试项目-20260726",
  "description": "用于验证极简AI团队需求管理智能体的本地接口。",
  "project_context": "本项目面向小型研发团队，用于统一收集、AI分析和管理产品需求。当前处于MVP测试阶段，核心流程包括创建项目、提交需求、AI标准化、优先级判断、伪需求识别和项目内需求查重。"
}
```

### 成功响应

HTTP 201：

```json
{
  "code": "OK",
  "message": "项目创建成功",
  "data": {
    "id": "98ddc1e877cc4a91b8dfd6e1cac76b52",
    "name": "Apifox本地测试项目-20260726",
    "description": "用于验证极简AI团队需求管理智能体的本地接口。",
    "project_context": "本项目面向小型研发团队，用于统一收集、AI分析和管理产品需求。当前处于MVP测试阶段，核心流程包括创建项目、提交需求、AI标准化、优先级判断、伪需求识别和项目内需求查重。",
    "department_id": null,
    "created_by": null,
    "status": "ACTIVE",
    "requirement_count": 0,
    "created_time": "2026-07-26T10:30:00",
    "updated_time": "2026-07-26T10:30:00"
  },
  "request_id": "6e761c15e19f442c891f9005345ade57"
}
```

### Apifox 后置操作（需要配置）

位置：本接口的“后置操作” → “自定义脚本”。

作用：创建项目成功后，把返回的项目 ID 保存为当前环境的 `project_id`，供创建需求和创建访谈使用。

```javascript
const body = pm.response.json();

if (body && body.code === "OK" && body.data && body.data.id) {
  pm.environment.set("project_id", body.data.id);
}
```

执行成功后，在 Apifox 当前环境中检查 `project_id` 已有 32 位值。后续请求使用：

```text
{{project_id}}
```

### 异常用例 A：名称重复

再次发送完全相同的 JSON。

预期 HTTP 409：

```json
{
  "code": "CONFLICT",
  "message": "项目名称已存在",
  "data": null,
  "details": null,
  "request_id": "6e761c15e19f442c891f9005345ade57"
}
```

### 异常用例 B：项目名称只有空格

```json
{
  "name": "   ",
  "description": "错误用例",
  "project_context": "用于测试空白名称校验。"
}
```

预期：HTTP 422，`code=VALIDATION_ERROR`。

### 异常用例 C：缺少项目		上下文

```json
{
  "name": "缺少上下文测试项目",
  "description": "错误用例"
}
```

预期：HTTP 422。

---

# 接口三：查询项目列表

## 七、GET `/api/v1/projects`

### 作用

分页查询项目，并返回每个项目的需求数量。

### JSON 请求体

无。GET 接口使用 Query 参数。

### Query 参数

| 参数          | 类型    | 必填 | 默认值 | 限制                |
| ------------- | ------- | ---- | ------ | ------------------- |
| `page`      | Integer | 否   | 1      | 最小 1              |
| `page_size` | Integer | 否   | 20     | 1～100              |
| `status`    | String  | 否   | 空     | `ACTIVE/ARCHIVED` |

### Apifox 标准参数

```text
方法：GET
Path：/api/v1/projects
```

Query：

```text
page=1
page_size=20
status=ACTIVE
```

完整测试地址：

```text
http://127.0.0.1:8000/api/v1/projects?page=1&page_size=20&status=ACTIVE
```

### 成功响应

HTTP 200：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "items": [
      {
        "id": "98ddc1e877cc4a91b8dfd6e1cac76b52",
        "name": "Apifox本地测试项目-20260726",
        "description": "用于验证极简AI团队需求管理智能体的本地接口。",
        "project_context": "本项目面向小型研发团队，用于统一收集、AI分析和管理产品需求。",
        "department_id": null,
        "created_by": null,
        "status": "ACTIVE",
        "requirement_count": 0,
        "created_time": "2026-07-26T10:30:00",
        "updated_time": "2026-07-26T10:30:00"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  },
  "request_id": "6e761c15e19f442c891f9005345ade57"
}
```

### 异常用例：页码为 0

```text
GET /api/v1/projects?page=0&page_size=20
```

预期：HTTP 422。

### 异常用例：非法状态

```text
GET /api/v1/projects?status=DELETED
```

预期：HTTP 422。

---

# 接口四：创建需求并进行 AI 分析

## 八、POST `/api/v1/requirements`

### 作用

完整执行：

1. 验证项目存在；
2. 保存用户原始需求；
3. 查询当前项目历史候选需求；
4. 调用 Dify Workflow；
5. 校验 Dify 固定 10 字段；
6. 成功时保存分析结果；
7. 失败时保留原始需求并记录错误。

### 请求字段

| 字段            | 类型        | 必填 | 限制                   | 说明          |
| --------------- | ----------- | ---- | ---------------------- | ------------- |
| `project_id`  | String      | 是   | 固定 32 字符           | 所属项目 ID   |
| `raw_content` | String      | 是   | 1～10000，不能全为空格 | 用户原始需求  |
| `created_by`  | String/Null | 否   | 最长 32                | 预留提交人 ID |

### 可直接复制的 Apifox JSON

前提：已把创建项目响应中的 ID 提取到 `project_id` 环境变量。

```json
{
  "project_id": "{{project_id}}",
  "raw_content": "希望客服工作台支持批量导入客户信息，导入时自动识别重复数据并提示，减少客服逐条录入和人工核对的时间。"
}
```

### AI 成功响应

HTTP 201：

```json
{
  "code": "OK",
  "message": "需求创建及 AI 分析完成",
  "data": {
    "id": "8404aed28c1b44b0b8746166790da3e8",
    "project_id": "98ddc1e877cc4a91b8dfd6e1cac76b52",
    "raw_content": "希望客服工作台支持批量导入客户信息，导入时自动识别重复数据并提示，减少客服逐条录入和人工核对的时间。",
    "standard_content": "面向客服人员，支持批量导入客户信息，并在导入过程中自动识别重复数据并进行提示。",
    "business_goal": "减少客服人员逐条录入与核对客户信息的时间，降低重复数据产生概率。",
    "type": "NEW_FEATURE",
    "priority": "P2",
    "is_fake": false,
    "fake_reason": "需求包含明确用户、使用场景和效率价值，判定为真实需求。",
    "is_duplicate": false,
    "related_id": "",
    "reference_rule": "TYPE-NEW；PRI-P2；FAKE-NOT",
    "analysis_summary": "该需求能够降低客服批量录入成本并减少重复数据，属于新增功能、P2优先级，当前未发现完整重复需求。",
    "analysis_status": "ANALYZED",
    "analysis_error_code": null,
    "analysis_error_message": null,
    "dify_workflow_run_id": "dify-run-id",
    "manual_modify": false,
    "created_by": null,
    "created_time": "2026-07-26T10:35:00",
    "updated_time": "2026-07-26T10:35:08"
  },
  "request_id": "6e761c15e19f442c891f9005345ade57"
}
```

实际 AI 文本、类型和优先级会根据项目上下文与 Dify 分析变化，不要求与示例文字完全一致。

### Apifox 后置操作（需要配置）

位置：本接口的“后置操作” → “自定义脚本”。

作用：无论 AI 分析成功还是需求已保存但 AI 分析失败，只要响应中已生成需求 ID，就保存为 `requirement_id`。

```javascript
const body = pm.response.json();

if (
  body &&
  (body.code === "OK" || body.code === "AI_ANALYSIS_FAILED") &&
  body.data &&
  body.data.id
) {
  pm.environment.set("requirement_id", body.data.id);
}
```

执行成功后，后续“查询需求详情”等接口可使用 `{{requirement_id}}`。

### AI 失败但需求保存成功

如果 API Key 错误、Dify 不可连接、超时或输出非法，通常仍返回 HTTP 201：

```json
{
  "code": "AI_ANALYSIS_FAILED",
  "message": "需求已保存，但 AI 分析失败，可稍后重新分析",
  "data": {
    "id": "8404aed28c1b44b0b8746166790da3e8",
    "project_id": "98ddc1e877cc4a91b8dfd6e1cac76b52",
    "raw_content": "希望客服工作台支持批量导入客户信息。",
    "standard_content": null,
    "business_goal": null,
    "type": null,
    "priority": null,
    "is_fake": null,
    "fake_reason": null,
    "is_duplicate": null,
    "related_id": "",
    "reference_rule": null,
    "analysis_summary": null,
    "analysis_status": "FAILED",
    "analysis_error_code": "DIFY_TIMEOUT",
    "analysis_error_message": "AI 分析超时，请稍后重试",
    "dify_workflow_run_id": null,
    "manual_modify": false,
    "created_by": null,
    "created_time": "2026-07-26T10:35:00",
    "updated_time": "2026-07-26T10:35:08"
  },
  "request_id": "6e761c15e19f442c891f9005345ade57"
}
```

常见 `analysis_error_code`：

```text
DIFY_NOT_CONFIGURED
DIFY_TIMEOUT
DIFY_HTTP_ERROR
DIFY_CONNECTION_ERROR
DIFY_WORKFLOW_FAILED
DIFY_OUTPUT_INVALID
```

### 异常用例 A：项目不存在

```json
{
  "project_id": "00000000000000000000000000000000",
  "raw_content": "这是用于验证项目不存在的测试需求。"
}
```

预期 HTTP 404：

```json
{
  "code": "NOT_FOUND",
  "message": "项目不存在",
  "data": null,
  "details": null,
  "request_id": "6e761c15e19f442c891f9005345ade57"
}
```

### 异常用例 B：项目 ID 长度错误

```json
{
  "project_id": "bad",
  "raw_content": "这是错误项目ID测试。"
}
```

预期：HTTP 422。

### 异常用例 C：需求只有空格

```json
{
  "project_id": "{{project_id}}",
  "raw_content": "   "
}
```

预期：HTTP 422。

### 异常用例 D：验证错误 Dify Key

该测试需要修改后端 `.env`，不是修改 Apifox 环境：

1. 把 `.env` 的 `DIFY_API_KEY` 临时改成错误值；
2. 重启 FastAPI；
3. 使用合法项目 ID 创建需求；
4. 预期 HTTP 201，但 `code=AI_ANALYSIS_FAILED`；
5. 检查 `analysis_error_code`；
6. 恢复正确 Key；
7. 再次重启 FastAPI。

每次测试都会在 SQLite 中留下原始需求记录。

---

# 接口五：查询需求列表

## 九、GET `/api/v1/requirements`

### 作用

分页查询需求，支持项目、关键词、优先级、类型、分析状态和真伪状态组合筛选。

### JSON 请求体

无。GET 接口使用 Query 参数。

### Query 参数

| 参数                | 类型    | 必填 | 默认值 | 说明                                  |
| ------------------- | ------- | ---- | ------ | ------------------------------------- |
| `project_id`      | String  | 否   | 空     | 32 位项目 ID                          |
| `page`            | Integer | 否   | 1      | 页码，最小 1                          |
| `page_size`       | Integer | 否   | 20     | 每页 1～100                           |
| `keyword`         | String  | 否   | 空     | 最长 100，搜索原文/标准内容/业务目标  |
| `priority`        | String  | 否   | 空     | P0～P3                                |
| `type`            | String  | 否   | 空     | `NEW_FEATURE/BUG/OPTIMIZATION`      |
| `analysis_status` | String  | 否   | 空     | `PENDING/ANALYZING/ANALYZED/FAILED` |
| `is_fake`         | Boolean | 否   | 空     | `true/false`                        |

### Apifox 基础测试参数

```text
方法：GET
Path：/api/v1/requirements
```

Query：

```text
project_id={{project_id}}
page=1
page_size=20
```

### 组合筛选示例

```text
GET /api/v1/requirements?project_id={{project_id}}&priority=P2&type=NEW_FEATURE&analysis_status=ANALYZED&is_fake=false&page=1&page_size=20
```

关键词示例：

```text
GET /api/v1/requirements?project_id={{project_id}}&keyword=批量导入&page=1&page_size=20
```

### 成功响应

HTTP 200：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "items": [
      {
        "id": "8404aed28c1b44b0b8746166790da3e8",
        "project_id": "98ddc1e877cc4a91b8dfd6e1cac76b52",
        "raw_content": "希望客服工作台支持批量导入客户信息。",
        "standard_content": "面向客服人员，支持批量导入客户信息。",
        "business_goal": "减少人工录入成本。",
        "type": "NEW_FEATURE",
        "priority": "P2",
        "is_fake": false,
        "fake_reason": "存在明确场景和业务价值。",
        "is_duplicate": false,
        "related_id": "",
        "reference_rule": "TYPE-NEW；PRI-P2；FAKE-NOT",
        "analysis_summary": "该需求可降低人工录入成本。",
        "analysis_status": "ANALYZED",
        "analysis_error_code": null,
        "analysis_error_message": null,
        "dify_workflow_run_id": "dify-run-id",
        "manual_modify": false,
        "created_by": null,
        "created_time": "2026-07-26T10:35:00",
        "updated_time": "2026-07-26T10:35:08"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  },
  "request_id": "6e761c15e19f442c891f9005345ade57"
}
```

### 空列表响应

没有匹配数据不是错误：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "items": [],
    "total": 0,
    "page": 1,
    "page_size": 20
  },
  "request_id": "6e761c15e19f442c891f9005345ade57"
}
```

### 异常用例 A：非法优先级

```text
GET /api/v1/requirements?priority=P9
```

预期：HTTP 422。

### 异常用例 B：每页超过 100

```text
GET /api/v1/requirements?page_size=101
```

预期：HTTP 422。

### 异常用例 C：项目 ID 长度不足

```text
GET /api/v1/requirements?project_id=bad
```

预期：HTTP 422。

注意：当前列表接口如果传入一个格式正确但不存在的 32 位项目 ID，会返回空列表，不会返回 404。

---

# 接口六：查询需求详情

## 十、GET `/api/v1/requirements/{requirement_id}`

### 作用

根据需求 ID 返回完整需求信息和 AI 分析结果。

### JSON 请求体

无。

### Path 参数

| 参数               | 类型   | 说明                        |
| ------------------ | ------ | --------------------------- |
| `requirement_id` | String | 需求 ID，正常情况下为 32 位 |

### Apifox 配置

```text
方法：GET
Path：/api/v1/requirements/{requirement_id}
Path 参数 requirement_id：{{requirement_id}}
```

变量 `requirement_id` 来自创建需求接口的后置提取。

### 成功响应

HTTP 200，`data` 字段结构与创建需求成功响应中的 `data` 相同：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "id": "8404aed28c1b44b0b8746166790da3e8",
    "project_id": "98ddc1e877cc4a91b8dfd6e1cac76b52",
    "raw_content": "希望客服工作台支持批量导入客户信息。",
    "standard_content": "面向客服人员，支持批量导入客户信息。",
    "business_goal": "减少人工录入成本。",
    "type": "NEW_FEATURE",
    "priority": "P2",
    "is_fake": false,
    "fake_reason": "存在明确场景和业务价值。",
    "is_duplicate": false,
    "related_id": "",
    "reference_rule": "TYPE-NEW；PRI-P2；FAKE-NOT",
    "analysis_summary": "该需求可降低人工录入成本。",
    "analysis_status": "ANALYZED",
    "analysis_error_code": null,
    "analysis_error_message": null,
    "dify_workflow_run_id": "dify-run-id",
    "manual_modify": false,
    "created_by": null,
    "created_time": "2026-07-26T10:35:00",
    "updated_time": "2026-07-26T10:35:08"
  },
  "request_id": "6e761c15e19f442c891f9005345ade57"
}
```

### 异常用例：需求不存在

```text
GET /api/v1/requirements/00000000000000000000000000000000
```

预期 HTTP 404：

```json
{
  "code": "NOT_FOUND",
  "message": "需求不存在",
  "data": null,
  "details": null,
  "request_id": "6e761c15e19f442c891f9005345ade57"
}
```

---

# 接口七：批量 AI 分析预留

## 十一、POST `/api/v1/requirements/batch-analyze`

### 当前状态

该接口目前只验证请求并返回一个临时任务 ID。

它不会：

- 检查需求是否存在；
- 调用 Dify；
- 创建数据库任务；
- 更新需求；
- 提供真实进度。

因此只能用于验证“未来接口请求格式”，不能用于实际批量分析。

### 请求字段

| 字段                | 类型        | 必填 | 限制                              |
| ------------------- | ----------- | ---- | --------------------------------- |
| `requirement_ids` | String 数组 | 是   | 1～50 个；不能重复；每个 ID 32 位 |

### 可直接复制的 Apifox JSON

```json
{
  "requirement_ids": [
    "{{requirement_id}}"
  ]
}
```

### 当前响应

HTTP 202：

```json
{
  "code": "ACCEPTED",
  "message": "批量 AI 分析接口已预留",
  "data": {
    "task_id": "47db8d215494460c8df883f3628b78ef",
    "total": 1,
    "status": "RESERVED",
    "message": "批量分析接口已预留，异步任务调度将在下一阶段实现"
  },
  "request_id": "6e761c15e19f442c891f9005345ade57"
}
```

不要把 `ACCEPTED/RESERVED` 理解为 AI 分析已经执行。

### 异常用例 A：空数组

```json
{
  "requirement_ids": []
}
```

预期：HTTP 422。

### 异常用例 B：ID 重复

```json
{
  "requirement_ids": [
    "{{requirement_id}}",
    "{{requirement_id}}"
  ]
}
```

预期：HTTP 422。

### 异常用例 C：ID 长度错误

```json
{
  "requirement_ids": [
    "bad"
  ]
}
```

预期：HTTP 422。

---

# Apifox 配置与调试

## 十二、方式一：通过 OpenAPI 自动导入

推荐使用这种方式，避免手工创建 24 个接口。V2.0 优先使用已经补充中文名称和版本标识的离线文件：

```text
docs/openapi-v2.0-apifox.json
```

### 第 1 步：先启动 FastAPI

确认浏览器可以访问：

```text
http://127.0.0.1:8000/openapi.json
```

### 第 2 步：导入

Apifox 中可以：

1. 新建 HTTP 项目时选择导入；
2. 或进入已有项目的“项目设置 → 导入数据”；
3. 选择 OpenAPI/Swagger；
4. 选择文件导入，并上传 `docs/openapi-v2.0-apifox.json`；
5. 如果希望直接同步正在运行的后端，也可以选择 URL 导入并输入：

```text
http://127.0.0.1:8000/openapi.json
```

6. 预览并确认导入。

如果 URL 导入失败：

1. 先在浏览器打开该 URL；
2. 将页面内容保存为 `openapi.json`；
3. 在 Apifox 中改用文件导入。

### 第 3 步：代码接口更新后重新导入

后端增加或修改接口后，可以再次从同一个 OpenAPI URL 导入。导入前注意检查 Apifox 提示的覆盖和冲突规则，避免覆盖手工维护的用例。

---

## 十三、配置“本地 FastAPI”环境

Apifox 官方推荐把服务器地址放在环境的“前置 URL（Base URL）”，接口本身只保留 `/api/v1/...` Path。

### 第 1 步：打开环境管理

在 Apifox 右上角打开“环境管理”。

### 第 2 步：新建环境

```text
环境名称：本地 FastAPI
前置 URL：http://127.0.0.1:8000
```

如果后端改用 8001，前置 URL 同步改为：

```text
http://127.0.0.1:8001
```

### 第 3 步：添加环境变量

| 变量名             | 本地值                               | 作用                |
| ------------------ | ------------------------------------ | ------------------- |
| `project_id`     | 先留空                               | 保存创建项目后的 ID |
| `requirement_id` | 先留空                               | 保存创建需求后的 ID |
| `not_found_id`   | `00000000000000000000000000000000` | 404 异常测试        |

保存并把“本地 FastAPI”切换为当前环境。

Apifox 客户端运行请求时使用变量的本地值。敏感内容不应填写为团队共享的远程值。

---

## 十四、配置接口间变量传递

### 1. 创建项目后提取 `project_id`

打开“创建项目”接口：

1. 进入运行/请求页面；
2. 找到“后置操作”；
3. 添加“提取变量”；
4. 来源选择响应 JSON；
5. JSONPath 填：

```text
$.data.id
```

6. 变量名称填：

```text
project_id
```

7. 保存到“本地 FastAPI”环境。

### 2. 创建需求时引用

请求 JSON：

```json
{
  "project_id": "{{project_id}}",
  "raw_content": "希望支持批量导入客户需求。"
}
```

发送前可以把鼠标移到变量上检查实际值。

### 3. 创建需求后提取 `requirement_id`

同样添加后置提取：

```text
JSONPath：$.data.id
变量名：requirement_id
```

### 4. 详情接口引用

在 Path 参数 `requirement_id` 的值中填写：

```text
{{requirement_id}}
```

---

## 十五、推荐的 Apifox 正常测试顺序

### 用例 1：后端健康

```text
GET /api/v1/health
```

预期：200、`code=OK`。

### 用例 2：创建项目

```text
POST /api/v1/projects
```

预期：

- HTTP 201；
- `code=OK`；
- 自动提取 `project_id`。

### 用例 3：查询项目列表

```text
GET /api/v1/projects?page=1&page_size=20
```

预期：

- HTTP 200；
- `total >= 1`；
- 能看到刚创建项目。

### 用例 4：创建并分析需求

```text
POST /api/v1/requirements
```

预期：

- HTTP 201；
- Dify 正常时 `code=OK`；
- `analysis_status=ANALYZED`；
- 10 个 AI 字段完整；
- 自动提取 `requirement_id`。

### 用例 5：查询需求列表

```text
GET /api/v1/requirements?project_id={{project_id}}&page=1&page_size=20
```

预期：能看到刚创建需求。

### 用例 6：查询需求详情

```text
GET /api/v1/requirements/{{requirement_id}}
```

预期：ID、原始内容与创建响应一致。

### 用例 7：批量接口格式

```text
POST /api/v1/requirements/batch-analyze
```

预期：HTTP 202、`status=RESERVED`。不验证真实 AI 执行。

---

## 十六、推荐的 Apifox 异常测试

| 用例          | 操作                              | 预期                                |
| ------------- | --------------------------------- | ----------------------------------- |
| 项目名称重复  | 连续两次创建同名项目              | HTTP 409、`CONFLICT`              |
| 项目名称空白  | `name="   "`                    | HTTP 422                            |
| 项目不存在    | 创建需求使用`{{not_found_id}}`  | HTTP 404、`NOT_FOUND`             |
| 需求内容空白  | `raw_content="   "`             | HTTP 422                            |
| 非法优先级    | 列表传`priority=P9`             | HTTP 422                            |
| 不存在需求    | 详情 ID 使用`{{not_found_id}}`  | HTTP 404                            |
| 批量空数组    | `requirement_ids=[]`            | HTTP 422                            |
| 批量重复 ID   | 数组放两个相同 ID                 | HTTP 422                            |
| Dify 密钥错误 | 修改后端`.env` 并重启后创建需求 | HTTP 201、`AI_ANALYSIS_FAILED`    |
| Dify 停止     | 停止 Dify 容器后创建需求          | HTTP 201、`DIFY_CONNECTION_ERROR` |

异常测试后记得：

- 恢复正确 Dify Key；
- 启动 Dify；
- 重启 FastAPI；
- 重新执行健康和正常创建需求测试。

---

## 十七、Apifox 断言建议

在接口“后置操作”中添加断言。

### 通用查询成功断言

| 目标             | 规则 | 值     |
| ---------------- | ---- | ------ |
| HTTP 状态码      | 等于 | 200    |
| `$.code`       | 等于 | `OK` |
| `$.request_id` | 存在 | —     |

### 创建项目断言

| 目标              | 规则 | 值         |
| ----------------- | ---- | ---------- |
| HTTP 状态码       | 等于 | 201        |
| `$.code`        | 等于 | `OK`     |
| `$.data.id`     | 存在 | —         |
| `$.data.status` | 等于 | `ACTIVE` |

### 创建需求 AI 成功断言

| 目标                        | 规则 | 值           |
| --------------------------- | ---- | ------------ |
| HTTP 状态码                 | 等于 | 201          |
| `$.code`                  | 等于 | `OK`       |
| `$.data.analysis_status`  | 等于 | `ANALYZED` |
| `$.data.standard_content` | 存在 | —           |
| `$.data.priority`         | 存在 | —           |
| `$.data.reference_rule`   | 存在 | —           |

### 创建需求 AI 失败断言

| 目标                           | 规则 | 值                     |
| ------------------------------ | ---- | ---------------------- |
| HTTP 状态码                    | 等于 | 201                    |
| `$.code`                     | 等于 | `AI_ANALYSIS_FAILED` |
| `$.data.analysis_status`     | 等于 | `FAILED`             |
| `$.data.raw_content`         | 存在 | —                     |
| `$.data.analysis_error_code` | 存在 | —                     |

---

## 十八、Apifox 常见问题

### 1. Apifox 显示连接被拒绝

检查：

- FastAPI 终端是否仍在运行；
- Base URL 端口是否正确；
- 地址是否误写成 `https`；
- 浏览器能否打开健康检查。

### 2. 变量没有被替换

检查：

- 右上角是否选择“本地 FastAPI”环境；
- 环境变量本地值是否为空；
- 是否写成双大括号 `{{project_id}}`；
- 创建项目后的提取操作是否成功；
- 查看 Apifox 的“实际请求”。

### 3. 创建项目一直返回 409

数据库已经存在同名项目。修改 JSON 中的 `name`，例如追加日期或编号。

### 4. OpenAPI URL 无法导入

先在浏览器打开：

```text
http://127.0.0.1:8000/openapi.json
```

浏览器也打不开说明后端未启动或端口错误。浏览器能打开但 Apifox 失败时，保存为本地 JSON 文件再导入。

### 5. Apifox 请求成功但 AI 失败

Apifox 只负责调用 FastAPI。继续检查响应：

```text
data.analysis_error_code
data.analysis_error_message
```

再按部署指南中的 Dify 故障清单处理。

---

## 十九、当前接口限制

- 没有登录鉴权；
- 没有创建人真实用户信息；
- 没有正式需求的编辑或删除接口（V2.0 仅支持在确认前编辑访谈总结）；
- 没有单条重新分析接口；
- 批量分析只预留响应；
- 没有批量任务进度接口；
- 没有操作日志接口；
- 项目详情没有独立接口；
- 需求响应只有 `project_id`，没有项目名称；
- 当前创建需求会同步等待 Dify。

Apifox 中不要自行编造这些未实现接口并当作可用能力。

---

## 二十、Apifox 官方参考

- [新建 API 项目与导入 OpenAPI](https://docs.apifox.com/create-api-project)
- [导入导出数据](https://docs.apifox.com/import-and-export)
- [环境管理与前置 URL](https://docs.apifox.com/environments-and-services)
- [全局变量与环境变量](https://docs.apifox.com/global-environment-session-variables)
- [前后置操作](https://docs.apifox.com/pre-post-processors)
- [接口之间传递数据](https://docs.apifox.com/doc-5793498)

配套本地部署文档：

```text
docs/本地测试环境部署指南-产品人员版.md
```

---

# V2.0 接口说明

> 本模块只说明接口契约。每个接口名称与 Apifox 左侧列表一致，枚举和值放在实际使用它们的接口中。完整测试流程统一放在“V2.0 测试用例”模块。

# V2.0 接口一：`【V2.0】 上传访谈图片`

Apifox 位置：`interviews → 【V2.0】 上传访谈图片`

请求地址：`POST /api/v1/interviews/attachments`

## 参数

| 类型                      | 参数名        | 必填 | 限制                              | 默认值   | 说明                         |
| ------------------------- | ------------- | ---- | --------------------------------- | -------- | ---------------------------- |
| Body（multipart/form-data） | `file`      | 是   | PNG、JPG/JPEG、WEBP；最大 10MB    | 无       | Apifox 中选择文件，不传 Base64 |
| Body（multipart/form-data） | `uploaded_by` | 否 | 最长 32 字符                      | `null` | 上传人标识，应与访谈创建人一致 |

## 示例

在 Apifox 的 Body 中选择 `form-data`：

```text
file        File    选择本地图片 position.png
uploaded_by Text    apifox-user-v2
```

## 成功响应要点

- HTTP 201、`code=OK`；
- `$.data.id` 为图片的 `attachment_id`；
- `mime_type` 只会是 `image/png`、`image/jpeg` 或 `image/webp`；
- `preview_url` 可用于工作台预览；
- 上传成功并不代表已经关联访谈，必须把返回 ID 放入创建或回答接口的 `attachment_ids`。

## Apifox 后置操作（需要配置）

位置：本接口的“后置操作” → “自定义脚本”。

```javascript
const body = pm.response.json();

if (body && body.code === "OK" && body.data && body.data.id) {
  pm.environment.set("attachment_id", body.data.id);
}
```

每上传一张新图片都会产生新的 ID。测试多图时，可手工保存为 `attachment_id_1`～`attachment_id_5`。

## 本接口异常用例

| 输入                         | 预期                              |
| ---------------------------- | --------------------------------- |
| 扩展名或 Content-Type 非图片 | HTTP 400，`INVALID_IMAGE`          |
| 文件内容与声明格式不一致     | HTTP 400，`INVALID_IMAGE`          |
| 空文件                       | HTTP 400，`INVALID_IMAGE`          |
| 图片超过 10MB                | HTTP 413，`IMAGE_TOO_LARGE`        |

---

# V2.0 接口二：`【V2.0】 预览访谈图片`

Apifox 位置：`interviews → 【V2.0】 预览访谈图片`

请求地址：`GET /api/v1/interviews/attachments/{attachment_id}/content`

## 参数

| 类型 | 参数名           | 必填 | 限制         | 默认值 | 说明                                                        |
| ---- | ---------------- | ---- | ------------ | ------ | ----------------------------------------------------------- |
| Path | `attachment_id`  | 是   | 固定 32 字符 | 无     | 图片附件 ID；Apifox Path 参数值填 `{{attachment_id}}`       |

## 示例

```text
GET /api/v1/interviews/attachments/{{attachment_id}}/content
```

本接口无请求体，成功时直接返回图片二进制，不返回统一 JSON 包装。不存在的附件或文件返回 HTTP 404。

---

# V2.0 接口三：`【V2.0】 创建访谈会话`

Apifox 位置：`interviews → 【V2.0】 创建访谈会话`

请求地址：`POST /api/v1/interviews`

## 参数

| 类型         | 参数名                | 必填 | 限制                        | 默认值   | 说明                                        |
| ------------ | --------------------- | ---- | --------------------------- | -------- | ------------------------------------------- |
| Body（JSON） | `project_id`        | 是   | 固定 32 字符                | 无       | V1.1 创建项目后获得，使用`{{project_id}}` |
| Body（JSON） | `raw_content`       | 否   | 最长 10000 字符             | `""`   | 用户提交的原始需求；与图片至少提交一项      |
| Body（JSON） | `created_by`        | 否   | 最长 32 字符                | `null` | 当前提交人或测试用户标识                    |
| Body（JSON） | `client_message_id` | 是   | 1～64 字符                  | 无       | 客户端消息唯一标识，用于幂等                |
| Body（JSON） | `attachment_ids`    | 否   | 0～5 项；ID 固定 32 字符    | `[]`     | 上传图片接口返回的附件 ID 列表              |

## 示例

```json
{
  "project_id": "{{project_id}}",
  "raw_content": "我希望需求池可以支持批量导出",
  "created_by": "apifox-user-v2",
  "client_message_id": "apifox-initial-001",
  "attachment_ids": ["{{attachment_id}}"]
}
```

## 本接口相关返回值

- `status=INTERVIEWING`：Agent 已生成下一问，可以继续回答；
- `status=CONFIRMING`：原始内容已足够，或命中停止条件，可以确认总结；
- 首条用户消息 `role=USER`、`action_type=INITIAL`；
- Agent 追问消息 `role=AGENT`；
- `request_type` 可能为 `NEW_FEATURE`、`BUG`、`OPTIMIZATION` 或 `null`。

## 成功响应要点

- HTTP 状态码为 `201`；
- `$.code` 为 `OK`；
- `$.data.id` 长度为 32，并保存为 `session_id`；
- `$.data.status` 通常为 `INTERVIEWING`；若原始内容已足够完整，也可能直接为 `CONFIRMING`；
- `$.data.messages[0].role` 为 `USER`；
- 携带图片时，`$.data.messages[0].attachments[0].id` 等于上传接口返回的 `attachment_id`；
- 处于 `INTERVIEWING` 时，`$.data.current_question.text` 不为空；
- `current_question` 一次只能问一件事，`target_field` 与问题语义一致；
- 已抽取字段必须能在用户消息中找到依据，不得凭空补充。

## Apifox 后置操作（需要配置）

位置：本接口的“后置操作” → “自定义脚本”。

作用：

- 每次创建成功后，把返回的会话 ID 保存为 `session_id`；
- 主流程首次创建时，同时保存为 `main_session_id`；
- 后续创建分支测试会话时，不覆盖已有的 `main_session_id`。

```javascript
const body = pm.response.json();

if (body && body.code === "OK" && body.data && body.data.id) {
  pm.environment.set("session_id", body.data.id);

  if (!pm.environment.get("main_session_id")) {
    pm.environment.set("main_session_id", body.data.id);
  }
}
```

每轮完整主流程测试开始前，先在当前 Apifox 环境中清空旧的 `session_id`、`main_session_id` 和 `requirement_id`，避免引用上一轮数据。

## 幂等规则

连续两次发送完全相同的请求，包括相同的 `client_message_id`。预期两次 HTTP 都为 201，返回相同的 `session_id`，不会重复创建会话或调用 Dify。

## 本接口异常用例

| 输入                                   | 预期                           |
| -------------------------------------- | ------------------------------ |
| `project_id` 少于 32 位              | HTTP 422，`VALIDATION_ERROR` |
| `raw_content` 为空且未传图片         | HTTP 422，`VALIDATION_ERROR` |
| `attachment_ids` 超过 5 项或存在重复 | HTTP 422，`VALIDATION_ERROR` |
| 图片不存在                           | HTTP 404，`NOT_FOUND`        |
| 图片已关联其他会话或上传人不一致     | HTTP 409，`CONFLICT`         |
| `client_message_id` 为空或超过 64 位 | HTTP 422，`VALIDATION_ERROR` |
| 项目不存在                             | HTTP 404，`NOT_FOUND`        |
| 项目已归档                             | HTTP 409，`CONFLICT`         |

---

# V2.0 接口四：`【V2.0】 查询未完成访谈`

Apifox 位置：`interviews → 【V2.0】 查询未完成访谈`

请求地址：`GET /api/v1/interviews/drafts`

## 参数

| 类型  | 参数名         | 必填 | 限制         | 默认值   | 说明                                         |
| ----- | -------------- | ---- | ------------ | -------- | -------------------------------------------- |
| Query | `created_by` | 否   | 最长 32 字符 | `null` | 只查询指定创建人的会话；不传则查询所有创建人 |
| Query | `limit`      | 否   | 1～100       | `20`   | 最多返回的会话数量                           |

## 示例

```text
GET /api/v1/interviews/drafts?created_by=apifox-user-v2&limit=20
```

## 本接口相关状态

本接口只返回以下未完成状态：

```text
DRAFT
INTERVIEWING
CONFIRMING
FAILED
```

不会返回 `SUBMITTED` 和 `ABANDONED`。

## 成功响应要点

预期 HTTP 200；结果按 `updated_time` 倒序；只包含上述四种状态；超过 `limit` 范围时返回 HTTP 422。

---

# V2.0 接口五：`【V2.0】 查询访谈详情`

Apifox 位置：`interviews → 【V2.0】 查询访谈详情`

请求地址：`GET /api/v1/interviews/{session_id}`

## 参数

| 类型 | 参数名         | 必填 | 限制         | 默认值 | 说明                                                |
| ---- | -------------- | ---- | ------------ | ------ | --------------------------------------------------- |
| Path | `session_id` | 是   | 固定 32 字符 | 无     | 访谈会话 ID；Apifox Path 参数值填`{{session_id}}` |

## 示例

```text
GET /api/v1/interviews/{{session_id}}
```

## 本接口相关枚举

访谈状态：

```text
DRAFT
INTERVIEWING
CONFIRMING
SUBMITTED
ABANDONED
FAILED
```

消息角色：

```text
USER
AGENT
SYSTEM_EVENT
```

用户消息动作：

```text
INITIAL
ANSWER
SKIP
UNKNOWN
DIRECT_SUMMARY
```

## 成功响应要点

- HTTP 200，`$.data.id` 等于 `session_id`；
- `messages` 按 `sequence_no` 递增；
- `current_card` 固定包含 11 个字段；
- `completeness_score` 在 0～100 之间；
- `INTERVIEWING` 状态应有 `current_question`，`CONFIRMING` 状态应为 `null`。

不存在的 `session_id` 应返回 HTTP 404 和 `NOT_FOUND`。

---

# V2.0 接口六：`【V2.0】 回答访谈问题`

Apifox 位置：`interviews → 【V2.0】 回答访谈问题`

请求地址：`POST /api/v1/interviews/{session_id}/messages`

## 参数

| 类型         | 参数名                | 必填 | 限制                        | 默认值 | 说明                                                |
| ------------ | --------------------- | ---- | --------------------------- | ------ | --------------------------------------------------- |
| Path         | `session_id`        | 是   | 固定 32 字符                | 无     | 访谈会话 ID；Apifox Path 参数值填`{{session_id}}` |
| Body（JSON） | `content`           | 否   | 最长 10000 字符             | `""` | 用户回答；与图片至少提交一项                         |
| Body（JSON） | `client_message_id` | 是   | 1～64 字符                  | 无     | 本次回答的幂等标识；每次新回答必须更换              |
| Body（JSON） | `attachment_ids`    | 否   | 0～5 项；ID 固定 32 字符    | `[]`   | 本次回答关联的图片附件 ID                            |

## 示例

```json
{
  "content": "产品经理每周做产品周报时，需要把本周需求同步给研发。现在只能逐条复制，整理很耗时，希望能一次导出本周全部需求。",
  "client_message_id": "apifox-answer-001",
  "attachment_ids": ["{{attachment_id}}"]
}
```

保存后的用户消息 `action_type=ANSWER`。

## 成功响应要点

- HTTP 200，消息被保存；
- `round_count` 比回答前增加 1；
- `consecutive_skip_count` 归零；
- 携带图片时，回答消息的 `attachments` 返回图片元数据和 `preview_url`；
- 需求卡片只保留用户明确表达的事实；
- 若核心信息已足够，状态进入 `CONFIRMING`；否则只返回一个新的追问。

## 幂等规则

连续两次发送相同内容和相同的 `client_message_id`。预期第二次不新增消息、不增加轮次、不重复调用 Dify。

已提交或已放弃的会话再次回答，应返回 HTTP 409 和 `CONFLICT`。

---

# V2.0 接口七：`【V2.0】 跳过当前问题`

Apifox 位置：`interviews → 【V2.0】 跳过当前问题`

请求地址：`POST /api/v1/interviews/{session_id}/actions/skip`

## 参数

| 类型         | 参数名                | 必填 | 限制         | 默认值 | 说明                                                |
| ------------ | --------------------- | ---- | ------------ | ------ | --------------------------------------------------- |
| Path         | `session_id`        | 是   | 固定 32 字符 | 无     | 访谈会话 ID；Apifox Path 参数值填`{{session_id}}` |
| Body（JSON） | `client_message_id` | 是   | 1～64 字符   | 无     | 本次跳过操作的幂等标识                              |

## 示例

```json
{
  "client_message_id": "apifox-skip-001"
}
```

本接口保存的用户消息 `action_type=SKIP`。

## 成功响应要点

预期当前问题的 `target_field` 加入 `skipped_fields`，`round_count` 和 `consecutive_skip_count` 各加 1，Agent 不再重复询问该字段。当前没有问题时调用应返回 HTTP 409。

---

# V2.0 接口八：`【V2.0】 标记为不清楚`

Apifox 位置：`interviews → 【V2.0】 标记为不清楚`

请求地址：`POST /api/v1/interviews/{session_id}/actions/unknown`

## 参数

| 类型         | 参数名                | 必填 | 限制         | 默认值 | 说明                                                |
| ------------ | --------------------- | ---- | ------------ | ------ | --------------------------------------------------- |
| Path         | `session_id`        | 是   | 固定 32 字符 | 无     | 访谈会话 ID；Apifox Path 参数值填`{{session_id}}` |
| Body（JSON） | `client_message_id` | 是   | 1～64 字符   | 无     | 本次“不清楚”操作的幂等标识                        |

## 示例

```json
{
  "client_message_id": "apifox-unknown-001"
}
```

本接口保存的用户消息 `action_type=UNKNOWN`。

## 与“跳过”组合时的停止规则

```text
第 1 步：interviews → 【V2.0】 跳过当前问题
第 2 步：interviews → 【V2.0】 标记为不清楚
```

预期第二次操作后 `status=CONFIRMING`、`stop_reason=CONSECUTIVE_SKIPS`、`consecutive_skip_count=2`。

---

# V2.0 接口九：`【V2.0】 按当前信息整理`

Apifox 位置：`interviews → 【V2.0】 按当前信息整理`

请求地址：`POST /api/v1/interviews/{session_id}/actions/summarize`

调用前提：会话仍处于 `INTERVIEWING`。

## 参数

| 类型 | 参数名         | 必填 | 限制         | 默认值 | 说明                                                |
| ---- | -------------- | ---- | ------------ | ------ | --------------------------------------------------- |
| Path | `session_id` | 是   | 固定 32 字符 | 无     | 访谈会话 ID；Apifox Path 参数值填`{{session_id}}` |

## 示例

```text
POST /api/v1/interviews/{{session_id}}/actions/summarize
```

本接口无请求体。

## 成功响应要点

预期 HTTP 200、`status=CONFIRMING`、`stop_reason=USER_DIRECT_SUMMARY`、`current_question=null`。

---

# V2.0 接口十：`【V2.0】 编辑需求总结`

Apifox 位置：`interviews → 【V2.0】 编辑需求总结`

请求地址：`PATCH /api/v1/interviews/{session_id}/summary`

## 参数

| 类型         | 参数名            | 必填 | 限制         | 默认值   | 说明                                                |
| ------------ | ----------------- | ---- | ------------ | -------- | --------------------------------------------------- |
| Path         | `session_id`    | 是   | 固定 32 字符 | 无       | 访谈会话 ID；Apifox Path 参数值填`{{session_id}}` |
| Body（JSON） | `fields`        | 是   | 1～11 个字段 | 无       | 需要人工修改的需求卡片字段；值可为`null`          |
| Body（JSON） | `summary_title` | 否   | 1～100 字符  | `null` | 人工修改后的需求标题                                |

## 示例

```json
{
  "summary_title": "需求池批量导出本周需求",
  "fields": {
    "target_user": "产品经理",
    "usage_scenario": "每周制作产品周报时",
    "user_goal": "汇总本周需求并同步给研发",
    "current_problem": "目前需要逐条复制，整理耗时",
    "expected_result": "一次导出本周全部需求"
  }
}
```

## 本接口可编辑字段

| 字段名                | 中文含义       | 核心完整度权重 |
| --------------------- | -------------- | -------------- |
| `target_user`       | 目标用户       | 15             |
| `usage_scenario`    | 使用场景       | 20             |
| `user_goal`         | 用户任务       | 20             |
| `current_problem`   | 当前问题       | 25             |
| `expected_result`   | 期望结果       | 20             |
| `proposed_solution` | 用户提出的方案 | 不计分         |
| `frequency`         | 发生频率       | 不计分         |
| `impact_scope`      | 影响范围       | 不计分         |
| `bug_steps`         | Bug 复现步骤   | 不计分         |
| `actual_result`     | 实际结果       | 不计分         |
| `environment`       | 发生环境       | 不计分         |

`fields` 至少传 1 个、最多传 11 个；字段值可以为 `null`；非空内容最多 2000 字符。`summary_title` 最长 100 字符。人工修改后的字段来源为 `USER_EDIT`。

## 成功响应要点

- HTTP 200；
- `summary_title` 与人工输入一致；
- 修改字段的 `source` 为 `USER_EDIT`；
- 五个核心字段齐全时 `completeness_score=100`；
- `clarified_content` 已按卡片字段重新生成。

异常用例：未知字段、空白字段、字段超过 2000 字或标题超过 100 字，均应返回 HTTP 422 和 `VALIDATION_ERROR`。

---

# V2.0 接口十一：`【V2.0】 确认并创建需求`

Apifox 位置：`interviews → 【V2.0】 确认并创建需求`

请求地址：`POST /api/v1/interviews/{session_id}/confirm`

调用前提：会话必须先进入 `CONFIRMING`。

## 参数

| 类型         | 参数名              | 必填 | 限制         | 默认值 | 说明                                                |
| ------------ | ------------------- | ---- | ------------ | ------ | --------------------------------------------------- |
| Path         | `session_id`      | 是   | 固定 32 字符 | 无     | 访谈会话 ID；Apifox Path 参数值填`{{session_id}}` |
| Body（JSON） | `idempotency_key` | 是   | 1～64 字符   | 无     | 确认操作的幂等标识，防止重复创建正式需求            |

## 示例

```json
{
  "idempotency_key": "apifox-confirm-001"
}
```

## 本接口相关返回值

访谈提交状态：

```text
SUBMITTED
```

正式需求 AI 分析状态：

```text
PENDING
ANALYZING
ANALYZED
FAILED
```

需求类型：`NEW_FEATURE`、`BUG`、`OPTIMIZATION`；优先级：`P0`、`P1`、`P2`、`P3`。

## 成功响应要点

- HTTP 200；
- `$.data.session.status` 为 `SUBMITTED`；
- `$.data.session.requirement_id` 等于 `$.data.requirement.id`；
- 将需求 ID 保存为 `requirement_id`；
- `requirement.interview_session_id` 等于 `session_id`；
- `requirement.raw_content` 保留首次原始需求；
- `requirement.clarified_content` 保存访谈后的结构化内容；
- AI 分析成功时 `code=OK` 且 `analysis_status=ANALYZED`；
- V1.1 分析 Workflow 失败时仍可能 HTTP 200，但 `code=AI_ANALYSIS_FAILED`、`analysis_status=FAILED`，需求本身已经创建。

## Apifox 后置操作（需要配置）

位置：本接口的“后置操作” → “自定义脚本”。

作用：把正式需求 ID 保存为 `requirement_id`。即使 V1.1 AI 分析失败，只要正式需求已创建，也会保存该 ID，便于继续查询需求和关联访谈。

```javascript
const body = pm.response.json();

if (
  body &&
  (body.code === "OK" || body.code === "AI_ANALYSIS_FAILED") &&
  body.data &&
  body.data.requirement &&
  body.data.requirement.id
) {
  pm.environment.set("requirement_id", body.data.requirement.id);
}
```

执行成功后，在 Apifox 当前环境中检查 `requirement_id` 已有 32 位值。

## 幂等规则

对已经提交的会话再次调用确认接口。预期返回同一个 `requirement_id`，不会重复创建正式需求。未进入 `CONFIRMING` 就确认，应返回 HTTP 409 和 `CONFLICT`。

---

# V2.0 接口十二：`【V2.0】 放弃访谈`

Apifox 位置：`interviews → 【V2.0】 放弃访谈`

请求地址：`POST /api/v1/interviews/{session_id}/abandon`

## 参数

| 类型 | 参数名         | 必填 | 限制         | 默认值 | 说明                                                |
| ---- | -------------- | ---- | ------------ | ------ | --------------------------------------------------- |
| Path | `session_id` | 是   | 固定 32 字符 | 无     | 访谈会话 ID；Apifox Path 参数值填`{{session_id}}` |

## 示例

```text
POST /api/v1/interviews/{{session_id}}/abandon
```

本接口无请求体。

## 成功响应要点

预期 HTTP 200、`status=ABANDONED`、`stop_reason=USER_ABANDONED`。放弃后再次回答应返回 HTTP 409；已经 `SUBMITTED` 的访谈不能放弃。

---

# V2.0 接口十三：`【V2.0】 查询需求关联访谈`

Apifox 位置：`requirements → 【V2.0】 查询需求关联访谈`

请求地址：`GET /api/v1/requirements/{requirement_id}/interview`

## 参数

| 类型 | 参数名             | 必填 | 限制         | 默认值 | 说明                                                    |
| ---- | ------------------ | ---- | ------------ | ------ | ------------------------------------------------------- |
| Path | `requirement_id` | 是   | 固定 32 字符 | 无     | 正式需求 ID；Apifox Path 参数值填`{{requirement_id}}` |

## 示例

```text
GET /api/v1/requirements/{{requirement_id}}/interview
```

## 成功响应要点

预期 HTTP 200、`$.data.id={{session_id}}`、状态为 `SUBMITTED`，历史消息和需求卡片完整可见。需求不存在，或需求没有关联访谈时，返回 HTTP 404 和 `NOT_FOUND`。

---

# V2.0 测试用例（按执行顺序）

> 本模块只放测试流程。建议从 V2-TC-01 开始依次执行；主流程完成后，再执行分支、幂等和异常用例。

## 测试前置条件

1. FastAPI 已在 `http://127.0.0.1:8000` 启动。
2. 本地私有部署的 Dify 访谈 Workflow 已发布。
3. `backend/v2.0/.env` 已配置 `DIFY_BASE_URL` 和 `DIFY_INTERVIEW_API_KEY`。
4. 先执行 `projects → 【V1.1】 创建项目`，把返回的项目 ID 保存为 `project_id`。
5. 测试 FastAPI 时不要在 Apifox 请求中填写 Dify API Key；密钥只保存在后端 `.env`。

建议创建以下 Apifox 环境变量：

| 变量名              | 初始值                    | 用途                     |
| ------------------- | ------------------------- | ------------------------ |
| `base_url`        | `http://127.0.0.1:8000` | FastAPI 前置 URL         |
| `project_id`      | 创建项目后写入            | 访谈所属项目             |
| `attachment_id`   | V2-TC-IMG-01 后写入       | 当前待关联的图片附件     |
| `session_id`      | V2-TC-01 后写入           | 主流程访谈会话           |
| `main_session_id` | V2-TC-01 后写入           | 分支测试后恢复主流程会话 |
| `requirement_id`  | V2-TC-07 后写入           | 主流程正式需求           |

## 测试顺序总览

| 顺序 | 用例                    | Apifox 接口                                   | 类型   |
| ---- | ----------------------- | --------------------------------------------- | ------ |
| 1    | V2-TC-IMG-01 上传首张图片 | `interviews → 【V2.0】 上传访谈图片`       | 主流程 |
| 2    | V2-TC-IMG-02 预览图片     | `interviews → 【V2.0】 预览访谈图片`       | 主流程 |
| 3    | V2-TC-01 创建访谈         | `interviews → 【V2.0】 创建访谈会话`       | 主流程 |
| 4    | V2-TC-02 查询访谈详情     | `interviews → 【V2.0】 查询访谈详情`       | 主流程 |
| 5    | V2-TC-IMG-03 上传回答图片 | `interviews → 【V2.0】 上传访谈图片`       | 主流程 |
| 6    | V2-TC-03 回答问题         | `interviews → 【V2.0】 回答访谈问题`       | 主流程 |
| 7    | V2-TC-04 查询未完成访谈   | `interviews → 【V2.0】 查询未完成访谈`     | 主流程 |
| 8    | V2-TC-05 按当前信息整理   | `interviews → 【V2.0】 按当前信息整理`     | 主流程 |
| 9    | V2-TC-06 编辑需求总结     | `interviews → 【V2.0】 编辑需求总结`       | 主流程 |
| 10   | V2-TC-07 确认并创建需求   | `interviews → 【V2.0】 确认并创建需求`     | 主流程 |
| 11   | V2-TC-08 回查关联访谈     | `requirements → 【V2.0】 查询需求关联访谈` | 主流程 |
| 12   | V2-TC-09 跳过问题         | `interviews → 【V2.0】 跳过当前问题`       | 分支   |
| 13   | V2-TC-10 标记不清楚       | `interviews → 【V2.0】 标记为不清楚`       | 分支   |
| 14   | V2-TC-11 放弃访谈         | `interviews → 【V2.0】 放弃访谈`           | 分支   |
| 15   | V2-TC-12 创建幂等         | `interviews → 【V2.0】 创建访谈会话`       | 幂等   |
| 16   | V2-TC-13 回答幂等         | `interviews → 【V2.0】 回答访谈问题`       | 幂等   |
| 17   | V2-TC-14 确认幂等         | `interviews → 【V2.0】 确认并创建需求`     | 幂等   |
| 18   | V2-TC-15 参数与状态异常   | 多个 V2.0 接口                                | 异常   |
| 19   | V2-TC-16 Dify 降级        | 创建访谈、回答访谈问题                        | 异常   |

## 测试用例 V2-TC-IMG-01：上传创建访谈使用的图片

Apifox 位置：`interviews → 【V2.0】 上传访谈图片`

Body 选择 `form-data`，`file` 选择一张产品页面截图，`uploaded_by` 填 `apifox-user-v2`。预期 HTTP 201、`code=OK`，后置脚本将图片 ID 保存为 `attachment_id`。

## 测试用例 V2-TC-IMG-02：预览已上传图片

Apifox 位置：`interviews → 【V2.0】 预览访谈图片`

```text
GET /api/v1/interviews/attachments/{{attachment_id}}/content
```

预期 HTTP 200，响应 `Content-Type` 与上传图片一致，Apifox 可以显示或下载原图。

## 测试用例 V2-TC-01：创建访谈并获取第一问

Apifox 位置：`interviews → 【V2.0】 创建访谈会话`

```json
{
  "project_id": "{{project_id}}",
  "raw_content": "我希望需求池可以支持批量导出",
  "created_by": "apifox-user-v2",
  "client_message_id": "apifox-main-initial-001",
  "attachment_ids": ["{{attachment_id}}"]
}
```

预期：HTTP 201、`code=OK`；返回 32 位会话 ID；首条用户消息的 `attachments[0].id` 等于 `attachment_id`；Dify 能看到图片；状态通常为 `INTERVIEWING`，信息充分时也可能直接为 `CONFIRMING`；Agent 一次只问一个问题，抽取字段必须有用户证据。

后置脚本：

```javascript
const body = pm.response.json();

if (body && body.code === "OK" && body.data && body.data.id) {
  pm.environment.set("session_id", body.data.id);

  if (!pm.environment.get("main_session_id")) {
    pm.environment.set("main_session_id", body.data.id);
  }
}
```

## 测试用例 V2-TC-02：查询访谈详情

Apifox 位置：`interviews → 【V2.0】 查询访谈详情`

```text
GET /api/v1/interviews/{{session_id}}
```

预期：HTTP 200；会话 ID 一致；消息按 `sequence_no` 递增；`current_card` 包含 11 个固定字段；完整度在 0～100；访谈中应存在 `current_question`。

## 测试用例 V2-TC-03：回答 Agent 当前问题

Apifox 位置：`interviews → 【V2.0】 回答访谈问题`

执行本用例前，先再次执行“上传访谈图片”，选择另一张截图。后置脚本会把新的图片 ID覆盖到 `attachment_id`，这就是 V2-TC-IMG-03。

```json
{
  "content": "产品经理每周做产品周报时，需要把本周需求同步给研发。现在只能逐条复制，整理很耗时，希望能一次导出本周全部需求。",
  "client_message_id": "apifox-main-answer-001",
  "attachment_ids": ["{{attachment_id}}"]
}
```

预期：HTTP 200；回答消息返回新的图片附件；`round_count` 增加 1；`consecutive_skip_count` 归零；需求卡片只保留文字和图片中有依据的事实；信息足够时进入 `CONFIRMING`，否则返回一个新问题。

## 测试用例 V2-TC-04：查询未完成访谈

Apifox 位置：`interviews → 【V2.0】 查询未完成访谈`

```text
GET /api/v1/interviews/drafts?created_by=apifox-user-v2&limit=20
```

预期：HTTP 200；当前 `session_id` 仍未提交时应出现在列表中；列表只包含 `DRAFT`、`INTERVIEWING`、`CONFIRMING`、`FAILED`，按更新时间倒序。

## 测试用例 V2-TC-05：按当前信息整理

Apifox 位置：`interviews → 【V2.0】 按当前信息整理`

```text
POST /api/v1/interviews/{{session_id}}/actions/summarize
```

无请求体。预期：HTTP 200、`status=CONFIRMING`、`stop_reason=USER_DIRECT_SUMMARY`、`current_question=null`。

## 测试用例 V2-TC-06：编辑需求总结

Apifox 位置：`interviews → 【V2.0】 编辑需求总结`

```json
{
  "summary_title": "需求池批量导出本周需求",
  "fields": {
    "target_user": "产品经理",
    "usage_scenario": "每周制作产品周报时",
    "user_goal": "汇总本周需求并同步给研发",
    "current_problem": "目前需要逐条复制，整理耗时",
    "expected_result": "一次导出本周全部需求"
  }
}
```

预期：HTTP 200；标题和字段与输入一致；人工字段 `source=USER_EDIT`；五个核心字段齐全时 `completeness_score=100`；`clarified_content` 已重新生成。

## 测试用例 V2-TC-07：确认并创建正式需求

Apifox 位置：`interviews → 【V2.0】 确认并创建需求`

```json
{
  "idempotency_key": "apifox-main-confirm-001"
}
```

预期：HTTP 200；访谈状态为 `SUBMITTED`；需求的 `interview_session_id` 等于 `session_id`；AI 成功时 `code=OK`、`analysis_status=ANALYZED`。V1.1 分析 Workflow 失败时，需求仍已创建，但 `code=AI_ANALYSIS_FAILED`、`analysis_status=FAILED`。

后置脚本：

```javascript
const body = pm.response.json();

if (
  body &&
  (body.code === "OK" || body.code === "AI_ANALYSIS_FAILED") &&
  body.data &&
  body.data.requirement &&
  body.data.requirement.id
) {
  pm.environment.set("requirement_id", body.data.requirement.id);
}
```

## 测试用例 V2-TC-08：从正式需求回查访谈

Apifox 位置：`requirements → 【V2.0】 查询需求关联访谈`

```text
GET /api/v1/requirements/{{requirement_id}}/interview
```

预期：HTTP 200；返回的会话 ID 等于 `session_id`；状态为 `SUBMITTED`；历史消息和需求卡片完整。

## 测试用例 V2-TC-09：跳过当前问题

Apifox 位置：`interviews → 【V2.0】 跳过当前问题`

准备：重新执行 V2-TC-01 创建一条分支会话，使用新的 `client_message_id`，并将返回 ID 保存为新的 `session_id`。不要覆盖 `main_session_id`。

```json
{
  "client_message_id": "apifox-branch-skip-001"
}
```

预期：当前字段加入 `skipped_fields`；`round_count` 和 `consecutive_skip_count` 各增加 1；Agent 不再询问同一字段。

## 测试用例 V2-TC-10：连续“跳过 + 不清楚”停止追问

Apifox 位置：`interviews → 【V2.0】 标记为不清楚`

准备：沿用 V2-TC-09 的分支会话，在跳过一次后执行：

```json
{
  "client_message_id": "apifox-branch-unknown-001"
}
```

预期：`status=CONFIRMING`、`stop_reason=CONSECUTIVE_SKIPS`、`consecutive_skip_count=2`。

## 测试用例 V2-TC-11：放弃访谈

Apifox 位置：`interviews → 【V2.0】 放弃访谈`

准备：创建一条新的未提交会话，然后调用放弃接口，无请求体。

预期：HTTP 200、`status=ABANDONED`、`stop_reason=USER_ABANDONED`；放弃后回答返回 HTTP 409；已经提交的访谈不能放弃。

## 测试用例 V2-TC-12：创建访谈幂等

Apifox 位置：`interviews → 【V2.0】 创建访谈会话`

连续两次发送完全相同的创建请求，包括相同的 `client_message_id`。预期两次均为 HTTP 201，返回同一个会话 ID，不重复创建会话或调用 Dify。

## 测试用例 V2-TC-13：回答消息幂等

Apifox 位置：`interviews → 【V2.0】 回答访谈问题`

对一条访谈中会话连续两次发送相同回答和相同 `client_message_id`。预期第二次不新增消息、不增加轮次、不重复调用 Dify。

## 测试用例 V2-TC-14：确认提交幂等

Apifox 位置：`interviews → 【V2.0】 确认并创建需求`

先把 `session_id` 恢复为 `main_session_id`，再对 V2-TC-07 已提交的主流程会话调用确认接口。预期返回原来的 `requirement_id`，不重复创建需求。

## 测试用例 V2-TC-15：参数与状态异常

按表中接口逐项执行：

| Apifox 接口                               | 测试输入                         | 预期                           |
| ----------------------------------------- | -------------------------------- | ------------------------------ |
| `interviews → 【V2.0】 上传访谈图片`     | 上传伪造 PNG 或非图片文件        | HTTP 400，`INVALID_IMAGE`    |
| `interviews → 【V2.0】 上传访谈图片`     | 图片超过 10MB                    | HTTP 413，`IMAGE_TOO_LARGE`  |
| `interviews → 【V2.0】 创建访谈会话`   | `project_id` 少于 32 位        | HTTP 422，`VALIDATION_ERROR` |
| `interviews → 【V2.0】 创建访谈会话`   | 无文字且 `attachment_ids=[]`  | HTTP 422，`VALIDATION_ERROR` |
| `interviews → 【V2.0】 创建访谈会话`   | 图片已关联另一条消息             | HTTP 409，`CONFLICT`         |
| `interviews → 【V2.0】 回答访谈问题`   | `client_message_id` 超过 64 位 | HTTP 422，`VALIDATION_ERROR` |
| `interviews → 【V2.0】 编辑需求总结`   | `fields` 使用未定义字段        | HTTP 422，`VALIDATION_ERROR` |
| `interviews → 【V2.0】 编辑需求总结`   | 卡片字段超过 2000 字             | HTTP 422，`VALIDATION_ERROR` |
| `interviews → 【V2.0】 确认并创建需求` | 尚未进入确认状态                 | HTTP 409，`CONFLICT`         |
| `interviews → 【V2.0】 跳过当前问题`   | 当前没有可跳过问题               | HTTP 409，`CONFLICT`         |
| `interviews → 【V2.0】 查询访谈详情`   | `session_id` 不存在            | HTTP 404，`NOT_FOUND`        |

## 测试用例 V2-TC-16：Dify 不可用时的降级

Apifox 位置：

```text
interviews → 【V2.0】 创建访谈会话
interviews → 【V2.0】 回答访谈问题
```

临时使用错误 Dify 地址、错误 Key、停止 Dify 服务，或让 Workflow 返回非法结构；不要提交真实密钥的改动。

预期：用户消息已保存；`agent_error_code` 记录错误；系统使用确定性兜底问题；Agent 连续失败两次后进入 `CONFIRMING`，`stop_reason=AGENT_FAILED_TWICE`。恢复配置后重新创建会话验证正常链路。

## Dify 结构与语义验收

结构层：

- `request_type` 只能为 `NEW_FEATURE`、`BUG`、`OPTIMIZATION` 或 `null`；
- `extracted_fields` 固定包含 11 个字段；非空字段包含 `value`、`evidence_message_ids`、`source`；
- `source` 只能为 `USER_INPUT` 或 `USER_EDIT`；
- `next_question` 为对象或 `null`，问题不超过 120 字且只问一件事；
- `validation_ok=false` 必须被后端拒绝；证据 ID 必须来自当前会话用户消息。

语义层：

- 不得把用户没有说过的内容补成事实；
- 用户只说“每周”时，不得改成“每周一次”；
- `expected_result` 描述期望结果，不偷换成导出格式等方案细节；
- 不重复询问已有可信值或已跳过字段；
- Bug 重点补齐实际结果、复现步骤、期望结果和发生环境；
- `validation_ok=true` 只表示代码校验通过，不代表业务语义一定正确。

每次回归记录测试时间、后端 Git 提交、Dify Workflow 发布版本、Prompt 版本、模型、输入、HTTP 状态、业务码和语义结论。LLM 文案具有非确定性，不把某一句固定追问作为唯一正确答案。
