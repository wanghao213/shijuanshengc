"""初始数据库结构.

Revision ID: 001_initial
Revises:
Create Date: 2026-05-02
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 启用扩展
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS zhparser")

    # 创建全文检索配置
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_ts_config WHERE cfgname = 'zhcfg'
            ) THEN
                CREATE TEXT SEARCH CONFIGURATION zhcfg (PARSER = zhparser);
                ALTER TEXT SEARCH CONFIGURATION zhcfg ADD MAPPING FOR n,v,a,i,e,l WITH simple;
            END IF;
        END$$;
    """)

    # --- knowledge_nodes ---
    op.create_table(
        "knowledge_nodes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("parent_id", sa.Integer, sa.ForeignKey("knowledge_nodes.id"), nullable=True),
        sa.Column("level", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("stage", sa.String(20), nullable=True),
        sa.Column("grade", sa.String(20), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("materialized_path", sa.String(500), nullable=False, server_default=""),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_knowledge_path", "knowledge_nodes", ["materialized_path"])
    op.create_index("ix_knowledge_stage_grade", "knowledge_nodes", ["stage", "grade"])

    # --- questions ---
    op.create_table(
        "questions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("content_latex", sa.Text, nullable=False),
        sa.Column("content_plain", sa.Text, nullable=False),
        sa.Column("question_type", sa.String(50), nullable=False),
        sa.Column("difficulty", sa.Float, nullable=False),
        sa.Column("score", sa.Float, nullable=True),
        sa.Column("answer_latex", sa.Text, nullable=True),
        sa.Column("solution_steps", JSONB, nullable=True),
        sa.Column("options", JSONB, nullable=True),
        sa.Column("source", sa.String(500), nullable=True),
        sa.Column("source_year", sa.Integer, nullable=True),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("exam_type", sa.String(50), nullable=True),
        sa.Column("is_ai_generated", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("review_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("current_version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # pgvector 向量列
    op.execute("ALTER TABLE questions ADD COLUMN embedding vector(1536)")
    op.execute(
        "CREATE INDEX ix_question_embedding ON questions USING hnsw (embedding vector_cosine_ops)"
    )

    # 全文检索向量列
    op.execute("ALTER TABLE questions ADD COLUMN content_tsv tsvector")
    op.execute("CREATE INDEX ix_question_tsv ON questions USING gin(content_tsv)")

    # tsvector 自动更新触发器
    op.execute("""
        CREATE OR REPLACE FUNCTION questions_tsv_update() RETURNS trigger AS $$
        BEGIN
            NEW.content_tsv := to_tsvector('zhcfg', COALESCE(NEW.content_plain, ''));
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_questions_tsv
        BEFORE INSERT OR UPDATE ON questions
        FOR EACH ROW EXECUTE FUNCTION questions_tsv_update();
    """)

    # --- question_versions ---
    op.create_table(
        "question_versions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("question_id", sa.Integer, sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("content_latex", sa.Text, nullable=False),
        sa.Column("answer_latex", sa.Text, nullable=True),
        sa.Column("solution_steps", JSONB, nullable=True),
        sa.Column("change_reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # --- question_knowledge ---
    op.create_table(
        "question_knowledge",
        sa.Column("question_id", sa.Integer, sa.ForeignKey("questions.id"), primary_key=True),
        sa.Column("knowledge_id", sa.Integer, sa.ForeignKey("knowledge_nodes.id"), primary_key=True),
        sa.Column("relevance_score", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default="true"),
    )

    # --- question_tags ---
    op.create_table(
        "question_tags",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("question_id", sa.Integer, sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("tag_type", sa.String(50), nullable=False),
        sa.Column("tag_value", sa.String(200), nullable=False),
    )
    op.create_index("ix_tag_type_value", "question_tags", ["tag_type", "tag_value"])

    # --- paper_templates ---
    op.create_table(
        "paper_templates",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("stage", sa.String(20), nullable=False),
        sa.Column("grade", sa.String(20), nullable=False),
        sa.Column("subject", sa.String(50), nullable=False, server_default="数学"),
        sa.Column("total_score", sa.Integer, nullable=False),
        sa.Column("duration_minutes", sa.Integer, nullable=False),
        sa.Column("structure", JSONB, nullable=False),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # --- papers ---
    op.create_table(
        "papers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("template_id", sa.Integer, sa.ForeignKey("paper_templates.id"), nullable=False),
        sa.Column("generation_params", JSONB, nullable=False, server_default="{}"),
        sa.Column("total_score", sa.Integer, nullable=False),
        sa.Column("difficulty_average", sa.Float, nullable=False, server_default="0"),
        sa.Column("knowledge_coverage", JSONB, nullable=False, server_default="{}"),
        sa.Column("review_status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("export_path", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # --- paper_questions ---
    op.create_table(
        "paper_questions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("paper_id", sa.Integer, sa.ForeignKey("papers.id"), nullable=False),
        sa.Column("question_id", sa.Integer, sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("section_index", sa.Integer, nullable=False),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column("assigned_score", sa.Float, nullable=False),
    )

    # --- generation_logs ---
    op.create_table(
        "generation_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("template_id", sa.Integer, sa.ForeignKey("paper_templates.id"), nullable=True),
        sa.Column("paper_id", sa.Integer, sa.ForeignKey("papers.id"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("current_step", sa.String(200), nullable=True),
        sa.Column("progress_pct", sa.Float, nullable=False, server_default="0"),
        sa.Column("planner_output", JSONB, nullable=True),
        sa.Column("retriever_output", JSONB, nullable=True),
        sa.Column("generator_output", JSONB, nullable=True),
        sa.Column("validator_output", JSONB, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("processing_time_seconds", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # --- ai_usage_logs ---
    op.create_table(
        "ai_usage_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("generation_log_id", sa.Integer, sa.ForeignKey("generation_logs.id"), nullable=True),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("operation", sa.String(100), nullable=False),
        sa.Column("input_tokens", sa.Integer, nullable=False),
        sa.Column("output_tokens", sa.Integer, nullable=False),
        sa.Column("cost_usd", sa.Float, nullable=False),
        sa.Column("latency_ms", sa.Integer, nullable=False),
        sa.Column("success", sa.Boolean, nullable=False),
        sa.Column("error_detail", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("ai_usage_logs")
    op.drop_table("generation_logs")
    op.drop_table("paper_questions")
    op.drop_table("papers")
    op.drop_table("paper_templates")
    op.drop_table("question_tags")
    op.drop_table("question_knowledge")
    op.drop_table("question_versions")

    op.execute("DROP TRIGGER IF EXISTS trg_questions_tsv ON questions")
    op.execute("DROP FUNCTION IF EXISTS questions_tsv_update()")
    op.drop_table("questions")
    op.drop_table("knowledge_nodes")

    op.execute("DROP TEXT SEARCH CONFIGURATION IF EXISTS zhcfg")
    op.execute("DROP EXTENSION IF EXISTS zhparser")
    op.execute("DROP EXTENSION IF EXISTS vector")
