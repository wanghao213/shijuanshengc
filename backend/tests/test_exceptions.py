"""自定义异常测试."""


from app.core.exceptions import (
    AppError,
    GenerationError,
    LaTeXError,
    LLMError,
    NotFoundError,
    ValidationError,
)


class TestAppError:
    """AppError 基础异常测试."""

    def test_app_error_basic(self):
        """测试基础创建."""
        err = AppError("服务器内部错误")
        assert str(err) == "服务器内部错误"
        assert err.message == "服务器内部错误"
        assert err.code == 500

    def test_app_error_custom_code(self):
        """测试自定义状态码."""
        err = AppError("自定义错误", code=503)
        assert err.code == 503
        assert err.message == "自定义错误"

    def test_app_error_is_exception(self):
        """测试继承关系."""
        err = AppError("test")
        assert isinstance(err, Exception)


class TestNotFoundError:
    """NotFoundError 测试."""

    def test_not_found_basic(self):
        """测试基本创建."""
        err = NotFoundError("题目", 42)
        assert "题目" in err.message
        assert "42" in err.message
        assert err.code == 404

    def test_not_found_string_id(self):
        """测试字符串 ID."""
        err = NotFoundError("模板", "abc-123")
        assert "abc-123" in err.message
        assert err.code == 404

    def test_not_found_is_app_error(self):
        """测试继承关系."""
        err = NotFoundError("test", 1)
        assert isinstance(err, AppError)


class TestValidationError:
    """ValidationError 测试."""

    def test_validation_error_basic(self):
        """测试基本创建."""
        err = ValidationError("字段不能为空")
        assert err.message == "字段不能为空"
        assert err.code == 422
        assert err.field is None

    def test_validation_error_with_field(self):
        """测试带字段名."""
        err = ValidationError("格式不正确", field="email")
        assert err.field == "email"
        assert err.code == 422

    def test_validation_error_is_app_error(self):
        """测试继承关系."""
        err = ValidationError("test")
        assert isinstance(err, AppError)


class TestLLMError:
    """LLMError 测试."""

    def test_llm_error_basic(self):
        """测试基本创建."""
        err = LLMError("API 调用失败")
        assert err.message == "API 调用失败"
        assert err.code == 502

    def test_llm_error_is_app_error(self):
        """测试继承关系."""
        err = LLMError("test")
        assert isinstance(err, AppError)


class TestLaTeXError:
    """LaTeXError 测试."""

    def test_latex_error_basic(self):
        """测试基本创建."""
        err = LaTeXError(["Undefined control sequence", "Missing $"])
        assert err.code == 422
        assert len(err.latex_errors) == 2
        assert "Undefined control sequence" in err.message

    def test_latex_error_empty_list(self):
        """测试空错误列表."""
        err = LaTeXError([])
        assert err.code == 422
        assert err.latex_errors == []

    def test_latex_error_is_app_error(self):
        """测试继承关系."""
        err = LaTeXError(["test"])
        assert isinstance(err, AppError)


class TestGenerationError:
    """GenerationError 测试."""

    def test_generation_error_basic(self):
        """测试基本创建."""
        err = GenerationError("生成超时")
        assert err.message == "生成超时"
        assert err.code == 500

    def test_generation_error_is_app_error(self):
        """测试继承关系."""
        err = GenerationError("test")
        assert isinstance(err, AppError)
