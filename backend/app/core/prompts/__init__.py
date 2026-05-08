"""Prompt 模板.

按主规范 7.1-7.3 分文件组织：
- question_gen.py: 新题生成 Prompt（7.1）
- question_check.py: 答案校验 Prompt（7.2）
- difficulty.py: 难度评估 Prompt（7.3）
- ocr_cleanup.py: OCR 结果清洗 Prompt
"""

from app.core.prompts.difficulty import build_difficulty_prompt
from app.core.prompts.ocr_cleanup import build_ocr_cleanup_prompt, build_ocr_extract_prompt
from app.core.prompts.question_check import build_answer_check_prompt
from app.core.prompts.question_gen import build_question_gen_prompt

__all__ = [
    "build_question_gen_prompt",
    "build_answer_check_prompt",
    "build_difficulty_prompt",
    "build_ocr_cleanup_prompt",
    "build_ocr_extract_prompt",
]
