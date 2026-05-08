"""AI 调用成本追踪器.

记录每次 AI 调用的 model、tokens、cost、latency，提供统计查询。
"""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.generation_log import AIUsageLog


class CostTracker:
    """AI 调用成本统计."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_total_cost(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> float:
        """获取总成本."""
        stmt = select(func.sum(AIUsageLog.cost_usd)).where(AIUsageLog.success == True)
        if start_date:
            stmt = stmt.where(AIUsageLog.created_at >= start_date)
        if end_date:
            stmt = stmt.where(AIUsageLog.created_at <= end_date)
        result = await self.session.execute(stmt)
        return result.scalar() or 0.0

    async def get_cost_by_model(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict]:
        """按模型统计成本."""
        stmt = (
            select(
                AIUsageLog.model,
                func.count(AIUsageLog.id).label("call_count"),
                func.sum(AIUsageLog.input_tokens).label("total_input_tokens"),
                func.sum(AIUsageLog.output_tokens).label("total_output_tokens"),
                func.sum(AIUsageLog.cost_usd).label("total_cost_usd"),
                func.avg(AIUsageLog.latency_ms).label("avg_latency_ms"),
            )
            .where(AIUsageLog.success == True)
            .group_by(AIUsageLog.model)
            .order_by(func.sum(AIUsageLog.cost_usd).desc())
        )
        if start_date:
            stmt = stmt.where(AIUsageLog.created_at >= start_date)
        if end_date:
            stmt = stmt.where(AIUsageLog.created_at <= end_date)

        result = await self.session.execute(stmt)
        return [
            {
                "model": row.model,
                "call_count": row.call_count,
                "total_input_tokens": row.total_input_tokens or 0,
                "total_output_tokens": row.total_output_tokens or 0,
                "total_cost_usd": round(row.total_cost_usd or 0, 6),
                "avg_latency_ms": round(row.avg_latency_ms or 0, 1),
            }
            for row in result
        ]

    async def get_cost_by_operation(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict]:
        """按操作类型统计成本."""
        stmt = (
            select(
                AIUsageLog.operation,
                func.count(AIUsageLog.id).label("call_count"),
                func.sum(AIUsageLog.input_tokens).label("total_input_tokens"),
                func.sum(AIUsageLog.output_tokens).label("total_output_tokens"),
                func.sum(AIUsageLog.cost_usd).label("total_cost_usd"),
                func.avg(AIUsageLog.latency_ms).label("avg_latency_ms"),
            )
            .where(AIUsageLog.success == True)
            .group_by(AIUsageLog.operation)
            .order_by(func.sum(AIUsageLog.cost_usd).desc())
        )
        if start_date:
            stmt = stmt.where(AIUsageLog.created_at >= start_date)
        if end_date:
            stmt = stmt.where(AIUsageLog.created_at <= end_date)

        result = await self.session.execute(stmt)
        return [
            {
                "operation": row.operation,
                "call_count": row.call_count,
                "total_input_tokens": row.total_input_tokens or 0,
                "total_output_tokens": row.total_output_tokens or 0,
                "total_cost_usd": round(row.total_cost_usd or 0, 6),
                "avg_latency_ms": round(row.avg_latency_ms or 0, 1),
            }
            for row in result
        ]

    async def get_daily_cost(
        self,
        days: int = 30,
    ) -> list[dict]:
        """获取每日成本趋势."""
        start_date = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(
                func.date(AIUsageLog.created_at).label("date"),
                func.count(AIUsageLog.id).label("call_count"),
                func.sum(AIUsageLog.cost_usd).label("total_cost_usd"),
            )
            .where(AIUsageLog.success == True)
            .where(AIUsageLog.created_at >= start_date)
            .group_by(func.date(AIUsageLog.created_at))
            .order_by(func.date(AIUsageLog.created_at))
        )
        result = await self.session.execute(stmt)
        return [
            {
                "date": str(row.date),
                "call_count": row.call_count,
                "total_cost_usd": round(row.total_cost_usd or 0, 6),
            }
            for row in result
        ]

    async def get_failed_calls(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """获取失败的调用记录."""
        stmt = (
            select(AIUsageLog)
            .where(AIUsageLog.success == False)
            .order_by(AIUsageLog.created_at.desc())
            .limit(limit)
        )
        if start_date:
            stmt = stmt.where(AIUsageLog.created_at >= start_date)
        if end_date:
            stmt = stmt.where(AIUsageLog.created_at <= end_date)

        result = await self.session.execute(stmt)
        return [
            {
                "id": log.id,
                "model": log.model,
                "operation": log.operation,
                "error_detail": log.error_detail,
                "latency_ms": log.latency_ms,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in result.scalars()
        ]

    async def get_summary(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict:
        """获取综合统计摘要."""
        stmt = select(
            func.count(AIUsageLog.id).label("total_calls"),
            func.sum(AIUsageLog.cost_usd).label("total_cost"),
            func.sum(AIUsageLog.input_tokens).label("total_input_tokens"),
            func.sum(AIUsageLog.output_tokens).label("total_output_tokens"),
            func.avg(AIUsageLog.latency_ms).label("avg_latency"),
            func.count(AIUsageLog.id).filter(AIUsageLog.success == False).label("failed_calls"),
        )
        if start_date:
            stmt = stmt.where(AIUsageLog.created_at >= start_date)
        if end_date:
            stmt = stmt.where(AIUsageLog.created_at <= end_date)

        result = await self.session.execute(stmt)
        row = result.one()
        return {
            "total_calls": row.total_calls or 0,
            "total_cost_usd": round(row.total_cost or 0, 6),
            "total_input_tokens": row.total_input_tokens or 0,
            "total_output_tokens": row.total_output_tokens or 0,
            "avg_latency_ms": round(row.avg_latency or 0, 1),
            "failed_calls": row.failed_calls or 0,
            "success_rate": round(
                (1 - (row.failed_calls or 0) / max(row.total_calls or 1, 1)) * 100, 2
            ),
        }
