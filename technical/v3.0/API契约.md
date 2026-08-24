# V3.0 API 契约

> 状态：开发前契约基线
> 前缀：`/api/v1`
> 数据格式：JSON；日期为 `YYYY-MM-DD`；时间为 UTC ISO 8601

## 1. 通用约定

### 1.1 成功与错误

继续沿用现有响应外壳：

```json
{
  "code": "OK",
  "message": "",
  "data": {},
  "details": null,
  "request_id": "32位请求ID"
}
```

错误状态：

| HTTP | 场景 |
|---:|---|
| 400 | 无法按业务语义处理的请求 |
| 401 | 未登录、会话过期或被撤销 |
| 403 | 已登录但无操作权限，或向归档项目写入业务数据；重新打开项目除外 |
| 404 | 对象不存在，或普通用户访问无权知晓的项目 |
| 409 | 修订冲突、唯一性冲突、对象仍被引用、成员仍负责任务 |
| 422 | 字段类型、长度、枚举或日期校验失败 |

关键错误码：

- `AUTH_INVALID_CREDENTIALS`
- `AUTH_INVITATION_USED`
- `AUTH_IDENTITY_MISMATCH`
- `AUTH_NAME_ALREADY_REGISTERED`
- `AUTH_SESSION_EXPIRED`
- `PERMISSION_DENIED`
- `PROJECT_ARCHIVED`
- `REVISION_CONFLICT`
- `LANE_REVISION_CONFLICT`
- `DEPARTMENT_IN_USE`
- `PROJECT_MEMBER_HAS_TASKS`
- `VERSION_PARTICIPANT_HAS_TASKS`
- `VERSION_REQUIRES_PARTICIPANT`
- `RESULT_LIMIT_EXCEEDED`

### 1.2 鉴权和防跨站请求

- 登录会话使用 HttpOnly Cookie，Axios 配置 `withCredentials: true`；
- 所有写请求同时携带服务端签发的 CSRF 令牌请求头；
- 登录页部门列表、创建会话和健康检查是公开接口；
- 其他接口必须通过会话依赖注入读取当前用户；
- `created_by`、`updated_by` 不接受客户端传值。

### 1.3 乐观并发

可编辑资源返回整数 `revision`。修改、删除和状态切换必须提交 `expected_revision`。服务端使用条件更新：

```text
UPDATE ... SET ..., revision = revision + 1
WHERE id = :id AND revision = :expected_revision
```

受影响行数为 0 时返回 409，不覆盖较新数据。冲突详情返回对象 ID、客户端修订号和当前修订号；前端提示刷新，不自动重放用户修改。

## 2. 身份与组织

### 2.1 会话

| 方法 | 路径 | 权限 | 用途 |
|---|---|---|---|
| `GET` | `/auth/departments` | 公开 | 登录页部门下拉，只返回 ID 和名称 |
| `POST` | `/auth/registrations` | 公开 | 使用部门、姓名和邀请码首次注册并设置会话 Cookie |
| `POST` | `/auth/sessions` | 公开 | 使用部门、姓名和公司统一密码登录 |
| `GET` | `/auth/me` | 登录 | 返回当前用户、角色和 CSRF 令牌 |
| `DELETE` | `/auth/session` | 登录 | 撤销当前会话并清除 Cookie |

`POST /auth/registrations` 请求：

```json
{
  "department_id": "uuid32",
  "name": "陈晨",
  "invitation_code": "ABCD12345"
}
```

`POST /auth/sessions` 请求：

```json
{
  "department_id": "uuid32",
  "name": "陈晨",
  "shared_password": "公司统一密码"
}
```

注册时邀请码不存在使用 `AUTH_INVALID_CREDENTIALS`，已使用为 `AUTH_INVITATION_USED`，同部门同名为 `AUTH_NAME_ALREADY_REGISTERED`。登录失败统一使用 `AUTH_IDENTITY_MISMATCH`，不区分账号不存在或密码错误。错误详情不得返回绑定用户、邀请码摘要、统一密码或其他内部字段。

### 2.2 部门、邀请码和用户

