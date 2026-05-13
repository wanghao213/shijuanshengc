"""增强版混合检索服务 - RAG 管线的核心优化.

支持:
- 三路检索融合：结构化检索 + 全文检索 (BM25) + 语义向量检索
- RRF (Reciprocal Rank Fusion) 重排序
- 数学符号特殊处理
- 知识点精准召回优化
- Elasticsearch 可选集成
"""

import asyncio
import re
from dataclasses import dataclass, field
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.llm_gateway import embed

logger = structlog.get_logger()

# RRF 融合常数
RRF_K = 60

# 数学符号正则表达式模式
MATH_SYMBOL_PATTERNS = [
    (r"\\frac\{([^}]*)\}\{([^}]*)\}", r"FRAC(\1,\2)"),  # 分数
    (r"\\sqrt\{([^}]*)\}", r"SQRT(\1)"),  # 根号
    (r"\\sum\^?\_?", "SUM"),  # 求和
    (r"\\int\^?\_?", "INT"),  # 积分
    (r"\\[a-zA-Z]+", "MATHCMD"),  # 其他 LaTeX 命令
    (r"[αβγδεζζηθικλμνξοπρστυφχψω]", "GREEK"),  # 希腊字母
    (r"\^[0-9]+", "SUPERSCRIPT"),  # 上标
    (r"\_[0-9]+", "SUBSCRIPT"),  # 下标
]


@dataclass
class RetrievalMetrics:
    """检索性能指标."""

    fulltext_latency_ms: float = 0.0
    semantic_latency_ms: float = 0.0
    structured_latency_ms: float = 0.0
    rrf_fusion_latency_ms: float = 0.0
    total_latency_ms: float = 0.0
    fulltext_count: int = 0
    semantic_count: int = 0
    final_count: int = 0
    recall_rate: float = 0.0


@dataclass
class HybridSearchResult:
    """混合检索结果."""

    question_id: int
    content_latex: str
    content_plain: str
    question_type: str
    difficulty: float
    score: float
    answer_latex: str | None
    options: dict | None
    source: str | None
    
    # 各路检索的排名和分数
    fulltext_rank: int | None = None
    fulltext_score: float | None = None
    semantic_rank: int | None = None
    semantic_similarity: float | None = None
    structured_rank: int | None = None
    
    # RRF 融合分数
    rrf_score: float = 0.0
    
    # 元数据
    knowledge_points: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


