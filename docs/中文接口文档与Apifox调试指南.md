# 极简 AI 团队需求管理智能体：中文接口文档与 Apifox 调试指南

文档版本：V0.1
本地后端默认地址：`http://127.0.0.1:8000`
接口统一前缀：`/api/v1`
数据格式：JSON
当前鉴权：未实现，测试接口不需要登录 Token。

---

## 一、开始前检查

必须先启动 FastAPI：

```bash
cd '/Users/zhanggengyu/Documents/极简AI团队需求管理智能体'
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

| 序号 | 方法 | 路径                                      | 作用                   | 当前状态               |
| ---- | ---- | ----------------------------------------- | ---------------------- | ---------------------- |
| 1    | GET  | `/api/v1/health`                        | 健康检查               | 可用                   |
| 2    | POST | `/api/v1/projects`                      | 创建项目               | 可用                   |
| 3    | GET  | `/api/v1/projects`                      | 查询项目列表           | 可用                   |
| 4    | POST | `/api/v1/requirements`                  | 创建需求并同步 AI 分析 | 可用                   |
| 5    | GET  | `/api/v1/requirements`                  | 查询需求列表           | 可用                   |
| 6    | GET  | `/api/v1/requirements/{requirement_id}` | 查询需求详情           | 可用                   |
| 7    | POST | `/api/v1/requirements/batch-analyze`    | 批量 AI 分析           | 仅预留响应，未真正执行 |

辅助地址：

| 地址              | 作用                         |
| ----------------- | ---------------------------- |
| `/docs`         | Swagger 可视化接口文档       |
| `/openapi.json` | OpenAPI JSON，供 Apifox 导入 |

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

### Apifox 后置提取

为了后续创建需求，建议把项目 ID 提取为环境变量：

| 设置项   | 值             |
| -------- | -------------- |
| 变量名   | `project_id` |
| JSONPath | `$.data.id`  |
| 存储位置 | 当前本地环境   |

发送成功后，后续请求可使用：

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

### Apifox 后置提取

把新需求 ID 保存为环境变量：

| 设置项   | 值                 |
| -------- | ------------------ |
| 变量名   | `requirement_id` |
| JSONPath | `$.data.id`      |
| 存储位置 | 当前本地环境       |

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

推荐使用这种方式，避免手工创建七个接口。

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
4. 选择 URL 导入；
5. 输入：

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
- 没有编辑或删除接口；
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
