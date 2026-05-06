from typing import Any

from langchain_core.messages import HumanMessage

from rag.rag_service import RagSummarizeService, reset_rag_scope, set_rag_scope
from utils.config import chat_conf
from utils.dialogue import get_history


class EducationChat:
    """行业问答聊天能力：默认走 RAG 检索增强链路。"""

    def __init__(self):
        self.rag_service = RagSummarizeService()
        history_conf = (chat_conf or {}).get("history", {}) if isinstance(chat_conf, dict) else {}
        self.max_history_turns = int(history_conf.get("max_history_turns", 20))

    def _build_query_with_history(self, query: str, user_id: str, session_id: str) -> str:
        history = get_history(user_id=user_id, session_id=session_id)
        history_messages = list(history.messages)
        if not history_messages or str(getattr(history_messages[-1], "content", "")) != str(query):
            history_messages.append(HumanMessage(content=query))

        recent = history_messages[-self.max_history_turns :]
        if len(recent) <= 1:
            return query

        history_lines = []
        for msg in recent[:-1]:
            role = "assistant" if msg.__class__.__name__.lower().startswith("ai") else "user"
            history_lines.append(f"{role}: {str(getattr(msg, 'content', ''))}")

        return f"对话历史:\n" + "\n".join(history_lines) + f"\n\n当前问题:\n{query}"

    def invoke(
        self,
        query: str,
        context: dict[str, Any] | None = None,
        user_id: str = "anonymous",
        session_id: str = "default",
    ) -> str:
        rag_query = self._build_query_with_history(query=query, user_id=user_id, session_id=session_id)
        scope_tokens = set_rag_scope(user_id, session_id)
        try:
            answer = self.rag_service.rag_summarize(rag_query, user_id=user_id, session_id=session_id)
        finally:
            reset_rag_scope(scope_tokens)
        return answer