"""试卷模式."""

from datetime import datetime

from pydantic import BaseModel


class PaperQuestionRead(BaseModel):
    """试卷题目响应."""

    id: int
    question_id: int
    section_index: int
    position: int
    assigned_score: float

    model_config = {"from_attributes": True}


class PaperRead(BaseModel):
    """试卷响应."""

    id: int
    title: str
    template_id: int
    total_score: int
    difficulty_average: float
    knowledge_coverage: dict
    review_status: str
    export_path: str | None = None
    questions: list[PaperQuestionRead] = []
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class PaperReviewRequest(BaseModel):
    """试卷审核请求."""

    status: str  # 'approved'/'rejected'
    comment: str | None = None
