"""题目模式."""

from pydantic import BaseModel, Field


class QuestionBase(BaseModel):
    """题目基础字段."""

    content_latex: str
    content_plain: str
    question_type: str  # 'choice'/'fill_blank'/'short_answer'/'proof'/'comprehensive'
    difficulty: float = Field(ge=1.0, le=5.0)
    score: float | None = None
    answer_latex: str | None = None
    solution_steps: dict | None = None
    options: dict | None = None
    source: str | None = None
    source_year: int | None = None
    region: str | None = None
    exam_type: str | None = None
    is_ai_generated: bool = False
    review_status: str = "pending"


class QuestionCreate(QuestionBase):
    """创建题目."""

    knowledge_point_ids: list[int] = []


class QuestionUpdate(BaseModel):
    """更新题目."""

    content_latex: str | None = None
    content_plain: str | None = None
    question_type: str | None = None
    difficulty: float | None = Field(default=None, ge=1.0, le=5.0)
    score: float | None = None
    answer_latex: str | None = None
    solution_steps: dict | None = None
    options: dict | None = None
    source: str | None = None
    source_year: int | None = None
    region: str | None = None
    exam_type: str | None = None
    review_status: str | None = None
    change_reason: str | None = None


class QuestionRead(QuestionBase):
    """题目响应."""

    id: int
    current_version: int
    knowledge_points: list = []

    model_config = {"from_attributes": True}


class QuestionSearchParams(BaseModel):
    """题目搜索参数."""

    q: str | None = None
    mode: str = "keyword"  # 'keyword'/'semantic'/'hybrid'
    stage: str | None = None
    grade: str | None = None
    question_type: str | None = None
    difficulty_min: float | None = None
    difficulty_max: float | None = None
    knowledge_id: int | None = None
    source: str | None = None
    review_status: str | None = None


class QuestionBatchImport(BaseModel):
    """批量导入题目."""

    questions: list[QuestionCreate]
