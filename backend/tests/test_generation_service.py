"""GenerationService 单元测试."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.generation import GenerationRequest
from app.services.generation_service import GenerationService, _knowledge_to_dicts


def _make_mock_generation_log(**kwargs):
    """创建 mock GenerationLog."""
    log = MagicMock()
    log.id = kwargs.get("id", 1)
    log.template_id = kwargs.get("template_id", 1)
    log.paper_id = kwargs.get("paper_id")
    log.status = kwargs.get("status", "pending")
    log.current_step = kwargs.get("current_step", "等待开始")
    log.progress_pct = kwargs.get("progress_pct", 0.0)
    log.error_message = kwargs.get("error_message")
    log.processing_time_seconds = kwargs.get("processing_time_seconds")
    log.planner_output = kwargs.get("planner_output")
    log.retriever_output = kwargs.get("retriever_output")
    log.generator_output = kwargs.get("generator_output")
    log.validator_output = kwargs.get("validator_output")
    return log


def _make_mock_template():
    """创建 mock PaperTemplate."""
    t = MagicMock()
    t.id = 1
    t.name = "期中考试"
    t.stage = "初中"
    t.grade = "七年级"
    t.subject = "数学"
    t.total_score = 100
    t.duration_minutes = 120
    t.structure = {"sections": [{"name": "选择题", "type": "choice", "count": 10}]}
    return t


@pytest.mark.asyncio
async def test_start_generation():
    """测试开始生成任务."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    svc = GenerationService(session)
    request = GenerationRequest(template_id=1)

    # 模拟 flush 后获得 id
    def set_id(obj):
        obj.id = 1
    session.flush = AsyncMock(side_effect=lambda: set_id(session.add.call_args[0][0]) if session.add.called else None)

    await svc.start_generation(request)

    session.add.assert_called_once()
    session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_update_progress():
    """测试更新进度."""
    session = AsyncMock()
    mock_log = _make_mock_generation_log()
    session.get = AsyncMock(return_value=mock_log)
    session.flush = AsyncMock()

    svc = GenerationService(session)
    await svc.update_progress(1, "planning", "正在制定计划", 25.0)

    assert mock_log.status == "planning"
    assert mock_log.current_step == "正在制定计划"
    assert mock_log.progress_pct == 25.0
    session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_update_progress_not_found():
    """测试更新不存在的任务进度."""
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.flush = AsyncMock()

    svc = GenerationService(session)
    await svc.update_progress(999, "planning", "test", 10.0)

    session.flush.assert_not_called()


@pytest.mark.asyncio
async def test_complete_generation():
    """测试完成生成."""
    session = AsyncMock()
    mock_log = _make_mock_generation_log()
    session.get = AsyncMock(return_value=mock_log)
    session.flush = AsyncMock()

    svc = GenerationService(session)
    await svc.complete_generation(1, paper_id=42, processing_time=12.5)

    assert mock_log.status == "completed"
    assert mock_log.paper_id == 42
    assert mock_log.progress_pct == 100.0
    assert mock_log.processing_time_seconds == 12.5


@pytest.mark.asyncio
async def test_fail_generation():
    """测试标记生成失败."""
    session = AsyncMock()
    mock_log = _make_mock_generation_log()
    session.get = AsyncMock(return_value=mock_log)
    session.flush = AsyncMock()

    svc = GenerationService(session)
    await svc.fail_generation(1, "模板不存在")

    assert mock_log.status == "failed"
    assert mock_log.error_message == "模板不存在"


def test_template_to_dict():
    """测试模板转字典."""
    t = _make_mock_template()
    d = GenerationService._template_to_dict(t)

    assert d["id"] == 1
    assert d["name"] == "期中考试"
    assert d["stage"] == "初中"
    assert d["total_score"] == 100


