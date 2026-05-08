"""题目相关模型."""

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    event,
    func,
    inspect,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin

try:
    from pgvector.sqlalchemy import Vector

    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False


class Question(TimestampMixin, SoftDeleteMixin, Base):
    """题目."""

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    content_latex: Mapped[str] = mapped_column(Text)
    content_plain: Mapped[str] = mapped_column(Text)
    question_type: Mapped[str] = mapped_column(String(50))  # 'choice'/'fill_blank'/'short_answer'/'proof'/'comprehensive'
    difficulty: Mapped[float] = mapped_column(Float)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    answer_latex: Mapped[str | None] = mapped_column(Text, nullable=True)
    solution_steps: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    options: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    source: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    exam_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    review_status: Mapped[str] = mapped_column(String(20), default="pending")
    current_version: Mapped[int] = mapped_column(Integer, default=1)

    # pgvector 向量列 (通过 Alembic 迁移创建索引)
    # embedding 列和索引在迁移中通过 op.execute() 添加

    # 全文检索向量列 (通过 Alembic 迁移创建触发器)
    # content_tsv 列和触发器在迁移中通过 op.execute() 添加

    # 关系
    knowledge_points: Mapped[list["KnowledgeNode"]] = relationship(
        secondary="question_knowledge", back_populates="questions"
    )
    versions: Mapped[list["QuestionVersion"]] = relationship(
        back_populates="question", order_by="QuestionVersion.version_number.desc()"
    )
    tags: Mapped[list["QuestionTag"]] = relationship(back_populates="question")


class QuestionVersion(TimestampMixin, Base):
    """题目版本历史."""

    __tablename__ = "question_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    version_number: Mapped[int] = mapped_column(Integer)
    content_latex: Mapped[str] = mapped_column(Text)
    answer_latex: Mapped[str | None] = mapped_column(Text, nullable=True)
    solution_steps: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    question: Mapped["Question"] = relationship(back_populates="versions")


class QuestionKnowledge(Base):
    """题目-知识点关联表."""

    __tablename__ = "question_knowledge"

    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), primary_key=True)
    knowledge_id: Mapped[int] = mapped_column(ForeignKey("knowledge_nodes.id"), primary_key=True)
    relevance_score: Mapped[float] = mapped_column(Float, default=1.0)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)


class QuestionTag(Base):
    """题目标签."""

    __tablename__ = "question_tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    tag_type: Mapped[str] = mapped_column(String(50))  # '题型特征'/'解题方法'/'易错点'/'核心素养'
    tag_value: Mapped[str] = mapped_column(String(200))

    question: Mapped["Question"] = relationship(back_populates="tags")

    __table_args__ = (Index("ix_tag_type_value", "tag_type", "tag_value"),)


# ---------------------------------------------------------------------------
# 题目更新时自动创建 QuestionVersion 记录
# ---------------------------------------------------------------------------

_TRACKED_FIELDS = ("content_latex", "answer_latex", "solution_steps")


@event.listens_for(Question, "before_update")
def _auto_create_question_version(mapper, connection, target):
    """当题目内容字段变更时，自动创建版本记录并递增版本号."""
    history = inspect(target).attrs
    has_changes = any(history[key].history.has_changes() for key in _TRACKED_FIELDS if key in history)
    if not has_changes:
        return

    # 查询当前最大版本号
    stmt = select(func.max(QuestionVersion.version_number)).where(
        QuestionVersion.question_id == target.id
    )
    result = connection.execute(stmt)
    max_ver = result.scalar() or 0

    new_ver = max_ver + 1
    # 插入新版本记录（保存变更后的内容）
    # 读取临时属性 _change_reason（由 service 层设置），默认为 "自动版本记录"
    change_reason = getattr(target, "_change_reason", None) or "自动版本记录"
    connection.execute(
        QuestionVersion.__table__.insert().values(
            question_id=target.id,
            version_number=new_ver,
            content_latex=target.content_latex,
            answer_latex=target.answer_latex,
            solution_steps=target.solution_steps,
            change_reason=change_reason,
        )
    )
    target.current_version = new_ver
