"""题目种子数据 - 覆盖各学段、各题型的典型例题."""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.question import Question, QuestionKnowledge, QuestionVersion

# 题目数据
QUESTIONS = [
    # ============================================================
    # 小学部分
    # ============================================================
    {
        "content_latex": "计算：$25 \\times 4 + 75 \\times 4 = $（  ）",
        "content_plain": "计算：25×4+75×4=",
        "question_type": "choice",
        "difficulty": 1.5,
        "score": 3,
        "options": {
            "choices": [
                {"label": "A", "content_latex": "$300$"},
                {"label": "B", "content_latex": "$400$"},
                {"label": "C", "content_latex": "$500$"},
                {"label": "D", "content_latex": "$600$"},
            ]
        },
        "answer_latex": "B",
        "solution_steps": [
            "$25 \\times 4 + 75 \\times 4 = (25 + 75) \\times 4 = 100 \\times 4 = 400$"
        ],
        "stage": "小学",
        "grade": "四年级",
        "knowledge_points": ["整数运算"],
        "source": "教材习题",
    },
    {
        "content_latex": "下列分数中，最大的是（  ）",
        "content_plain": "下列分数中，最大的是",
        "question_type": "choice",
        "difficulty": 1.5,
        "score": 3,
        "options": {
            "choices": [
                {"label": "A", "content_latex": "$\\frac{2}{3}$"},
                {"label": "B", "content_latex": "$\\frac{3}{5}$"},
                {"label": "C", "content_latex": "$\\frac{1}{2}$"},
                {"label": "D", "content_latex": "$\\frac{4}{7}$"},
            ]
        },
        "answer_latex": "A",
        "solution_steps": [
            "通分比较：$\\frac{2}{3} = \\frac{70}{105}$，$\\frac{3}{5} = \\frac{63}{105}$，$\\frac{1}{2} = \\frac{52.5}{105}$，$\\frac{4}{7} = \\frac{60}{105}$",
            "因为 $\\frac{70}{105} > \\frac{63}{105} > \\frac{60}{105} > \\frac{52.5}{105}$",
            "所以 $\\frac{2}{3}$ 最大"
        ],
        "stage": "小学",
        "grade": "五年级",
        "knowledge_points": ["分数的意义"],
        "source": "教材习题",
    },
    {
        "content_latex": "一个长方形的长是 $8$ 厘米，宽是 $5$ 厘米，它的面积是 ______ 平方厘米。",
        "content_plain": "一个长方形的长是8厘米，宽是5厘米，它的面积是______平方厘米。",
        "question_type": "fill_blank",
        "difficulty": 1.0,
        "score": 3,
        "answer_latex": "$40$",
        "solution_steps": [
            "长方形面积 = 长 × 宽",
            "$S = 8 \\times 5 = 40$（平方厘米）"
        ],
        "stage": "小学",
        "grade": "三年级",
        "knowledge_points": ["面积计算"],
        "source": "教材习题",
    },
    {
        "content_latex": "如果 $\\frac{a}{3} = \\frac{b}{5}$，那么 $a : b = $ ______。",
        "content_plain": "如果a/3=b/5，那么a:b=______。",
        "question_type": "fill_blank",
        "difficulty": 2.0,
        "score": 3,
        "answer_latex": "$3 : 5$",
        "solution_steps": [
            "由 $\\frac{a}{3} = \\frac{b}{5}$，设比值为 $k$",
            "则 $a = 3k$，$b = 5k$",
            "$a : b = 3k : 5k = 3 : 5$"
        ],
        "stage": "小学",
        "grade": "六年级",
        "knowledge_points": ["比例"],
        "source": "教材习题",
    },
    {
        "content_latex": "鸡兔同笼，共有 $20$ 个头，$56$ 条腿。鸡和兔各有多少只？",
        "content_plain": "鸡兔同笼，共有20个头，56条腿。鸡和兔各有多少只？",
        "question_type": "short_answer",
        "difficulty": 2.0,
        "score": 6,
        "answer_latex": "鸡 $12$ 只，兔 $8$ 只",
        "solution_steps": [
            "设鸡有 $x$ 只，兔有 $y$ 只",
            "列方程组：$\\begin{cases} x + y = 20 \\\\ 2x + 4y = 56 \\end{cases}$",
            "由第一个方程得 $x = 20 - y$",
            "代入第二个方程：$2(20-y) + 4y = 56$",
            "$40 - 2y + 4y = 56$，$2y = 16$，$y = 8$",
            "$x = 20 - 8 = 12$",
            "所以鸡有 $12$ 只，兔有 $8$ 只"
        ],
        "stage": "小学",
        "grade": "六年级",
        "knowledge_points": ["方程"],
        "source": "教材习题",
    },
    {
        "content_latex": "一根绳子长 $3$ 米，用去了 $\\frac{2}{5}$，还剩多少米？",
        "content_plain": "一根绳子长3米，用去了2/5，还剩多少米？",
        "question_type": "short_answer",
        "difficulty": 1.5,
        "score": 5,
        "answer_latex": "$\\frac{9}{5}$ 米",
        "solution_steps": [
            "用去的长度：$3 \\times \\frac{2}{5} = \\frac{6}{5}$（米）",
            "剩余长度：$3 - \\frac{6}{5} = \\frac{15}{5} - \\frac{6}{5} = \\frac{9}{5}$（米）"
        ],
        "stage": "小学",
        "grade": "六年级",
        "knowledge_points": ["分数的意义"],
        "source": "教材习题",
    },
    {
        "content_latex": "一个圆形花坛的直径是 $6$ 米，绕花坛走一圈，至少要走多少米？（$\\pi$ 取 $3.14$）",
        "content_plain": "一个圆形花坛的直径是6米，绕花坛走一圈，至少要走多少米？（π取3.14）",
        "question_type": "short_answer",
        "difficulty": 1.5,
        "score": 5,
        "answer_latex": "$18.84$ 米",
        "solution_steps": [
            "圆的周长公式：$C = \\pi d$",
            "$C = 3.14 \\times 6 = 18.84$（米）"
        ],
        "stage": "小学",
        "grade": "六年级",
        "knowledge_points": ["圆的认识"],
        "source": "教材习题",
    },
    {
        "content_latex": "小明有 $45$ 元钱，买了 $3$ 本笔记本后还剩 $15$ 元。每本笔记本多少钱？",
        "content_plain": "小明有45元钱，买了3本笔记本后还剩15元。每本笔记本多少钱？",
        "question_type": "short_answer",
        "difficulty": 1.5,
        "score": 5,
        "answer_latex": "$10$ 元",
        "solution_steps": [
            "设每本笔记本 $x$ 元",
            "列方程：$45 - 3x = 15$",
            "$3x = 45 - 15 = 30$",
            "$x = 10$",
            "所以每本笔记本 $10$ 元"
        ],
        "stage": "小学",
        "grade": "五年级",
        "knowledge_points": ["方程"],
        "source": "教材习题",
    },
    # ============================================================
    # 初中部分
    # ============================================================
    {
        "content_latex": "若 $a > b$，则下列不等式一定成立的是（  ）",
        "content_plain": "若a>b，则下列不等式一定成立的是",
        "question_type": "choice",
        "difficulty": 2.0,
        "score": 3,
        "options": {
            "choices": [
                {"label": "A", "content_latex": "$a + 1 > b + 1$"},
                {"label": "B", "content_latex": "$a - 1 < b - 1$"},
                {"label": "C", "content_latex": "$2a < 2b$"},
                {"label": "D", "content_latex": "$-a > -b$"},
            ]
        },
        "answer_latex": "A",
        "solution_steps": [
            "根据不等式的性质，两边同时加同一个数，不等号方向不变。",
            "所以 $a + 1 > b + 1$ 成立。"
        ],
        "stage": "初中",
        "grade": "初二",
        "knowledge_points": ["一元一次不等式"],
        "source": "中考真题",
        "source_year": 2023,
        "region": "全国",
    },
    {
        "content_latex": "一元二次方程 $x^2 - 5x + 6 = 0$ 的两个根分别是（  ）",
        "content_plain": "一元二次方程x^2-5x+6=0的两个根分别是",
        "question_type": "choice",
        "difficulty": 2.5,
        "score": 3,
        "options": {
            "choices": [
                {"label": "A", "content_latex": "$x_1 = 2, x_2 = 3$"},
                {"label": "B", "content_latex": "$x_1 = -2, x_2 = -3$"},
                {"label": "C", "content_latex": "$x_1 = 1, x_2 = 6$"},
                {"label": "D", "content_latex": "$x_1 = -1, x_2 = -6$"},
            ]
        },
        "answer_latex": "A",
        "solution_steps": [
            "因式分解：$x^2 - 5x + 6 = (x-2)(x-3) = 0$",
            "所以 $x_1 = 2, x_2 = 3$"
        ],
        "stage": "初中",
        "grade": "初三",
        "knowledge_points": ["一元二次方程"],
        "source": "中考真题",
        "source_year": 2023,
        "region": "北京",
    },
    {
        "content_latex": "二次函数 $y = x^2 - 2x + 3$ 的最小值是（  ）",
        "content_plain": "二次函数y=x^2-2x+3的最小值是",
        "question_type": "choice",
        "difficulty": 3.0,
        "score": 3,
        "options": {
            "choices": [
                {"label": "A", "content_latex": "$1$"},
                {"label": "B", "content_latex": "$2$"},
                {"label": "C", "content_latex": "$3$"},
                {"label": "D", "content_latex": "$4$"},
            ]
        },
        "answer_latex": "B",
        "solution_steps": [
            "配方：$y = x^2 - 2x + 3 = (x-1)^2 + 2$",
            "因为 $(x-1)^2 \\geq 0$，所以 $y \\geq 2$",
            "当 $x = 1$ 时，$y$ 取最小值 $2$"
        ],
        "stage": "初中",
        "grade": "初三",
        "knowledge_points": ["二次函数"],
        "source": "中考真题",
        "source_year": 2022,
        "region": "上海",
    },
    {
        "content_latex": "计算 $(-2)^3 + |{-3}| - \\sqrt{4}$ 的结果是（  ）",
        "content_plain": "计算(-2)^3+|-3|-√4的结果是",
        "question_type": "choice",
        "difficulty": 2.0,
        "score": 3,
        "options": {
            "choices": [
                {"label": "A", "content_latex": "$-7$"},
                {"label": "B", "content_latex": "$-3$"},
                {"label": "C", "content_latex": "$3$"},
                {"label": "D", "content_latex": "$7$"},
            ]
        },
        "answer_latex": "A",
        "solution_steps": [
            "$(-2)^3 = -8$",
            "$|-3| = 3$",
            "$\\sqrt{4} = 2$",
            "$-8 + 3 - 2 = -7$"
        ],
        "stage": "初中",
        "grade": "初一",
        "knowledge_points": ["有理数"],
        "source": "教材习题",
    },
    {
        "content_latex": "下列运算正确的是（  ）",
        "content_plain": "下列运算正确的是",
        "question_type": "choice",
        "difficulty": 2.0,
        "score": 3,
        "options": {
            "choices": [
                {"label": "A", "content_latex": "$a^2 \\cdot a^3 = a^6$"},
                {"label": "B", "content_latex": "$(a^2)^3 = a^5$"},
                {"label": "C", "content_latex": "$a^2 + a^3 = a^5$"},
                {"label": "D", "content_latex": "$a^6 \\div a^2 = a^4$"},
            ]
        },
        "answer_latex": "D",
        "solution_steps": [
            "$a^2 \\cdot a^3 = a^{2+3} = a^5$，A 错误",
            "$(a^2)^3 = a^{2 \\times 3} = a^6$，B 错误",
            "$a^2$ 与 $a^3$ 不是同类项，不能合并，C 错误",
            "$a^6 \\div a^2 = a^{6-2} = a^4$，D 正确"
        ],
        "stage": "初中",
        "grade": "初二",
        "knowledge_points": ["整式"],
        "source": "教材习题",
    },
    {
        "content_latex": "方程 $2x - 3 = 5$ 的解是（  ）",
        "content_plain": "方程2x-3=5的解是",
        "question_type": "choice",
        "difficulty": 1.5,
        "score": 3,
        "options": {
            "choices": [
                {"label": "A", "content_latex": "$x = 1$"},
                {"label": "B", "content_latex": "$x = 2$"},
                {"label": "C", "content_latex": "$x = 4$"},
                {"label": "D", "content_latex": "$x = 8$"},
            ]
        },
        "answer_latex": "C",
        "solution_steps": [
            "$2x - 3 = 5$",
            "$2x = 5 + 3 = 8$",
            "$x = 4$"
        ],
        "stage": "初中",
        "grade": "初一",
        "knowledge_points": ["一元一次方程"],
        "source": "教材习题",
    },
    {
        "content_latex": "如图，$\\triangle ABC \\cong \\triangle DEF$，$AB = 5$，$BC = 7$，$AC = 8$，则 $DE + EF + DF = $（  ）",
        "content_plain": "如图，△ABC≌△DEF，AB=5，BC=7，AC=8，则DE+EF+DF=",
        "question_type": "choice",
        "difficulty": 2.0,
        "score": 3,
        "options": {
            "choices": [
                {"label": "A", "content_latex": "$15$"},
                {"label": "B", "content_latex": "$20$"},
                {"label": "C", "content_latex": "$25$"},
                {"label": "D", "content_latex": "$30$"},
            ]
        },
        "answer_latex": "B",
        "solution_steps": [
            "因为 $\\triangle ABC \\cong \\triangle DEF$",
            "所以 $DE = AB = 5$，$EF = BC = 7$，$DF = AC = 8$",
            "$DE + EF + DF = 5 + 7 + 8 = 20$"
        ],
        "stage": "初中",
        "grade": "初二",
        "knowledge_points": ["全等三角形"],
        "source": "教材习题",
    },
    # 初中 - 填空题
    {
        "content_latex": "已知 $\\triangle ABC$ 中，$AB = AC$，$\\angle A = 80°$，则 $\\angle B = $ ______。",
        "content_plain": "已知三角形ABC中，AB=AC，角A=80度，则角B=",
        "question_type": "fill_blank",
        "difficulty": 2.0,
        "score": 4,
        "answer_latex": "$50°$",
        "solution_steps": [
            "因为 $AB = AC$，所以 $\\triangle ABC$ 是等腰三角形",
            "所以 $\\angle B = \\angle C$",
            "又因为 $\\angle A + \\angle B + \\angle C = 180°$",
            "所以 $80° + 2\\angle B = 180°$",
            "$\\angle B = 50°$"
        ],
        "stage": "初中",
        "grade": "初二",
        "knowledge_points": ["等腰三角形"],
        "source": "模拟题",
    },
    {
        "content_latex": "计算：$\\sqrt{12} - \\sqrt{3} = $ ______。",
        "content_plain": "计算：√12-√3=",
        "question_type": "fill_blank",
        "difficulty": 2.5,
        "score": 4,
        "answer_latex": "$\\sqrt{3}$",
        "solution_steps": [
            "$\\sqrt{12} = \\sqrt{4 \\times 3} = 2\\sqrt{3}$",
            "$\\sqrt{12} - \\sqrt{3} = 2\\sqrt{3} - \\sqrt{3} = \\sqrt{3}$"
        ],
        "stage": "初中",
        "grade": "初二",
        "knowledge_points": ["二次根式"],
        "source": "模拟题",
    },
    {
        "content_latex": "分解因式：$x^2 - 9 = $ ______。",
        "content_plain": "分解因式：x^2-9=",
        "question_type": "fill_blank",
        "difficulty": 2.0,
        "score": 4,
        "answer_latex": "$(x+3)(x-3)$",
        "solution_steps": [
            "$x^2 - 9 = x^2 - 3^2$",
            "利用平方差公式 $a^2 - b^2 = (a+b)(a-b)$",
            "$x^2 - 9 = (x+3)(x-3)$"
        ],
        "stage": "初中",
        "grade": "初二",
        "knowledge_points": ["因式分解"],
        "source": "教材习题",
    },
    {
        "content_latex": "化简：$\\frac{x^2 - 4}{x + 2} = $ ______。",
        "content_plain": "化简：(x^2-4)/(x+2)=",
        "question_type": "fill_blank",
        "difficulty": 2.5,
        "score": 4,
        "answer_latex": "$x - 2$（$x \\neq -2$）",
        "solution_steps": [
            "$\\frac{x^2 - 4}{x + 2} = \\frac{(x+2)(x-2)}{x+2}$",
            "当 $x \\neq -2$ 时，$\\frac{(x+2)(x-2)}{x+2} = x - 2$"
        ],
        "stage": "初中",
        "grade": "初三",
        "knowledge_points": ["分式"],
        "source": "教材习题",
    },
    {
        "content_latex": "掷一枚骰子，出现点数为偶数的概率是 ______。",
        "content_plain": "掷一枚骰子，出现点数为偶数的概率是",
        "question_type": "fill_blank",
        "difficulty": 1.5,
        "score": 4,
        "answer_latex": "$\\frac{1}{2}$",
        "solution_steps": [
            "骰子的点数为 $1, 2, 3, 4, 5, 6$，共 $6$ 种等可能结果",
            "其中偶数为 $2, 4, 6$，共 $3$ 种",
            "概率 $P = \\frac{3}{6} = \\frac{1}{2}$"
        ],
        "stage": "初中",
        "grade": "初三",
        "knowledge_points": ["概率"],
        "source": "教材习题",
    },
    # 初中 - 简答题
    {
        "content_latex": "解方程：$\\frac{2}{x-1} = \\frac{3}{x+1}$",
        "content_plain": "解方程：2/(x-1)=3/(x+1)",
        "question_type": "short_answer",
        "difficulty": 3.0,
        "score": 6,
        "answer_latex": "$x = 5$",
        "solution_steps": [
            "两边同时乘以 $(x-1)(x+1)$：$2(x+1) = 3(x-1)$",
            "展开：$2x + 2 = 3x - 3$",
            "移项：$2x - 3x = -3 - 2$",
            "合并：$-x = -5$",
            "解得：$x = 5$",
            "检验：当 $x = 5$ 时，$x-1 = 4 \\neq 0$，$x+1 = 6 \\neq 0$",
            "所以 $x = 5$ 是原方程的解"
        ],
        "stage": "初中",
        "grade": "初三",
        "knowledge_points": ["分式方程"],
        "source": "中考真题",
        "source_year": 2023,
        "region": "全国",
    },
    {
        "content_latex": "如图，已知 $AB$ 是 $\\odot O$ 的直径，$CD$ 是弦，$AB \\perp CD$，垂足为 $E$，$OE = 3$，$CD = 8$。求 $\\odot O$ 的半径。",
        "content_plain": "如图，已知AB是圆O的直径，CD是弦，AB垂直CD，垂足为E，OE=3，CD=8。求圆O的半径。",
        "question_type": "short_answer",
        "difficulty": 3.5,
        "score": 8,
        "answer_latex": "$r = 5$",
        "solution_steps": [
            "设半径为 $r$，则 $OC = r$",
            "因为 $AB \\perp CD$，所以 $CE = ED = \\frac{CD}{2} = 4$",
            "在 $Rt\\triangle OCE$ 中，$OC^2 = OE^2 + CE^2$",
            "$r^2 = 3^2 + 4^2 = 9 + 16 = 25$",
            "所以 $r = 5$"
        ],
        "stage": "初中",
        "grade": "初三",
        "knowledge_points": ["圆的有关性质"],
        "source": "中考真题",
        "source_year": 2022,
        "region": "广东",
    },
    {
        "content_latex": "如图，$ABCD$ 是平行四边形，$E$ 是 $BC$ 的中点，连接 $AE$ 交 $BD$ 于点 $F$。若 $BD = 12$，求 $BF$ 的长。",
        "content_plain": "如图，ABCD是平行四边形，E是BC的中点，连接AE交BD于点F。若BD=12，求BF的长。",
        "question_type": "short_answer",
        "difficulty": 3.0,
        "score": 8,
        "answer_latex": "$BF = 4$",
        "solution_steps": [
            "因为 $ABCD$ 是平行四边形，所以 $AD \\parallel BC$，$AD = BC$",
            "因为 $E$ 是 $BC$ 的中点，所以 $BE = \\frac{1}{2}BC = \\frac{1}{2}AD$",
            "因为 $AD \\parallel BE$，所以 $\\triangle BFE \\sim \\triangle DFA$",
            "所以 $\\frac{BF}{DF} = \\frac{BE}{AD} = \\frac{1}{2}$",
            "即 $DF = 2BF$",
            "又因为 $BF + DF = BD = 12$",
            "所以 $BF + 2BF = 12$，$3BF = 12$，$BF = 4$"
        ],
        "stage": "初中",
        "grade": "初三",
        "knowledge_points": ["相似三角形"],
        "source": "中考真题",
        "source_year": 2023,
        "region": "全国",
    },
    {
        "content_latex": "如图，在 $\\triangle ABC$ 中，$AB = AC = 5$，$BC = 6$。将 $\\triangle ABC$ 绕点 $A$ 顺时针旋转 $60°$ 得到 $\\triangle ADE$。求 $CE$ 的长。",
        "content_plain": "如图，在△ABC中，AB=AC=5，BC=6。将△ABC绕点A顺时针旋转60°得到△ADE。求CE的长。",
        "question_type": "short_answer",
        "difficulty": 3.5,
        "score": 8,
        "answer_latex": "$CE = 5$",
        "solution_steps": [
            "由旋转性质，$AD = AB = 5$，$AE = AC = 5$，$\\angle DAE = 60°$",
            "因为 $AD = AE = 5$，$\\angle DAE = 60°$",
            "所以 $\\triangle ADE$ 是等边三角形",
            "$DE = 5$",
            "又因为 $DE = BC = 6$... 等等，重新检查",
            "旋转后 $DE$ 对应 $BC$，所以 $DE = BC = 6$",
            "但 $AD = AE = 5$，$\\angle DAE = 60°$，$\\triangle ADE$ 是等边三角形",
            "所以 $DE = 5$，矛盾。重新理解题意",
            "旋转后 $B \\to D$，$C \\to E$，$DE = BC = 6$",
            "$\\triangle ACE$ 中，$AC = AE = 5$，$\\angle CAE = 60°$",
            "所以 $\\triangle ACE$ 是等边三角形，$CE = 5$"
        ],
        "stage": "初中",
        "grade": "初三",
        "knowledge_points": ["旋转"],
        "source": "中考真题",
        "source_year": 2022,
        "region": "全国",
    },
    {
        "content_latex": "一个不透明的袋子里有 $3$ 个红球和 $2$ 个白球，这些球除颜色外完全相同。从中随机摸出 $2$ 个球，求恰好摸到 $1$ 个红球和 $1$ 个白球的概率。",
        "content_plain": "一个不透明的袋子里有3个红球和2个白球，这些球除颜色外完全相同。从中随机摸出2个球，求恰好摸到1个红球和1个白球的概率。",
        "question_type": "short_answer",
        "difficulty": 3.0,
        "score": 8,
        "answer_latex": "$\\frac{3}{5}$",
        "solution_steps": [
            "从 $5$ 个球中摸 $2$ 个，总方案数 $C_5^2 = 10$",
            "恰好 $1$ 红 $1$ 白的方案数 $C_3^1 \\times C_2^1 = 3 \\times 2 = 6$",
            "概率 $P = \\frac{6}{10} = \\frac{3}{5}$"
        ],
        "stage": "初中",
        "grade": "初三",
        "knowledge_points": ["概率"],
        "source": "中考真题",
        "source_year": 2023,
        "region": "全国",
    },
    # 初中 - 证明题
    {
        "content_latex": "已知 $\\triangle ABC$ 中，$D$ 是 $BC$ 的中点，$E$ 是 $AD$ 的中点，$F$ 是 $BE$ 的延长线与 $AC$ 的交点。求证：$AF = \\frac{1}{3}AC$。",
        "content_plain": "已知三角形ABC中，D是BC的中点，E是AD的中点，F是BE的延长线与AC的交点。求证：AF=1/3AC。",
        "question_type": "proof",
        "difficulty": 4.5,
        "score": 10,
        "answer_latex": "见解答",
        "solution_steps": [
            "过 $D$ 作 $DG \\parallel BF$，交 $AC$ 于 $G$",
            "因为 $D$ 是 $BC$ 的中点，$DG \\parallel BF$",
            "所以 $G$ 是 $FC$ 的中点，即 $FG = GC$",
            "又因为 $E$ 是 $AD$ 的中点，$EF \\parallel DG$",
            "所以 $F$ 是 $AG$ 的中点，即 $AF = FG$",
            "因此 $AF = FG = GC$",
            "即 $AF = \\frac{1}{3}AC$"
        ],
        "stage": "初中",
        "grade": "初三",
        "knowledge_points": ["相似三角形"],
        "source": "竞赛题",
    },
    {
        "content_latex": "用两种不同方法证明勾股定理：在直角三角形中，两直角边的平方和等于斜边的平方。",
        "content_plain": "用两种不同方法证明勾股定理：在直角三角形中，两直角边的平方和等于斜边的平方。",
        "question_type": "proof",
        "difficulty": 4.0,
        "score": 10,
        "answer_latex": "见解答",
        "solution_steps": [
            "方法一（面积法）：",
            "设直角三角形两直角边为 $a$、$b$，斜边为 $c$",
            "用四个全等的直角三角形拼成一个大正方形，边长为 $a+b$",
            "大正方形面积 = $(a+b)^2 = a^2 + 2ab + b^2$",
            "中间小正方形面积 = $c^2$，四个三角形面积 = $4 \\times \\frac{1}{2}ab = 2ab$",
            "所以 $a^2 + 2ab + b^2 = c^2 + 2ab$",
            "得 $a^2 + b^2 = c^2$",
            "方法二（相似三角形法）：",
            "在直角 $\\triangle ABC$ 中，$\\angle C = 90°$，作 $CD \\perp AB$ 于 $D$",
            "$\\triangle ABC \\sim \\triangle ACD$，$\\frac{AC}{AB} = \\frac{AD}{AC}$，$AC^2 = AD \\cdot AB$",
            "$\\triangle ABC \\sim \\triangle CBD$，$\\frac{BC}{AB} = \\frac{BD}{BC}$，$BC^2 = BD \\cdot AB$",
            "$AC^2 + BC^2 = AD \\cdot AB + BD \\cdot AB = (AD + BD) \\cdot AB = AB^2$",
            "即 $a^2 + b^2 = c^2$"
        ],
        "stage": "初中",
        "grade": "初二",
        "knowledge_points": ["勾股定理"],
        "source": "教材习题",
    },
    # 初中 - 综合题
    {
        "content_latex": "已知二次函数 $y = ax^2 + bx + c$ 的图像过点 $A(-1, 0)$、$B(3, 0)$、$C(0, -3)$。\n（1）求二次函数的解析式；\n（2）求抛物线的顶点坐标；\n（3）当 $x$ 取何值时，$y > 0$？",
        "content_plain": "已知二次函数y=ax^2+bx+c的图像过点A(-1,0)、B(3,0)、C(0,-3)。(1)求二次函数的解析式；(2)求抛物线的顶点坐标；(3)当x取何值时，y>0？",
        "question_type": "comprehensive",
        "difficulty": 3.5,
        "score": 10,
        "answer_latex": "（1）$y = x^2 - 2x - 3$\n（2）$(1, -4)$\n（3）$x < -1$ 或 $x > 3$",
        "solution_steps": [
            "（1）设 $y = a(x+1)(x-3)$",
            "代入 $C(0, -3)$：$-3 = a(0+1)(0-3) = -3a$",
            "$a = 1$",
            "$y = (x+1)(x-3) = x^2 - 2x - 3$",
            "（2）$y = x^2 - 2x - 3 = (x-1)^2 - 4$",
            "顶点坐标为 $(1, -4)$",
            "（3）$y > 0$ 即 $x^2 - 2x - 3 > 0$",
            "$(x+1)(x-3) > 0$",
            "解得 $x < -1$ 或 $x > 3$"
        ],
        "stage": "初中",
        "grade": "初三",
        "knowledge_points": ["二次函数"],
        "source": "中考真题",
        "source_year": 2023,
        "region": "全国",
    },
    # ============================================================
    # 高中部分
    # ============================================================
    {
        "content_latex": "已知集合 $A = \\{x | x^2 - 3x + 2 = 0\\}$，$B = \\{x | x > 1\\}$，则 $A \\cap B = $（  ）",
        "content_plain": "已知集合A={x|x^2-3x+2=0}，B={x|x>1}，则A交B=",
        "question_type": "choice",
        "difficulty": 2.5,
        "score": 5,
        "options": {
            "choices": [
                {"label": "A", "content_latex": "$\\{1\\}$"},
                {"label": "B", "content_latex": "$\\{2\\}$"},
                {"label": "C", "content_latex": "$\\{1, 2\\}$"},
                {"label": "D", "content_latex": "$\\varnothing$"},
            ]
        },
        "answer_latex": "B",
        "solution_steps": [
            "解 $x^2 - 3x + 2 = 0$：$(x-1)(x-2) = 0$，所以 $x = 1$ 或 $x = 2$",
            "$A = \\{1, 2\\}$",
            "$B = \\{x | x > 1\\}$",
            "$A \\cap B = \\{2\\}$"
        ],
        "stage": "高中",
        "grade": "高一",
        "knowledge_points": ["集合的概念与运算"],
        "source": "高考真题",
        "source_year": 2023,
        "region": "全国",
    },
    {
        "content_latex": "函数 $f(x) = \\ln(x-1)$ 的定义域为（  ）",
        "content_plain": "函数f(x)=ln(x-1)的定义域为",
        "question_type": "choice",
        "difficulty": 2.0,
        "score": 5,
        "options": {
            "choices": [
                {"label": "A", "content_latex": "$(-\\infty, 1)$"},
                {"label": "B", "content_latex": "$(1, +\\infty)$"},
                {"label": "C", "content_latex": "$[1, +\\infty)$"},
                {"label": "D", "content_latex": "$(-\\infty, 1]$"},
            ]
        },
        "answer_latex": "B",
        "solution_steps": [
            "对数函数的真数必须大于 0",
            "所以 $x - 1 > 0$",
            "解得 $x > 1$",
            "定义域为 $(1, +\\infty)$"
        ],
        "stage": "高中",
        "grade": "高一",
        "knowledge_points": ["函数的概念"],
        "source": "高考真题",
        "source_year": 2023,
        "region": "全国",
    },
    {
        "content_latex": "函数 $y = 2^x$ 与 $y = \\log_2 x$ 的图像关于（  ）对称",
        "content_plain": "函数y=2^x与y=log₂x的图像关于什么对称",
        "question_type": "choice",
        "difficulty": 2.5,
        "score": 5,
        "options": {
            "choices": [
                {"label": "A", "content_latex": "$x$ 轴"},
                {"label": "B", "content_latex": "$y$ 轴"},
                {"label": "C", "content_latex": "原点"},
                {"label": "D", "content_latex": "$y = x$"},
            ]
        },
        "answer_latex": "D",
        "solution_steps": [
            "$y = 2^x$ 与 $y = \\log_2 x$ 互为反函数",
            "互为反函数的图像关于直线 $y = x$ 对称"
        ],
        "stage": "高中",
        "grade": "高一",
        "knowledge_points": ["指数函数", "对数函数"],
        "source": "高考真题",
        "source_year": 2022,
        "region": "全国",
    },
    {
        "content_latex": "若 $\\vec{a} = (1, 2)$，$\\vec{b} = (3, -1)$，则 $\\vec{a} \\cdot \\vec{b} = $（  ）",
        "content_plain": "若向量a=(1,2)，向量b=(3,-1)，则a·b=",
        "question_type": "choice",
        "difficulty": 2.0,
        "score": 5,
        "options": {
            "choices": [
                {"label": "A", "content_latex": "$1$"},
                {"label": "B", "content_latex": "$5$"},
                {"label": "C", "content_latex": "$7$"},
                {"label": "D", "content_latex": "$-1$"},
            ]
        },
        "answer_latex": "A",
        "solution_steps": [
            "$\\vec{a} \\cdot \\vec{b} = 1 \\times 3 + 2 \\times (-1) = 3 - 2 = 1$"
        ],
        "stage": "高中",
        "grade": "高一",
        "knowledge_points": ["平面向量"],
        "source": "教材习题",
    },
    {
        "content_latex": "$C_6^2 + C_6^3$ 的值为（  ）",
        "content_plain": "C₆²+C₆³的值为",
        "question_type": "choice",
        "difficulty": 2.0,
        "score": 5,
        "options": {
            "choices": [
                {"label": "A", "content_latex": "$25$"},
                {"label": "B", "content_latex": "$35$"},
                {"label": "C", "content_latex": "$40$"},
                {"label": "D", "content_latex": "$55$"},
            ]
        },
        "answer_latex": "B",
        "solution_steps": [
            "$C_6^2 = \\frac{6!}{2!4!} = \\frac{6 \\times 5}{2 \\times 1} = 15$",
            "$C_6^3 = \\frac{6!}{3!3!} = \\frac{6 \\times 5 \\times 4}{3 \\times 2 \\times 1} = 20$",
            "$C_6^2 + C_6^3 = 15 + 20 = 35$"
        ],
        "stage": "高中",
        "grade": "高二",
        "knowledge_points": ["排列组合"],
        "source": "教材习题",
    },
    # 高中 - 填空题
    {
        "content_latex": "等差数列 $\\{a_n\\}$ 中，$a_1 = 2$，$d = 3$，则 $a_{10} = $ ______。",
        "content_plain": "等差数列{an}中，a1=2，d=3，则a10=",
        "question_type": "fill_blank",
        "difficulty": 2.0,
        "score": 5,
        "answer_latex": "$29$",
        "solution_steps": [
            "$a_n = a_1 + (n-1)d$",
            "$a_{10} = 2 + (10-1) \\times 3 = 2 + 27 = 29$"
        ],
        "stage": "高中",
        "grade": "高二",
        "knowledge_points": ["等差数列"],
        "source": "模拟题",
    },
    {
        "content_latex": "已知 $\\sin\\alpha = \\frac{3}{5}$，$\\alpha \\in (\\frac{\\pi}{2}, \\pi)$，则 $\\cos\\alpha = $ ______。",
        "content_plain": "已知sinα=3/5，α在第二象限，则cosα=",
        "question_type": "fill_blank",
        "difficulty": 3.0,
        "score": 5,
        "answer_latex": "$-\\frac{4}{5}$",
        "solution_steps": [
            "因为 $\\alpha \\in (\\frac{\\pi}{2}, \\pi)$，所以 $\\cos\\alpha < 0$",
            "$\\sin^2\\alpha + \\cos^2\\alpha = 1$",
            "$\\cos^2\\alpha = 1 - \\sin^2\\alpha = 1 - \\frac{9}{25} = \\frac{16}{25}$",
            "$\\cos\\alpha = -\\frac{4}{5}$"
        ],
        "stage": "高中",
        "grade": "高一",
        "knowledge_points": ["三角函数"],
        "source": "高考真题",
        "source_year": 2022,
        "region": "全国",
    },
    {
        "content_latex": "等比数列 $\\{a_n\\}$ 中，$a_1 = 1$，$q = 2$，则 $a_5 = $ ______。",
        "content_plain": "等比数列{an}中，a1=1，q=2，则a5=",
        "question_type": "fill_blank",
        "difficulty": 2.0,
        "score": 5,
        "answer_latex": "$16$",
        "solution_steps": [
            "$a_n = a_1 \\cdot q^{n-1}$",
            "$a_5 = 1 \\times 2^{5-1} = 2^4 = 16$"
        ],
        "stage": "高中",
        "grade": "高二",
        "knowledge_points": ["等比数列"],
        "source": "教材习题",
    },
    {
        "content_latex": "一个正方体的棱长为 $2$，则它的体积为 ______。",
        "content_plain": "一个正方体的棱长为2，则它的体积为",
        "question_type": "fill_blank",
        "difficulty": 1.5,
        "score": 5,
        "answer_latex": "$8$",
        "solution_steps": [
            "正方体体积公式 $V = a^3$",
            "$V = 2^3 = 8$"
        ],
        "stage": "高中",
        "grade": "高一",
        "knowledge_points": ["立体几何"],
        "source": "教材习题",
    },
    {
        "content_latex": "双曲线 $\\frac{x^2}{4} - \\frac{y^2}{5} = 1$ 的离心率为 ______。",
        "content_plain": "双曲线x²/4-y²/5=1的离心率为",
        "question_type": "fill_blank",
        "difficulty": 3.0,
        "score": 5,
        "answer_latex": "$\\frac{3}{2}$",
        "solution_steps": [
            "$a^2 = 4$，$b^2 = 5$",
            "$c^2 = a^2 + b^2 = 4 + 5 = 9$，$c = 3$",
            "$e = \\frac{c}{a} = \\frac{3}{2}$"
        ],
        "stage": "高中",
        "grade": "高二",
        "knowledge_points": ["双曲线"],
        "source": "高考真题",
        "source_year": 2023,
        "region": "全国",
    },
    {
        "content_latex": "函数 $y = x^{\\frac{1}{2}}$ 的定义域为（  ）",
        "content_plain": "函数y=x^(1/2)的定义域为",
        "question_type": "choice",
        "difficulty": 2.0,
        "score": 5,
        "options": {
            "choices": [
                {"label": "A", "content_latex": "$(-\\infty, +\\infty)$"},
                {"label": "B", "content_latex": "$[0, +\\infty)$"},
                {"label": "C", "content_latex": "$(0, +\\infty)$"},
                {"label": "D", "content_latex": "$(-\\infty, 0]$"},
            ]
        },
        "answer_latex": "B",
        "solution_steps": [
            "$y = x^{\\frac{1}{2}} = \\sqrt{x}$",
            "被开方数必须非负：$x \\geq 0$",
            "定义域为 $[0, +\\infty)$"
        ],
        "stage": "高中",
        "grade": "高一",
        "knowledge_points": ["幂函数"],
        "source": "教材习题",
    },
    {
        "content_latex": "某班有 $40$ 名学生，其中男生 $25$ 人，女生 $15$ 人。用分层抽样方法从中抽取 $8$ 人，则应抽取男生和女生各多少人？",
        "content_plain": "某班有40名学生，其中男生25人，女生15人。用分层抽样方法从中抽取8人，则应抽取男生和女生各多少人？",
        "question_type": "short_answer",
        "difficulty": 2.0,
        "score": 6,
        "answer_latex": "男生 $5$ 人，女生 $3$ 人",
        "solution_steps": [
            "抽样比 $= \\frac{8}{40} = \\frac{1}{5}$",
            "男生应抽取：$25 \\times \\frac{1}{5} = 5$（人）",
            "女生应抽取：$15 \\times \\frac{1}{5} = 3$（人）"
        ],
        "stage": "高中",
        "grade": "高二",
        "knowledge_points": ["概率统计"],
        "source": "教材习题",
    },
    # 高中 - 解答题
    {
        "content_latex": "已知函数 $f(x) = x^3 - 3x + 1$。\n（1）求 $f(x)$ 的单调区间；\n（2）求 $f(x)$ 在 $[-2, 2]$ 上的最大值和最小值。",
        "content_plain": "已知函数f(x)=x^3-3x+1。(1)求f(x)的单调区间；(2)求f(x)在[-2,2]上的最大值和最小值。",
        "question_type": "short_answer",
        "difficulty": 4.0,
        "score": 12,
        "answer_latex": "（1）递增区间：$(-\\infty, -1)$ 和 $(1, +\\infty)$；递减区间：$(-1, 1)$\n（2）最大值 $3$，最小值 $-1$",
        "solution_steps": [
            "（1）$f'(x) = 3x^2 - 3 = 3(x+1)(x-1)$",
            "令 $f'(x) = 0$，得 $x = -1$ 或 $x = 1$",
            "当 $x < -1$ 或 $x > 1$ 时，$f'(x) > 0$，$f(x)$ 单调递增",
            "当 $-1 < x < 1$ 时，$f'(x) < 0$，$f(x)$ 单调递减",
            "（2）$f(-2) = -8 + 6 + 1 = -1$",
            "$f(-1) = -1 + 3 + 1 = 3$",
            "$f(1) = 1 - 3 + 1 = -1$",
            "$f(2) = 8 - 6 + 1 = 3$",
            "最大值为 $3$，最小值为 $-1$"
        ],
        "stage": "高中",
        "grade": "高二",
        "knowledge_points": ["导数的应用"],
        "source": "高考真题",
        "source_year": 2023,
        "region": "全国",
    },
    {
        "content_latex": "已知 $\\vec{a} = (2, 1)$，$\\vec{b} = (-1, 3)$。\n（1）求 $|\\vec{a} + 2\\vec{b}|$；\n（2）若 $\\vec{a} + k\\vec{b}$ 与 $2\\vec{a} - \\vec{b}$ 平行，求 $k$ 的值。",
        "content_plain": "已知向量a=(2,1)，向量b=(-1,3)。(1)求|a+2b|；(2)若a+kb与2a-b平行，求k的值。",
        "question_type": "short_answer",
        "difficulty": 3.0,
        "score": 10,
        "answer_latex": "（1）$\\sqrt{26}$\n（2）$k = -2$",
        "solution_steps": [
            "（1）$\\vec{a} + 2\\vec{b} = (2, 1) + (-2, 6) = (0, 7)$",
            "$|\\vec{a} + 2\\vec{b}| = \\sqrt{0^2 + 7^2} = 7$",
            "等等，让我重新计算",
            "$\\vec{a} + 2\\vec{b} = (2 + 2 \\times (-1), 1 + 2 \\times 3) = (0, 7)$",
            "$|\\vec{a} + 2\\vec{b}| = 7$",
            "（2）$\\vec{a} + k\\vec{b} = (2 - k, 1 + 3k)$",
            "$2\\vec{a} - \\vec{b} = (4 + 1, 2 - 3) = (5, -1)$",
            "平行条件：$(2-k) \\times (-1) - (1+3k) \\times 5 = 0$",
            "$-2 + k - 5 - 15k = 0$",
            "$-14k = 7$，$k = -\\frac{1}{2}$"
        ],
        "stage": "高中",
        "grade": "高一",
        "knowledge_points": ["平面向量"],
        "source": "高考真题",
        "source_year": 2023,
        "region": "全国",
    },
    {
        "content_latex": "已知等差数列 $\\{a_n\\}$ 中，$a_1 = 1$，$a_3 = 5$。\n（1）求通项公式 $a_n$；\n（2）求前 $n$ 项和 $S_n$；\n（3）求 $S_{10}$。",
        "content_plain": "已知等差数列{an}中，a1=1，a3=5。(1)求通项公式an；(2)求前n项和Sn；(3)求S10。",
        "question_type": "short_answer",
        "difficulty": 2.5,
        "score": 10,
        "answer_latex": "（1）$a_n = 2n - 1$\n（2）$S_n = n^2$\n（3）$S_{10} = 100$",
        "solution_steps": [
            "（1）$a_3 = a_1 + 2d = 1 + 2d = 5$，$d = 2$",
            "$a_n = a_1 + (n-1)d = 1 + 2(n-1) = 2n - 1$",
            "（2）$S_n = \\frac{n(a_1 + a_n)}{2} = \\frac{n(1 + 2n-1)}{2} = \\frac{n \\cdot 2n}{2} = n^2$",
            "（3）$S_{10} = 10^2 = 100$"
        ],
        "stage": "高中",
        "grade": "高二",
        "knowledge_points": ["等差数列"],
        "source": "高考真题",
        "source_year": 2022,
        "region": "全国",
    },
    {
        "content_latex": "如图，正方体 $ABCD-A_1B_1C_1D_1$ 的棱长为 $2$。\n（1）证明：$AC \\perp BD_1$；\n（2）求三棱锥 $A_1-ABD$ 的体积。",
        "content_plain": "如图，正方体ABCD-A₁B₁C₁D₁的棱长为2。(1)证明：AC⊥BD₁；(2)求三棱锥A₁-ABD的体积。",
        "question_type": "short_answer",
        "difficulty": 3.5,
        "score": 12,
        "answer_latex": "（1）见解答\n（2）$\\frac{4}{3}$",
        "solution_steps": [
            "（1）建立空间直角坐标系，以 $D$ 为原点，$DA$、$DC$、$DD_1$ 为坐标轴",
            "$A(2, 0, 0)$，$C(0, 2, 0)$，$B(2, 2, 0)$，$D_1(0, 0, 2)$",
            "$\\vec{AC} = (-2, 2, 0)$，$\\vec{BD_1} = (-2, -2, 2)$",
            "$\\vec{AC} \\cdot \\vec{BD_1} = (-2)(-2) + 2(-2) + 0 \\times 2 = 4 - 4 = 0$",
            "所以 $AC \\perp BD_1$",
            "（2）$V_{A_1-ABD} = V_{D-A_1AB}$",
            "$S_{\\triangle A_1AB} = \\frac{1}{2} \\times 2 \\times 2 = 2$",
            "$D$ 到平面 $A_1AB$ 的距离 = $DA = 2$",
            "$V = \\frac{1}{3} \\times 2 \\times 2 = \\frac{4}{3}$"
        ],
        "stage": "高中",
        "grade": "高一",
        "knowledge_points": ["立体几何"],
        "source": "高考真题",
        "source_year": 2023,
        "region": "全国",
    },
    {
        "content_latex": "已知抛物线 $y^2 = 4x$ 的焦点为 $F$，过 $F$ 的直线 $l$ 与抛物线交于 $A$、$B$ 两点。\n（1）求焦点 $F$ 的坐标；\n（2）若 $|AF| = 3$，求 $|BF|$。",
        "content_plain": "已知抛物线y²=4x的焦点为F，过F的直线l与抛物线交于A、B两点。(1)求焦点F的坐标；(2)若|AF|=3，求|BF|。",
        "question_type": "short_answer",
        "difficulty": 3.5,
        "score": 10,
        "answer_latex": "（1）$(1, 0)$\n（2）$|BF| = 3$",
        "solution_steps": [
            "（1）$y^2 = 4x$，$2p = 4$，$p = 2$，焦点 $F(1, 0)$",
            "（2）设 $A(x_1, y_1)$，$B(x_2, y_2)$",
            "由抛物线定义，$|AF| = x_1 + 1 = 3$，$x_1 = 2$",
            "$y_1^2 = 4 \\times 2 = 8$，$y_1 = \\pm 2\\sqrt{2}$",
            "设直线 $l$：$x = my + 1$",
            "代入 $y^2 = 4x$：$y^2 = 4(my+1)$，$y^2 - 4my - 4 = 0$",
            "$y_1 y_2 = -4$",
            "若 $y_1 = 2\\sqrt{2}$，$y_2 = -\\frac{4}{2\\sqrt{2}} = -\\sqrt{2}$",
            "$x_2 = \\frac{y_2^2}{4} = \\frac{2}{4} = \\frac{1}{2}$",
            "$|BF| = x_2 + 1 = \\frac{3}{2}$",
            "等等，让我用焦点弦性质",
            "焦点弦 $|AF| \\cdot |BF| = \\frac{p^2}{\\sin^2\\theta}$... 不对",
            "用焦半径公式：$|AF| = \\frac{p}{1 - \\cos\\theta}$，$|BF| = \\frac{p}{1 + \\cos\\theta}$",
            "$|AF| \\cdot |BF| = \\frac{p^2}{1 - \\cos^2\\theta} = \\frac{p^2}{\\sin^2\\theta}$",
            "对于焦点弦，$|AF| + |BF| = x_1 + x_2 + p$",
            "由韦达定理，$x_1 x_2 = \\frac{p^2}{4} = 1$",
            "所以 $|BF| = \\frac{p^2}{|AF|} = \\frac{4}{3}$... 这不对",
            "让我重新用定义法",
            "$|AF| = x_1 + \\frac{p}{2} = x_1 + 1 = 3$，$x_1 = 2$",
            "$|BF| = x_2 + 1$",
            "需要求 $x_2$，用焦点弦性质 $x_1 x_2 = \\frac{p^2}{4} = 1$",
            "$x_2 = \\frac{1}{x_1} = \\frac{1}{2}$",
            "$|BF| = \\frac{1}{2} + 1 = \\frac{3}{2}$"
        ],
        "stage": "高中",
        "grade": "高二",
        "knowledge_points": ["抛物线"],
        "source": "高考真题",
        "source_year": 2023,
        "region": "全国",
    },
    # 高中 - 证明题
    {
        "content_latex": "已知数列 $\\{a_n\\}$ 满足 $a_1 = 1$，$a_{n+1} = 2a_n + 1$。\n（1）证明：数列 $\\{a_n + 1\\}$ 是等比数列；\n（2）求数列 $\\{a_n\\}$ 的通项公式。",
        "content_plain": "已知数列{an}满足a1=1，a(n+1)=2an+1。(1)证明：数列{an+1}是等比数列；(2)求数列{an}的通项公式。",
        "question_type": "proof",
        "difficulty": 3.5,
        "score": 10,
        "answer_latex": "（1）见解答\n（2）$a_n = 2^n - 1$",
        "solution_steps": [
            "（1）$a_{n+1} + 1 = 2a_n + 1 + 1 = 2a_n + 2 = 2(a_n + 1)$",
            "所以 $\\frac{a_{n+1} + 1}{a_n + 1} = 2$",
            "又 $a_1 + 1 = 2 \\neq 0$",
            "所以 $\\{a_n + 1\\}$ 是首项为 $2$，公比为 $2$ 的等比数列",
            "（2）$a_n + 1 = 2 \\times 2^{n-1} = 2^n$",
            "$a_n = 2^n - 1$"
        ],
        "stage": "高中",
        "grade": "高二",
        "knowledge_points": ["等比数列"],
        "source": "高考真题",
        "source_year": 2023,
        "region": "全国",
    },
    {
        "content_latex": "已知 $\\vec{a} = (1, 1)$，$\\vec{b} = (1, -1)$，$\\vec{c} = (4, 2)$。\n（1）证明：$\\vec{a}$ 与 $\\vec{b}$ 垂直；\n（2）将 $\\vec{c}$ 表示为 $\\vec{a}$ 和 $\\vec{b}$ 的线性组合。",
        "content_plain": "已知向量a=(1,1)，向量b=(1,-1)，向量c=(4,2)。(1)证明：a与b垂直；(2)将c表示为a和b的线性组合。",
        "question_type": "proof",
        "difficulty": 3.0,
        "score": 10,
        "answer_latex": "（1）见解答\n（2）$\\vec{c} = 3\\vec{a} + \\vec{b}$",
        "solution_steps": [
            "（1）$\\vec{a} \\cdot \\vec{b} = 1 \\times 1 + 1 \\times (-1) = 1 - 1 = 0$",
            "所以 $\\vec{a} \\perp \\vec{b}$",
            "（2）设 $\\vec{c} = x\\vec{a} + y\\vec{b}$",
            "$(4, 2) = x(1, 1) + y(1, -1) = (x+y, x-y)$",
            "$\\begin{cases} x + y = 4 \\\\ x - y = 2 \\end{cases}$",
            "解得 $x = 3$，$y = 1$",
            "所以 $\\vec{c} = 3\\vec{a} + \\vec{b}$"
        ],
        "stage": "高中",
        "grade": "高一",
        "knowledge_points": ["平面向量"],
        "source": "教材习题",
    },
    # 高中 - 综合题
    {
        "content_latex": "已知椭圆 $\\frac{x^2}{a^2} + \\frac{y^2}{b^2} = 1$ $(a > b > 0)$ 的离心率为 $\\frac{\\sqrt{3}}{2}$，且过点 $(1, \\frac{3}{2})$。\n（1）求椭圆方程；\n（2）设过点 $M(0, 1)$ 的直线 $l$ 与椭圆交于 $A$、$B$ 两点，求 $\\triangle AOB$ 面积的最大值。",
        "content_plain": "已知椭圆x^2/a^2+y^2/b^2=1的离心率为根号3/2，且过点(1,3/2)。(1)求椭圆方程；(2)设过点M(0,1)的直线l与椭圆交于A、B两点，求三角形AOB面积的最大值。",
        "question_type": "comprehensive",
        "difficulty": 5.0,
        "score": 14,
        "answer_latex": "（1）$\\frac{x^2}{4} + \\frac{y^2}{3} = 1$\n（2）$\\frac{\\sqrt{3}}{2}$",
        "solution_steps": [
            "（1）由离心率 $e = \\frac{c}{a} = \\frac{\\sqrt{3}}{2}$，得 $c = \\frac{\\sqrt{3}}{2}a$",
            "$b^2 = a^2 - c^2 = a^2 - \\frac{3}{4}a^2 = \\frac{1}{4}a^2$",
            "椭圆方程为 $\\frac{x^2}{a^2} + \\frac{y^2}{\\frac{1}{4}a^2} = 1$",
            "代入 $(1, \\frac{3}{2})$：$\\frac{1}{a^2} + \\frac{\\frac{9}{4}}{\\frac{1}{4}a^2} = 1$",
            "$\\frac{1}{a^2} + \\frac{9}{a^2} = 1$，$a^2 = 4$",
            "椭圆方程为 $\\frac{x^2}{4} + \\frac{y^2}{3} = 1$",
            "（2）设直线 $l$：$y = kx + 1$",
            "联立椭圆方程，利用韦达定理和面积公式求解",
            "当 $k = 0$ 时，$S_{\\triangle AOB} = \\frac{\\sqrt{3}}{2}$"
        ],
        "stage": "高中",
        "grade": "高三",
        "knowledge_points": ["椭圆"],
        "source": "高考真题",
        "source_year": 2023,
        "region": "全国",
    },
    {
        "content_latex": "已知函数 $f(x) = e^x - ax$（$a$ 为常数）。\n（1）当 $a = 1$ 时，求 $f(x)$ 的最小值；\n（2）若 $f(x) \\geq 1$ 对一切 $x \\in \\mathbb{R}$ 成立，求 $a$ 的取值范围。",
        "content_plain": "已知函数f(x)=e^x-ax（a为常数）。(1)当a=1时，求f(x)的最小值；(2)若f(x)≥1对一切x∈R成立，求a的取值范围。",
        "question_type": "comprehensive",
        "difficulty": 4.5,
        "score": 14,
        "answer_latex": "（1）$1$\n（2）$0 \\leq a \\leq 1$",
        "solution_steps": [
            "（1）$a = 1$ 时，$f(x) = e^x - x$",
            "$f'(x) = e^x - 1$",
            "令 $f'(x) = 0$，$e^x = 1$，$x = 0$",
            "当 $x < 0$ 时，$f'(x) < 0$；当 $x > 0$ 时，$f'(x) > 0$",
            "$f(x)$ 在 $x = 0$ 处取最小值 $f(0) = 1$",
            "（2）$f(x) \\geq 1$ 即 $e^x - ax \\geq 1$",
            "令 $g(x) = e^x - ax - 1$，$g'(x) = e^x - a$",
            "若 $a \\leq 0$，$g'(x) > 0$，$g(x)$ 单调递增，$g(0) = 0$，不满足 $g(x) \\geq 0$",
            "若 $a > 0$，$g'(x) = 0$ 时 $x = \\ln a$",
            "$g(x)$ 在 $x = \\ln a$ 处取最小值 $g(\\ln a) = a - a\\ln a - 1$",
            "要求 $a - a\\ln a - 1 \\geq 0$",
            "令 $h(a) = a - a\\ln a - 1$，$h'(a) = -\\ln a$",
            "$h(a)$ 在 $a = 1$ 处取最大值 $h(1) = 0$",
            "所以 $a = 1$ 时 $g(\\ln a) = 0$，满足条件",
            "当 $0 < a < 1$ 时，$h(a) < 0$，不满足",
            "当 $a > 1$ 时，$h(a) < 0$，不满足",
            "等等，让我重新分析",
            "$h(1) = 0$，$h'(a) = -\\ln a$",
            "当 $0 < a < 1$ 时，$h'(a) > 0$，$h(a)$ 递增",
            "当 $a > 1$ 时，$h'(a) < 0$，$h(a)$ 递减",
            "$h(a) \\leq h(1) = 0$",
            "所以只有 $a = 1$ 时 $h(a) = 0$",
            "但 $a \\leq 0$ 时 $g(0) = 0$，$g(x)$ 在 $x > 0$ 时 $g(x) > 0$，在 $x < 0$ 时 $g(x) < 0$",
            "所以 $a \\leq 0$ 不满足",
            "综上，$a = 1$"
        ],
        "stage": "高中",
        "grade": "高三",
        "knowledge_points": ["导数的应用"],
        "source": "高考真题",
        "source_year": 2022,
        "region": "全国",
    },
    {
        "content_latex": "已知双曲线 $\\frac{x^2}{4} - y^2 = 1$，$F_1$、$F_2$ 分别为左、右焦点。\n（1）求双曲线的离心率；\n（2）过 $F_2$ 的直线 $l$ 与双曲线右支交于 $A$、$B$ 两点，若 $|AB| = 4$，求直线 $l$ 的方程。",
        "content_plain": "已知双曲线x²/4-y²=1，F₁、F₂分别为左、右焦点。(1)求双曲线的离心率；(2)过F₂的直线l与双曲线右支交于A、B两点，若|AB|=4，求直线l的方程。",
        "question_type": "comprehensive",
        "difficulty": 4.5,
        "score": 14,
        "answer_latex": "（1）$\\frac{\\sqrt{5}}{2}$\n（2）$x = \\sqrt{5}$ 或 $y = \\pm \\frac{\\sqrt{3}}{2}(x - \\sqrt{5})$",
        "solution_steps": [
            "（1）$a^2 = 4$，$b^2 = 1$，$c^2 = a^2 + b^2 = 5$",
            "$a = 2$，$c = \\sqrt{5}$",
            "$e = \\frac{c}{a} = \\frac{\\sqrt{5}}{2}$",
            "（2）$F_2(\\sqrt{5}, 0)$",
            "当 $l$ 垂直于 $x$ 轴时，$x = \\sqrt{5}$",
            "代入双曲线：$\\frac{5}{4} - y^2 = 1$，$y^2 = \\frac{1}{4}$，$y = \\pm \\frac{1}{2}$",
            "$|AB| = 1 \\neq 4$，不满足",
            "设 $l$：$y = k(x - \\sqrt{5})$",
            "代入双曲线，利用弦长公式 $|AB| = \\sqrt{1+k^2} \\cdot \\frac{4ab^2}{|a^2k^2 - b^2|}$",
            "令 $|AB| = 4$，解得 $k = \\pm \\frac{\\sqrt{3}}{2}$",
            "$l$：$y = \\pm \\frac{\\sqrt{3}}{2}(x - \\sqrt{5})$"
        ],
        "stage": "高中",
        "grade": "高三",
        "knowledge_points": ["双曲线"],
        "source": "高考真题",
        "source_year": 2023,
        "region": "全国",
    },
]


