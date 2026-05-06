from typing import Sequence

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.runnables.history import BaseChatMessageHistory

from api.db import get_db_connection, now_str


def _normalize_scope(user_id: str | None, session_id: str | None) -> tuple[str, str]:
    user = (user_id or "anonymous").strip() or "anonymous"
    session = (session_id or "default").strip() or "default"
    return user, session


class DialogueRepository:
    def session_exists_for_user(self, user_id: str, session_id: str) -> bool:
        user, session = _normalize_scope(user_id, session_id)
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT id FROM chat_sessions WHERE id = ? AND user_id = ?",
                (session, user),
            ).fetchone()
        return row is not None

    def list_session_messages(self, session_id: str) -> list[dict]:
        with get_db_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, role, content, created_at
                FROM chat_messages
                WHERE session_id = ?
                ORDER BY id ASC
                """,
                (session_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_session_attachments(self, session_id: str) -> list[dict]:
        with get_db_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, message_id, filename, file_path, file_size, content_preview, created_at
                FROM chat_attachments
                WHERE message_id IN (
                    SELECT id FROM chat_messages WHERE session_id = ?
                )
                """,
                (session_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def append_message(
        self,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
        created_at: str | None = None,
    ) -> int | None:
        user, session = _normalize_scope(user_id, session_id)
        now = created_at or now_str()

        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT id FROM chat_sessions WHERE id = ? AND user_id = ?",
                (session, user),
            ).fetchone()
            if row is None:
                return None

            cursor = conn.execute(
                "INSERT INTO chat_messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (session, role, content, now),
            )
            conn.execute(
                "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
                (now, session),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def delete_history(self, user_id: str, session_id: str) -> bool:
        user, session = _normalize_scope(user_id, session_id)
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT id FROM chat_sessions WHERE id = ? AND user_id = ?",
                (session, user),
            ).fetchone()
            if row is None:
                return False
            conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session,))
            conn.commit()
        return True


dialogue_repo = DialogueRepository()


def get_history(user_id: str = "anonymous", session_id: str = "default"):
    user, session = _normalize_scope(user_id, session_id)
    return DialogueHistoryStore(user_id=user, session_id=session, repository=dialogue_repo)


class DialogueHistoryStore(BaseChatMessageHistory):
    def __init__(self, user_id: str, session_id: str, repository: DialogueRepository):
        self.user_id = user_id
        self.session_id = session_id
        self.repository = repository

    def _resolve_valid_session(self) -> bool:
        return self.repository.session_exists_for_user(self.user_id, self.session_id)

    @staticmethod
    def _role_for_message(message: BaseMessage) -> str:
        if isinstance(message, HumanMessage):
            return "user"
        if isinstance(message, AIMessage):
            return "assistant"
        return "user"

    def add_message(self, message: BaseMessage) -> None:
        self.add_messages([message])

    def add_messages(self, messages: Sequence[BaseMessage]) -> None:
        if not messages or not self._resolve_valid_session():
            return

        now = now_str()
        for msg in messages:
            self.repository.append_message(
                user_id=self.user_id,
                session_id=self.session_id,
                role=self._role_for_message(msg),
                content=str(msg.content),
                created_at=now,
            )

    @property
    def messages(self) -> list[BaseMessage]:
        if not self._resolve_valid_session():
            return []

        rows = self.repository.list_session_messages(self.session_id)

        result: list[BaseMessage] = []
        for row in rows:
            role = row["role"]
            content = row["content"]
            if role == "assistant":
                result.append(AIMessage(content=content))
            else:
                result.append(HumanMessage(content=content))
        return result

    def clear(self) -> None:
        self.repository.delete_history(self.user_id, self.session_id)