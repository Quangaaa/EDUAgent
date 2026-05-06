from contextvars import ContextVar

from rag.vector_store import VectorStoreService
from utils.prompt import load_rag_prompts
from langchain_core.prompts import PromptTemplate
from model.factory import get_chat_model
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document

_RAG_USER_ID: ContextVar[str] = ContextVar("rag_user_id", default="anonymous")
_RAG_SESSION_ID: ContextVar[str] = ContextVar("rag_session_id", default="default")


def set_rag_scope(user_id: str | None, session_id: str | None):
    user = (user_id or "anonymous").strip() or "anonymous"
    session = (session_id or "default").strip() or "default"
    return _RAG_USER_ID.set(user), _RAG_SESSION_ID.set(session)


def reset_rag_scope(tokens) -> None:
    user_token, session_token = tokens
    _RAG_USER_ID.reset(user_token)
    _RAG_SESSION_ID.reset(session_token)

class RagSummarizeService(object):
    def __init__(self):
        self.vector_store_service = VectorStoreService()
        self.prompt_text = load_rag_prompts()
        self.prompt_template = PromptTemplate.from_template(self.prompt_text)
        self.model = get_chat_model()
        self.chain = self._init_chain()

    def _init_chain(self):
        chain = self.prompt_template | self.model | StrOutputParser()
        return chain

    def _resolve_scope(self, user_id: str | None, session_id: str | None) -> tuple[str, str]:
        user = (user_id or _RAG_USER_ID.get() or "anonymous").strip() or "anonymous"
        session = (session_id or _RAG_SESSION_ID.get() or "default").strip() or "default"
        return user, session
        
    def retriever_docs(self, query: str, user_id: str | None = None, session_id: str | None = None) -> list[Document]:
        user, session = self._resolve_scope(user_id, session_id)
        retriever = self.vector_store_service.get_retriever(user, session)
        return retriever.invoke(query)
        
    def rag_summarize(self, query: str, user_id: str | None = None, session_id: str | None = None) -> str:
        docs = self.retriever_docs(query, user_id, session_id)
        context = ""
        for doc in docs:
            context += f"[参考资料:{doc.page_content} | 参考资料元数据：{doc.metadata}]\n"
        input_data = {"query": query, "context": context}
        return self.chain.invoke(input_data)
        
if __name__ == "__main__":
    rag_summarize_service = RagSummarizeService()
    query = "请总结一下什么是RAG？"
    print(rag_summarize_service.rag_summarize(query))