from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

from chat.react import EducationChat
from model.factory import get_chat_model
from utils.config import agent_conf, plan_conf
from utils.dialogue import get_history
from plan.tools.middleware import log_before_plan_model, monitor_plan_tool
from plan.tools.plan_tools import ALL_PLAN_TOOLS, generate_study_plan


class EducationPlan:
	"""学习规划能力：由计划工具集驱动，并保留必要的澄清交互。"""

	def __init__(self, chat_service: EducationChat | None = None):
		self.chat_service = chat_service or EducationChat()
		planning_conf = plan_conf if isinstance(plan_conf, dict) and plan_conf else {}
		if not planning_conf and isinstance(agent_conf, dict):
			planning_conf = (agent_conf or {}).get("planning", {})

		self.default_horizon_days = planning_conf.get("default_horizon_days", 7)
		self.default_daily_minutes = planning_conf.get("default_daily_minutes", 30)
		self.default_grade = planning_conf.get("default_grade", "初中")
		self.default_subject = planning_conf.get("default_subject", "数学")
		self.clarify_enabled = bool((planning_conf.get("clarification") or {}).get("enabled", True))
		self.ask_when_target_missing = bool(
			(planning_conf.get("clarification") or {}).get("ask_when_target_missing", True)
		)
		self.max_history_turns = 20

		self.plan_agent = create_agent(
			model=get_chat_model(),
			tools=ALL_PLAN_TOOLS,
			system_prompt=(
				"你是学习规划助手。优先调用工具完成澄清与计划生成，"
				"输出要可执行、结构化、简洁。"
			),
			middleware=[monitor_plan_tool, log_before_plan_model],
		)

	def _extract_answer(self, result: Any) -> str:
		if isinstance(result, dict) and result.get("messages"):
			last_message = result["messages"][-1]
			content = getattr(last_message, "content", "")
			if isinstance(content, list):
				return "\n".join(str(item) for item in content)
			return str(content)
		return str(result)

	def _build_query_with_history(self, query: str, user_id: str, session_id: str) -> tuple[str, list]:
		history = get_history(user_id=user_id, session_id=session_id)
		history_messages = list(history.messages)
		if not history_messages or str(getattr(history_messages[-1], "content", "")) != str(query):
			history_messages.append(HumanMessage(content=query))

		recent = history_messages[-self.max_history_turns :]
		if len(recent) <= 1:
			return query, recent[:-1]

		history_lines = []
		for msg in recent[:-1]:
			role = "assistant" if msg.__class__.__name__.lower().startswith("ai") else "user"
			history_lines.append(f"{role}: {str(getattr(msg, 'content', ''))}")

		return f"对话历史:\n" + "\n".join(history_lines) + f"\n\n当前问题:\n{query}", recent[:-1]

	def invoke(
		self,
		query: str,
		context: dict[str, Any] | None = None,
		user_id: str = "anonymous",
		session_id: str = "default",
	) -> str:
		ctx = context or {}
		target = (ctx.get("target") or "").strip()

		if self.clarify_enabled and self.ask_when_target_missing and not target:
			return self.chat_service.invoke(
				"为了给你制定学习计划，请先告诉我学习目标、可用时长和目标学科。",
				context=ctx,
				user_id=user_id,
				session_id=session_id,
			)

		query_with_history, history_messages = self._build_query_with_history(
			query=query,
			user_id=user_id,
			session_id=session_id,
		)
		payload = {
			"messages": [*history_messages, HumanMessage(content=query_with_history)],
			"context": {
				**ctx,
				"target": target or query,
				"available_time_per_day": ctx.get("available_time_per_day", f"{self.default_daily_minutes}分钟"),
				"horizon_days": ctx.get("horizon_days", self.default_horizon_days),
				"grade": ctx.get("grade", self.default_grade),
				"subject": ctx.get("subject", self.default_subject),
			},
		}

		# 若外部未给目标，至少通过工具直接生成一次计划，避免空回复。
		if not target:
			answer = generate_study_plan.invoke(
				{
					"query": query,
					"target": query,
					"available_time_per_day": payload["context"]["available_time_per_day"],
					"horizon_days": payload["context"]["horizon_days"],
					"grade": payload["context"]["grade"],
					"subject": payload["context"]["subject"],
				}
			)
		else:
			result = self.plan_agent.invoke(payload)
			answer = self._extract_answer(result)
		return answer
