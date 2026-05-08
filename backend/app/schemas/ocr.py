"""OCR 相关数据模式."""

from pydantic import BaseModel, Field


class OCRProcessRequest(BaseModel):
    """OCR 处理请求（手动输入模式）."""

    text: str = Field(..., min_length=10, description="用户粘贴的试卷文本")
    source: str | None = Field(default=None, description="来源（如：2024年中考真题）")
    source_year: int | None = None
    region: str | None = None
    exam_type: str | None = None
    auto_tag: bool = Field(default=True, description="是否自动标注知识点和难度")


class ExtractedQuestionData(BaseModel):
    """提取的题目数据."""

    number: str
    content_latex: str
    question_type: str = "short_answer"
    options: list[dict] | None = None
    answer_latex: str | None = None
    knowledge_points: list[str] = []
    estimated_difficulty: float = 3.0


class OCRResultResponse(BaseModel):
    """OCR 处理结果."""

    status: str
    raw_text: str = ""
    cleaned_text: str = ""
    questions: list[ExtractedQuestionData] = []
    corrections: list[dict] = []
    confidence: float = 0.0
    notes: str = ""
    error: str | None = None
    saved_question_ids: list[int] = []
