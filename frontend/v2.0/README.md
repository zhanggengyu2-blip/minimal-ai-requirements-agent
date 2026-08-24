# 前端 V3.0 运行说明

当前前端保留项目、需求和对话式需求访谈能力，并已完成 V3.0 身份会话、项目成员、团队任务、版本排期与共用甘特图。

本项目的前端固定采用 Vue 3 + TypeScript + Element Plus + Axios + Vue Router + Vite。

## 本地运行

确保 FastAPI 服务已运行在 `http://127.0.0.1:8000`，然后执行：

```bash
cd frontend/v2.0
pnpm install
pnpm run generate:api
pnpm run dev
```

浏览器访问 `http://127.0.0.1:3000`。

首次使用由管理员提供部门、姓名和邀请码完成注册；后续使用部门、姓名和公司统一密码登录。统一密码和 CSRF 令牌只保存在当前内存与服务端会话中，不写入浏览器持久化存储。

如需使用其他后端地址，可在本地环境变量中设置：

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

## 类型与构建

`src/api/generated.ts` 由 `../../backend/v2.0/app/openapi.json` 自动生成，请勿手动修改。该路径由 `package.json` 中的脚本从前端目录解析，已对应新的职能分层目录。后端接口变更后执行：

```bash
pnpm run generate:api
pnpm run test
pnpm run build
```

## Playwright 闭环验收

关键闭环用例位于 `e2e/core-flow.spec.ts`，使用 1280×900 视口验证登录、团队任务、版本排期和两个甘特图共用同一任务。它只允许连接一次性测试库，不得对正式库运行。

```bash
pnpm exec playwright install chromium
pnpm run test:e2e
```

请求封装位于 `src/api/http.ts`，业务请求函数位于 `src/api/index.ts`。Axios 默认携带 Cookie，写请求附加 CSRF 令牌；401、403、409 和 422 使用不同交互路径。

## 路由与权限

- `/login`：后续登录与首次注册双模式；
- `/projects`：项目管理；
- `/projects/:projectId/requirements`：项目需求；
- `/projects/:projectId/interviews`：项目访谈记录；
- `/projects/:projectId/tasks/board`、`/tasks/gantt`：团队任务稳定路由；
- `/projects/:projectId/versions`：版本排期稳定路由；
- `/admin/departments`、`/admin/invitations`：管理员专属入口。

未登录访问业务路由会保留返回地址并跳转登录；项目不存在或不可见时展示 404。归档项目仍可通过侧栏入口查看，但页面使用只读上下文禁用写操作。

## 用户与部门管理

侧边栏“用户与部门”区域包含：

- 部门管理：新增、编辑、永久删除和关键字筛选；存在引用时由服务端拒绝删除。
- 邀请码管理：生成、复制、停用、部门与使用状态筛选。
- 项目成员：从内部用户目录选择成员；仍负责任务的成员不可移除，并使用成员修订号处理并发冲突。

对应后端接口为 `/api/v1/departments` 与 `/api/v1/invitations`，数据持久化在项目配置的 SQLite 数据库中。
