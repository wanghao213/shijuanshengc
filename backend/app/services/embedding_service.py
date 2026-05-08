"""Embedding 服务."""

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm_gateway import embed

logger = structlog.get_logger()


class EmbeddingService:
    """Embedding 业务逻辑."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def generate_embedding(self, question_id: int) -> list[float]:
        """为单个题目生成 embedding."""
        result = await self.session.execute(
            text("SELECT content_plain FROM questions WHERE id = :id"),
            {"id": question_id},
        )
        row = result.first()
        if not row:
            return []

        content = row[0]
        embeddings = await embed([content], session=self.session)
        if not embeddings:
            return []

        embedding = embeddings[0]

        await self.session.execute(
            text(
                """
                UPDATE questions
                SET embedding = :embedding::vector
                WHERE id = :id
                """
            ),
            {"id": question_id, "embedding": str(embedding)},
        )
        await self.session.flush()

        logger.info("embedding_generated", question_id=question_id)
        return embedding

    async def batch_generate_embeddings(
        self,
        question_ids: list[int] | None = None,
        batch_size: int = 20,
        skip_existing: bool = True,
    ) -> int:
        """批量生成 embeddings.

        Args:
            question_ids: 指定题目 ID 列表，None 则处理所有无 embedding 的题目
            batch_size: 每批处理数量
            skip_existing: 跳过已有 embedding 的题目

        Returns:
            成功生成的数量
        """
        if question_ids is None:
            # 获取需要处理的题目
            if skip_existing:
                result = await self.session.execute(
                    text("SELECT id FROM questions WHERE is_deleted = false AND embedding IS NULL")
                )
            else:
                result = await self.session.execute(
                    text("SELECT id FROM questions WHERE is_deleted = false")
                )
            question_ids = [row[0] for row in result]

        success_count = 0
        for i in range(0, len(question_ids), batch_size):
            batch = question_ids[i : i + batch_size]
            for qid in batch:
                try:
                    await self.generate_embedding(qid)
                    success_count += 1
                except Exception as e:
                    logger.error("embedding_failed", question_id=qid, error=str(e))

        logger.info("batch_embedding_complete", total=len(question_ids), success=success_count)
        return success_count
