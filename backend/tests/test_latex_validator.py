"""LaTeX 验证器测试."""

from app.core.latex_validator import validate_latex

# === 基础功能测试 ===

def test_valid_latex():
    """测试有效 LaTeX."""
    result = validate_latex("$x^2 + y^2 = z^2$")
    assert result.is_valid
    assert len(result.errors) == 0


def test_empty_latex():
    """测试空 LaTeX."""
    result = validate_latex("")
    assert not result.is_valid
    assert "为空" in result.errors[0]


def test_whitespace_only():
    """测试纯空白."""
    result = validate_latex("   ")
    assert not result.is_valid


def test_clean_latex():
    """测试 LaTeX 清洗."""
    result = validate_latex("  $x^2$  ")
    assert result.is_valid
    assert result.cleaned_latex == "$x^2$"


def test_clean_latex_multiple_spaces():
    """测试多余空格清洗."""
    result = validate_latex("$x^2  +  y^2$")
    assert result.is_valid
    assert "  " not in result.cleaned_latex


# === 括号匹配测试 ===

def test_unmatched_braces():
    """测试未匹配的大括号."""
    result = validate_latex("\\frac{a}{b")
    assert not result.is_valid
    assert any("未闭合" in e for e in result.errors)


def test_matched_braces():
    """测试匹配的大括号."""
    result = validate_latex("\\frac{a}{b}")
    assert result.is_valid


def test_nested_braces():
    """测试嵌套大括号."""
    result = validate_latex("\\frac{x^2}{y+1}")
    assert result.is_valid


def test_unmatched_parentheses():
    """测试未匹配的圆括号."""
    result = validate_latex("$(x + y$")
    assert not result.is_valid
    assert any("未闭合" in e for e in result.errors)


def test_matched_parentheses():
    """测试匹配的圆括号."""
    result = validate_latex("$(x + y)$")
    assert result.is_valid


def test_unmatched_square_brackets():
    """测试未匹配的方括号."""
    result = validate_latex("$[x, y$")
    assert not result.is_valid


def test_matched_square_brackets():
    """测试匹配的方括号."""
    result = validate_latex("$[x, y]$")
    assert result.is_valid


def test_mixed_brackets():
    """测试混合括号."""
    result = validate_latex("$f(x) = [x^2 + 1]$")
    assert result.is_valid


def test_extra_closing_brace():
    """测试多余的闭合大括号."""
    result = validate_latex("$x^2}$")
    assert not result.is_valid
    assert any("多余" in e for e in result.errors)


# === 数学模式测试 ===

def test_unmatched_dollar():
    """测试未匹配的 $."""
    result = validate_latex("$x + y")
    assert not result.is_valid
    assert any("$" in e for e in result.errors)


def test_matched_dollar():
    """测试匹配的 $."""
    result = validate_latex("$x + y$")
    assert result.is_valid


def test_double_dollar():
    """测试 $$ 数学模式."""
    result = validate_latex("$$x^2 + y^2 = z^2$$")
    assert result.is_valid


def test_unmatched_double_dollar():
    """测试未匹配的 $$."""
    result = validate_latex("$$x^2")
    assert not result.is_valid


def test_paren_math_mode():
    """测试 \\( \\) 数学模式."""
    result = validate_latex("\\(x + y\\)")
    assert result.is_valid


def test_unmatched_paren_math_mode():
    """测试未匹配的 \\( \\)."""
    result = validate_latex("\\(x + y")
    assert not result.is_valid


def test_bracket_math_mode():
    """测试 \\[ \\] 数学模式."""
    result = validate_latex("\\[x^2 + y^2\\]")
    assert result.is_valid


def test_unmatched_bracket_math_mode():
    """测试未匹配的 \\[ \\]."""
    result = validate_latex("\\[x^2")
    assert not result.is_valid


def test_escaped_dollar():
    """测试转义的 \\$."""
    result = validate_latex("\\$100")
    assert result.is_valid


# === 环境配对测试 ===

def test_unmatched_begin_end():
    """测试未匹配的 \\begin-\\end."""
    result = validate_latex("\\begin{equation} x = 1")
    assert not result.is_valid
    assert any("未闭合" in e for e in result.errors)


def test_matched_begin_end():
    """测试匹配的 \\begin-\\end."""
    result = validate_latex("\\begin{equation} x = 1 \\end{equation}")
    assert result.is_valid


def test_nested_environments():
    """测试嵌套环境."""
    result = validate_latex(
        "\\begin{equation} \\begin{aligned} x &= 1 \\\\ y &= 2 \\end{aligned} \\end{equation}"
    )
    assert result.is_valid


def test_mismatched_environments():
    """测试不匹配的环境."""
    result = validate_latex("\\begin{equation} x = 1 \\end{align}")
    assert not result.is_valid
    assert any("不匹配" in e for e in result.errors)


def test_extra_end():
    """测试多余的 \\end."""
    result = validate_latex("x = 1 \\end{equation}")
    assert not result.is_valid
    assert any("多余" in e for e in result.errors)


# === 警告测试 ===

def test_sqrt_warning():
    """测试 \\sqrt 警告."""
    result = validate_latex("\\sqrt{x}{}")
    assert len(result.warnings) > 0


def test_frac_warning():
    """测试 \\frac 缺少分母警告."""
    result = validate_latex("\\frac{a}")
    assert len(result.warnings) > 0


# === 复杂表达式测试 ===

def test_complex_latex():
    """测试复杂 LaTeX 表达式."""
    latex = r"""
    \begin{equation}
        \int_{0}^{\infty} e^{-x^2} dx = \frac{\sqrt{\pi}}{2}
    \end{equation}
    """
    result = validate_latex(latex)
    assert result.is_valid


def test_matrix_latex():
    """测试矩阵表达式."""
    latex = r"""
    \begin{pmatrix}
        1 & 2 \\
        3 & 4
    \end{pmatrix}
    """
    result = validate_latex(latex)
    assert result.is_valid


def test_cases_latex():
    """测试分段函数."""
    latex = r"""
    f(x) = \begin{cases}
        x^2 & x \geq 0 \\
        -x & x < 0
    \end{cases}
    """
    result = validate_latex(latex)
    assert result.is_valid


def test_multiple_math_modes():
    """测试多个数学模式."""
    latex = "设 $a > 0$，则 $\\sqrt{a} > 0$"
    result = validate_latex(latex)
    assert result.is_valid


def test_inline_and_display_math():
    """测试行内和行间数学混合."""
    latex = r"""
    已知 $a + b = 1$，则：
    \[a^2 + b^2 \geq \frac{1}{2}\]
    """
    result = validate_latex(latex)
    assert result.is_valid
