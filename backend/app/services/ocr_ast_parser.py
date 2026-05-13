"""基于 AST 的 OCR 解析清理工具 - 文档解析与 OCR 清洗增强.

功能:
1. LaTeX 公式语法树解析和验证
2. 数学表达式结构化提取
3. OCR 错误自动检测和修复建议
4. 轻量级公式专用多模态模型集成（Nougat 可选）
5. 结构化 JSON/Markdown 混合格式输出
6. 难度标签预标注

使用场景:
- 在 LLM 处理之前，先进行 AST 级别的语法验证和清洗
- 降低 LLM 幻觉风险，减少 token 消耗
- 提高公式识别准确率
"""

import ast
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

import structlog

logger = structlog.get_logger()


class LatexNodeType(Enum):
    """LaTeX 节点类型."""

    FRACTION = auto()
    SQUARE_ROOT = auto()
    NTH_ROOT = auto()
    SUPERSCRIPT = auto()
    SUBSCRIPT = auto()
    SUMMATION = auto()
    INTEGRAL = auto()
    LIMIT = auto()
    GREEK_LETTER = auto()
    FUNCTION = auto()
    MATRIX = auto()
    ALIGN_ENV = auto()
    TEXT = auto()
    SYMBOL = auto()


@dataclass
class LatexNode:
    """LaTeX 语法树节点."""

    node_type: LatexNodeType
    raw_text: str
    children: list["LatexNode"] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)
    position: tuple[int, int] = (0, 0)  # (start, end) in original text
    is_valid: bool = True
    error_message: str | None = None


@dataclass
class ParseError:
    """解析错误信息."""

    error_type: str
    message: str
    position: tuple[int, int]
    suggestion: str
    severity: str = "error"  # 'error' / 'warning' / 'info'


@dataclass
class ParsedDocument:
    """解析后的文档结构."""

    raw_text: str
    cleaned_text: str
    latex_tree: list[LatexNode] = field(default_factory=list)
    questions: list[dict] = field(default_factory=list)
    errors: list[ParseError] = field(default_factory=list)
    warnings: list[ParseError] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    
    # 预标注的难度标签
    estimated_difficulty: float = 3.0
    knowledge_points: list[str] = field(default_factory=list)
    
    # 统计信息
    formula_count: int = 0
    inline_formula_count: int = 0
    display_formula_count: int = 0