| 方法 | 路径 | 权限 | 用途 |
|---|---|---|---|
| `GET` | `/departments` | 管理员 | 分页查询部门 |
| `POST` | `/departments` | 管理员 | 新增部门 |
| `PATCH` | `/departments/{department_id}` | 管理员 | 修改名称 |
| `DELETE` | `/departments/{department_id}` | 管理员 | 永久删除无引用部门 |
| `GET` | `/invitations` | 管理员 | 查询完整邀请码、部门和状态，支持复制 |
| `POST` | `/invitations` | 管理员 | 生成并保存邀请码 |
| `POST` | `/invitations/{invitation_id}/disable` | 管理员 | 停用未使用邀请码 |
| `GET` | `/users` | 登录 | 供项目成员选择，支持姓名和部门筛选 |

删除被引用部门时返回：

```json
{
  "code": "DEPARTMENT_IN_USE",
  "message": "部门仍被使用，无法删除",
  "details": {"user_count": 3, "project_count": 1, "invitation_count": 2}
}
```

## 3. 项目与成员

| 方法 | 路径 | 权限 | 用途 |
|---|---|---|---|
| `GET` | `/projects` | 登录 | 普通用户返回本人项目；管理员返回全部 |
| `POST` | `/projects` | 登录 | 创建项目并写入首批成员，当前用户自动排在首位 |
| `GET` | `/projects/{project_id}` | 可见项目 | 项目详情 |
| `PATCH` | `/projects/{project_id}` | 项目成员 | 编辑、归档或重新启用项目 |
| `GET` | `/projects/{project_id}/members` | 可见项目 | 按项目成员顺序返回成员、顺序值和任务数量 |
| `PUT` | `/projects/{project_id}/members` | 项目成员/管理员 | 用完整且有序的用户 ID 列表保存成员与顺序 |

创建项目请求中的 `member_ids` 是首批项目成员的有序用户 ID 列表。服务端无论客户端是否包含创建人，都会将当前用户放在首位；用户校验和项目创建在同一事务中完成。

成员保存请求：

```json
{
  "user_ids": ["user-a", "user-b"],
  "expected_member_revision": 3
}
```

规则：`user_ids` 的数组顺序就是项目成员顺序；至少一名成员；新增成员放在客户端提交的位置，前端默认追加末尾；删除时逐人检查是否仍负责任务。任一删除不合法则整个请求回滚并返回冲突明细，不做部分成功。

任意项目成员均可通过项目更新接口归档或重新打开项目；本期不区分项目创建者和普通项目成员。

## 4. 任务

### 4.1 查询

`GET /projects/{project_id}/tasks`

查询参数：

| 参数 | 规则 |
|---|---|
| `keyword` | 可空，最多 100 字符，只匹配任务名称 |
| `status` | `ALL/UNFINISHED/NOT_STARTED/IN_PROGRESS/COMPLETED/CANCELED` |
| `version_id` | 可空；提供时只返回当前项目该版本任务 |

响应：

```json
{
  "items": [],
  "total": 340,
  "lanes": [
    {"assignee_id": "user-a", "revision": 6}
  ]
}
```

返回符合搜索和筛选条件的全部任务。成员任务容量由创建和修改接口统一约束，不通过查询截断控制。

### 4.2 创建、修改和删除

| 方法 | 路径 | 用途 |
|---|---|---|
| `POST` | `/projects/{project_id}/tasks` | 创建任务 |
| `GET` | `/projects/{project_id}/tasks/{task_id}` | 任务详情 |
| `PATCH` | `/projects/{project_id}/tasks/{task_id}` | 修改任务 |
| `DELETE` | `/projects/{project_id}/tasks/{task_id}?expected_revision=3` | 永久删除任务 |

创建字段：

```json
{
  "name": "整理访谈结论",
  "assignee_id": "user-a",
  "status": "NOT_STARTED",
  "priority": "P1",
  "version_id": null,
  "start_date": null,
  "due_date": null,
  "description": ""
}
```

修改请求增加 `expected_revision`，未提供的字段保持不变。关键规则：

