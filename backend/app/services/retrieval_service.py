"""混合检索服务 - RAG 管线的核心."""

import asyncio

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm_gateway import embed

logger = structlog.get_logger()

# RRF 融合常数
RRF_K = 60


class RetrievalService:
    """三路检索融合."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def structured_search(
        self,
        question_type: str | None = None,
        difficulty_min: float | None = None,
        difficulty_max: float | None = None,
        stage: str | None = None,
        grade: str | None = None,
        knowledge_id: int | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """结构化检索 - 按条件精确筛选."""
        conditions = ["q.is_deleted = false", "q.review_status = 'approved'"]
        params: dict = {}

        if question_type:
            conditions.append("q.question_type = :question_type")
            params["question_type"] = question_type
        if difficulty_min is not None:
            conditions.append("q.difficulty >= :difficulty_min")
            params["difficulty_min"] = difficulty_min
        if difficulty_max is not None:
            conditions.append("q.difficulty <= :difficulty_max")
            params["difficulty_max"] = difficulty_max
        if knowledge_id is not None:
            conditions.append(
                "EXISTS (SELECT 1 FROM question_knowledge qk WHERE qk.question_id = q.id AND qk.knowledge_id = :knowledge_id)"
            )
            params["knowledge_id"] = knowledge_id

        query = f"""
            SELECT q.id, q.content_latex, q.content_plain, q.question_type,
                   q.difficulty, q.score, q.answer_latex, q.options, q.source
            FROM questions q
            WHERE {' AND '.join(conditions)}
            ORDER BY q.id DESC
            LIMIT :limit
        """
        params["limit"] = limit

        result = await self.session.execute(text(query), params)
        return [dict(row._mapping) for row in result]

    async def fulltext_search(self, query_text: str, limit: int = 50) -> list[dict]:
        """全文检索 - 使用 tsvector."""
        query = """
            SELECT id, content_latex, content_plain, question_type,
                   difficulty, score, answer_latex, options, source,
                   ts_rank(content_tsv, plainto_tsquery('zhcfg', :query)) as rank
            FROM questions
            WHERE is_deleted = false
              AND content_tsv @@ plainto_tsquery('zhcfg', :query)
            ORDER BY rank DESC
            LIMIT :limit
        """
        result = await self.session.execute(
            text(query), {"query": query_text, "limit": limit}
        )
        return [dict(row._mapping) for row in result]

    async def semantic_search(self, query_text: str, top_k: int = 50) -> list[dict]:
        """语义向量检索."""
        try:
            query_embedding = await embed([query_text])
        except Exception as e:
            logger.warning("semantic_search_embed_failed", error=str(e))
            return []

        if not query_embedding or not query_embedding[0]:
            return []

        query = """
            SELECT id, content_latex, content_plain, question_type,
                   difficulty, score, answer_latex, options, source,
                   1 - (embedding <=> :embedding::vector) as similarity
            FROM questions
            WHERE is_deleted = false AND embedding IS NOT NULL
            ORDER BY embedding <=> :embedding::vector
            LIMIT :limit
        """
        result = await self.session.execute(
            text(query),
            {"embedding": str(query_embedding[0]), "limit": top_k},
        )
        return [dict(row._mapping) for row in result]

    async def hybrid_search(
        self,
        query_text: str,
        filters: dict | None = None,
        top_k: int = 50,
    ) -> list[dict]:
        """混合检索 - RRF 融合全文和向量检索."""
        # 并行执行两路检索
        fulltext_results, semantic_results = await asyncio.gather(
            self.fulltext_search(query_text, limit=top_k * 2),
            self.semantic_search(query_text, top_k=top_k * 2),
        )

        # RRF 融合
        rrf_scores: dict[int, float] = {}
        id_to_question: dict[int, dict] = {}

        for rank, q in enumerate(fulltext_results):
            qid = q["id"]
            rrf_scores[qid] = rrf_scores.get(qid, 0) + 1.0 / (RRF_K + rank + 1)
            id_to_question[qid] = q

        for rank, q in enumerate(semantic_results):
            qid = q["id"]
            rrf_scores[qid] = rrf_scores.get(qid, 0) + 1.0 / (RRF_K + rank + 1)
            id_to_question[qid] = q

        # 按 RRF 分数排序
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        results = []
        for qid in sorted_ids[:top_k]:
            q = id_to_question[qid]
            q["rrf_score"] = rrf_scores[qid]
            results.append(q)

        # 后过滤
        if filters:
            results = self._apply_filters(results, filters)

        return results

    def _apply_filters(self, results: list[dict], filters: dict) -> list[dict]:
        """后过滤."""
        filtered = results
        if filters.get("question_type"):
            filtered = [r for r in filtered if r.get("question_type") == filters["question_type"]]
        if filters.get("difficulty_min") is not None:
            filtered = [r for r in filtered if r.get("difficulty", 0) >= filters["difficulty_min"]]
        if filters.get("difficulty_max") is not None:
            filtered = [r for r in filtered if r.get("difficulty", 5) <= filters["difficulty_max"]]
        return filtered

    async def find_similar_questions(
        self, question_id: int, threshold: float = 0.92, limit: int = 10
    ) -> list[dict]:
        """查找相似题目（用于去重）."""
        query = """
            SELECT q2.id, q2.content_latex, q2.question_type, q2.difficulty,
                   1 - (q1.embedding <=> q2.embedding) as similarity
            FROM questions q1, questions q2
            WHERE q1.id = :question_id
              AND q2.id != :question_id
              AND q1.embedding IS NOT NULL
              AND q2.embedding IS NOT NULL
              AND q2.is_deleted = false
              AND 1 - (q1.embedding <=> q2.embedding) > :threshold
            ORDER BY similarity DESC
            LIMIT :limit
        """
        result = await self.session.execute(
            text(query),
            {"question_id": question_id, "threshold": threshold, "limit": limit},
        )
        return [dict(row._mapping) for row in result]
