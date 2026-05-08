"""CostTracker 单元测试."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.llm_cost_tracker import CostTracker


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def tracker(mock_session):
    return CostTracker(mock_session)


@pytest.mark.asyncio
async def test_get_total_cost(tracker, mock_session):
    """测试获取总成本."""
    mock_result = MagicMock()
    mock_result.scalar.return_value = 1.5
    mock_session.execute.return_value = mock_result

    cost = await tracker.get_total_cost()
    assert cost == 1.5


@pytest.mark.asyncio
async def test_get_total_cost_none(tracker, mock_session):
    """测试总成本为 None 时返回 0."""
    mock_result = MagicMock()
    mock_result.scalar.return_value = None
    mock_session.execute.return_value = mock_result

    cost = await tracker.get_total_cost()
    assert cost == 0.0


@pytest.mark.asyncio
async def test_get_total_cost_with_dates(tracker, mock_session):
    """测试带日期范围的总成本."""
    mock_result = MagicMock()
    mock_result.scalar.return_value = 0.5
    mock_session.execute.return_value = mock_result

    cost = await tracker.get_total_cost(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 12, 31),
    )
    assert cost == 0.5


@pytest.mark.asyncio
async def test_get_cost_by_model(tracker, mock_session):
    """测试按模型统计成本."""
    mock_row = MagicMock()
    mock_row.model = "claude-sonnet"
    mock_row.call_count = 10
    mock_row.total_input_tokens = 5000
    mock_row.total_output_tokens = 2000
    mock_row.total_cost_usd = 0.15
    mock_row.avg_latency_ms = 1500.0

    mock_result = MagicMock()
    mock_result.__iter__ = MagicMock(return_value=iter([mock_row]))
    mock_session.execute.return_value = mock_result

    results = await tracker.get_cost_by_model()
    assert len(results) == 1
    assert results[0]["model"] == "claude-sonnet"
    assert results[0]["call_count"] == 10


@pytest.mark.asyncio
async def test_get_cost_by_operation(tracker, mock_session):
    """测试按操作统计成本."""
    mock_row = MagicMock()
    mock_row.operation = "question_generation"
    mock_row.call_count = 5
    mock_row.total_input_tokens = 3000
    mock_row.total_output_tokens = 1500
    mock_row.total_cost_usd = 0.08
    mock_row.avg_latency_ms = 2000.0

    mock_result = MagicMock()
    mock_result.__iter__ = MagicMock(return_value=iter([mock_row]))
    mock_session.execute.return_value = mock_result

    results = await tracker.get_cost_by_operation()
    assert len(results) == 1
    assert results[0]["operation"] == "question_generation"


@pytest.mark.asyncio
async def test_get_daily_cost(tracker, mock_session):
    """测试每日成本趋势."""
    mock_row = MagicMock()
    mock_row.date = "2024-01-15"
    mock_row.call_count = 20
    mock_row.total_cost_usd = 0.25

    mock_result = MagicMock()
    mock_result.__iter__ = MagicMock(return_value=iter([mock_row]))
    mock_session.execute.return_value = mock_result

    results = await tracker.get_daily_cost(days=30)
    assert len(results) == 1
    assert results[0]["date"] == "2024-01-15"


@pytest.mark.asyncio
async def test_get_failed_calls(tracker, mock_session):
    """测试获取失败调用."""
    mock_log = MagicMock()
    mock_log.id = 1
    mock_log.model = "test-model"
    mock_log.operation = "test"
    mock_log.error_detail = "timeout"
    mock_log.latency_ms = 30000
    mock_log.created_at = datetime(2024, 1, 15)

    mock_result = MagicMock()
    mock_result.scalars.return_value = [mock_log]
    mock_session.execute.return_value = mock_result

    results = await tracker.get_failed_calls()
    assert len(results) == 1
    assert results[0]["error_detail"] == "timeout"


@pytest.mark.asyncio
async def test_get_summary(tracker, mock_session):
    """测试综合统计摘要."""
    mock_row = MagicMock()
    mock_row.total_calls = 100
    mock_row.total_cost = 1.5
    mock_row.total_input_tokens = 50000
    mock_row.total_output_tokens = 20000
    mock_row.avg_latency = 1500.0
    mock_row.failed_calls = 5

    mock_result = MagicMock()
    mock_result.one.return_value = mock_row
    mock_session.execute.return_value = mock_result

    summary = await tracker.get_summary()
    assert summary["total_calls"] == 100
    assert summary["total_cost_usd"] == 1.5
    assert summary["failed_calls"] == 5
    assert summary["success_rate"] == 95.0
