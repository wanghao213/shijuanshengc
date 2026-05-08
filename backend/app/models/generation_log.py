"""生成日志与AI计量模型."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class GenerationLog(Base):
    """生成日志."""

    __tablename__ = "generation_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("paper_templates.id"), nullable=True
    )
    paper_id: Mapped[int | None] = mapped_column(
        ForeignKey("papers.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # 'pending'/'planning'/'retrieving'/'generating'/'validating'/'assembling'/'completed'/'failed'
    current_step: Mapped[str | None] = mapped_column(String(200), nullable=True)
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0)

    # Agent 执行记录
    planner_output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    retriever_output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    generator_output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    validator_output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_time_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 关系
    usage_logs: Mapped[list["AIUsageLog"]] = relationship(back_populates="generation_log")


class AIUsageLog(Base):
    """AI 调用计量，追踪每次 LLM 调用的成本."""

    __tablename__ = "ai_usage_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    generation_log_id: Mapped[int | None] = mapped_column(
        ForeignKey("generation_logs.id"), nullable=True
    )
    model: Mapped[str] = mapped_column(String(100))
    operation: Mapped[str] = mapped_column(String(100))
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)
    cost_usd: Mapped[float] = mapped_column(Float)
    latency_ms: Mapped[int] = mapped_column(Integer)
    success: Mapped[bool] = mapped_column(Boolean)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 关系
    generation_log: Mapped["GenerationLog | None"] = relationship(
        back_populates="usage_logs"
    )
