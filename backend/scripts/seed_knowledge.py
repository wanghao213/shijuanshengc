"""知识点种子数据 - 覆盖小学、初中、高中数学知识体系."""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.knowledge import KnowledgeNode

# 知识点树结构
KNOWLEDGE_TREE = {
    "小学": {
        "一年级": {
            "数与代数": ["10以内数的认识", "10以内加减法", "20以内数的认识", "20以内加减法"],
            "图形与几何": ["认识图形（一）", "位置"],
            "统计与概率": ["分类"],
        },
        "二年级": {
            "数与代数": ["100以内数的认识", "100以内加减法", "表内乘法", "认识时间"],
            "图形与几何": ["长度单位", "角的初步认识"],
            "统计与概率": ["数据收集整理"],
        },
        "三年级": {
            "数与代数": ["万以内数的认识", "万以内加减法", "多位数乘一位数", "分数的初步认识", "年月日"],
            "图形与几何": ["测量（毫米、分米、千米）", "长方形和正方形", "周长"],
            "统计与概率": ["可能性"],
        },
        "四年级": {
            "数与代数": ["大数的认识", "三位数乘两位数", "除数是两位数的除法", "小数的意义和性质", "小数加减法"],
            "图形与几何": ["角的度量", "平行四边形和梯形"],
            "统计与概率": ["条形统计图"],
        },
        "五年级": {
            "数与代数": ["小数乘法", "小数除法", "简易方程", "因数和倍数", "分数的意义和性质", "分数加减法"],
            "图形与几何": ["多边形面积", "组合图形面积"],
            "统计与概率": ["可能性大小"],
        },
        "六年级": {
            "数与代数": ["分数乘法", "分数除法", "百分数", "比和比例", "负数"],
            "图形与几何": ["圆的认识", "圆的周长和面积", "圆柱和圆锥", "图形的运动"],
            "统计与概率": ["扇形统计图", "统计与概率综合"],
        },
    },
    "初中": {
        "初一": {
            "有理数": ["正数和负数", "有理数的概念", "有理数的加减法", "有理数的乘除法", "有理数的乘方"],
            "整式": ["整式", "整式的加减"],
            "一元一次方程": ["从算式到方程", "解一元一次方程", "实际问题与一元一次方程"],
            "图形认识初步": ["多姿多彩的图形", "直线、射线、线段", "角"],
            "相交线与平行线": ["相交线", "平行线及其判定", "平行线的性质", "平移"],
        },
        "初二": {
            "三角形": ["与三角形有关的线段", "与三角形有关的角", "多边形及其内角和", "全等三角形"],
            "全等三角形": ["全等三角形的性质", "三角形全等的判定", "角平分线的性质"],
            "轴对称": ["轴对称", "作轴对称图形", "等腰三角形"],
            "整式乘除与因式分解": ["整式的乘法", "乘法公式", "整式的除法", "因式分解"],
            "分式": ["分式", "分式的运算", "分式方程"],
            "二次根式": ["二次根式的概念", "二次根式的运算"],
        },
        "初三": {
            "一元二次方程": ["一元二次方程的概念", "解一元二次方程", "一元二次方程的应用"],
            "二次函数": ["二次函数的概念", "二次函数的图象和性质", "二次函数的应用"],
            "旋转": ["旋转的概念", "旋转的性质"],
            "圆": ["圆的有关性质", "点和圆的位置关系", "直线和圆的位置关系", "圆和圆的位置关系", "正多边形和圆", "弧长和扇形面积"],
            "相似": ["图形的相似", "相似三角形", "位似"],
            "锐角三角函数": ["锐角三角函数", "解直角三角形"],
            "概率初步": ["随机事件与概率", "用列举法求概率", "用频率估计概率"],
        },
    },
    "高中": {
        "高一": {
            "集合与常用逻辑用语": ["集合的概念与运算", "充分条件与必要条件", "全称量词与存在量词"],
            "一元二次函数与不等式": ["二次函数", "一元二次不等式", "基本不等式"],
            "函数的概念与性质": ["函数的概念", "函数的单调性与最值", "函数的奇偶性", "指数函数", "对数函数", "幂函数"],
            "三角函数": ["任意角和弧度制", "三角函数的概念", "三角函数的图象与性质", "三角恒等变换", "三角函数的应用"],
            "平面向量": ["向量的概念", "向量的运算", "向量的坐标表示", "向量的应用"],
        },
        "高二": {
            "数列": ["数列的概念", "等差数列", "等比数列", "数列求和"],
            "立体几何": ["空间几何体", "点线面的位置关系", "直线与平面平行", "直线与平面垂直", "平面与平面平行", "平面与平面垂直", "空间向量与立体几何"],
            "解析几何": ["直线与方程", "圆与方程", "椭圆", "双曲线", "抛物线"],
            "导数": ["导数的概念", "导数的运算", "导数的应用"],
            "计数原理": ["分类加法与分步乘法", "排列与组合", "二项式定理"],
            "概率与统计": ["随机变量及其分布", "统计案例", "回归分析"],
        },
        "高三": {
            "常用逻辑用语": ["命题与逻辑", "充要条件"],
            "圆锥曲线综合": ["椭圆综合", "双曲线综合", "抛物线综合", "圆锥曲线综合应用"],
            "导数综合": ["导数与函数零点", "导数与不等式", "导数与数列"],
            "概率与统计综合": ["概率综合", "统计综合"],
            "数学思想方法": ["函数与方程思想", "数形结合思想", "分类讨论思想", "转化与化归思想"],
        },
    },
}


async def seed_knowledge(session: AsyncSession) -> None:
    """播种知识点数据."""
    count = 0

    for stage, grades in KNOWLEDGE_TREE.items():
        # 创建学段节点
        stage_node = KnowledgeNode(
            name=stage,
            level="stage",
            stage=stage,
            materialized_path="",
            sort_order=count,
        )
        session.add(stage_node)
        await session.flush()
        stage_node.materialized_path = str(stage_node.id)
        count += 1

        for grade, chapters in grades.items():
            # 创建年级节点
            grade_node = KnowledgeNode(
                name=grade,
                level="grade",
                stage=stage,
                grade=grade,
                parent_id=stage_node.id,
                materialized_path="",
                sort_order=count,
            )
            session.add(grade_node)
            await session.flush()
            grade_node.materialized_path = f"{stage_node.id}/{grade_node.id}"
            count += 1

            for chapter, sections in chapters.items():
                # 创建章节点
                chapter_node = KnowledgeNode(
                    name=chapter,
                    level="chapter",
                    stage=stage,
                    grade=grade,
                    parent_id=grade_node.id,
                    materialized_path="",
                    sort_order=count,
                )
                session.add(chapter_node)
                await session.flush()
                chapter_node.materialized_path = (
                    f"{stage_node.id}/{grade_node.id}/{chapter_node.id}"
                )
                count += 1

                for i, section in enumerate(sections):
                    # 创建知识点节点
                    kp_node = KnowledgeNode(
                        name=section,
                        level="knowledge_point",
                        stage=stage,
                        grade=grade,
                        parent_id=chapter_node.id,
                        materialized_path="",
                        sort_order=i,
                    )
                    session.add(kp_node)
                    await session.flush()
                    kp_node.materialized_path = (
                        f"{stage_node.id}/{grade_node.id}/{chapter_node.id}/{kp_node.id}"
                    )
                    count += 1

    await session.commit()
    print(f"知识点播种完成，共 {count} 个节点")


async def main():
    async with async_session_factory() as session:
        await seed_knowledge(session)


if __name__ == "__main__":
    asyncio.run(main())
