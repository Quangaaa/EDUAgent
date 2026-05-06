from abc import ABC, abstractmethod
from typing import Optional

from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.chat_models import ChatTongyi
from langchain_community.chat_models.tongyi import BaseChatModel
from langchain_core.embeddings import Embeddings

from utils.config import rag_conf

class BaseModelFactory(ABC):
    @abstractmethod
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        pass


def _required_rag_value(key: str) -> str:
    value = str(rag_conf.get(key, "")).strip()
    if not value:
        raise ValueError(f"Missing `{key}` in config/rag.yaml")
    return value


class ChatModelFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        return ChatTongyi(
            model=_required_rag_value("chat_model_name"),
            dashscope_api_key=_required_rag_value("dashscope_api_key"),
        )


class EmbeddingsFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        return DashScopeEmbeddings(
            model=_required_rag_value("embedding_model_name"),
            dashscope_api_key=_required_rag_value("dashscope_api_key"),
        )


_chat_model: BaseChatModel | None = None
_embedding_model: Embeddings | None = None
_chat_model_error: str | None = None
_embedding_model_error: str | None = None


def get_chat_model() -> BaseChatModel:
    global _chat_model, _chat_model_error
    if _chat_model is None and _chat_model_error is None:
        try:
            _chat_model = ChatModelFactory().generator()
        except Exception as e:
            _chat_model_error = str(e)

    if _chat_model is None:
        raise RuntimeError(f"chat model init failed: {_chat_model_error}")
    return _chat_model


def get_embedding_model() -> Embeddings:
    global _embedding_model, _embedding_model_error
    if _embedding_model is None and _embedding_model_error is None:
        try:
            _embedding_model = EmbeddingsFactory().generator()
        except Exception as e:
            _embedding_model_error = str(e)

    if _embedding_model is None:
        raise RuntimeError(f"embedding model init failed: {_embedding_model_error}")
    return _embedding_model


def warmup_models(raise_on_error: bool = False) -> dict:
    result = {
        "chat_model_ready": False,
        "chat_model_error": None,
        "embedding_model_ready": False,
        "embedding_model_error": None,
    }

    try:
        get_chat_model()
        result["chat_model_ready"] = True
    except Exception as e:
        result["chat_model_error"] = str(e)
        if raise_on_error:
            raise

    try:
        get_embedding_model()
        result["embedding_model_ready"] = True
    except Exception as e:
        result["embedding_model_error"] = str(e)
        if raise_on_error:
            raise

    return result


def get_model_init_status() -> dict:
    return {
        "chat_model_ready": _chat_model is not None,
        "chat_model_error": _chat_model_error,
        "embedding_model_ready": _embedding_model is not None,
        "embedding_model_error": _embedding_model_error,
    }