class EnhancedRetrievalService:
    """增强版检索服务.

    在基础检索之上增加:
    1. 数学符号预处理和标准化
    2. 三路检索结果加权融合
    3. 知识点相关性重排序
    4. 查询扩展（同义词、上下位概念）
    5. Elasticsearch 可选集成
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.metrics = RetrievalMetrics()
        self.use_elasticsearch = settings.elasticsearch_enabled if hasattr(settings, 'elasticsearch_enabled') else False

    async def hybrid_search(
        self,
        query_text: str,
        filters: dict | None = None,
        top_k: int = 50,
        use_query_expansion: bool = True,
        emphasize_math_symbols: bool = True,
    ) -> list[HybridSearchResult]:
        """增强版混合检索 - RRF 融合全文、向量和结构化检索.

        Args:
            query_text: 查询文本（可以是自然语言或 LaTeX 公式）
            filters: 过滤条件（题型、难度、知识点等）
            top_k: 返回结果数量
            use_query_expansion: 是否使用查询扩展
            emphasize_math_symbols: 是否强调数学符号匹配

        Returns:
            HybridSearchResult 列表，按 RRF 分数降序排列
        """
        import time
        start_time = time.time()

        # 第一步：查询预处理
        processed_query = self._preprocess_query(
            query_text,
            emphasize_math_symbols=emphasize_math_symbols,
        )

        # 第二步：查询扩展（可选）
        expanded_queries = []
        if use_query_expansion:
            expanded_queries = await self._expand_query(processed_query)
        
        all_queries = [processed_query] + expanded_queries

        # 第三步：并行执行三路检索
        tasks = []
        
        # 全文检索（对每个扩展查询）
        for q in all_queries:
            tasks.append(self._fulltext_search_with_metrics(q, limit=top_k * 2))
        
        # 语义检索（仅对主查询）
        tasks.append(self._semantic_search_with_metrics(processed_query, top_k=top_k * 2))
        
        # 结构化检索（如果有知识点 ID 过滤）
        if filters and filters.get("knowledge_id"):
            tasks.append(self._structured_search_with_metrics(
                knowledge_id=filters["knowledge_id"],
                question_type=filters.get("question_type"),
                difficulty_min=filters.get("difficulty_min"),
                difficulty_max=filters.get("difficulty_max"),
                limit=top_k * 2,
            ))

        # 等待所有检索完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 分离各路检索结果
        fulltext_results = []
        semantic_results = []
        structured_results = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning("retrieval_task_failed", task_index=i, error=str(result))
                continue
            
            if i < len(all_queries):
                # 全文检索结果
                fulltext_results.extend(result)
            elif i == len(all_queries):
                # 语义检索结果
                semantic_results = result
            else:
                # 结构化检索结果
                structured_results = result

        # 第四步：RRF 融合
        fused_results = self._rrf_fusion(
            fulltext_results=fulltext_results,
            semantic_results=semantic_results,
            structured_results=structured_results,
            top_k=top_k,
        )

        # 第五步：后过滤
        if filters:
            fused_results = self._apply_filters(fused_results, filters)

        # 第六步：知识点相关性重排序
        if filters and filters.get("knowledge_id"):
            fused_results = self._rerank_by_knowledge_relevance(
                fused_results,
                target_knowledge_id=filters["knowledge_id"],
            )

        # 记录指标
        self.metrics.total_latency_ms = (time.time() - start_time) * 1000
        self.metrics.final_count = len(fused_results)

        logger.info(
            "hybrid_search_completed",
            query=query_text[:50],
            results_count=len(fused_results),
            latency_ms=self.metrics.total_latency_ms,
        )

        return fused_results

    def _preprocess_query(self, query_text: str, emphasize_math_symbols: bool = True) -> str:
        """预处理查询文本.

        - 提取和标准化数学符号
        - 移除无关字符
        - 保留关键 LaTeX 结构
        """
        if not query_text:
            return ""

        processed = query_text

        if emphasize_math_symbols:
            # 提取关键数学结构作为关键词
            math_keywords = []
            for pattern, replacement in MATH_SYMBOL_PATTERNS:
                matches = re.findall(pattern, query_text)
                math_keywords.extend(matches if isinstance(matches[0], tuple) else [matches])
            
            # 将数学关键词附加到查询末尾（提高权重）
            if math_keywords:
                unique_keywords = list(set(str(m) for m in math_keywords[:10]))
                processed = f"{query_text} {' '.join(unique_keywords)}"

        # 清理多余空白
        processed = re.sub(r"\s+", " ", processed).strip()

        return processed

    async def _expand_query(self, query_text: str) -> list[str]:
        """查询扩展 - 生成同义词和相关概念.

        使用轻量级规则扩展，避免 LLM 调用成本：
        1. 数学术语同义词
        2. 上下位概念
        3. 常见缩写展开
        """
        expansions = []

        # 数学术语映射表
        synonym_map = {
            "函数": ["映射", "对应关系"],
            "导数": ["微分", "变化率", "斜率"],
            "积分": ["面积", "累积"],
            "三角形": ["△", "三边形"],
            "圆": ["圆形", "圆周"],
            "方程": ["等式", "关系式"],
            "不等式": ["不等关系"],
            "向量": ["矢量", "有向线段"],
            "概率": ["几率", "可能性"],
            "数列": ["序列"],
        }

        # 查找并扩展
        for term, synonyms in synonym_map.items():
            if term in query_text:
                for synonym in synonyms:
                    expanded = query_text.replace(term, synonym, 1)
                    if expanded != query_text:
                        expansions.append(expanded)

        # 限制扩展数量
        return expansions[:3]

    async def _fulltext_search_with_metrics(
        self,
        query_text: str,
        limit: int = 50,
    ) -> list[dict]:
        """全文检索（带指标追踪）."""
        import time
        start = time.time()

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
        
        try:
            result = await self.session.execute(
                text(query),
                {"query": query_text, "limit": limit},
            )
            rows = [dict(row._mapping) for row in result]
            self.metrics.fulltext_latency_ms += (time.time() - start) * 1000
            self.metrics.fulltext_count = len(rows)
            return rows
        except Exception as e:
            logger.error("fulltext_search_failed", error=str(e))
            return []

    async def _semantic_search_with_metrics(
        self,
        query_text: str,
        top_k: int = 50,
    ) -> list[dict]:
        """语义向量检索（带指标追踪）."""
        import time
        start = time.time()

        try:
            query_embedding = await embed([query_text])
        except Exception as e:
            logger.warning("semantic_search_embed_failed", error=str(e))
            self.metrics.semantic_latency_ms = (time.time() - start) * 1000
            return []

        if not query_embedding or not query_embedding[0]:
            self.metrics.semantic_latency_ms = (time.time() - start) * 1000
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
        
        try:
            result = await self.session.execute(
                text(query),
                {"embedding": str(query_embedding[0]), "limit": top_k},
            )
            rows = [dict(row._mapping) for row in result]
            self.metrics.semantic_latency_ms = (time.time() - start) * 1000
            self.metrics.semantic_count = len(rows)
            return rows
        except Exception as e:
            logger.error("semantic_search_failed", error=str(e))
            self.metrics.semantic_latency_ms = (time.time() - start) * 1000
            return []

    async def _structured_search_with_metrics(
        self,
        knowledge_id: int | None = None,
        question_type: str | None = None,
        difficulty_min: float | None = None,
        difficulty_max: float | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """结构化检索（带指标追踪）."""
        import time
        start = time.time()

        conditions = ["q.is_deleted = false", "q.review_status = 'approved'"]
        params: dict = {}

        if knowledge_id:
            conditions.append(
                "EXISTS (SELECT 1 FROM question_knowledge qk WHERE qk.question_id = q.id AND qk.knowledge_id = :knowledge_id)"
            )
            params["knowledge_id"] = knowledge_id
        
        if question_type:
            conditions.append("q.question_type = :question_type")
            params["question_type"] = question_type
        
        if difficulty_min is not None:
            conditions.append("q.difficulty >= :difficulty_min")
            params["difficulty_min"] = difficulty_min
        
        if difficulty_max is not None:
            conditions.append("q.difficulty <= :difficulty_max")
            params["difficulty_max"] = difficulty_max

        query = f"""
            SELECT q.id, q.content_latex, q.content_plain, q.question_type,
                   q.difficulty, q.score, q.answer_latex, q.options, q.source
            FROM questions q
            WHERE {' AND '.join(conditions)}
            ORDER BY q.id DESC
            LIMIT :limit
        """
        params["limit"] = limit

        try:
            result = await self.session.execute(text(query), params)
            rows = [dict(row._mapping) for row in result]
            self.metrics.structured_latency_ms = (time.time() - start) * 1000
            return rows
        except Exception as e:
            logger.error("structured_search_failed", error=str(e))
            return []

    def _rrf_fusion(
        self,
        fulltext_results: list[dict],
        semantic_results: list[dict],
        structured_results: list[dict],
        top_k: int = 50,
    ) -> list[HybridSearchResult]:
        """RRF (Reciprocal Rank Fusion) 融合多路检索结果.

        RRF 公式：RRF_score(d) = Σ 1/(k + rank_i(d))
        其中 k 是常数（通常取 60），rank_i 是文档在第 i 路检索中的排名
        """
        import time
        start = time.time()

        rrf_scores: dict[int, float] = {}
        id_to_data: dict[int, dict] = {}
        rank_info: dict[int, dict] = {}

        # 全文检索贡献
        for rank, item in enumerate(fulltext_results):
            qid = item["id"]
            score = 1.0 / (RRF_K + rank + 1)
            rrf_scores[qid] = rrf_scores.get(qid, 0) + score
            
            if qid not in id_to_data:
                id_to_data[qid] = item
            
            if qid not in rank_info:
                rank_info[qid] = {}
            rank_info[qid]["fulltext_rank"] = rank + 1
            rank_info[qid]["fulltext_score"] = item.get("rank", 0)

        # 语义检索贡献
        for rank, item in enumerate(semantic_results):
            qid = item["id"]
            score = 1.0 / (RRF_K + rank + 1)
            rrf_scores[qid] = rrf_scores.get(qid, 0) + score * 1.2  # 语义检索权重略高
            
            if qid not in id_to_data:
                id_to_data[qid] = item
            
            if qid not in rank_info:
                rank_info[qid] = {}
            rank_info[qid]["semantic_rank"] = rank + 1
            rank_info[qid]["semantic_similarity"] = item.get("similarity", 0)

        # 结构化检索贡献（精确匹配权重最高）
        for rank, item in enumerate(structured_results):
            qid = item["id"]
            score = 1.0 / (RRF_K + rank + 1)
            rrf_scores[qid] = rrf_scores.get(qid, 0) + score * 1.5  # 结构化检索权重最高
            
            if qid not in id_to_data:
                id_to_data[qid] = item
            
            if qid not in rank_info:
                rank_info[qid] = {}
            rank_info[qid]["structured_rank"] = rank + 1

        # 按 RRF 分数排序
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        # 构建最终结果
        results = []
        for qid in sorted_ids[:top_k]:
            data = id_to_data[qid]
            info = rank_info.get(qid, {})
            
            result = HybridSearchResult(
                question_id=data["id"],
                content_latex=data.get("content_latex", ""),
                content_plain=data.get("content_plain", ""),
                question_type=data.get("question_type", ""),
                difficulty=data.get("difficulty", 3.0),
                score=data.get("score", 0.0),
                answer_latex=data.get("answer_latex"),
                options=data.get("options"),
                source=data.get("source"),
                fulltext_rank=info.get("fulltext_rank"),
                fulltext_score=info.get("fulltext_score"),
                semantic_rank=info.get("semantic_rank"),
                semantic_similarity=info.get("semantic_similarity"),
                structured_rank=info.get("structured_rank"),
                rrf_score=rrf_scores[qid],
            )
            results.append(result)

        self.metrics.rrf_fusion_latency_ms = (time.time() - start) * 1000

        return results

    def _apply_filters(
        self,
        results: list[HybridSearchResult],
        filters: dict,
    ) -> list[HybridSearchResult]:
        """后过滤."""
        filtered = results
        
        if filters.get("question_type"):
            filtered = [r for r in filtered if r.question_type == filters["question_type"]]
        
        if filters.get("difficulty_min") is not None:
            filtered = [r for r in filtered if r.difficulty >= filters["difficulty_min"]]
        
        if filters.get("difficulty_max") is not None:
            filtered = [r for r in filtered if r.difficulty <= filters["difficulty_max"]]

        return filtered

    def _rerank_by_knowledge_relevance(
        self,
        results: list[HybridSearchResult],
        target_knowledge_id: int,
    ) -> list[HybridSearchResult]:
        """按知识点相关性重排序.

        对于包含目标知识点的题目，提升其排名。
        """
        # TODO: 需要从数据库获取题目的知识点关联
        # 这里暂时不做实际重排序，仅保留接口
        return results

    async def find_similar_questions(
        self,
        question_id: int,
        threshold: float = 0.92,
        limit: int = 10,
    ) -> list[HybridSearchResult]:
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
        
        return [
            HybridSearchResult(
                question_id=row.id,
                content_latex=row.content_latex,
                content_plain="",
                question_type=row.question_type,
                difficulty=row.difficulty,
                score=0.0,
                answer_latex=None,
                options=None,
                source=None,
                semantic_similarity=row.similarity,
            )
            for row in result
        ]

    def get_metrics(self) -> RetrievalMetrics:
        """获取检索性能指标."""
        return self.metrics
