"""答案校验 Prompt 模板（主规范 7.2）."""


def build_answer_check_prompt(
    content_latex: str,
    options: list[dict] | None,
    question_type: str,
    stage: str,
    grade: str,
) -> str:
    """构建答案校验的 Prompt.

    关键：不提供答案，要求 AI 独立解题。
    """
    options_text = ""
    if options:
        options_text = "\n\n选项：\n"
        for opt in options:
            options_text += f"{opt['label']}. {opt['content_latex']}\n"

    type_map = {
        "choice": "选择题",
        "fill_blank": "填空题",
        "short_answer": "简答题",
        "proof": "证明题",
        "comprehensive": "综合题",
    }
    type_desc = type_map.get(question_type, question_type)

    prompt = f"""你是一位数学教育专家，请独立解答以下数学题，并给出详细解答过程。

## 题目信息
- 学段：{stage}
- 年级：{grade}
- 题型：{type_desc}

## 题目内容
{content_latex}
{options_text}

## 解题要求
1. 请逐步推理，展示完整的解题过程
2. 每一步都要有清晰的数学推导
3. 最终给出明确的答案
4. 如果是选择题，请分析每个选项的正确性

## 输出格式要求
请严格按照以下 JSON 格式输出，不要有任何额外文字：

```json
{{
  "solution_steps": ["步骤1：...", "步骤2：...", "步骤3：..."],
  "final_answer": "B",
  "confidence": 0.95,
  "reasoning": "详细的推理过程..."
}}
```

请开始解题："""

    return prompt
