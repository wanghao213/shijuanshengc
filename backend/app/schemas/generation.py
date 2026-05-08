"""试卷生成模式."""

from datetime import datetime

from pydantic import BaseModel, Field


class GenerationCustomParams(BaseModel):
    """生成自定义参数."""

    difficulty_target: float | None = Field(default=None, ge=1.0, le=5.0)
    knowledge_focus: list[str] = []
    avoid_question_ids: list[int] = []
    prefer_real_questions: bool = True
    allow_ai_generation: bool = True
    count: int = Field(default=1, ge=1, le=10)
    title_override: str | None = None


class GenerationRequest(BaseModel):
    """生成请求."""

    template_id: int
    custom_params: GenerationCustomParams = GenerationCustomParams()


class GenerationTaskStatus(BaseModel):
    """生成任务状态."""

    task_id: str
    status: str  # 'pending'/'planning'/'retrieving'/'generating'/'validating'/'assembling'/'completed'/'failed'
    current_step: str | None = None
    progress_pct: float = 0.0
    paper_id: int | None = None
    error_message: str | None = None
    created_at: datetime | None = None


class GenerationWsMessage(BaseModel):
    """WebSocket 推送消息."""

    task_id: str
    status: str
    current_step: str | None = None
    progress_pct: float = 0.0
    detail: dict | None = None
    timestamp: datetime