class LatexASTParser:
    """LaTeX 公式 AST 解析器.

    将 LaTeX 公式解析为抽象语法树，用于:
    1. 语法验证
    2. 错误检测
    3. 结构化提取
    4. 自动修复建议
    """

    # LaTeX 命令映射表
    LATEX_COMMANDS = {
        "frac": LatexNodeType.FRACTION,
        "sqrt": LatexNodeType.SQUARE_ROOT,
        "sum": LatexNodeType.SUMMATION,
        "int": LatexNodeType.INTEGRAL,
        "lim": LatexNodeType.LIMIT,
        "begin{matrix}": LatexNodeType.MATRIX,
        "begin{pmatrix}": LatexNodeType.MATRIX,
        "begin{align}": LatexNodeType.ALIGN_ENV,
        "begin{equation}": LatexNodeType.ALIGN_ENV,
    }

    GREEK_LETTERS = {
        "alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta",
        "iota", "kappa", "lambda", "mu", "nu", "xi", "pi", "rho", "sigma",
        "tau", "upsilon", "phi", "chi", "psi", "omega",
        "Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta",
        "Iota", "Kappa", "Lambda", "Mu", "Nu", "Xi", "Pi", "Rho", "Sigma",
        "Tau", "Upsilon", "Phi", "Chi", "Psi", "Omega",
    }

    MATH_FUNCTIONS = {
        "sin", "cos", "tan", "cot", "sec", "csc",
        "arcsin", "arccos", "arctan",
        "sinh", "cosh", "tanh",
        "log", "ln", "exp", "lg",
        "lim", "max", "min", "sup", "inf",
        "dim", "ker", "deg", "det", "mod",
    }

    def __init__(self):
        self.errors: list[ParseError] = []
        self.warnings: list[ParseError] = []

    def parse(self, latex_text: str) -> ParsedDocument:
        """解析 LaTeX 文本.

        Args:
            latex_text: 包含 LaTeX 公式的文本

        Returns:
            ParsedDocument 包含解析结果和错误信息
        """
        self.errors = []
        self.warnings = []

        # 第一步：提取所有公式
        formulas = self._extract_formulas(latex_text)

        # 第二步：解析每个公式为 AST
        latex_tree = []
        for formula_info in formulas:
            try:
                tree = self._parse_formula(
                    formula_info["content"],
                    formula_info["type"],
                    formula_info["position"],
                )
                latex_tree.append(tree)
            except Exception as e:
                logger.warning("formula_parse_failed", formula=formula_info["content"][:50], error=str(e))
                self.errors.append(ParseError(
                    error_type="parse_failure",
                    message=f"公式解析失败：{str(e)}",
                    position=formula_info["position"],
                    suggestion="检查公式语法是否正确",
                ))

        # 第三步：验证和错误检测
        self._validate_tree(latex_tree)

        # 第四步：生成清洗后的文本
        cleaned_text = self._generate_cleaned_text(latex_text, latex_tree)

        # 第五步：提取题目结构
        questions = self._extract_questions(cleaned_text)

        # 第六步：预标注难度和知识点
        difficulty, knowledge_points = self._pre_annotate(latex_tree, questions)

        # 统计信息
        inline_count = sum(1 for f in formulas if f["type"] == "inline")
        display_count = sum(1 for f in formulas if f["type"] == "display")

        return ParsedDocument(
            raw_text=latex_text,
            cleaned_text=cleaned_text,
            latex_tree=latex_tree,
            questions=questions,
            errors=self.errors,
            warnings=self.warnings,
            metadata={
                "formula_positions": [(f["type"], f["position"]) for f in formulas],
            },
            estimated_difficulty=difficulty,
            knowledge_points=knowledge_points,
            formula_count=len(formulas),
            inline_formula_count=inline_count,
            display_formula_count=display_count,
        )

    def _extract_formulas(self, text: str) -> list[dict]:
        """提取文本中的所有 LaTeX 公式.

        Returns:
            列表，每项包含：
            - content: 公式内容
            - type: 'inline' 或 'display'
            - position: (start, end) 位置
        """
        formulas = []

        # 提取行内公式 $...$
        for match in re.finditer(r"\$(.+?)\$", text):
            content = match.group(1).strip()
            # 排除空公式和纯空格
            if content and not content.isspace():
                formulas.append({
                    "content": content,
                    "type": "inline",
                    "position": (match.start(), match.end()),
                })

        # 提取独立公式 $$...$$
        for match in re.finditer(r"\$\$(.+?)\$\$", text, re.DOTALL):
            content = match.group(1).strip()
            if content and not content.isspace():
                formulas.append({
                    "content": content,
                    "type": "display",
                    "position": (match.start(), match.end()),
                })

        # 提取 \[...\] 和 \(...\)
        for match in re.finditer(r"\\\[(.+?)\\\]", text, re.DOTALL):
            content = match.group(1).strip()
            if content and not content.isspace():
                formulas.append({
                    "content": content,
                    "type": "display",
                    "position": (match.start(), match.end()),
                })

        for match in re.finditer(r"\\\((.+?)\\\)", text):
            content = match.group(1).strip()
            if content and not content.isspace():
                formulas.append({
                    "content": content,
                    "type": "inline",
                    "position": (match.start(), match.end()),
                })

        return formulas

    def _parse_formula(
        self,
        content: str,
        formula_type: str,
        position: tuple[int, int],
    ) -> LatexNode:
        """解析单个 LaTeX 公式为 AST."""
        # 创建根节点
        root = LatexNode(
            node_type=LatexNodeType.TEXT,
            raw_text=content,
            position=position,
        )

        # 递归解析子节点
        children = self._parse_content(content, 0)
        root.children = children

        return root

    def _parse_content(self, text: str, start_pos: int = 0) -> list[LatexNode]:
        """递归解析 LaTeX 内容."""
        nodes = []
        i = 0
        n = len(text)

        while i < n:
            # 跳过空白
            if text[i].isspace():
                i += 1
                continue

            # 检查是否是命令
            if text[i] == "\\":
                node, consumed = self._parse_command(text, i, start_pos + i)
                if node:
                    nodes.append(node)
                    i += consumed
                    continue
                else:
                    i += 1
                    continue

            # 检查是否是分组符号
            if text[i] in "{}":
                node, consumed = self._parse_group(text, i, start_pos + i)
                if node:
                    nodes.append(node)
                    i += consumed
                    continue
                else:
                    i += 1
                    continue

            # 检查是否是上下标
            if text[i] in "^_":
                node, consumed = self._parse_script(text, i, start_pos + i)
                if node:
                    nodes.append(node)
                    i += consumed
                    continue
                else:
                    i += 1
                    continue

            # 普通字符
            char_node = LatexNode(
                node_type=LatexNodeType.SYMBOL,
                raw_text=text[i],
                position=(start_pos + i, start_pos + i + 1),
            )
            nodes.append(char_node)
            i += 1

        return nodes

    def _parse_command(
        self,
        text: str,
        pos: int,
        abs_pos: int,
    ) -> tuple[LatexNode | None, int]:
        """解析 LaTeX 命令."""
        if text[pos] != "\\":
            return None, 0

        # 提取命令名
        match = re.match(r"\\([a-zA-Z]+)(\*?)", text[pos:])
        if not match:
            # 特殊字符如 \{ \} 等
            if pos + 1 < len(text) and text[pos + 1] in "{}&%#$_^~":
                return LatexNode(
                    node_type=LatexNodeType.SYMBOL,
                    raw_text=text[pos : pos + 2],
                    position=(abs_pos, abs_pos + 2),
                ), 2
            return None, 0

        cmd_name = match.group(1)
        star = match.group(2)
        cmd_len = len(match.group(0))

        # 确定节点类型
        node_type = LatexNodeType.SYMBOL
        if cmd_name in self.GREEK_LETTERS:
            node_type = LatexNodeType.GREEK_LETTER
        elif cmd_name in self.MATH_FUNCTIONS:
            node_type = LatexNodeType.FUNCTION
        elif cmd_name in ["frac", "dfrac", "tfrac"]:
            node_type = LatexNodeType.FRACTION
        elif cmd_name in ["sqrt", "cbrt"]:
            node_type = LatexNodeType.SQUARE_ROOT
        elif cmd_name in ["sum", "prod", "bigcup", "bigcap"]:
            node_type = LatexNodeType.SUMMATION
        elif cmd_name in ["int", "iint", "iiint", "oint"]:
            node_type = LatexNodeType.INTEGRAL
        elif cmd_name == "lim":
            node_type = LatexNodeType.LIMIT

        # 解析参数
        children = []
        remaining = text[pos + cmd_len :]

        # 检查可选参数 [...]
        if remaining.startswith("["):
            opt_arg, consumed = self._parse_bracket(remaining, 0)
            if opt_arg:
                children.append(opt_arg)
                remaining = remaining[consumed:]
                cmd_len += consumed

        # 解析必需参数 {...}
        param_count = self._get_command_param_count(cmd_name)
        for _ in range(param_count):
            if remaining.strip().startswith("{"):
                arg, consumed = self._parse_brace(remaining, 0)
                if arg:
                    children.append(arg)
                    remaining = remaining[consumed:]
                    cmd_len += consumed

        node = LatexNode(
            node_type=node_type,
            raw_text=text[pos : pos + cmd_len],
            children=children,
            attributes={"command": cmd_name, "star": bool(star)},
            position=(abs_pos, abs_pos + cmd_len),
        )

        return node, cmd_len

    def _parse_group(
        self,
        text: str,
        pos: int,
        abs_pos: int,
    ) -> tuple[LatexNode | None, int]:
        """解析分组符号 {...}."""
        if text[pos] not in "{}":
            return None, 0

        node, consumed = self._parse_brace(text, pos)
        if node:
            node.position = (abs_pos, abs_pos + consumed)
        return node, consumed

    def _parse_script(
        self,
        text: str,
        pos: int,
        abs_pos: int,
    ) -> tuple[LatexNode | None, int]:
        """解析上下标 ^ 或 _."""
        if text[pos] not in "^_":
            return None, 0

        script_type = LatexNodeType.SUPERSCRIPT if text[pos] == "^" else LatexNodeType.SUBSCRIPT
        consumed = 1
        children = []

        remaining = text[pos + 1 :]

        # 跳过空白
        while remaining and remaining[0].isspace():
            consumed += 1
            remaining = remaining[1:]

        if not remaining:
            return None, 0

        # 解析脚本内容
        if remaining[0] == "{":
            arg, arg_consumed = self._parse_brace(remaining, 0)
            if arg:
                children.append(arg)
                consumed += arg_consumed
        else:
            # 单个字符
            char_node = LatexNode(
                node_type=LatexNodeType.SYMBOL,
                raw_text=remaining[0],
                position=(abs_pos + consumed, abs_pos + consumed + 1),
            )
            children.append(char_node)
            consumed += 1

        node = LatexNode(
            node_type=script_type,
            raw_text=text[pos : pos + consumed],
            children=children,
            position=(abs_pos, abs_pos + consumed),
        )

        return node, consumed

    def _parse_brace(self, text: str, pos: int) -> tuple[LatexNode | None, int]:
        """解析 {...} 分组."""
        if pos >= len(text) or text[pos] != "{":
            return None, 0

        depth = 0
        i = pos
        while i < len(text):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    # 找到匹配的右括号
                    content = text[pos + 1 : i]
                    children = self._parse_content(content, pos + 1)
                    node = LatexNode(
                        node_type=LatexNodeType.TEXT,
                        raw_text=text[pos : i + 1],
                        children=children,
                        position=(pos, i + 1),
                    )
                    return node, i - pos + 1
            elif text[i] == "\\":
                # 跳过转义字符
                i += 2
                continue
            i += 1

        # 未找到匹配的右括号
        self.errors.append(ParseError(
            error_type="unmatched_brace",
            message="未匹配的左大括号 {",
            position=(pos, pos + 1),
            suggestion="添加对应的右大括号 }",
            severity="error",
        ))
        return None, 0

    def _parse_bracket(self, text: str, pos: int) -> tuple[LatexNode | None, int]:
        """解析 [...] 可选参数."""
        if pos >= len(text) or text[pos] != "[":
            return None, 0

        depth = 0
        i = pos
        while i < len(text):
            if text[i] == "[":
                depth += 1
            elif text[i] == "]":
                depth -= 1
                if depth == 0:
                    content = text[pos + 1 : i]
                    children = self._parse_content(content, pos + 1)
                    node = LatexNode(
                        node_type=LatexNodeType.TEXT,
                        raw_text=text[pos : i + 1],
                        children=children,
                        position=(pos, i + 1),
                    )
                    return node, i - pos + 1
            elif text[i] == "\\":
                i += 2
                continue
            i += 1

        return None, 0

    def _get_command_param_count(self, cmd_name: str) -> int:
        """获取 LaTeX 命令的参数数量."""
        param_map = {
            "frac": 2,
            "sqrt": 1,
            "overset": 2,
            "underset": 2,
            "substack": 1,
        }
        return param_map.get(cmd_name, 0)

    def _validate_tree(self, tree: list[LatexNode]) -> None:
        """验证 AST 并收集错误."""
        for node in tree:
            self._validate_node(node)

    def _validate_node(self, node: LatexNode) -> None:
        """验证单个节点."""
        # 检查分数命令是否有两个参数
        if node.node_type == LatexNodeType.FRACTION:
            if len(node.children) < 2:
                node.is_valid = False
                node.error_message = "分数命令 \\frac 需要两个参数"
                self.errors.append(ParseError(
                    error_type="missing_argument",
                    message="\\frac 缺少参数",
                    position=node.position,
                    suggestion="确保 \\frac{分子}{分母} 格式正确",
                ))

        # 检查根号命令是否有参数
        if node.node_type == LatexNodeType.SQUARE_ROOT:
            if not node.children:
                node.is_valid = False
                node.error_message = "根号命令 \\sqrt 需要一个参数"
                self.errors.append(ParseError(
                    error_type="missing_argument",
                    message="\\sqrt 缺少参数",
                    position=node.position,
                    suggestion="确保 \\sqrt{被开方数} 格式正确",
                ))

        # 递归验证子节点
        for child in node.children:
            self._validate_node(child)

    def _generate_cleaned_text(
        self,
        original: str,
        tree: list[LatexNode],
    ) -> str:
        """生成清洗后的文本.

        基于 AST 重构 LaTeX，修复常见错误。
        """
        # 简单实现：直接返回原文本
        # TODO: 实现基于 AST 的重构逻辑
        cleaned = original

        # 自动修复一些常见错误
        # 1. 修复不匹配的括号
        cleaned = self._fix_unmatched_braces(cleaned)

        # 2. 修复常见的 OCR 错误
        cleaned = self._fix_ocr_errors(cleaned)

        return cleaned

    def _fix_unmatched_braces(self, text: str) -> str:
        """修复不匹配的大括号."""
        # 简单的括号匹配修复
        depth = 0
        result = []
        for char in text:
            if char == "{":
                depth += 1
                result.append(char)
            elif char == "}":
                if depth > 0:
                    depth -= 1
                    result.append(char)
                # 否则忽略多余的右括号
            else:
                result.append(char)

        # 添加缺失的右括号
        result.extend(["}"] * depth)

        return "".join(result)

    def _fix_ocr_errors(self, text: str) -> str:
        """修复常见的 OCR 识别错误."""
        fixes = [
            # 希腊字母误识别
            (r"\ba\b(?=\s*[=+\-])", r"\\alpha"),
            (r"\bB\b(?=\s*[=+\-])", r"\\beta"),
            (r"\bn\b(?=\s*[=+\-])", r"\\pi"),
            # 乘号误识别
            (r"(?<![a-zA-Z])x(?![a-zA-Z])", r"\\times"),
            # 除号误识别
            (r"(?<!\\)/", r"\\div"),
        ]

        for pattern, replacement in fixes:
            text = re.sub(pattern, replacement, text)

        return text

    def _extract_questions(self, text: str) -> list[dict]:
        """从文本中提取题目结构."""
        questions = []

        # 按题号分割
        # 匹配模式：数字 + "." 或 数字 + ")" 或 "第 x 题"
        patterns = [
            r"(^\d+[\.、]\s*)",  # 1. 或 1、
            r"(^\d+\)\s*)",  # 1)
            r"(第\s*\d+\s*题\s*)",  # 第 1 题
        ]

        combined_pattern = "|".join(f"({p})" for p in patterns)

        parts = re.split(f"({combined_pattern})", text, flags=re.MULTILINE)

        current_number = ""
        current_content = ""

        for part in parts:
            if not part:
                continue

            # 检查是否是题号标记
            match = re.search(combined_pattern, part)
            if match and part.strip() == match.group():
                # 保存之前的题目
                if current_number and current_content:
                    questions.append({
                        "number": current_number,
                        "content": current_content.strip(),
                    })

                # 提取新题号
                current_number = self._extract_number(part)
                current_content = ""
            else:
                current_content += part

        # 添加最后一道题
        if current_number and current_content:
            questions.append({
                "number": current_number,
                "content": current_content.strip(),
            })

        return questions

    def _extract_number(self, text: str) -> str:
        """从题号标记中提取数字."""
        match = re.search(r"\d+", text)
        return match.group() if match else ""

    def _pre_annotate(
        self,
        tree: list[LatexNode],
        questions: list[dict],
    ) -> tuple[float, list[str]]:
        """预标注难度和知识点.

        基于公式复杂度进行启发式评估。
        """
        # 计算公式复杂度
        complexity_score = 0.0

        for node in tree:
            complexity_score += self._calculate_node_complexity(node)

        # 根据复杂度估算难度 (1.0 - 5.0)
        if complexity_score == 0:
            difficulty = 2.0  # 无公式，基础题
        elif complexity_score < 5:
            difficulty = 2.5
        elif complexity_score < 15:
            difficulty = 3.0
        elif complexity_score < 30:
            difficulty = 4.0
        else:
            difficulty = 5.0

        # 识别知识点
        knowledge_points = []

        # 检查是否包含特定类型的公式
        has_calculus = any(
            node.node_type in (LatexNodeType.INTEGRAL, LatexNodeType.SUMMATION, LatexNodeType.LIMIT)
            for node in tree
        )
        has_algebra = any(
            node.node_type == LatexNodeType.FRACTION
            for node in tree
        )
        has_geometry = any(
            "triangle" in node.raw_text.lower() or "angle" in node.raw_text.lower()
            for node in tree
        )

        if has_calculus:
            knowledge_points.append("微积分")
        if has_algebra:
            knowledge_points.append("代数")
        if has_geometry:
            knowledge_points.append("几何")

        return difficulty, knowledge_points

    def _calculate_node_complexity(self, node: LatexNode) -> float:
        """计算节点复杂度."""
        base_scores = {
            LatexNodeType.FRACTION: 2.0,
            LatexNodeType.SQUARE_ROOT: 1.5,
            LatexNodeType.SUPERSCRIPT: 0.5,
            LatexNodeType.SUBSCRIPT: 0.5,
            LatexNodeType.SUMMATION: 3.0,
            LatexNodeType.INTEGRAL: 4.0,
            LatexNodeType.LIMIT: 3.0,
            LatexNodeType.MATRIX: 5.0,
            LatexNodeType.ALIGN_ENV: 3.0,
        }

        score = base_scores.get(node.node_type, 0.1)

        # 递归累加子节点复杂度
        for child in node.children:
            score += self._calculate_node_complexity(child) * 0.5

        return score


