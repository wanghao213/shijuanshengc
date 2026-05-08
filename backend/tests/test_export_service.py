"""ExportService 单元测试."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.export_service import ExportService


def _sample_paper_data():
    """示例试卷数据."""
    return {
        "id": 1,
        "title": "七年级期中考试数学试卷",
        "total_score": 100,
        "sections": [
            {
                "name": "选择题",
                "questions": [
                    {
                        "content_latex": "$x^2 - 4 = 0$，求 $x$ 的值。",
                        "score": 5,
                        "options": {
                            "A": "$x=2$",
                            "B": "$x=-2$",
                            "C": "$x=\\pm 2$",
                            "D": "无实数解",
                        },
                        "answer_latex": "C",
                    },
                    {
                        "content_latex": "计算 $3 + 5 \\times 2$。",
                        "score": 5,
                        "answer_latex": "13",
                    },
                ],
            },
            {
                "name": "填空题",
                "questions": [
                    {
                        "content_latex": "若 $a + b = 5$，$ab = 6$，则 $a^2 + b^2 = $____。",
                        "score": 5,
                        "answer_latex": "13",
                    },
                ],
            },
        ],
    }


@pytest.mark.asyncio
async def test_export_to_latex_structure():
    """测试 LaTeX 导出包含必要结构."""
    svc = ExportService()
    paper_data = _sample_paper_data()

    latex = await svc.export_to_latex(paper_data, include_answers=True)

    # 检查文档类
    assert "\\documentclass" in latex
    assert "ctexart" in latex

    # 检查必要的包
    assert "amsmath" in latex
    assert "geometry" in latex

    # 检查标题
    assert "七年级期中考试数学试卷" in latex

    # 检查总分
    assert "100" in latex

    # 检查题目
    assert "x^2 - 4 = 0" in latex
    assert "3 + 5" in latex

    # 检查选项
    assert "\\item" in latex

    # 检查答案部分
    assert "参考答案" in latex

    # 检查文档结束
    assert "\\end{document}" in latex


@pytest.mark.asyncio
async def test_export_to_latex_no_answers():
    """测试 LaTeX 导出不含答案."""
    svc = ExportService()
    paper_data = _sample_paper_data()

    latex = await svc.export_to_latex(paper_data, include_answers=False)

    assert "\\documentclass" in latex
    assert "参考答案" not in latex


@pytest.mark.asyncio
async def test_export_to_latex_empty_sections():
    """测试空试卷的 LaTeX 导出."""
    svc = ExportService()
    paper_data = {"title": "空试卷", "total_score": 0, "sections": []}

    latex = await svc.export_to_latex(paper_data)

    assert "\\documentclass" in latex
    assert "空试卷" in latex
    assert "\\end{document}" in latex


@pytest.mark.asyncio
async def test_export_to_latex_list_options():
    """测试 list 格式选项的 LaTeX 导出."""
    svc = ExportService()
    paper_data = {
        "title": "测试",
        "total_score": 10,
        "sections": [
            {
                "name": "选择题",
                "questions": [
                    {
                        "content_latex": "题目",
                        "score": 5,
                        "options": [
                            {"label": "A", "content_latex": "选项A"},
                            {"label": "B", "content_latex": "选项B"},
                        ],
                        "answer_latex": "A",
                    }
                ],
            }
        ],
    }

    latex = await svc.export_to_latex(paper_data)
    assert "\\item 选项A" in latex
    assert "\\item 选项B" in latex


def test_escape_latex():
    """测试 LaTeX 特殊字符转义."""
    assert ExportService._escape_latex("A & B") == r"A \& B"
    assert ExportService._escape_latex("100%") == r"100\%"
    assert ExportService._escape_latex("#1") == r"\#1"
    assert ExportService._escape_latex("a_b") == r"a\_b"
    assert ExportService._escape_latex("普通文本") == "普通文本"


def test_extract_latex_errors():
    """测试从 LaTeX 日志提取错误."""
    log = """\
