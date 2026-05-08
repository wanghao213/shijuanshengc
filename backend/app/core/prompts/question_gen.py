"""新题生成 Prompt 模板."""

import json


def build_question_gen_prompt(
    question_type: str,
    difficulty: float,
    knowledge_points: list[str],
    stage: str,
    grade: str,
    reference_examples: list[dict],
    count: int = 1,
) -> str:
    """构建新题生成的完整 Prompt."""
    examples_text = ""
    if reference_examples:
        examples_text = "\n\n以下是从题库中检索到的参考题目，请参考其风格和难度：\n"
        for i, ex in enumerate(reference_examples, 1):
            examples_text += f"\n--- 参考题 {i} ---\n"
            examples_text += f"题型: {ex.get('question_type', '未知')}\n"
            examples_text += f"难度: {ex.get('difficulty', '未知')}\n"
            examples_text += f"内容: {ex.get('content_latex', '')}\n"
            if ex.get("answer_latex"):
                examples_text += f"答案: {ex['answer_latex']}\n"

    type_map = {
        "choice": "选择题（4个选项，单选）",
        "fill_blank": "填空题",
        "short_answer": "简答题",
        "proof": "证明题",
        "comprehensive": "综合题",
    }
    type_desc = type_map.get(question_type, question_type)

    prompt = f"""你是一位资深数学教育命题专家，擅长命制各学段数学试题。

## 命题任务

请命制 {count} 道数学题目，具体要求如下：

### 基本信息
- 学段：{stage}
- 年级：{grade}
- 题型：{type_desc}
- 目标难度：{difficulty}/5.0
- 考查知识点：{', '.join(knowledge_points)}

### 命题规范
1. 难度控制：题目难度应接近目标难度值，不要偏差过大
2. 数学严谨性：所有数学表达式必须准确无误
3. LaTeX 格式：使用标准 LaTeX 数学语法，如 $x^2$、$\\frac{{a}}{{b}}$、$\\sqrt{{x}}$ 等
4. 题目完整性：每道题必须有完整的题干、解答过程和标准答案
5. 知识点覆盖：确保题目确实考查所列知识点
6. 原创性：不要直接复制参考题目，而是参考其风格和难度

### 选择题特别要求
- 4个选项（A、B、C、D）
- 干扰项必须有合理性，不能明显荒谬
- 正确答案分布要合理
- 每个选项的 LaTeX 格式正确

### 输出格式要求
请严格按照以下 JSON 格式输出，不要有任何额外文字：

```json
{{
  "questions": [
    {{
      "content_latex": "题目内容（LaTeX 格式）",
      "question_type": "{question_type}",
      "options": [
        {{"label": "A", "content_latex": "选项A内容"}},
        {{"label": "B", "content_latex": "选项B内容"}},
        {{"label": "C", "content_latex": "选项C内容"}},
        {{"label": "D", "content_latex": "选项D内容"}}
      ],
      "correct_answer": "B",
      "answer_latex": "答案的 LaTeX 表达",
      "solution_steps": ["步骤1", "步骤2", "步骤3"],
      "difficulty_self_assessment": {difficulty},
      "knowledge_points": {json.dumps(knowledge_points, ensure_ascii=False)},
      "design_intent": "本题考查了..."
    }}
  ]
}}
```

{examples_text}

请开始命题："""

    return prompt


