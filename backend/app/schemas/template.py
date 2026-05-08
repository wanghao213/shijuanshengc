"""试卷模板模式."""

from pydantic import BaseModel, Field


class TemplateSectionKnowledge(BaseModel):
    """大题知识点要求."""

    required_topics: list[str] = []
    min_coverage: float = 0.6


class TemplateSectionConstraints(BaseModel):
    """大题约束条件."""

    no_repeat_source: bool = True
    min_unique_knowledge_points: int = 5
    max_same_source_ratio: float = 0.3


class TemplateSection(BaseModel):
    """模板大题结构."""

    name: str
    type: str  # 'choice'/'fill_blank'/'short_answer'/'proof'/'comprehensive'
    score: int
    count: int
    per_question_score: int
    difficulty_range: list[float] = [1.0, 3.0]
    knowledge_requirements: TemplateSectionKnowledge = TemplateSectionKnowledge()
    constraints: TemplateSectionConstraints = TemplateSectionConstraints()


class TemplateStructure(BaseModel):
    """模板结构."""

    sections: list[TemplateSection]


class TemplateBase(BaseModel):
    """模板基础字段."""

    name: str = Field(max_length=200)
    stage: str
    grade: str
    subject: str = "数学"
    total_score: int
    duration_minutes: int
    structure: dict
    is_default: bool = False
    description: str | None = None


class TemplateCreate(TemplateBase):
    """创建模板."""

    pass


class TemplateUpdate(BaseModel):
    """更新模板."""

    name: str | None = Field(default=None, max_length=200)
    stage: str | None = None
    grade: str | None = None
    subject: str | None = None
    total_score: int | None = None
    duration_minutes: int | None = None
    structure: dict | None = None
    is_default: bool | None = None
    description: str | None = None


class TemplateRead(TemplateBase):
    """模板响应."""

    id: int

    model_config = {"from_attributes": True}
