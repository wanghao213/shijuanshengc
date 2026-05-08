"""自定义异常层次."""


class AppError(Exception):
    """应用基础异常."""

    def __init__(self, message: str, code: int = 500):
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundError(AppError):
    """资源未找到."""

    def __init__(self, resource: str, resource_id: int | str):
        super().__init__(f"{resource} {resource_id} 不存在", code=404)


class ValidationError(AppError):
    """数据验证错误."""

    def __init__(self, message: str, field: str | None = None):
        self.field = field
        super().__init__(message, code=422)


class LLMError(AppError):
    """LLM 调用错误."""

    def __init__(self, message: str):
        super().__init__(message, code=502)


class LaTeXError(AppError):
    """LaTeX 语法错误."""

    def __init__(self, errors: list[str]):
        self.latex_errors = errors
        super().__init__(f"LaTeX 验证失败: {'; '.join(errors)}", code=422)


class GenerationError(AppError):
    """试卷生成错误."""

    def __init__(self, message: str):
        super().__init__(message, code=500)
