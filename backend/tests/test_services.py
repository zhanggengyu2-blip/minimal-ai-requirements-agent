from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.core.exceptions import ConflictError, DifyInterviewTimeoutError, DifyTimeoutError
from app.db.models import (
    AnalysisStatus,
    Department,
    InterviewStatus,
    InvitationCode,
    InvitationStatus,
    Project,
    Requirement,
    RequirementPriority,
    RequirementType,
    UserAccount,
    UserRole,
)
from app.schemas.dify import (
    DifyAnalysisResult,
    DifyInterviewFields,
    DifyInterviewQuestion,
    DifyInterviewResult,
)
from app.schemas.interview import InterviewCreate, InterviewMessageCreate, InterviewSummaryUpdate
from app.schemas.organization import InvitationCreate
from app.schemas.requirement import RequirementCreate
from app.services.dify_interview_service import DifyInterviewWorkflowResult
from app.services.dify_service import DifyWorkflowResult
from app.services.interview_service import InterviewService
from app.services.organization_service import DepartmentService, InvitationService
from app.services.requirement_service import RequirementService


def _project(db_session, *, name: str = "Service 测试项目") -> Project:
    project = Project(name=name, project_context="Service 自动化测试上下文")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


def _analysis(*, related_id: str = "", duplicate: bool = False) -> DifyAnalysisResult:
    return DifyAnalysisResult(
        standard_content="支持批量导入并检查重复需求",
        business_goal="降低人工整理成本",
        type="NEW_FEATURE",
        priority="P2",
        is_fake=False,
        fake_reason="用户场景明确",
        is_duplicate=duplicate,
        related_id=related_id,
        reference_rule="TYPE-NEW；PRI-P2",
        analysis_summary="真实新增功能，建议按 P2 评估。",
    )


def _empty_interview_fields() -> DifyInterviewFields:
    return DifyInterviewFields(
        target_user=None,
        usage_scenario=None,
        user_goal=None,
        current_problem=None,
        expected_result=None,
        proposed_solution=None,
        frequency=None,
        impact_scope=None,
        bug_steps=None,
        actual_result=None,
        environment=None,
    )


def _interview_result() -> DifyInterviewWorkflowResult:
    return DifyInterviewWorkflowResult(
        interview=DifyInterviewResult(
            request_type="NEW_FEATURE",
            extracted_fields=_empty_interview_fields(),
            next_question=DifyInterviewQuestion(
                text="你通常在什么场景使用？",
                target_field="usage_scenario",
                reason_code="MISSING_CORE_FIELD",
            ),
            summary_title="待澄清需求",
        ),
        workflow_run_id="interview-run",
    )


@pytest.mark.asyncio
async def test_requirement_service_success_writes_analysis_fields(db_session):
    project = _project(db_session)
    dify = AsyncMock()
    dify.analyze_requirement.return_value = DifyWorkflowResult(_analysis(), "run-success")
    service = RequirementService(db_session, dify=dify)

    requirement = await service.create_and_analyze(
        RequirementCreate(project_id=project.id, raw_content="需要批量导入", analyze_with_ai=True),
        created_by="a" * 32,
    )

    assert requirement.analysis_status == AnalysisStatus.ANALYZED
    assert requirement.type == RequirementType.NEW_FEATURE
    assert requirement.priority == RequirementPriority.P2
    assert requirement.standard_content == "支持批量导入并检查重复需求"
    assert requirement.dify_workflow_run_id == "run-success"
    assert requirement.analysis_error_code is None


@pytest.mark.asyncio
async def test_requirement_service_app_error_persists_failed_state(db_session):
    project = _project(db_session)
    dify = AsyncMock()
    dify.analyze_requirement.side_effect = DifyTimeoutError()
    service = RequirementService(db_session, dify=dify)

    requirement = await service.create_and_analyze(
        RequirementCreate(project_id=project.id, raw_content="超时需求", analyze_with_ai=True),
        created_by="a" * 32,
    )

    db_session.expire_all()
    stored = db_session.get(Requirement, requirement.id)
    assert stored is not None
    assert stored.analysis_status == AnalysisStatus.FAILED
    assert stored.analysis_error_code == "DIFY_TIMEOUT"
    assert stored.raw_content == "超时需求"
    assert stored.standard_content is None


def test_requirement_candidates_are_same_project_analyzed_and_exclude_current(db_session):
    project = _project(db_session)
    other_project = _project(db_session, name="其他项目")
    rows = [
        Requirement(
            project_id=project.id,
            raw_content="当前",
            standard_content="当前标准内容",
            analysis_status=AnalysisStatus.ANALYZED,
        ),
        Requirement(
            project_id=project.id,
            raw_content="有效候选",
            standard_content="有效标准内容",
            analysis_status=AnalysisStatus.ANALYZED,
        ),
        Requirement(
            project_id=project.id,
            raw_content="仍在分析",
            standard_content="不可用内容",
            analysis_status=AnalysisStatus.ANALYZING,
        ),
        Requirement(
            project_id=other_project.id,
            raw_content="其他项目",
            standard_content="跨项目内容",
            analysis_status=AnalysisStatus.ANALYZED,
        ),
    ]
    db_session.add_all(rows)
    db_session.commit()

    candidates = RequirementService(db_session)._candidate_requirements(
        project.id, exclude_id=rows[0].id
    )

    assert candidates == [{"id": rows[1].id, "standard_content": "有效标准内容"}]


