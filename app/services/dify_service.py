import json
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.core.exceptions import DifyError, DifyOutputError, DifyTimeoutError
from app.schemas.dify import DifyAnalysisResult


ANALYSIS_FIELDS = frozenset(DifyAnalysisResult.model_fields)


@dataclass(slots=True)
class DifyWorkflowResult:
    analysis: DifyAnalysisResult
    workflow_run_id: str | None = None


class DifyService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def analyze_requirement(
        self,
        *,
        project_name: str,
        project_context: str,
        raw_content: str,
        candidates: list[dict[str, str]],
        user: str,
    ) -> DifyWorkflowResult:
        if not self.settings.dify_api_key:
            raise DifyError("Dify API Key 未配置", code="DIFY_NOT_CONFIGURED")

        payload = {
            "inputs": {
                "project_name": project_name,
                "project_context": project_context,
                "raw_content": raw_content,
                "candidate_requirements": json.dumps(candidates, ensure_ascii=False),
            },
            "response_mode": "blocking",
            "user": user,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.dify_api_key}",
            "Content-Type": "application/json",
        }

        try:
            timeout = httpx.Timeout(self.settings.dify_timeout_seconds)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(self.settings.dify_workflow_url, headers=headers, json=payload)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise DifyTimeoutError() from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise DifyError(
                f"Dify Workflow 调用失败（HTTP {status}）",
                code="DIFY_HTTP_ERROR",
                details={"http_status": status},
            ) from exc
        except httpx.RequestError as exc:
            raise DifyError("无法连接 Dify Workflow 服务", code="DIFY_CONNECTION_ERROR") from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise DifyOutputError("response is not JSON") from exc

        data = body.get("data")
        if not isinstance(data, dict):
            raise DifyOutputError("missing data object")
        if data.get("status") == "failed" or data.get("error"):
            raise DifyError(
                "Dify Workflow 执行失败",
                code="DIFY_WORKFLOW_FAILED",
                details={"error": str(data.get("error", "unknown"))[:500]},
            )

        outputs = data.get("outputs")
        raw_result = self._extract_analysis(outputs)
        try:
            analysis = DifyAnalysisResult.model_validate(raw_result)
        except ValidationError as exc:
            raise DifyOutputError(exc.errors(include_url=False)) from exc

        candidate_ids = {item["id"] for item in candidates}
        if analysis.is_duplicate and analysis.related_id not in candidate_ids:
            raise DifyOutputError("related_id 不在当前项目候选需求中")

        return DifyWorkflowResult(
            analysis=analysis,
            workflow_run_id=str(body.get("workflow_run_id") or data.get("id") or "") or None,
        )

    @staticmethod
    def _extract_analysis(outputs: Any) -> dict[str, Any]:
        if not isinstance(outputs, dict):
            raise DifyOutputError("missing outputs object")

        # 设计文档要求 10 个变量作为 outputs 顶层字段返回。
        if ANALYSIS_FIELDS.issubset(outputs):
            return {field: outputs[field] for field in ANALYSIS_FIELDS}

        # 兼容 Dify 将结构化结果放在 result 中的常见配置误差。
        nested = outputs.get("result")
        if isinstance(nested, str):
            try:
                nested = json.loads(nested)
            except json.JSONDecodeError as exc:
                raise DifyOutputError("outputs.result is not valid JSON") from exc
        if isinstance(nested, dict):
            return nested
        raise DifyOutputError("outputs 缺少固定的 10 个分析字段")

