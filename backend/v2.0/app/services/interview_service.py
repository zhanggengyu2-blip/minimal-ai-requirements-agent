from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppError, ConflictError, DifyInterviewOutputError, NotFoundError
from app.db.models import (
    InterviewActionType,
    InterviewMessage,
    InterviewMessageRole,
    InterviewSession,
    InterviewStatus,
    Project,
    ProjectResolveMode,
    ProjectStatus,
    Requirement,
    RequirementType,
    SourceChannel,
)
from app.schemas.dify import (
    DifyInterviewField,
    DifyInterviewQuestion,
    DifyInterviewResult,
    InterviewFieldName,
)
from app.schemas.interview import (
    InterviewActionRequest,
    InterviewConfirmRequest,
    InterviewCreate,
    InterviewMessageCreate,
    InterviewSessionRead,
    InterviewSummaryUpdate,
)
from app.services.dify_interview_service import DifyInterviewService
from app.services.interview_attachment_service import InterviewAttachmentService
from app.services.requirement_service import RequirementService


FIELD_NAMES: tuple[InterviewFieldName, ...] = (
    "target_user",
    "usage_scenario",
    "user_goal",
    "current_problem",
    "expected_result",
    "proposed_solution",
    "frequency",
    "impact_scope",
    "bug_steps",
    "actual_result",
    "environment",
)

CORE_WEIGHTS: dict[InterviewFieldName, int] = {
    "target_user": 15,
    "usage_scenario": 20,
    "user_goal": 20,
    "current_problem": 25,
    "expected_result": 20,
}

QUESTION_ORDER: tuple[InterviewFieldName, ...] = (
    "current_problem",
    "usage_scenario",
    "user_goal",
    "target_user",
    "expected_result",
    "actual_result",
    "bug_steps",
    "environment",
    "frequency",
    "impact_scope",
)

FALLBACK_QUESTIONS: dict[InterviewFieldName, tuple[str, str]] = {
    "current_problem": ("目前具体卡在哪里，或者出现了什么结果？", "MISSING_CORE_FIELD"),
    "usage_scenario": ("通常在什么情况下会遇到这个问题？", "MISSING_CORE_FIELD"),
    "user_goal": ("当时你原本想完成什么事情？", "MISSING_CORE_FIELD"),
    "target_user": ("主要是谁会遇到这个问题或使用这个能力？", "MISSING_CORE_FIELD"),
    "expected_result": ("如果问题解决，你希望最终达到什么状态？", "MISSING_CORE_FIELD"),
    "actual_result": ("实际发生了什么，是否有报错或结果异常？", "MISSING_BUG_FIELD"),
    "bug_steps": ("可以简单说一下出现问题前做了哪些操作吗？", "MISSING_BUG_FIELD"),
    "environment": ("这个问题发生在哪个页面、客户端或系统环境？", "MISSING_BUG_FIELD"),
    "frequency": ("这个情况大概多久会发生一次？", "MISSING_RECOMMENDED_FIELD"),
    "impact_scope": ("目前主要影响哪些人或工作流程？", "MISSING_RECOMMENDED_FIELD"),
}

FIELD_LABELS: dict[InterviewFieldName, str] = {
    "target_user": "目标用户",
    "usage_scenario": "使用场景",
    "user_goal": "用户任务",
    "current_problem": "当前问题",
    "expected_result": "期望结果",
    "proposed_solution": "用户提出的方案",
    "frequency": "发生频率",
    "impact_scope": "影响范围",
    "bug_steps": "Bug 复现步骤",
    "actual_result": "实际结果",
    "environment": "发生环境",
}


