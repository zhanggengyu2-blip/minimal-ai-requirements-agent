# 前端 V2.0 运行说明

当前前端在保留 V1.1 项目、需求、部门和邀请码管理能力的基础上，新增 V2.0 对话式需求访谈工作台。

本项目的前端固定采用 Vue 3 + TypeScript + Element Plus + Axios + Vite。

## 本地运行

确保 FastAPI 服务已运行在 `http://127.0.0.1:8000`，然后执行：

```bash
pnpm install
pnpm run generate:api
pnpm run dev
```

浏览器访问 `http://127.0.0.1:3000`。

如需使用其他后端地址，可在本地环境变量中设置：

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

## 类型与构建

`src/api/generated.ts` 由 `../../backend/v2.0/app/openapi.json` 自动生成，请勿手动修改。后端接口变更后执行：

```bash
pnpm run generate:api
pnpm run build
```

请求封装位于 `src/api/http.ts`，业务请求函数位于 `src/api/index.ts`。

## 用户与部门管理

侧边栏“用户与部门”区域包含：

- 部门管理：新增、编辑、启用/停用、关键字与状态筛选。
- 邀请码管理：生成、复制、停用、部门与使用状态筛选。

对应后端接口为 `/api/v1/departments` 与 `/api/v1/invitations`，数据持久化在项目配置的 SQLite 数据库中。
