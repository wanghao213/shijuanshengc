"""LaTeX 语法验证器.

在题目入库前验证 LaTeX 语法合法性。
"""

import re
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """验证结果."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    cleaned_latex: str = ""


def _check_bracket_matching(latex: str) -> list[str]:
    """检查括号匹配."""
    errors = []
    stack = []
    pairs = {"{": "}", "(": ")", "[": "]"}
    openers = set(pairs.keys())
    closers = set(pairs.values())

    for i, ch in enumerate(latex):
        if ch in openers:
            stack.append((ch, i))
        elif ch in closers:
            if not stack:
                errors.append(f"位置 {i}: 多余的 '{ch}'")
            else:
                open_ch, _ = stack.pop()
                if pairs.get(open_ch) != ch:
                    errors.append(f"位置 {i}: 括号不匹配，期望 '{pairs[open_ch]}' 但得到 '{ch}'")

    for ch, pos in stack:
        errors.append(f"位置 {pos}: 未闭合的 '{ch}'")

    return errors


def _check_math_mode(latex: str) -> list[str]:
    """检查数学模式配对."""
    errors = []

    # 检查 $ 配对（简单计数，忽略 \$ 转义）
    cleaned = re.sub(r"\\\$", "", latex)
    dollar_count = cleaned.count("$")
    if dollar_count % 2 != 0:
        errors.append("'$' 数量不匹配（奇数个）")

    # 检查 $$ 配对
    double_dollar = cleaned.count("$$")
    if double_dollar % 2 != 0:
        errors.append("'$$' 数量不匹配")

    # 检查 \( \) 配对
    if cleaned.count(r"\(") != cleaned.count(r"\)"):
        errors.append("'\\(' 和 '\\)' 数量不匹配")

    # 检查 \[ \] 配对
    if cleaned.count(r"\[") != cleaned.count(r"\]"):
        errors.append("'\\[' 和 '\\]' 数量不匹配")

    return errors


def _check_environments(latex: str) -> list[str]:
    """检查 \\begin-\\end 环境配对."""
    errors = []

    stack = []
    for match in re.finditer(r"\\(begin|end)\{(\w+)\}", latex):
        cmd, env = match.group(1), match.group(2)
        if cmd == "begin":
            stack.append(env)
        else:
            if not stack:
                errors.append(f"多余的 \\end{{{env}}}")
            elif stack[-1] != env:
                errors.append(
                    f"环境不匹配: \\begin{{{stack[-1]}}} 与 \\end{{{env}}}"
                )
            else:
                stack.pop()

    for env in stack:
        errors.append(f"未闭合的 \\begin{{{env}}}")

    return errors


def _clean_latex(latex: str) -> str:
    """清洗 LaTeX 内容."""
    # 规范化空格
    cleaned = re.sub(r"\s+", " ", latex.strip())
    # 移除首尾多余空格
    cleaned = cleaned.strip()
    return cleaned


def validate_latex(latex: str) -> ValidationResult:
    """验证 LaTeX 语法."""
    errors = []
    warnings = []

    if not latex or not latex.strip():
        return ValidationResult(
            is_valid=False, errors=["LaTeX 内容为空"], cleaned_latex=""
        )

    # 括号匹配
    errors.extend(_check_bracket_matching(latex))

    # 数学模式配对
    errors.extend(_check_math_mode(latex))

    # 环境配对
    errors.extend(_check_environments(latex))

    # 警告：常见问题
    if re.search(r"\\frac\{[^}]*\}\s*$", latex):
        warnings.append("\\frac 命令似乎缺少分母")

    if re.search(r"\\sqrt\{[^}]*\}\s*\{", latex):
        warnings.append("\\sqrt 命令后可能有多余的大括号")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        cleaned_latex=_clean_latex(latex),
    )