This is XeTeX
! Undefined control sequence.
l.10 \\badcommand
Some text here
! Fatal error occurred
More text
Error: something went wrong
Normal line
"""

    errors = ExportService._extract_latex_errors(log)

    assert len(errors) == 3
    assert any("Undefined control sequence" in e for e in errors)
    assert any("Fatal" in e for e in errors)
    assert any("Error" in e for e in errors)


def test_extract_latex_errors_limit():
    """测试错误数量限制."""
    lines = ["! Error " + str(i) for i in range(20)]
    log = "\n".join(lines)

    errors = ExportService._extract_latex_errors(log)

    assert len(errors) == 10  # 最多 10 条


def test_extract_latex_errors_empty():
    """测试无错误的日志."""
    log = "Everything is fine\nNo errors here"
    errors = ExportService._extract_latex_errors(log)
    assert errors == []


@pytest.mark.asyncio
@patch("app.services.export_service.ExportService.export_to_latex")
async def test_export_to_docx(mock_export_latex):
    """测试 DOCX 导出."""
    mock_export_latex.return_value = "\\documentclass{ctexart}"

    svc = ExportService()
    paper_data = _sample_paper_data()

    docx_bytes = await svc.export_to_docx(paper_data, include_answers=True)

    assert isinstance(docx_bytes, bytes)
    assert len(docx_bytes) > 0
    # DOCX 文件以 PK (ZIP) 签名开头
    assert docx_bytes[:2] == b"PK"


@pytest.mark.asyncio
async def test_export_to_docx_minimal():
    """测试最小数据的 DOCX 导出."""
    svc = ExportService()
    paper_data = {"title": "测试", "total_score": 10, "sections": []}

    docx_bytes = await svc.export_to_docx(paper_data)

    assert isinstance(docx_bytes, bytes)
    assert len(docx_bytes) > 0


@pytest.mark.asyncio
@patch("app.services.export_service.ExportService.export_to_latex")
@patch("app.services.export_service.asyncio.create_subprocess_exec")
async def test_export_to_pdf_success(mock_subprocess, mock_export_latex):
    """测试 PDF 导出成功."""
    mock_export_latex.return_value = "\\documentclass{ctexart}\\begin{document}test\\end{document}"

    mock_proc = AsyncMock()
    mock_proc.communicate = AsyncMock(return_value=(b"", b""))
    mock_proc.returncode = 0
    mock_subprocess.return_value = mock_proc

    svc = ExportService()
    paper_data = _sample_paper_data()

    with patch("os.path.exists", return_value=False):
        result = await svc.export_to_pdf(paper_data)

    # 当 PDF 文件不存在时返回空字符串
    assert result == ""


@pytest.mark.asyncio
@patch("app.services.export_service.ExportService.export_to_latex")
@patch("app.services.export_service.asyncio.create_subprocess_exec")
async def test_export_to_pdf_compile_failure(mock_subprocess, mock_export_latex):
    """测试 PDF 编译失败."""
    mock_export_latex.return_value = "\\documentclass{ctexart}"

    mock_proc = AsyncMock()
    mock_proc.communicate = AsyncMock(return_value=(b"! Error", b""))
    mock_proc.returncode = 1
    mock_subprocess.return_value = mock_proc

    svc = ExportService()
    paper_data = _sample_paper_data()

    result = await svc.export_to_pdf(paper_data)

    assert result == ""


@pytest.mark.asyncio
@patch("app.services.export_service.ExportService.export_to_latex")
@patch("app.services.export_service.asyncio.create_subprocess_exec")
async def test_export_to_pdf_timeout(mock_subprocess, mock_export_latex):
    """测试 PDF 编译超时."""
    mock_export_latex.return_value = "\\documentclass{ctexart}"

    mock_proc = AsyncMock()
    mock_proc.communicate = AsyncMock(side_effect=TimeoutError)
    mock_subprocess.return_value = mock_proc

    svc = ExportService()
    paper_data = _sample_paper_data()

    result = await svc.export_to_pdf(paper_data)

    assert result == ""


@pytest.mark.asyncio
@patch("app.services.export_service.ExportService.export_to_latex")
@patch("app.services.export_service.asyncio.create_subprocess_exec")
async def test_export_to_pdf_compiler_not_found(mock_subprocess, mock_export_latex):
    """测试 LaTeX 编译器不存在."""
    mock_export_latex.return_value = "\\documentclass{ctexart}"
    mock_subprocess.side_effect = FileNotFoundError

    svc = ExportService()
    paper_data = _sample_paper_data()

    result = await svc.export_to_pdf(paper_data)

    assert result == ""


@pytest.mark.asyncio
@patch("app.services.export_service.ExportService.export_to_latex")
@patch("app.services.export_service.asyncio.create_subprocess_exec")
async def test_export_to_pdf_bytes_success(mock_subprocess, mock_export_latex):
    """测试 PDF 字节流导出."""
    mock_export_latex.return_value = "\\documentclass{ctexart}"

    mock_proc = AsyncMock()
    mock_proc.communicate = AsyncMock(return_value=(b"", b""))
    mock_proc.returncode = 0
    mock_subprocess.return_value = mock_proc

    svc = ExportService()
    paper_data = _sample_paper_data()

    with patch("os.path.exists", return_value=False):
        result = await svc.export_to_pdf_bytes(paper_data)

    assert result == b""
