from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

from model.factory import get_chat_model
from agent.tools.agent_tools import ALL_TOOLS
from agent.tools.middleware import monitor_tool, log_before_model, report_prompt_switch
from chat.react import EducationChat
from plan.react import EducationPlan
from rag.rag_service import reset_rag_scope, set_rag_scope
from utils.config import agent_conf, chat_conf, control_conf
from utils.dialogue import get_history
from utils.prompt import load_system_prompts


class EducationAgent:
    def __init__(self, tools=None):
        self.tools = tools or ALL_TOOLS
        self.system_prompt = load_system_prompts()
        self.max_iterations = agent_conf.get("max_iterations", 6) if isinstance(agent_conf, dict) else 6
        keyword_conf = (agent_conf or {}).get("mode_keywords", {}) if isinstance(agent_conf, dict) else {}
        routing_conf = (control_conf or {}).get("routing", {}) if isinstance(control_conf, dict) else {}
        module_conf = (control_conf or {}).get("modules", {}) if isinstance(control_conf, dict) else {}
        configured_default = routing_conf.get(
            "default_mode",
            (chat_conf or {}).get("default_mode", "agent") if isinstance(chat_conf, dict) else "agent",
        )
        self.default_mode = configured_default if configured_default in {"chat", "plan", "agent"} else "agent"
        self.allowed_modes = set(routing_conf.get("allow_modes", ["chat", "agent", "plan"]))
        self.module_enabled = {
            "chat": bool(module_conf.get("chat_enabled", True)),
            "agent": bool(module_conf.get("agent_enabled", True)),
            "plan": bool(module_conf.get("plan_enabled", True)),
        }
        fallback_plan_keywords = ("学习计划", "制定计划", "计划", "规划", "学习路径", "复习计划", "安排")
        fallback_chat_keywords = ("聊一聊", "聊聊", "对话", "随便聊", "闲聊", "陪我聊")
        self.plan_keywords = tuple(
            str(item).strip().lower()
            for item in keyword_conf.get("plan", fallback_plan_keywords)
            if str(item).strip()
        )
        self.chat_keywords = tuple(
            str(item).strip().lower()
            for item in keyword_conf.get("chat", fallback_chat_keywords)
            if str(item).strip()
        )
        self.chat_service = EducationChat()
        self.plan_service = EducationPlan(chat_service=self.chat_service)
        self.max_history_turns = 20
        self.agent = create_agent(
            model=get_chat_model(),
            tools=self.tools,
            system_prompt=self.system_prompt,
            middleware=[monitor_tool, log_before_model, report_prompt_switch],
        )

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

    def _resolve_mode(self, query: str, context: dict[str, Any] | None) -> str:
        ctx = context or {}
        raw = str(ctx.get("mode") or ctx.get("task_type") or "").strip().lower()
        if raw in {"chat", "plan", "agent"}:
            return raw
        if raw in {"general", "rag_summary", "report"}:
            return "agent"

        text = (query or "").strip().lower()

        if any(k in text for k in self.plan_keywords):
            return "plan"
        if any(k in text for k in self.chat_keywords):
            return "chat"
        return "agent"

    def invoke(
        self,
        query: str,
        context: dict[str, Any] | None = None,
        user_id: str = "anonymous",
        session_id: str = "default",
    ) -> str:
        mode = self._resolve_mode(query, context)
        if mode not in self.allowed_modes:
            mode = self.default_mode

        if not self.module_enabled.get(mode, True):
            mode = self.default_mode

        if mode == "chat":
            return self.chat_service.invoke(
                query=query,
                context=context,
                user_id=user_id,
                session_id=session_id,
            )

        if mode == "plan":
            return self.plan_service.invoke(
                query=query,
                context=context,
                user_id=user_id,
                session_id=session_id,
            )

        query_with_history, history_messages = self._build_query_with_history(
            query=query,
            user_id=user_id,
            session_id=session_id,
        )
        scope_tokens = set_rag_scope(user_id, session_id)

        payload = {
            "messages": [*history_messages, HumanMessage(content=query_with_history)],
            "context": context or {},
        }
        try:
            result = self.agent.invoke(payload)
        finally:
            reset_rag_scope(scope_tokens)

        if isinstance(result, dict) and result.get("messages"):
            last_message = result["messages"][-1]
            content = getattr(last_message, "content", "")
            answer = ""
            if isinstance(content, list):
                answer = "\n".join(str(item) for item in content)
            else:
                answer = str(content)
            return answer

        answer = str(result)
        return answer