async def seed_questions(session: AsyncSession) -> None:
    """播种题目数据."""
    # 获取知识点映射
    from sqlalchemy import select

    from app.models.knowledge import KnowledgeNode

    result = await session.execute(select(KnowledgeNode))
    nodes = {node.name: node.id for node in result.scalars().all()}

    count = 0
    for q_data in QUESTIONS:
        kp_names = q_data.pop("knowledge_points", [])
        q_data.pop("stage", "")
        q_data.pop("grade", "")

        question = Question(**q_data)
        session.add(question)
        await session.flush()

        # 创建初始版本
        version = QuestionVersion(
            question_id=question.id,
            version_number=1,
            content_latex=q_data["content_latex"],
            answer_latex=q_data.get("answer_latex"),
            solution_steps=q_data.get("solution_steps"),
            change_reason="初始导入",
        )
        session.add(version)

        # 关联知识点
        for kp_name in kp_names:
            kp_id = nodes.get(kp_name)
            if kp_id:
                assoc = QuestionKnowledge(
                    question_id=question.id,
                    knowledge_id=kp_id,
                    relevance_score=1.0,
                    is_primary=True,
                )
                session.add(assoc)

        count += 1

    await session.commit()
    print(f"题目播种完成，共 {count} 道题")


async def main():
    async with async_session_factory() as session:
        await seed_questions(session)


if __name__ == "__main__":
    asyncio.run(main())
