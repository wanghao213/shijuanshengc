"""试卷导出服务 - LaTeX / PDF / DOCX 导出."""

import asyncio
import io
import os
import re
import shutil
import tempfile

import structlog

from app.config import settings

logger = structlog.get_logger()


class ExportService:
    """试卷导出服务.

    支持三种格式：
    - LaTeX: 生成完整 XeLaTeX 源码（ctexart 文档类）
    - PDF: 通过 xelatex 编译生成 PDF
    - DOCX: 通过 python-docx 生成 Word 文档
    """

    async def export_to_latex(self, paper_data: dict, include_answers: bool = True) -> str:
        """导出为 LaTeX 源码.

        使用 ctexart 文档类，格式遵循试卷规范 6.6。
        """
        sections = paper_data.get("sections", [])
        title = paper_data.get("title", "数学试卷")
        total_score = paper_data.get("total_score", "")

        latex = self._build_latex_document(title, total_score, sections, include_answers)
        return latex

    async def export_to_pdf(self, paper_data: dict, include_answers: bool = True) -> str:
        """导出为 PDF 文件.

        两遍编译处理交叉引用，临时目录管理，编译后清理。
        返回导出文件路径，失败返回空字符串。
        """
        latex_content = await self.export_to_latex(paper_data, include_answers)

        with tempfile.TemporaryDirectory() as tmpdir:
            tex_file = os.path.join(tmpdir, "paper.tex")
            pdf_file = os.path.join(tmpdir, "paper.pdf")

            with open(tex_file, "w", encoding="utf-8") as f:
                f.write(latex_content)

            # 两遍编译（处理交叉引用和页码）
            for pass_num in range(2):
                try:
                    proc = await asyncio.create_subprocess_exec(
                        settings.latex_compiler,
                        "-interaction=nonstopmode",
                        "-output-directory", tmpdir,
                        tex_file,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, stderr = await asyncio.wait_for(
                        proc.communicate(), timeout=settings.latex_timeout
                    )

                    if proc.returncode != 0 and pass_num == 1:
                        # 第二遍编译失败时才报错
                        error_log = self._extract_latex_errors(stdout.decode())
                        logger.error(
                            "latex_compile_failed",
                            pass_num=pass_num + 1,
                            errors=error_log,
                        )
                        return ""

                except TimeoutError:
                    logger.error("latex_compile_timeout", pass_num=pass_num + 1)
                    return ""
                except FileNotFoundError:
                    logger.error("latex_compiler_not_found", compiler=settings.latex_compiler)
                    return ""

            # 复制到导出目录
            if os.path.exists(pdf_file):
                os.makedirs(settings.export_dir, exist_ok=True)
                paper_id = paper_data.get("id", "unknown")
                export_path = os.path.join(
                    settings.export_dir, f"paper_{paper_id}.pdf"
                )
                shutil.copy2(pdf_file, export_path)
                logger.info("pdf_exported", path=export_path)
                return export_path

        return ""

    async def export_to_pdf_bytes(self, paper_data: dict, include_answers: bool = True) -> bytes:
        """导出为 PDF 字节流（用于直接下载）."""
        latex_content = await self.export_to_latex(paper_data, include_answers)

        with tempfile.TemporaryDirectory() as tmpdir:
            tex_file = os.path.join(tmpdir, "paper.tex")
            pdf_file = os.path.join(tmpdir, "paper.pdf")

            with open(tex_file, "w", encoding="utf-8") as f:
                f.write(latex_content)

            for _ in range(2):
                try:
                    proc = await asyncio.create_subprocess_exec(
                        settings.latex_compiler,
                        "-interaction=nonstopmode",
                        "-output-directory", tmpdir,
                        tex_file,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    await asyncio.wait_for(
                        proc.communicate(), timeout=settings.latex_timeout
                    )
                except (TimeoutError, FileNotFoundError):
                    return b""

            if os.path.exists(pdf_file):
                with open(pdf_file, "rb") as f:
                    return f.read()

        return b""

    async def export_to_docx(self, paper_data: dict, include_answers: bool = True) -> bytes:
        """导出为 DOCX 字节流.

        使用 python-docx 生成 Word 文档。
        数学公式以 LaTeX 源码形式呈现（Word 不原生支持 LaTeX 渲染）。
        """
        try:
            from docx import Document
            from docx.enum.section import WD_ORIENT
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            from docx.shared import Cm, Pt, RGBColor
        except ImportError:
            logger.error("python-docx not installed")
            return b""

        doc = Document()

        # 页面设置
        section = doc.sections[0]
        section.page_width = Cm(21)
        section.page_height = Cm(29.7)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)

        # 设置默认字体
        style = doc.styles["Normal"]
        font = style.font
        font.name = "宋体"
        font.size = Pt(12)

        title = paper_data.get("title", "数学试卷")
        total_score = paper_data.get("total_score", "")
        sections = paper_data.get("sections", [])

        # 标题
        title_para = doc.add_heading(title, level=0)
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # 考试信息
        info_para = doc.add_paragraph()
        info_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = info_para.add_run(f"总分：{total_score}分")
        run.font.size = Pt(11)

        doc.add_paragraph()  # 空行

        # 各大题
        for section_data in sections:
            section_name = section_data.get("name", "")
            questions = section_data.get("questions", [])

            # 大题标题
            heading = doc.add_heading(section_name, level=2)
            heading.runs[0].font.size = Pt(14)

            for i, q in enumerate(questions, 1):
                content = q.get("content_latex", "")
                score = q.get("score", "")
                score_text = f"（{score}分）" if score else ""

                # 题目内容
                para = doc.add_paragraph()
                para.paragraph_format.space_after = Pt(6)
                run = para.add_run(f"{i}. ")
                run.bold = True
                run.font.size = Pt(12)

                # 题目文本（LaTeX 以等宽字体显示）
                self._add_latex_paragraph(para, content)

                if score_text:
                    run = para.add_run(score_text)
                    run.font.size = Pt(11)
                    run.font.color.rgb = RGBColor(128, 128, 128)

                # 选项（选择题）
                if q.get("options"):
                    options = q["options"]
                    if isinstance(options, dict):
                        # dict 格式 {"A": "...", "B": "..."}
                        for label, opt_content in options.items():
                            opt_para = doc.add_paragraph()
                            opt_para.paragraph_format.left_indent = Cm(1)
                            run = opt_para.add_run(f"{label}. ")
                            run.bold = True
                            self._add_latex_paragraph(opt_para, opt_content, font_size=11)
                    elif isinstance(options, list):
                        # list 格式 [{"label": "A", "content_latex": "..."}]
                        for opt in options:
                            label = opt.get("label", "")
                            opt_content = opt.get("content_latex", "")
                            opt_para = doc.add_paragraph()
                            opt_para.paragraph_format.left_indent = Cm(1)
                            run = opt_para.add_run(f"{label}. ")
                            run.bold = True
                            self._add_latex_paragraph(opt_para, opt_content, font_size=11)

        # 参考答案
        if include_answers:
            doc.add_page_break()
            answer_heading = doc.add_heading("参考答案", level=1)
            answer_heading.alignment = WD_ALIGN_PARAGRAPH.CENTER

            for section_data in sections:
                section_name = section_data.get("name", "")
                questions = section_data.get("questions", [])

                if section_name:
                    doc.add_heading(section_name, level=3)

                for i, q in enumerate(questions, 1):
                    answer = q.get("answer_latex", "")
                    if answer:
                        para = doc.add_paragraph()
                        run = para.add_run(f"{i}. ")
                        run.bold = True
                        self._add_latex_paragraph(para, answer, font_size=11)

        # 导出为字节流
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer.read()

    def _add_latex_paragraph(self, para, latex_text: str, font_size: int = 12) -> None:
        """向段落中添加 LaTeX 文本.

        数学公式部分使用等宽字体 + 蓝色标注。
        """
        from docx.shared import Pt, RGBColor

        # 简单分割行内公式和普通文本
        parts = re.split(r"(\$\$.*?\$\$|\$.*?\$)", latex_text)

        for part in parts:
            if not part:
                continue

            if part.startswith("$$") and part.endswith("$$"):
                # 独立公式
                formula = part[2:-2].strip()
                run = para.add_run(formula)
                run.font.name = "Cambria Math"
                run.font.size = Pt(font_size)
                run.font.color.rgb = RGBColor(0, 0, 180)
            elif part.startswith("$") and part.endswith("$"):
                # 行内公式
                formula = part[1:-1].strip()
                run = para.add_run(formula)
                run.font.name = "Cambria Math"
                run.font.size = Pt(font_size)
                run.font.color.rgb = RGBColor(0, 0, 180)
            else:
                # 普通文本
                run = para.add_run(part)
                run.font.size = Pt(font_size)

    def _build_latex_document(
        self, title: str, total_score, sections: list, include_answers: bool
    ) -> str:
        """构建完整 XeLaTeX 文档.

        使用 ctexart 文档类，格式遵循试卷规范 6.6。
        """
        # 安全转义 LaTeX 特殊字符
        safe_title = self._escape_latex(title)

        latex = r"""\documentclass[12pt,a4paper]{ctexart}
\usepackage{amsmath,amssymb,amsthm}
\usepackage{geometry}
\usepackage{enumitem}
\usepackage{fancyhdr}
\usepackage{xcolor}
\usepackage{tabularx}

\geometry{left=2.5cm,right=2.5cm,top=2.5cm,bottom=2.5cm}

\pagestyle{fancy}
\fancyhf{}
\rhead{""" + safe_title + r"""}
\lhead{姓名：\underline{\hspace{3cm}} \quad 班级：\underline{\hspace{2cm}}}
\rfoot{\thepage}
\renewcommand{\headrulewidth}{0.4pt}

\setlength{\parskip}{0.5em}
\setlength{\parindent}{0pt}

\newcommand{\score}[1]{\hfill\textcolor{gray}{（#1 分）}}

\begin{document}

\begin{center}
{\Large\bfseries """ + safe_title + r"""}

\vspace{0.3cm}
{\normalsize 总分：""" + str(total_score) + r"""分 \quad 时间：\underline{\hspace{1.5cm}}分钟}
\end{center}

\vspace{0.5cm}

"""

        question_counter = 0

        for section in sections:
            section_name = self._escape_latex(section.get("name", ""))
            latex += f"\\noindent\\textbf{{{section_name}}}\n"
            latex += r"\vspace{0.3cm}" + "\n\n"

            for q in section.get("questions", []):
                question_counter += 1
                content = q.get("content_latex", "")
                score = q.get("score", "")

                # 题号 + 内容
                score_cmd = f" \\score{{{score}}}" if score else ""
                latex += f"\\textbf{{{question_counter}.}} {content}{score_cmd}\n\n"

                # 选项
                options = q.get("options")
                if options:
                    if isinstance(options, dict):
                        latex += "\\begin{enumerate}[label=\\Alph*., itemsep=2pt, left=2em]\n"
                        for opt_content in options.values():
                            latex += f"  \\item {opt_content}\n"
                        latex += "\\end{enumerate}\n\n"
                    elif isinstance(options, list):
                        latex += "\\begin{enumerate}[label=\\Alph*., itemsep=2pt, left=2em]\n"
                        for opt in options:
                            latex += f"  \\item {opt.get('content_latex', '')}\n"
                        latex += "\\end{enumerate}\n\n"

            latex += r"\vspace{0.5cm}" + "\n\n"

        # 参考答案
        if include_answers:
            latex += r"""
\newpage
\begin{center}
{\Large\bfseries 参考答案}
\end{center}

\vspace{0.5cm}
"""

            for section in sections:
                section_name = self._escape_latex(section.get("name", ""))
                latex += f"\\noindent\\textbf{{{section_name}}}\n\n"

                for i, q in enumerate(section.get("questions", []), 1):
                    answer = q.get("answer_latex", "")
                    if answer:
                        latex += f"\\textbf{{{i}.}} {answer} \\quad "
                latex += "\n\n"

        latex += r"\end{document}"
        return latex

    @staticmethod
    def _escape_latex(text: str) -> str:
        """转义 LaTeX 特殊字符（不转义数学公式内的内容）."""
        # 只转义非数学模式的特殊字符
        special = {"&": r"\&", "%": r"\%", "#": r"\#", "_": r"\_"}
        for char, escaped in special.items():
            text = text.replace(char, escaped)
        return text

    @staticmethod
    def _extract_latex_errors(log: str) -> list[str]:
        """从 LaTeX 编译日志中提取错误信息."""
        errors = []
        lines = log.split("\n")
        for line in lines:
            if line.startswith("!") or "Error" in line or "Fatal" in line:
                errors.append(line.strip())
        return errors[:10]  # 最多返回 10 条