def test_knowledge_to_dicts():
    """测试知识点树转字典."""
    child = MagicMock()
    child.id = 2
    child.name = "方程"
    child.level = "knowledge_point"
    child.stage = "初中"
    child.grade = "七年级"
    child.description = "一元一次方程"
    child.children = []

    parent = MagicMock()
    parent.id = 1
    parent.name = "代数"
    parent.level = "chapter"
    parent.stage = "初中"
    parent.grade = "七年级"
    parent.description = "代数基础"
    parent.children = [child]

    result = _knowledge_to_dicts([parent])

    assert len(result) == 1
    assert result[0]["id"] == 1
    assert result[0]["name"] == "代数"
    assert len(result[0]["children"]) == 1
    assert result[0]["children"][0]["name"] == "方程"


@pytest.mark.asyncio
@patch("app.services.generation_service.AssemblerAgent")
@patch("app.services.generation_service.ValidatorAgent")
@patch("app.services.generation_service.GeneratorAgent")
@patch("app.services.generation_service.RetrieverAgent")
@patch("app.services.generation_service.PlannerAgent")
@patch("app.services.generation_service.KnowledgeService")
@patch("app.services.generation_service.RetrievalService")
@patch("app.services.generation_service.ValidationService")
async def test_generate_paper_success(
    mock_validation_svc_cls,
    mock_retrieval_svc_cls,
    mock_knowledge_svc_cls,
    mock_planner_cls,
    mock_retriever_cls,
    mock_generator_cls,
    mock_validator_cls,
    mock_assembler_cls,
):
    """测试完整的试卷生成管线."""
    session = AsyncMock()

    # mock template
    mock_template = _make_mock_template()
    session.get = AsyncMock(return_value=mock_template)

    # mock KnowledgeService
    mock_knowledge_svc = MagicMock()
    mock_knowledge_svc.get_tree = AsyncMock(return_value=[])
    mock_knowledge_svc_cls.return_value = mock_knowledge_svc

    # mock RetrievalService
    mock_retrieval_svc = MagicMock()
    mock_retrieval_svc_cls.return_value = mock_retrieval_svc

    # mock ValidationService
    mock_validation_svc = MagicMock()
    mock_validation_svc_cls.return_value = mock_validation_svc

    # mock question stats query
    stats_result = MagicMock()
    stats_result.__iter__ = MagicMock(return_value=iter([]))
    session.execute = AsyncMock(return_value=stats_result)

    # mock PlannerAgent
    mock_planner = MagicMock()
    mock_planner.run = AsyncMock(return_value={
        "sections_plan": [{"name": "选择题"}],
        "total_questions": 10,
    })
    mock_planner_cls.return_value = mock_planner

    # mock RetrieverAgent
    mock_retriever = MagicMock()
    mock_retriever.run = AsyncMock(return_value={
        "sections": [{"selected": [], "selected_count": 5, "gaps": []}],
    })
    mock_retriever_cls.return_value = mock_retriever

    # mock GeneratorAgent
    mock_generator = MagicMock()
    mock_generator.run = AsyncMock(return_value={
        "generated_questions": [],
    })
    mock_generator_cls.return_value = mock_generator

    # mock ValidatorAgent
    mock_validator = MagicMock()
    mock_validator.run = AsyncMock(return_value={
        "is_valid": True,
        "issues": [],
    })
    mock_validator_cls.return_value = mock_validator

    # mock AssemblerAgent
    mock_assembler = MagicMock()
    mock_assembler.run = AsyncMock(return_value={
        "paper_id": 42,
        "stats": {"total_score": 100},
    })
    mock_assembler_cls.return_value = mock_assembler

    session.commit = AsyncMock()
    session.flush = AsyncMock()

    svc = GenerationService(session)
    request = GenerationRequest(template_id=1)
    result = await svc.generate_paper(log_id=1, request=request)

    assert result["paper_id"] == 42
    assert "stats" in result


@pytest.mark.asyncio
async def test_generate_paper_template_not_found():
    """测试模板不存在时的生成."""
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.commit = AsyncMock()
    session.flush = AsyncMock()

    mock_log = _make_mock_generation_log()
    # 第一次 get 返回 None（模板），第二次返回 log
    session.get = AsyncMock(side_effect=[None, mock_log])

    svc = GenerationService(session)
    request = GenerationRequest(template_id=999)
    result = await svc.generate_paper(log_id=1, request=request)

    assert "error" in result
    assert "模板不存在" in result["error"]