def test_requirement_list_combines_filters_and_escapes_wildcards(db_session):
    project = _project(db_session)
    wanted = Requirement(
        project_id=project.id,
        raw_content="导出 100%_完整数据",
        standard_content="批量导出",
        type=RequirementType.OPTIMIZATION,
        priority=RequirementPriority.P1,
        is_fake=False,
        analysis_status=AnalysisStatus.ANALYZED,
    )
    other = Requirement(project_id=project.id, raw_content="导出 100XX完整数据")
    db_session.add_all([wanted, other])
    db_session.commit()

    items, total = RequirementService(db_session).list(
        project_id=project.id,
        page=1,
        page_size=20,
        keyword="100%_",
        priority=RequirementPriority.P1,
        requirement_type=RequirementType.OPTIMIZATION,
        analysis_status=AnalysisStatus.ANALYZED,
        is_fake=False,
    )

    assert total == 1
    assert [item.id for item in items] == [wanted.id]


def test_department_reference_counts_and_invitation_creation(db_session):
    department = Department(name="测试部门")
    db_session.add(department)
    db_session.flush()
    db_session.add(Project(name="部门项目", project_context="上下文", department_id=department.id))
    db_session.commit()

    read = DepartmentService(db_session)._to_read(department)
    assert read.project_count == 1
    assert read.user_count == 0

    admin = db_session.scalar(select(UserAccount).where(UserAccount.role == UserRole.ADMIN))
    invitation = InvitationService(db_session).create(
        InvitationCreate(department_id=department.id, intended_user_name="用户"),
        actor_id=admin.id,
    )
    assert invitation.intended_user_name == "用户"
    assert DepartmentService(db_session)._to_read(department).invitation_count == 1


def test_used_invitation_cannot_be_disabled(db_session):
    department = Department(name="邀请码部门")
    db_session.add(department)
    db_session.flush()
    admin = db_session.scalar(select(UserAccount).where(UserAccount.role == UserRole.ADMIN))
    invitation_read = InvitationService(db_session).create(
        InvitationCreate(department_id=department.id), actor_id=admin.id
    )
    invitation = db_session.get(InvitationCode, invitation_read.id)
    invitation.status = InvitationStatus.USED
    db_session.commit()

    with pytest.raises(ConflictError, match="已使用"):
        InvitationService(db_session).disable(invitation_read.id)


@pytest.mark.asyncio
async def test_interview_two_agent_failures_enter_confirming(db_session):
    project = _project(db_session)
    dify = AsyncMock()
    dify.run_turn.side_effect = DifyInterviewTimeoutError()
    service = InterviewService(db_session, dify=dify)

    session = await service.create(
        InterviewCreate(
            project_id=project.id,
            raw_content="需要一个功能",
            client_message_id="initial-failure",
        ),
        created_by="a" * 32,
    )
    assert session.status == InterviewStatus.INTERVIEWING
    assert session.consecutive_agent_failures == 1

    session = await service.answer(
        session.id,
        InterviewMessageCreate(content="补充内容", client_message_id="answer-failure"),
    )
    assert session.status == InterviewStatus.CONFIRMING
    assert session.consecutive_agent_failures == 2
    assert session.stop_reason == "AGENT_FAILED_TWICE"


@pytest.mark.asyncio
async def test_manual_summary_edit_is_not_overwritten_by_ai(db_session):
    project = _project(db_session)
    dify = AsyncMock()
    dify.run_turn.return_value = _interview_result()
    service = InterviewService(db_session, dify=dify)
    session = await service.create(
        InterviewCreate(
            project_id=project.id,
            raw_content="需要优化流程",
            client_message_id="manual-edit-initial",
        ),
        created_by="a" * 32,
    )

    service.update_summary(
        session.id,
        InterviewSummaryUpdate(fields={"target_user": "产品经理"}),
    )
    fields = service._load_fields(session)
    assert fields["target_user"] == {
        "value": "产品经理",
        "evidence_message_ids": [],
        "source": "USER_EDIT",
    }

    incoming = DifyInterviewResult(
        request_type="NEW_FEATURE",
        extracted_fields=DifyInterviewFields(
            **{
                **_empty_interview_fields().model_dump(),
                "target_user": {
                    "value": "研发人员",
                    "evidence_message_ids": [session.messages[0].id],
                    "source": "USER_INPUT",
                },
            }
        ),
        next_question=None,
        summary_title="AI 摘要",
    )
    merged = service._merge_fields(
        fields, incoming, session=session, latest_message_id=session.messages[0].id
    )
    assert merged["target_user"]["value"] == "产品经理"
    assert merged["target_user"]["source"] == "USER_EDIT"


@pytest.mark.asyncio
async def test_interview_confirmation_is_idempotent_after_requirement_link(db_session):
    project = _project(db_session)
    interview_dify = AsyncMock()
    interview_dify.run_turn.return_value = _interview_result()
    requirement_dify = AsyncMock()
    requirement_dify.analyze_requirement.return_value = DifyWorkflowResult(
        _analysis(), "confirm-analysis"
    )
    requirement_service = RequirementService(db_session, dify=requirement_dify)
    service = InterviewService(
        db_session,
        dify=interview_dify,
        requirement_service=requirement_service,
    )
    session = await service.create(
        InterviewCreate(
            project_id=project.id,
            raw_content="访谈确认需求",
            client_message_id="confirm-initial",
        ),
        created_by="a" * 32,
    )
    service.summarize(session.id)

    from app.schemas.interview import InterviewConfirmRequest

    first_session, first_requirement = await service.confirm(
        session.id, InterviewConfirmRequest(idempotency_key="confirm-key-1")
    )
    second_session, second_requirement = await service.confirm(
        session.id, InterviewConfirmRequest(idempotency_key="confirm-key-2")
    )

    assert first_session.status == InterviewStatus.SUBMITTED
    assert second_session.id == first_session.id
    assert second_requirement.id == first_requirement.id
    assert requirement_dify.analyze_requirement.await_count == 1
