"""OCR 结果清洗 Prompt 模板."""



def build_ocr_cleanup_prompt(raw_text: str) -> str:
    """构建 OCR 结果清洗的 Prompt.

    输入：MinerU 识别的原始文本
    输出：清洗后的结构化文本（修复OCR错误、统一LaTeX格式）
    """
    prompt = f"""你是一位专业的数学文档 OCR 后处理专家。
以下内容是由 OCR 系统（MinerU）从数学试卷中识别出来的原始文本。
由于 OCR 的局限性，文本中可能存在各种识别错误。

## 你的任务

1. **修复 OCR 常见错误**：
   - 数字和字母混淆（如 0/O、1/l/I、5/S、2/Z）
   - 数学符号识别错误（如 × 被识别为 x，÷ 被识别为 /）
   - 上下标丢失或错位（如 x² 被识别为 x2）
   - 分数线丢失（如 a/b 应为 \\frac{{a}}{{b}}）
   - 希腊字母识别错误（如 α→a、β→B、π→n）
   - 括号不匹配或缺失

2. **统一 LaTeX 格式**：
   - 行内公式使用 $...$ 包裹
   - 独立公式使用 $$...$$ 包裹
   - 修复常见的 LaTeX 命令拼写错误
   - 确保所有数学表达式都是有效的 LaTeX

3. **结构化整理**：
   - 识别每道题的题号和边界
   - 保留题目的层次结构（大题、小题）
   - 保留选项的对齐关系
   - 识别并标记答案区域

## 输出格式要求
请严格按照以下 JSON 格式输出，不要有任何额外文字：

```json
{{
  "cleaned_text": "清洗后的完整文本，保留原始结构",
  "questions": [
    {{
      "number": "1",
      "content_latex": "题目内容（LaTeX格式）",
      "options": [
        {{"label": "A", "content_latex": "选项A"}},
        {{"label": "B", "content_latex": "选项B"}}
      ],
      "answer_latex": "答案（如果原文中有）",
      "question_type": "choice/fill_blank/short_answer/proof/comprehensive"
    }}
  ],
  "corrections": [
    {{
      "original": "原始OCR文本片段",
      "corrected": "修正后的文本",
      "reason": "修正原因"
    }}
  ],
  "confidence": 0.85,
  "notes": "处理过程中的特殊说明"
}}
```

## 原始 OCR 文本

{raw_text}

请开始清洗和结构化："""

    return prompt


def build_ocr_extract_prompt(cleaned_text: str) -> str:
    """构建 OCR 结构化提取的 Prompt.

    从清洗后的文本中提取结构化的题目数据。
    """
    prompt = f"""你是一位数学教育专家，请从以下已清洗的数学试卷文本中提取结构化的题目数据。

## 文本内容
{cleaned_text}

## 提取要求
1. 识别每道题的边界和题号
2. 提取题目内容（LaTeX格式）
3. 提取选项（如果有）
4. 提取答案（如果有）
5. 判断题型
6. 识别考查的知识点

## 输出格式要求
请严格按照以下 JSON 格式输出：

```json
{{
  "questions": [
    {{
      "number": "1",
      "content_latex": "完整的题目内容",
      "question_type": "choice",
      "options": [
        {{"label": "A", "content_latex": "..."}},
        {{"label": "B", "content_latex": "..."}},
        {{"label": "C", "content_latex": "..."}},
        {{"label": "D", "content_latex": "..."}}
      ],
      "answer_latex": "标准答案",
      "knowledge_points": ["知识点1", "知识点2"],
      "estimated_difficulty": 3.0
    }}
  ]
}}
```

请开始提取："""

    return prompt
