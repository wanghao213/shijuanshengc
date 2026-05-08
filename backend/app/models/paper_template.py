"""试卷模板模型."""

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class PaperTemplate(TimestampMixin, Base):
    """试卷模板."""

    __tablename__ = "paper_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    stage: Mapped[str] = mapped_column(String(20))
    grade: Mapped[str] = mapped_column(String(20))
    subject: Mapped[str] = mapped_column(String(50), default="数学")
    total_score: Mapped[int] = mapped_column(Integer)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    structure: Mapped[dict] = mapped_column(JSONB)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