- 负责人必须是当前项目成员；
- 每位负责人在单个项目中最多拥有 200 条任务，按全部状态和版本计数；
- 创建或转交到已满泳道返回 409 `TASK_ASSIGNEE_LIMIT_REACHED`；删除或转出任务后恢复名额；
- 版本必须属于当前项目；
- 同时有两个日期时 `due_date >= start_date`；
- 修改负责人后任务进入新负责人泳道底部；
- 有版本且新负责人不是版本参与人员时自动加入；
- 归档项目所有写入返回 403。

### 4.3 排序

`GET /projects/{project_id}/task-lanes/{assignee_id}/order` 返回完整泳道任务 ID 顺序和当前 `lane_revision`，供筛选状态下合并可见任务顺序。

`PUT /projects/{project_id}/task-lanes/{assignee_id}/order`

```json
{
  "expected_lane_revision": 6,
  "ordered_task_ids": ["task-c", "task-a", "task-b"]
}
```

- 请求必须包含该项目、该负责人完整泳道中的全部任务 ID，即使当前界面有筛选；
- 不得包含其他负责人或其他项目任务；
- 成功后返回新 `lane_revision`；
- 并发冲突返回 `LANE_REVISION_CONFLICT`；
- 只有团队任务面板调用该接口。

## 5. 版本

### 5.1 查询和基本操作

| 方法 | 路径 | 用途 |
|---|---|---|
| `GET` | `/projects/{project_id}/versions` | 按创建时间倒序返回实际版本 |
| `POST` | `/projects/{project_id}/versions` | 创建版本及初始参与人员 |
| `GET` | `/projects/{project_id}/versions/{version_id}` | 版本详情、参与人员、任务统计 |
| `PATCH` | `/projects/{project_id}/versions/{version_id}` | 修改名称、日期、状态或参与人员 |
| `GET` | `/projects/{project_id}/versions/{version_id}/completion-impact` | 返回未完成任务数量 |
| `DELETE` | `/projects/{project_id}/versions/{version_id}?expected_revision=4` | 删除版本并解除任务关联 |

创建请求：

```json
{
  "name": "V3.0",
  "start_date": "2026-08-24",
  "end_date": "2026-09-11",
  "participant_ids": ["user-a", "user-b"]
}
```

更新请求使用完整 `participant_ids` 并携带 `expected_revision`。规则：

- 至少一名参与人员，且全部是项目成员；
- 结束日期不得早于开始日期；
- 移除仍负责当前版本任务的参与人员时整个请求失败；
- 切换到 `COMPLETED` 只修改版本状态，不修改任务；
- 删除成功响应包含 `unlinked_task_count`；
- 删除最后一个版本后返回 `next_version_id: null`，否则返回剩余最新版本 ID。

### 5.2 版本任务

版本排期不建立第二套任务接口。前端使用：

```text
GET /projects/{project_id}/tasks?version_id={version_id}&status=ALL
```

创建版本任务仍调用项目任务创建接口并传 `version_id`。这样可以从契约层保证任务只存在一份。

## 6. 前端类型生成

1. 后端 schema 和路由完成后生成 `backend/v2.0/app/openapi.json`；
2. 前端执行现有 `generate:api` 生成 TypeScript 类型；
3. CI 检查生成文件无未提交差异；
4. 手写 API 封装只能组合生成类型，不得复制一套独立接口类型；
5. OpenAPI 示例不得包含真实邀请码、会话令牌或本地业务数据。

## 7. 契约测试最低范围

- 所有写接口未登录、非成员、管理员非成员、归档项目四种权限路径；
- 首次邀请码注册、同部门同名冲突和统一密码后续登录；
- 会话 7 天空闲过期、30 天绝对过期和滚动续期；
- 邀请码并发核销；
- 部门引用删除冲突；
- 项目成员和版本参与人员移除冲突；
- 任务和版本 409 乐观锁；
- 成员达到 200 条任务时，创建和负责人转交均返回容量冲突；
- 删除版本后任务仍存在且 `version_id = null`；
- 负责人变化时排序和版本参与人员自动补齐；
- OpenAPI 生成类型与后端契约一致。
