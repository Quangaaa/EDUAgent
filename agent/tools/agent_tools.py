from langchain_core.tools import tool
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from model.factory import get_chat_model
from rag.rag_service import RagSummarizeService

rag = RagSummarizeService()


def _run_text_chain(template: str, input_data: dict) -> str:
    chain = PromptTemplate.from_template(template) | get_chat_model() | StrOutputParser()
    return chain.invoke(input_data)


@tool(description="从知识库检索并归纳与问题相关的学习证据")
def retrieve_learning_evidence(query: str) -> str:
    return rag.rag_summarize(query)


@tool(description="按年级和学科生成分层讲解，适用于课前预习和课后复盘")
def explain_concept(query: str, grade: str = "初中", subject: str = "数学") -> str:
    evidence = rag.rag_summarize(query)
    template = """
你是一名教育大模型讲解助手。
请基于输入证据，为{grade}{subject}学生生成结构化讲解。

要求：
1) 先给一句话定义，再给核心原理。
2) 给出一个贴近学生场景的例子。
3) 给出一个常见误区和纠正方式。
4) 最后给1个用于自测的简答题。

问题：{query}
证据：{evidence}
"""
    return _run_text_chain(template, {"grade": grade, "subject": subject, "query": query, "evidence": evidence})


@tool(description="基于题目与学生答案进行错因归类，并给出针对性改进建议")
def diagnose_mistake(question: str, student_answer: str, reference_answer: str = "", subject: str = "数学") -> str:
    template = """
你是一名教育评测助手，请输出错因诊断报告。

学科：{subject}
题目：{question}
学生答案：{student_answer}
参考答案：{reference_answer}

输出格式：
1) 错因类型（概念不清/审题偏差/计算失误/步骤缺失/表达不规范）
2) 关键证据
3) 改进建议（3条）
4) 一道同类型巩固题
"""
    return _run_text_chain(
        template,
        {
            "subject": subject,
            "question": question,
            "student_answer": student_answer,
            "reference_answer": reference_answer,
        },
    )


@tool(description="按知识点、难度和题量生成分层练习题")
def generate_practice(knowledge_point: str, level: str = "中等", count: int = 3, subject: str = "数学") -> str:
    template = """
你是一名出题助手，请围绕给定知识点出题。

学科：{subject}
知识点：{knowledge_point}
难度：{level}
题量：{count}

要求：
1) 题型多样化。
2) 每题提供答案与简要解析。
3) 标注每题考查点。
"""
    return _run_text_chain(
        template,
        {
            "subject": subject,
            "knowledge_point": knowledge_point,
            "level": level,
            "count": count,
        },
    )


@tool(description="根据学习目标与时间预算生成阶段性学习计划")
def plan_learning_path(
    target: str,
    available_time_per_day: str = "30分钟",
    horizon_days: int = 7,
    grade: str = "初中",
    subject: str = "数学",
) -> str:
    template = """
你是一名学习规划助手，请为学生生成可执行计划。

年级：{grade}
学科：{subject}
学习目标：{target}
每日可用时间：{available_time_per_day}
周期天数：{horizon_days}

输出要求：
1) 按天拆解任务（输入-练习-复盘）。
2) 给出每天的达成标准。
3) 标出高风险薄弱点和补救策略。
"""
    return _run_text_chain(
        template,
        {
            "grade": grade,
            "subject": subject,
            "target": target,
            "available_time_per_day": available_time_per_day,
            "horizon_days": horizon_days,
        },
    )


ALL_TOOLS = [
    retrieve_learning_evidence,
    explain_concept,
    diagnose_mistake,
    generate_practice,
    plan_learning_path,
]