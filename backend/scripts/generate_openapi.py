"""生成供 Apifox 导入的中文版 OpenAPI 文档。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app


OUTPUTS = (
    ROOT / "app" / "openapi.json",
    ROOT / "docs" / "openapi-v3.0-apifox.json",
    # 保留旧文件名，避免已建立的 Apifox 导入配置立即失效。
    ROOT / "docs" / "openapi-v2.0-apifox.json",
)

OPERATION_META: dict[tuple[str, str], tuple[str, str, str]] = {
    ("/api/v1/health", "get"): ("健康检查", "V1.1", "检查 FastAPI 服务是否可访问。"),
    ("/api/v1/ready", "get"): ("就绪检查", "V3.0", "检查数据库连接和 Alembic 迁移是否已到最新版本。"),
    ("/api/v1/auth/departments", "get"): ("查询登录部门", "V3.0", "公开返回登录和首次注册可选择的部门 ID 与名称。"),
    ("/api/v1/auth/registrations", "post"): ("首次注册", "V3.0", "使用部门、姓名和一次性邀请码创建普通成员并建立登录会话。"),
    ("/api/v1/auth/sessions", "post"): ("统一密码登录", "V3.0", "使用部门、姓名和公司统一密码建立服务端会话。"),
    ("/api/v1/auth/me", "get"): ("查询当前用户", "V3.0", "返回当前用户、角色和写请求所需的 CSRF 令牌。"),
    ("/api/v1/auth/session", "delete"): ("退出登录", "V3.0", "撤销当前服务端会话并清除 HttpOnly Cookie。"),
    ("/api/v1/projects", "post"): ("创建项目", "V3.0", "创建需求所属项目并写入首批成员，当前用户自动排在项目成员首位。"),
    ("/api/v1/projects", "get"): ("查询项目列表", "V3.0", "普通成员分页查询本人项目；管理员分页查询全部项目。"),
    ("/api/v1/projects/{project_id}", "get"): ("查询项目详情", "V3.0", "查询当前用户可见的项目详情、修订号和统计信息。"),
    ("/api/v1/projects/{project_id}", "patch"): ("更新项目", "V3.0", "项目成员使用修订号编辑、归档或重新打开项目。"),
    ("/api/v1/projects/{project_id}/members", "get"): ("查询项目成员", "V3.0", "按项目统一顺序返回成员、部门、任务数量和成员集合修订号。"),
    ("/api/v1/projects/{project_id}/members", "put"): ("保存项目成员", "V3.0", "用完整有序用户 ID 列表和成员修订号原子保存项目成员及顺序。"),
    ("/api/v1/projects/{project_id}/tasks", "get"): ("查询项目任务", "V3.0", "按名称、状态和版本筛选项目任务，并返回负责人泳道修订号。"),
    ("/api/v1/projects/{project_id}/tasks", "post"): ("创建任务", "V3.0", "为项目成员创建任务并放到负责人泳道底部；每位负责人在单个项目中最多拥有 200 条任务。"),
    ("/api/v1/projects/{project_id}/tasks/{task_id}", "get"): ("查询任务详情", "V3.0", "查询当前项目中的单个任务。"),
    ("/api/v1/projects/{project_id}/tasks/{task_id}", "patch"): ("更新任务", "V3.0", "使用任务修订号修改任务；更换负责人时移动到新泳道底部。"),
    ("/api/v1/projects/{project_id}/tasks/{task_id}", "delete"): ("永久删除任务", "V3.0", "使用任务修订号永久删除任务并更新泳道修订号。"),
    ("/api/v1/projects/{project_id}/task-lanes/{assignee_id}/order", "get"): ("查询完整泳道顺序", "V3.0", "返回负责人完整任务 ID 顺序和泳道修订号。"),
    ("/api/v1/projects/{project_id}/task-lanes/{assignee_id}/order", "put"): ("保存完整泳道顺序", "V3.0", "使用泳道修订号原子保存完整任务 ID 顺序。"),
    ("/api/v1/projects/{project_id}/versions", "get"): ("查询版本列表", "V3.0", "按创建时间倒序返回当前项目中的全部实际版本和任务统计。"),
    ("/api/v1/projects/{project_id}/versions", "post"): ("创建版本", "V3.0", "创建版本及至少一名初始参与人员，参与人员必须是当前项目成员。"),
    ("/api/v1/projects/{project_id}/versions/{version_id}", "get"): ("查询版本详情", "V3.0", "返回版本信息、按项目成员顺序排列的参与人员及任务统计。"),
    ("/api/v1/projects/{project_id}/versions/{version_id}", "patch"): ("更新版本", "V3.0", "使用版本修订号修改名称、日期、状态或完整参与人员集合。"),
    ("/api/v1/projects/{project_id}/versions/{version_id}", "delete"): ("删除版本", "V3.0", "使用版本修订号删除版本并解除任务关联，不删除任何任务。"),
    ("/api/v1/projects/{project_id}/versions/{version_id}/completion-impact", "get"): ("查询版本完成影响", "V3.0", "返回当前版本全部任务数和未完成任务数，供完成确认使用。"),
    ("/api/v1/requirements", "post"): ("直接保存需求（可选 AI 分析）", "V3.0", "直接保存原始需求；analyze_with_ai 默认 false，返回 NOT_RUN。显式开启后先返回 PENDING，响应发送后执行 AI 分析，通过列表或详情查询 ANALYZING、ANALYZED 或 FAILED。"),
    ("/api/v1/requirements", "get"): ("查询需求列表", "V1.1", "分页、筛选和搜索需求。"),
    ("/api/v1/requirements/{requirement_id}", "get"): ("查询需求详情", "V1.1", "按需求 ID 查询需求详情。"),
    ("/api/v1/requirements/batch-analyze", "post"): ("批量分析需求（预留）", "V1.1", "当前仅返回预留任务，不执行实际批量分析。"),
    ("/api/v1/departments", "post"): ("创建部门", "V1.1", "创建内部组织部门。"),
    ("/api/v1/departments", "get"): ("查询部门列表", "V1.1", "分页查询部门。"),
    ("/api/v1/departments/{department_id}", "patch"): ("更新部门", "V3.0", "修改部门名称。"),
    ("/api/v1/departments/{department_id}", "delete"): ("删除部门", "V3.0", "永久删除没有用户、项目或邀请码引用的部门。"),
    ("/api/v1/invitations", "post"): ("生成邀请码", "V1.1", "为指定部门生成邀请码。"),
    ("/api/v1/invitations", "get"): ("查询邀请码列表", "V1.1", "分页查询邀请码。"),
    ("/api/v1/invitations/{invitation_id}/disable", "post"): ("停用邀请码", "V1.1", "停用尚未使用的邀请码。"),
    ("/api/v1/users", "get"): ("查询用户选择列表", "V3.0", "供项目成员和负责人选择器按姓名或部门查询已注册用户。"),
    ("/api/v1/interviews", "post"): ("创建访谈会话", "V2.0", "保存原始需求并调用 Dify 访谈 Workflow 生成第一轮追问。"),
    ("/api/v1/interviews/attachments", "post"): ("上传访谈图片", "V2.0", "上传 PNG、JPG/JPEG 或 WEBP 图片，返回供创建或回答接口关联的附件 ID。"),
    ("/api/v1/interviews/attachments/{attachment_id}/content", "get"): ("预览访谈图片", "V2.0", "按附件 ID 返回原始图片内容，用于访谈工作台预览。"),
    ("/api/v1/interviews/drafts", "get"): ("查询未完成访谈", "V2.0", "查询草稿、访谈中、待确认或失败状态的会话。"),
    ("/api/v1/interviews/{session_id}", "get"): ("查询访谈详情", "V2.0", "返回对话记录、需求卡片、完整度和当前问题。"),
    ("/api/v1/interviews/{session_id}/messages", "post"): ("回答访谈问题", "V2.0", "保存用户回答并调用 Dify 生成字段抽取结果和下一问。"),
    ("/api/v1/interviews/{session_id}/actions/skip", "post"): ("跳过当前问题", "V2.0", "跳过当前字段；连续两次跳过会进入待确认。"),
    ("/api/v1/interviews/{session_id}/actions/unknown", "post"): ("标记为不清楚", "V2.0", "将当前字段标记为不清楚；与跳过共享连续计数。"),
    ("/api/v1/interviews/{session_id}/actions/summarize", "post"): ("按当前信息整理", "V2.0", "立即结束追问并进入需求确认。"),
    ("/api/v1/interviews/{session_id}/summary", "patch"): ("编辑需求总结", "V2.0", "人工修正右侧需求卡片和标题，人工值优先于后续 AI 抽取。"),
    ("/api/v1/interviews/{session_id}/confirm", "post"): ("确认并创建需求", "V2.0", "将访谈结果转为正式需求并调用 V1.1 需求分析 Workflow。"),
    ("/api/v1/interviews/{session_id}/abandon", "post"): ("放弃访谈", "V2.0", "结束未提交的访谈会话。"),
    ("/api/v1/requirements/{requirement_id}/interview", "get"): ("查询需求关联访谈", "V2.0", "从正式需求回查完整访谈记录。"),
}

TAG_META = {
    "health": "服务状态",
    "auth": "身份注册、登录与会话（V3.0）",
    "projects": "项目与成员管理（V3.0）",
    "tasks": "团队任务与泳道排序（V3.0）",
    "versions": "版本排期与参与人员（V3.0）",
    "requirements": "需求管理（V1.1/V2.0）",
    "interviews": "对话式需求访谈（V2.0）",
    "departments": "部门管理（V1.1）",
    "invitations": "邀请码管理（V1.1）",
    "users": "内部用户选择（V3.0）",
}


def build_schema() -> dict[str, Any]:
    schema = app.openapi()
    schema["info"].update(
        {
            "title": "极简 AI 团队需求管理智能体 API",
            "version": "3.0.0",
            "description": (
                "供 Apifox 导入和本地联调。V3.0 新增邀请注册、统一密码登录、"
                "HttpOnly Cookie 会话、CSRF、管理员权限、项目成员、项目级访问控制、团队任务和版本排期；"
                "Dify API Key 仍仅由后端环境变量持有。"
            ),
        }
    )
    schema["servers"] = [
        {"url": "http://127.0.0.1:8000", "description": "本地 FastAPI"}
    ]
    schema["tags"] = [
        {"name": name, "description": description}
        for name, description in TAG_META.items()
    ]

    missing: list[str] = []
    for path, path_item in schema["paths"].items():
        for method, operation in path_item.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            meta = OPERATION_META.get((path, method))
            if meta is None:
                missing.append(f"{method.upper()} {path}")
                continue
            summary, version, description = meta
            operation["summary"] = f"【{version}】 {summary}"
            operation["description"] = description
            operation["x-api-version"] = version

    if missing:
        raise RuntimeError(f"以下接口缺少中文元数据: {', '.join(missing)}")
    if len(OPERATION_META) != sum(
        method in {"get", "post", "put", "patch", "delete"}
        for item in schema["paths"].values()
        for method in item
    ):
        raise RuntimeError("中文接口元数据与实际路由数量不一致")
    return schema


def main() -> None:
    content = json.dumps(build_schema(), ensure_ascii=False, indent=2) + "\n"
    for path in OUTPUTS:
        path.write_text(content, encoding="utf-8")
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