class InterviewService:
    def __init__(
        self,
        db: Session,
        dify: DifyInterviewService | None = None,
        requirement_service: RequirementService | None = None,
    ) -> None:
        self.db = db
        self.dify = dify or DifyInterviewService()
        self.attachments = InterviewAttachmentService(db)
        self.requirements = requirement_service or RequirementService(db)
        self.settings = get_settings()

    async def create(self, payload: InterviewCreate, *, created_by: str) -> InterviewSession:
        existing = self.db.scalar(
            select(InterviewSession).where(
                InterviewSession.source_channel == SourceChannel.MANAGEMENT_WEB,
                InterviewSession.source_message_id == payload.client_message_id,
            )
        )
        if existing is not None:
            return existing

        project = self.db.get(Project, payload.project_id)
        if project is None:
            raise NotFoundError("项目不存在")
        if project.status != ProjectStatus.ACTIVE:
            raise ConflictError("归档项目不能创建需求访谈")

        session = InterviewSession(
            project_id=project.id,
            created_by=created_by,
            source_channel=SourceChannel.MANAGEMENT_WEB,
            source_user_id=created_by,
            source_message_id=payload.client_message_id,
            project_resolve_mode=ProjectResolveMode.USER_SELECTED,
            status=InterviewStatus.DRAFT,
            raw_content=payload.raw_content,
            structured_data=self._dump_fields(self._empty_fields()),
            skipped_fields="[]",
            prompt_version=self.settings.dify_interview_prompt_version,
        )
        self.db.add(session)
        self.db.flush()
        initial = InterviewMessage(
            session_id=session.id,
            sequence_no=1,
            role=InterviewMessageRole.USER,
            content=payload.raw_content,
            action_type=InterviewActionType.INITIAL,
            client_message_id=payload.client_message_id,
        )
        self.db.add(initial)
        self.db.flush()
        self.attachments.bind_to_message(
            payload.attachment_ids,
            session=session,
            message=initial,
            uploaded_by=created_by,
        )
        self.db.commit()
        self.db.refresh(session)

        await self._run_agent(session, initial, InterviewActionType.INITIAL)
        return session

    def get(self, session_id: str) -> InterviewSession:
        session = self.db.get(InterviewSession, session_id)
        if session is None:
            raise NotFoundError("访谈会话不存在")
        return session

    async def answer(
        self, session_id: str, payload: InterviewMessageCreate
    ) -> InterviewSession:
        session = self.get(session_id)
        self._ensure_can_continue(session)
        duplicate = self.db.scalar(
            select(InterviewMessage).where(
                InterviewMessage.session_id == session.id,
                InterviewMessage.client_message_id == payload.client_message_id,
            )
        )
        if duplicate is not None:
            return session

        session.status = InterviewStatus.INTERVIEWING
        session.stop_reason = None
        session.round_count += 1
        session.consecutive_skip_count = 0
        message = self._append_message(
            session,
            role=InterviewMessageRole.USER,
            content=payload.content,
            action_type=InterviewActionType.ANSWER,
            client_message_id=payload.client_message_id,
        )
        self.attachments.bind_to_message(
            payload.attachment_ids,
            session=session,
            message=message,
            uploaded_by=session.created_by,
        )
        self.db.commit()
        await self._run_agent(session, message, InterviewActionType.ANSWER)
        return session

    async def skip_or_unknown(
        self,
        session_id: str,
        payload: InterviewActionRequest,
        *,
        action: InterviewActionType,
    ) -> InterviewSession:
        session = self.get(session_id)
        self._ensure_can_continue(session)
        duplicate = self.db.scalar(
            select(InterviewMessage).where(
                InterviewMessage.session_id == session.id,
                InterviewMessage.client_message_id == payload.client_message_id,
            )
        )
        if duplicate is not None:
            return session

        question = self._current_question(session)
        if question is None:
            raise ConflictError("当前没有可跳过的问题")
        skipped = self._load_skipped(session)
        if question.target_field not in skipped:
            skipped.append(question.target_field)
        session.skipped_fields = json.dumps(skipped, ensure_ascii=False)
        session.status = InterviewStatus.INTERVIEWING
        session.round_count += 1
        session.consecutive_skip_count += 1
        content = "不清楚" if action == InterviewActionType.UNKNOWN else "跳过这个问题"
        message = self._append_message(
            session,
            role=InterviewMessageRole.USER,
            content=content,
            action_type=action,
            target_field=question.target_field,
            client_message_id=payload.client_message_id,
        )
        self.db.commit()

        if session.consecutive_skip_count >= 2:
            self._enter_confirming(session, "CONSECUTIVE_SKIPS")
            self.db.commit()
            return session
        await self._run_agent(session, message, action)
        return session

    def summarize(self, session_id: str) -> InterviewSession:
        session = self.get(session_id)
        self._ensure_can_continue(session)
        self._enter_confirming(session, "USER_DIRECT_SUMMARY")
        self.db.commit()
        return session

    def update_summary(
        self, session_id: str, payload: InterviewSummaryUpdate
    ) -> InterviewSession:
        session = self.get(session_id)
        self._ensure_can_continue(session)
        fields = self._load_fields(session)
        for name, value in payload.fields.items():
            fields[name] = (
                None
                if value is None
                else {"value": value, "evidence_message_ids": [], "source": "USER_EDIT"}
            )
        if payload.summary_title is not None:
            session.summary_title = payload.summary_title.strip()
        session.structured_data = self._dump_fields(fields)
        session.completeness_score = self._completeness(fields)
        session.clarified_content = self._render_clarified(fields)
        self.db.commit()
        return session

    async def confirm(
        self, session_id: str, payload: InterviewConfirmRequest
    ) -> tuple[InterviewSession, Requirement]:
        session = self.get(session_id)
        if session.requirement_id:
            requirement = self.db.get(Requirement, session.requirement_id)
            if requirement is None:
                raise ConflictError("会话已提交但关联需求不存在")
            return session, requirement
        if session.status != InterviewStatus.CONFIRMING:
            raise ConflictError("请先完成整理再确认提交")

        session.confirm_idempotency_key = payload.idempotency_key
        fields = self._load_fields(session)
        session.clarified_content = self._render_clarified(fields)
        self.db.commit()

        requirement = await self.requirements.create_from_interview(
            project_id=session.project_id,
            raw_content=session.raw_content,
            clarified_content=session.clarified_content,
            interview_session_id=session.id,
            interview_rounds=session.round_count,
            completeness_score=session.completeness_score,
            created_by=session.created_by,
        )
        session.requirement_id = requirement.id
        session.status = InterviewStatus.SUBMITTED
        session.stop_reason = session.stop_reason or "USER_CONFIRMED"
        self.db.commit()
        self.db.refresh(session)
        return session, requirement

    def abandon(self, session_id: str) -> InterviewSession:
        session = self.get(session_id)
        if session.status == InterviewStatus.SUBMITTED:
            raise ConflictError("已提交的访谈不能放弃")
        session.status = InterviewStatus.ABANDONED
        session.stop_reason = "USER_ABANDONED"
        self.db.commit()
        return session

    def drafts(self, *, created_by: str | None, limit: int = 20) -> list[InterviewSession]:
        query = select(InterviewSession).where(
            InterviewSession.status.in_(
                [
                    InterviewStatus.DRAFT,
                    InterviewStatus.INTERVIEWING,
                    InterviewStatus.CONFIRMING,
                    InterviewStatus.FAILED,
                ]
            )
        )
        if created_by is not None:
            query = query.where(InterviewSession.created_by == created_by)
        return list(
            self.db.scalars(query.order_by(InterviewSession.updated_time.desc()).limit(limit))
        )

    def to_read(self, session: InterviewSession) -> InterviewSessionRead:
        return InterviewSessionRead(
            id=session.id,
            project_id=session.project_id,
            created_by=session.created_by,
            source_channel=session.source_channel,
            project_resolve_mode=session.project_resolve_mode,
            status=session.status,
            raw_content=session.raw_content,
            request_type=session.request_type,
            current_card=self._load_fields(session),
            skipped_fields=self._load_skipped(session),
            completeness_score=session.completeness_score,
            round_count=session.round_count,
            consecutive_skip_count=session.consecutive_skip_count,
            stop_reason=session.stop_reason,
            summary_title=session.summary_title,
            clarified_content=session.clarified_content,
            requirement_id=session.requirement_id,
            current_question=self._current_question(session),
            messages=list(session.messages),
            agent_error_code=session.agent_error_code,
            created_time=session.created_time,
            updated_time=session.updated_time,
        )

    async def _run_agent(
        self,
        session: InterviewSession,
        latest_message: InterviewMessage,
        action: InterviewActionType,
    ) -> None:
        project = self.db.get(Project, session.project_id)
        if project is None:
            raise NotFoundError("项目不存在")
        fields = self._load_fields(session)
        skipped = self._load_skipped(session)

        try:
            result = await self.dify.run_turn(
                session_id=session.id,
                project_name=project.name,
                project_context=project.project_context,
                raw_content=session.raw_content,
                messages=self._messages_for_dify(session),
                current_fields=fields,
                skipped_fields=skipped,
                latest_message_id=latest_message.id,
                latest_action=action.value,
                current_round=session.round_count,
                source_channel=session.source_channel.value,
                images=[
                    {
                        "attachment_id": attachment.id,
                        "path": attachment.storage_path,
                        "name": attachment.original_name,
                        "mime_type": attachment.mime_type,
                        "dify_upload_file_id": attachment.dify_upload_file_id,
                        "dify_user": attachment.dify_user,
                    }
                    for attachment in latest_message.attachments
                ],
            )
            if result.uploaded_file_ids:
                for attachment in latest_message.attachments:
                    upload_file_id = result.uploaded_file_ids.get(attachment.id)
                    if upload_file_id:
                        attachment.dify_upload_file_id = upload_file_id
                        attachment.dify_user = f"interview:{session.id}"
            fields = self._merge_fields(
                fields,
                result.interview,
                session=session,
                latest_message_id=latest_message.id,
            )
            session.structured_data = self._dump_fields(fields)
            session.request_type = (
                RequirementType(result.interview.request_type)
                if result.interview.request_type
                else session.request_type
            )
            session.summary_title = result.interview.summary_title
            session.consecutive_agent_failures = 0
            session.agent_error_code = None
            session.agent_error_message = None
            proposed_question = result.interview.next_question
            workflow_run_id = result.workflow_run_id
        except AppError as exc:
            session.consecutive_agent_failures += 1
            session.agent_error_code = exc.code
            session.agent_error_message = exc.message
            proposed_question = None
            workflow_run_id = None

        session.completeness_score = self._completeness(fields)
        session.clarified_content = self._render_clarified(fields)
        stop_reason = self._stop_reason(session, fields)
        if stop_reason:
            self._enter_confirming(session, stop_reason)
            self.db.commit()
            return

        question = self._validated_question(proposed_question, fields, skipped)
        if question is None:
            question = self._fallback_question(fields, skipped, session.request_type)
        if question is None:
            self._enter_confirming(session, "NO_FURTHER_QUESTION")
            self.db.commit()
            return

        session.status = InterviewStatus.INTERVIEWING
        session.stop_reason = None
        self._append_message(
            session,
            role=InterviewMessageRole.AGENT,
            content=question.text,
            target_field=question.target_field,
            reason_code=question.reason_code,
            agent_run_id=workflow_run_id,
        )
        self.db.commit()
        self.db.refresh(session)

    def _merge_fields(
        self,
        current: dict[str, Any],
        result: DifyInterviewResult,
        *,
        session: InterviewSession,
        latest_message_id: str,
    ) -> dict[str, Any]:
        merged = dict(current)
        user_message_ids = {
            message.id
            for message in session.messages
            if message.role == InterviewMessageRole.USER
        }
        incoming = result.extracted_fields.model_dump(mode="json")
        invalid_core_count = 0
        for name in FIELD_NAMES:
            value = incoming[name]
            if value is None:
                continue
            old = merged.get(name)
            if value["source"] == "USER_EDIT":
                if old and old.get("source") == "USER_EDIT" and old.get("value") == value["value"]:
                    continue
                invalid_core_count += int(name in CORE_WEIGHTS)
                continue
            evidence = set(value["evidence_message_ids"])
            if not evidence or not evidence.issubset(user_message_ids):
                invalid_core_count += int(name in CORE_WEIGHTS)
                continue
            if old and old.get("source") == "USER_EDIT":
                continue
            if old is None or latest_message_id in evidence or old.get("value") == value["value"]:
                merged[name] = value
        if invalid_core_count >= 2:
            raise DifyInterviewOutputError("多个核心字段的证据消息 ID 非法")
        return merged

    @staticmethod
    def _validated_question(
        question: DifyInterviewQuestion | None,
        fields: dict[str, Any],
        skipped: list[str],
    ) -> DifyInterviewQuestion | None:
        if question is None or question.target_field in skipped:
            return None
        if fields.get(question.target_field) is not None and question.reason_code != "CLARIFY_CONFLICT":
            return None
        question_marks = question.text.count("？") + question.text.count("?")
        if question_marks > 1:
            return None
        return question

    def _fallback_question(
        self,
        fields: dict[str, Any],
        skipped: list[str],
        request_type: RequirementType | None,
    ) -> DifyInterviewQuestion | None:
        for name in QUESTION_ORDER:
            if name in skipped or fields.get(name) is not None:
                continue
            if name in {"actual_result", "bug_steps", "environment"} and request_type != RequirementType.BUG:
                continue
            text, reason = FALLBACK_QUESTIONS[name]
            return DifyInterviewQuestion(text=text, target_field=name, reason_code=reason)
        return None

    def _stop_reason(self, session: InterviewSession, fields: dict[str, Any]) -> str | None:
        if session.consecutive_agent_failures >= 2:
            return "AGENT_FAILED_TWICE"
        if session.consecutive_skip_count >= 2:
            return "CONSECUTIVE_SKIPS"
        max_rounds = 5 if session.request_type == RequirementType.BUG else 4
        if session.round_count >= max_rounds:
            return "MAX_ROUNDS_REACHED"
        if session.completeness_score >= 80 and self._type_requirements_met(
            session.request_type, fields
        ):
            return "CORE_FIELDS_SUFFICIENT"
        return None

    @staticmethod
    def _type_requirements_met(
        request_type: RequirementType | None, fields: dict[str, Any]
    ) -> bool:
        if request_type != RequirementType.BUG:
            return True
        completed = sum(
            fields.get(name) is not None
            for name in ("bug_steps", "actual_result", "expected_result")
        )
        return fields.get("actual_result") is not None and completed >= 2

    @staticmethod
    def _completeness(fields: dict[str, Any]) -> int:
        return sum(weight for name, weight in CORE_WEIGHTS.items() if fields.get(name) is not None)

    def _enter_confirming(self, session: InterviewSession, reason: str) -> None:
        session.status = InterviewStatus.CONFIRMING
        session.stop_reason = reason
        session.clarified_content = self._render_clarified(self._load_fields(session))

    @staticmethod
    def _ensure_can_continue(session: InterviewSession) -> None:
        if session.status == InterviewStatus.SUBMITTED:
            raise ConflictError("该访谈已经提交")
        if session.status == InterviewStatus.ABANDONED:
            raise ConflictError("该访谈已放弃")

    def _append_message(
        self,
        session: InterviewSession,
        *,
        role: InterviewMessageRole,
        content: str,
        action_type: InterviewActionType | None = None,
        target_field: str | None = None,
        reason_code: str | None = None,
        client_message_id: str | None = None,
        agent_run_id: str | None = None,
    ) -> InterviewMessage:
        sequence_no = max((item.sequence_no for item in session.messages), default=0) + 1
        message = InterviewMessage(
            session_id=session.id,
            sequence_no=sequence_no,
            role=role,
            content=content,
            action_type=action_type,
            target_field=target_field,
            reason_code=reason_code,
            client_message_id=client_message_id,
            agent_run_id=agent_run_id,
        )
        self.db.add(message)
        session.messages.append(message)
        return message

    @staticmethod
    def _empty_fields() -> dict[str, None]:
        return {name: None for name in FIELD_NAMES}

    def _load_fields(self, session: InterviewSession) -> dict[str, Any]:
        try:
            parsed = json.loads(session.structured_data)
        except (TypeError, json.JSONDecodeError):
            parsed = {}
        return {name: parsed.get(name) for name in FIELD_NAMES}

    @staticmethod
    def _dump_fields(fields: dict[str, Any]) -> str:
        return json.dumps(fields, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _load_skipped(session: InterviewSession) -> list[InterviewFieldName]:
        try:
            values = json.loads(session.skipped_fields)
        except (TypeError, json.JSONDecodeError):
            return []
        return [value for value in values if value in FIELD_NAMES]

    @staticmethod
    def _messages_for_dify(session: InterviewSession) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        for item in session.messages:
            message: dict[str, Any] = {
                "id": item.id,
                "role": item.role.value,
                "content": item.content,
            }
            if item.action_type:
                message["action_type"] = item.action_type.value
            if item.target_field:
                message["target_field"] = item.target_field
            if item.attachments:
                message["attachments"] = [
                    {
                        "id": attachment.id,
                        "name": attachment.original_name,
                        "mime_type": attachment.mime_type,
                    }
                    for attachment in item.attachments
                ]
            messages.append(message)
        return messages

    @staticmethod
    def _render_clarified(fields: dict[str, Any]) -> str:
        lines: list[str] = []
        for name in FIELD_NAMES:
            field = fields.get(name)
            if field is None and name not in CORE_WEIGHTS:
                continue
            value = field["value"] if field else "待补充"
            lines.append(f"【{FIELD_LABELS[name]}】{value}")
        return "\n".join(lines)

    def _current_question(self, session: InterviewSession) -> DifyInterviewQuestion | None:
        if session.status != InterviewStatus.INTERVIEWING:
            return None
        for item in reversed(session.messages):
            if item.role == InterviewMessageRole.USER:
                return None
            if item.role == InterviewMessageRole.AGENT and item.target_field and item.reason_code:
                return DifyInterviewQuestion(
                    text=item.content,
                    target_field=item.target_field,
                    reason_code=item.reason_code,
                )
        return None
