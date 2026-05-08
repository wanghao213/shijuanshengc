"""难度评估 Prompt 模板（主规范 7.3）."""


def build_difficulty_prompt(
    content_latex: str,
    question_type: str,
    stage: str,
    grade: str,
) -> str:
    """构建难度评估 Prompt.

    从4个维度独立评分（1-5），然后加权计算总难度。
    """
    type_map = {
        "choice": "选择题",
        "fill_blank": "填空题",
        "short_answer": "简答题",
        "proof": "证明题",
        "comprehensive": "综合题",
    }
    type_desc = type_map.get(question_type, question_type)

    prompt = f"""你是一位数学教育评估专家，请对以下数学题进行难度评估。

## 题目信息
- 学段：{stage}
- 年级：{grade}
- 题型：{type_desc}

## 题目内容
{content_latex}

## 评估维度
请从以下4个维度独立评分（1-5分）：

1. **知识点数量和深度**（权重 0.25）
   - 1分：单一基础知识点
   - 3分：2-3个知识点的综合
   - 5分：多个深层知识点的复杂综合

2. **计算复杂度**（权重 0.20）
   - 1分：简单计算
   - 3分：中等计算量
   - 5分：复杂计算或需要特殊技巧

3. **思维难度/推理步骤数**（权重 0.35）
   - 1分：直接应用公式
   - 3分：需要2-3步推理
   - 5分：需要多步复杂推理或创造性思维

4. **技巧要求**（权重 0.20）
   - 1分：常规方法可解
   - 3分：需要特定技巧
   - 5分：需要辅助线、换元等非常规方法

## 输出格式要求
请严格按照以下 JSON 格式输出，不要有任何额外文字：

```json
{{
  "dimensions": {{
    "knowledge": {{"score": 3, "reason": "..."}},
    "calculation": {{"score": 2, "reason": "..."}},
    "reasoning": {{"score": 4, "reason": "..."}},
    "technique": {{"score": 2, "reason": "..."}}
  }},
  "weighted_score": 3.05,
  "difficulty_level": "中等偏难",
  "analysis": "综合分析..."
}}
```

请开始评估："""

    return prompt
