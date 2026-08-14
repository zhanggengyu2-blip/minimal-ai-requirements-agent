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
    ROOT / "docs" / "openapi-v2.0-apifox.json",
)

OPERATION_META: dict[tuple[str, str], tuple[str, str, str]] = {
    ("/api/v1/health", "get"): ("健康检查", "V1.1", "检查 FastAPI 服务是否可访问。"),
    ("/api/v1/projects", "post"): ("创建项目", "V1.1", "创建需求所属项目。"),
    ("/api/v1/projects", "get"): ("查询项目列表", "V1.1", "分页查询项目。"),
    ("/api/v1/requirements", "post"): ("直接创建并分析需求", "V1.1", "不经过访谈，直接保存原始需求并调用需求分析 Workflow。"),
    ("/api/v1/requirements", "get"): ("查询需求列表", "V1.1", "分页、筛选和搜索需求。"),
    ("/api/v1/requirements/{requirement_id}", "get"): ("查询需求详情", "V1.1", "按需求 ID 查询需求详情。"),
    ("/api/v1/requirements/batch-analyze", "post"): ("批量分析需求（预留）", "V1.1", "当前仅返回预留任务，不执行实际批量分析。"),
    ("/api/v1/departments", "post"): ("创建部门", "V1.1", "创建内部组织部门。"),
    ("/api/v1/departments", "get"): ("查询部门列表", "V1.1", "分页查询部门。"),
    ("/api/v1/departments/{department_id}", "patch"): ("更新部门", "V1.1", "修改部门名称或状态。"),
    ("/api/v1/invitations", "post"): ("生成邀请码", "V1.1", "为指定部门生成邀请码。"),
    ("/api/v1/invitations", "get"): ("查询邀请码列表", "V1.1", "分页查询邀请码。"),
    ("/api/v1/invitations/{invitation_id}/disable", "post"): ("停用邀请码", "V1.1", "停用尚未使用的邀请码。"),
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
    "projects": "项目管理（V1.1）",
    "requirements": "需求管理（V1.1/V2.0）",
    "interviews": "对话式需求访谈（V2.0）",
    "departments": "部门管理（V1.1）",
    "invitations": "邀请码管理（V1.1）",
}


def build_schema() -> dict[str, Any]:
    schema = app.openapi()
    schema["info"].update(
        {
            "title": "极简 AI 团队需求管理智能体 API",
            "version": "2.0.0",
            "description": (
                "供 Apifox 导入和本地联调。V1.1 接口保持兼容，V2.0 新增对话式需求访谈。"
                "当前未实现登录鉴权；Dify API Key 仅由后端环境变量持有。"
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
