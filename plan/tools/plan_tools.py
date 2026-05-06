from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool

from model.factory import get_chat_model


def _run_text_chain(template: str, input_data: dict) -> str:
	chain = PromptTemplate.from_template(template) | get_chat_model() | StrOutputParser()
	return chain.invoke(input_data)


@tool(description="当用户信息不足时，生成澄清问题以补齐学习计划必要参数")
def clarify_plan_requirements(
	query: str,
	target: str = "",
	available_time_per_day: str = "",
	horizon_days: int = 0,
	grade: str = "",
	subject: str = "",
) -> str:
	missing = []
	if not target.strip():
		missing.append("学习目标")
	if not available_time_per_day.strip():
		missing.append("每日可用时长")
	if horizon_days <= 0:
		missing.append("计划周期天数")
	if not grade.strip():
		missing.append("年级")
	if not subject.strip():
		missing.append("学科")

	if not missing:
		return "信息已足够，可直接生成学习计划。"

	template = """
你是学习规划助手。请根据用户问题生成一段简洁、礼貌、结构化的澄清提问。

用户问题：{query}
缺失信息：{missing}

要求：
1) 先肯定用户需求。
2) 用1-3个问题补齐关键信息。
3) 使用中文，语气自然。
"""
	return _run_text_chain(template, {"query": query, "missing": "、".join(missing)})


@tool(description="根据目标、时长、周期、年级和学科输出可执行学习计划")
def generate_study_plan(
	query: str,
	target: str,
	available_time_per_day: str = "30分钟",
	horizon_days: int = 7,
	grade: str = "初中",
	subject: str = "数学",
) -> str:
	template = """
你是一名学习规划助手，请为学生生成可执行学习计划。

用户问题：{query}
学习目标：{target}
每日可用时间：{available_time_per_day}
周期天数：{horizon_days}
年级：{grade}
学科：{subject}

输出要求：
1) 按天拆分任务（输入-练习-复盘）。
2) 每天给出达成标准。
3) 标注高风险薄弱点与补救策略。
"""
	return _run_text_chain(
		template,
		{
			"query": query,
			"target": target,
			"available_time_per_day": available_time_per_day,
			"horizon_days": horizon_days,
			"grade": grade,
			"subject": subject,
		},
	)


ALL_PLAN_TOOLS = [clarify_plan_requirements, generate_study_plan]
