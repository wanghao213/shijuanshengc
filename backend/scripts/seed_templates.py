"""试卷模板种子数据."""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.paper_template import PaperTemplate

TEMPLATES = [
    {
        "name": "中考数学标准试卷",
        "stage": "初中",
        "grade": "初三",
        "subject": "数学",
        "total_score": 120,
        "duration_minutes": 120,
        "is_default": True,
        "description": "中考数学标准试卷模板，包含选择题、填空题、解答题",
        "structure": {
            "sections": [
                {
                    "name": "一、选择题",
                    "type": "choice",
                    "score": 30,
                    "count": 10,
                    "per_question_score": 3,
                    "difficulty_range": [1.0, 3.0],
                    "knowledge_requirements": {
                        "required_topics": ["代数基础", "几何基础", "函数"],
                        "min_coverage": 0.6,
                    },
                    "constraints": {
                        "no_repeat_source": True,
                        "min_unique_knowledge_points": 5,
                        "max_same_source_ratio": 0.3,
                    },
                },
                {
                    "name": "二、填空题",
                    "type": "fill_blank",
                    "score": 24,
                    "count": 6,
                    "per_question_score": 4,
                    "difficulty_range": [2.0, 3.5],
                    "knowledge_requirements": {
                        "required_topics": ["代数", "几何", "统计"],
                        "min_coverage": 0.5,
                    },
                    "constraints": {
                        "no_repeat_source": True,
                        "min_unique_knowledge_points": 4,
                        "max_same_source_ratio": 0.3,
                    },
                },
                {
                    "name": "三、解答题",
                    "type": "short_answer",
                    "score": 66,
                    "count": 8,
                    "per_question_score": 8,
                    "difficulty_range": [2.5, 5.0],
                    "knowledge_requirements": {
                        "required_topics": ["函数", "几何证明", "概率统计", "综合应用"],
                        "min_coverage": 0.7,
                    },
                    "constraints": {
                        "no_repeat_source": True,
                        "min_unique_knowledge_points": 6,
                        "max_same_source_ratio": 0.25,
                    },
                },
            ]
        },
    },
    {
        "name": "高考数学标准试卷",
        "stage": "高中",
        "grade": "高三",
        "subject": "数学",
        "total_score": 150,
        "duration_minutes": 120,
        "is_default": False,
        "description": "高考数学标准试卷模板",
        "structure": {
            "sections": [
                {
                    "name": "一、选择题",
                    "type": "choice",
                    "score": 40,
                    "count": 8,
                    "per_question_score": 5,
                    "difficulty_range": [2.0, 4.0],
                    "knowledge_requirements": {
                        "required_topics": ["集合", "函数", "三角函数", "数列", "立体几何", "解析几何"],
                        "min_coverage": 0.7,
                    },
                    "constraints": {
                        "no_repeat_source": True,
                        "min_unique_knowledge_points": 6,
                        "max_same_source_ratio": 0.25,
                    },
                },
                {
                    "name": "二、填空题",
                    "type": "fill_blank",
                    "score": 20,
                    "count": 4,
                    "per_question_score": 5,
                    "difficulty_range": [2.5, 4.5],
                    "knowledge_requirements": {
                        "required_topics": ["向量", "概率", "导数"],
                        "min_coverage": 0.5,
                    },
                    "constraints": {
                        "no_repeat_source": True,
                        "min_unique_knowledge_points": 3,
                        "max_same_source_ratio": 0.3,
                    },
                },
                {
                    "name": "三、解答题",
                    "type": "short_answer",
                    "score": 90,
                    "count": 6,
                    "per_question_score": 15,
                    "difficulty_range": [3.0, 5.0],
                    "knowledge_requirements": {
                        "required_topics": ["三角函数", "数列", "立体几何", "解析几何", "导数", "概率统计"],
                        "min_coverage": 0.8,
                    },
                    "constraints": {
                        "no_repeat_source": True,
                        "min_unique_knowledge_points": 6,
                        "max_same_source_ratio": 0.2,
                    },
                },
            ]
        },
    },
    {
        "name": "初中数学单元测试",
        "stage": "初中",
        "grade": "初二",
        "subject": "数学",
        "total_score": 100,
        "duration_minutes": 90,
        "is_default": False,
        "description": "初中数学单元测试模板",
        "structure": {
            "sections": [
                {
                    "name": "一、选择题",
                    "type": "choice",
                    "score": 30,
                    "count": 10,
                    "per_question_score": 3,
                    "difficulty_range": [1.0, 2.5],
                    "knowledge_requirements": {
                        "required_topics": ["本单元知识点"],
                        "min_coverage": 0.8,
                    },
                    "constraints": {
                        "no_repeat_source": True,
                        "min_unique_knowledge_points": 5,
                        "max_same_source_ratio": 0.3,
                    },
                },
                {
                    "name": "二、填空题",
                    "type": "fill_blank",
                    "score": 24,
                    "count": 6,
                    "per_question_score": 4,
                    "difficulty_range": [1.5, 3.0],
                    "knowledge_requirements": {
                        "required_topics": ["本单元知识点"],
                        "min_coverage": 0.7,
                    },
                    "constraints": {
                        "no_repeat_source": True,
                        "min_unique_knowledge_points": 4,
                        "max_same_source_ratio": 0.3,
                    },
                },
                {
                    "name": "三、解答题",
                    "type": "short_answer",
                    "score": 46,
                    "count": 5,
                    "per_question_score": 9,
                    "difficulty_range": [2.0, 4.0],
                    "knowledge_requirements": {
                        "required_topics": ["本单元知识点", "综合应用"],
                        "min_coverage": 0.6,
                    },
                    "constraints": {
                        "no_repeat_source": True,
                        "min_unique_knowledge_points": 4,
                        "max_same_source_ratio": 0.3,
                    },
                },
            ]
        },
    },
]


async def seed_templates(session: AsyncSession) -> None:
    """播种模板数据."""
    count = 0
    for tpl_data in TEMPLATES:
        template = PaperTemplate(**tpl_data)
        session.add(template)
        count += 1

    await session.commit()
    print(f"模板播种完成，共 {count} 个模板")


async def main():
    async with async_session_factory() as session:
        await seed_templates(session)


if __name__ == "__main__":
    asyncio.run(main())