class DocumentParser:
    """文档解析器 - 整合 AST 解析和可选的多模态模型."""

    def __init__(self, use_nougat: bool = False):
        """初始化解析器.

        Args:
            use_nougat: 是否使用 Nougat 多模态模型（需要额外安装）
        """
        self.latex_parser = LatexASTParser()
        self.use_nougat = use_nougat
        self.nougat_model = None

        if use_nougat:
            self._load_nougat_model()

    def _load_nougat_model(self) -> None:
        """加载 Nougat 模型."""
        try:
            # Nougat 需要单独安装：pip install nougat-ocr
            from transformers import AutoProcessor, VisionEncoderDecoderModel

            logger.info("loading_nougat_model")
            # 这里只是示例，实际需要配置模型路径
            self.nougat_model = None
        except ImportError:
            logger.warning("nougat_not_installed", fallback="using_rule_based_parser")
            self.use_nougat = False

    async def parse_document(self, text: str) -> ParsedDocument:
        """解析文档.

        Args:
            text: 输入文本（可以是 OCR 原始输出）

        Returns:
            ParsedDocument 包含结构化结果
        """
        # 使用 AST 解析器进行处理
        result = self.latex_parser.parse(text)

        # 如果有 Nougat 模型，可以进行额外的图像到 Markdown 转换
        if self.use_nougat and self.nougat_model:
            # TODO: 集成 Nougat 图像处理
            pass

        return result

    def to_json(self, parsed: ParsedDocument) -> dict:
        """将解析结果转换为 JSON 格式."""
        return {
            "status": "success" if not parsed.errors else "partial",
            "cleaned_text": parsed.cleaned_text,
            "questions": parsed.questions,
            "formulas": {
                "total": parsed.formula_count,
                "inline": parsed.inline_formula_count,
                "display": parsed.display_formula_count,
            },
            "errors": [
                {
                    "type": e.error_type,
                    "message": e.message,
                    "position": e.position,
                    "suggestion": e.suggestion,
                    "severity": e.severity,
                }
                for e in parsed.errors + parsed.warnings
            ],
            "metadata": {
                "estimated_difficulty": parsed.estimated_difficulty,
                "knowledge_points": parsed.knowledge_points,
            },
        }

    def to_markdown(self, parsed: ParsedDocument) -> str:
        """将解析结果转换为 Markdown 格式."""
        lines = []

        # 添加元数据
        lines.append("## 文档分析\n")
        lines.append(f"- 公式总数：{parsed.formula_count}")
        lines.append(f"- 行内公式：{parsed.inline_formula_count}")
        lines.append(f"- 独立公式：{parsed.display_formula_count}")
        lines.append(f"- 预估难度：{parsed.estimated_difficulty}/5.0")
        lines.append(f"- 知识点：{', '.join(parsed.knowledge_points)}\n")

        # 添加错误和警告
        if parsed.errors:
            lines.append("## 错误\n")
            for err in parsed.errors:
                lines.append(f"- [{err.severity.upper()}] {err.message}")
                lines.append(f"  建议：{err.suggestion}\n")

        # 添加题目
        if parsed.questions:
            lines.append("## 题目\n")
            for q in parsed.questions:
                lines.append(f"### 第 {q['number']} 题\n")
                lines.append(q["content"])
                lines.append("")

        return "\n".join(lines)
