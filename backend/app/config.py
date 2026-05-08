"""应用配置管理，使用 Pydantic Settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置."""

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/mathpaperforge"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/mathpaperforge"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # AI Models
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    deepseek_api_key: str = ""

    # Default models
    default_chat_model: str = "claude-sonnet-4-20250514"
    default_embedding_model: str = "text-embedding-3-small"
    default_fast_model: str = "deepseek-chat"

    # LiteLLM
    litellm_max_concurrent: int = 10
    litellm_request_timeout: int = 60

    # Application
    app_name: str = "MathPaperForge"
    environment: str = "development"
    app_env: str = "development"
    app_debug: bool = False
    app_secret_key: str = ""
    app_log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # File Storage
    upload_dir: str = "./uploads"
    export_dir: str = "./exports"

    # LaTeX
    latex_compiler: str = "xelatex"
    latex_timeout: int = 30

    # OCR
    mineru_enabled: bool = True
    mineru_model_dir: str = "./models/mineru"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
