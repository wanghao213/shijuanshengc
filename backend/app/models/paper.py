"""生成的试卷模型."""

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Paper(TimestampMixin, Base):
    """生成的试卷."""

    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    template_id: Mapped[int] = mapped_column(ForeignKey("paper_templates.id"))
    generation_params: Mapped[dict] = mapped_column(JSONB)
    total_score: Mapped[int] = mapped_column(Integer)
    difficulty_average: Mapped[float] = mapped_column(Float)
    knowledge_coverage: Mapped[dict] = mapped_column(JSONB)
    review_status: Mapped[str] = mapped_column(String(20), default="draft")
    export_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    template: Mapped["PaperTemplate"] = relationship()
    questions: Mapped[list["PaperQuestion"]] = relationship(
        back_populates="paper", order_by="PaperQuestion.position"
    )


class PaperQuestion(Base):
    """试卷-题目关联."""

    __tablename__ = "paper_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id"))
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    section_index: Mapped[int] = mapped_column(Integer)
    position: Mapped[int] = mapped_column(Integer)
    assigned_score: Mapped[float] = mapped_column(Float)

    paper: Mapped["Paper"] = relationship(back_populates="questions")
    question: Mapped["Question"] = relationship()
