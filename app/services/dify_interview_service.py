import json
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    DifyError,
    DifyInterviewOutputError,
    DifyInterviewTimeoutError,
)
from app.schemas.dify import DifyInterviewResult


INTERVIEW_OUTPUT_FIELDS = frozenset(DifyInterviewResult.model_fields)


@dataclass(slots=True)
class DifyInterviewWorkflowResult:
    interview: DifyInterviewResult
    workflow_run_id: str | None = None


class DifyInterviewService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def run_turn(
        self,
        *,
        session_id: str,
        project_name: str,
        project_context: str,
        raw_content: str,
        messages: list[dict[str, Any]],
        current_fields: dict[str, Any],
        skipped_fields: list[str],
        latest_message_id: str,
        latest_action: str,
        current_round: int,
        source_channel: str,
    ) -> DifyInterviewWorkflowResult:
        if not self.settings.dify_interview_api_key:
            raise DifyError(
                "Dify 访谈 Workflow API Key 未配置",
                code="DIFY_INTERVIEW_NOT_CONFIGURED",
            )

        payload = {
            "inputs": {
                "project_name": project_name,
                "project_context": project_context,
                "raw_content": raw_content,
                "messages_json": json.dumps(messages, ensure_ascii=False),
                "current_fields_json": json.dumps(current_fields, ensure_ascii=False),
                "skipped_fields_json": json.dumps(skipped_fields, ensure_ascii=False),
                "latest_message_id": latest_message_id,
                "latest_action": latest_action,
                "current_round": current_round,
                "source_channel": source_channel,
            },
            "response_mode": "blocking",
            "user": f"interview:{session_id}",
        }
        headers = {
            "Authorization": f"Bearer {self.settings.dify_interview_api_key}",
            "Content-Type": "application/json",
        }

        try:
            timeout = httpx.Timeout(self.settings.dify_interview_timeout_seconds)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    self.settings.dify_interview_workflow_url,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise DifyInterviewTimeoutError() from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            try:
                error_body = exc.response.json()
            except ValueError:
                error_body = {}
            raise DifyError(
                f"Dify 访谈 Workflow 调用失败（HTTP {status}）",
                code="DIFY_INTERVIEW_HTTP_ERROR",
                details={
                    "http_status": status,
                    "dify_code": str(error_body.get("code", ""))[:100],
                },
            ) from exc
        except httpx.RequestError as exc:
            raise DifyError(
                "无法连接 Dify 访谈 Workflow 服务",
                code="DIFY_INTERVIEW_CONNECTION_ERROR",
            ) from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise DifyInterviewOutputError("response is not JSON") from exc

        data = body.get("data")
        if not isinstance(data, dict):
            raise DifyInterviewOutputError("missing data object")
        if data.get("status") == "failed" or data.get("error"):
            raise DifyError(
                "Dify 访谈 Workflow 执行失败",
                code="DIFY_INTERVIEW_WORKFLOW_FAILED",
                details={"error": str(data.get("error", "unknown"))[:500]},
            )

        raw_result = self._extract_interview(data.get("outputs"))
        try:
            interview = DifyInterviewResult.model_validate(raw_result)
        except ValidationError as exc:
            raise DifyInterviewOutputError(exc.errors(include_url=False)) from exc

        return DifyInterviewWorkflowResult(
            interview=interview,
            workflow_run_id=str(body.get("workflow_run_id") or data.get("id") or "") or None,
        )

    @classmethod
    def _extract_interview(cls, outputs: Any) -> dict[str, Any]:
        if not isinstance(outputs, dict):
            raise DifyInterviewOutputError("missing outputs object")

        candidate: Any = outputs
        if not INTERVIEW_OUTPUT_FIELDS.issubset(candidate):
            candidate = cls._decode_json(outputs.get("result"))
        if not isinstance(candidate, dict):
            raise DifyInterviewOutputError("输出缺少固定访谈字段")

        normalized = dict(candidate)
        for key in ("extracted_fields", "next_question", "validation_errors"):
            normalized[key] = cls._decode_json(normalized.get(key))
        return normalized

    @staticmethod
    def _decode_json(value: Any) -> Any:
        if not isinstance(value, str):
            return value
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
