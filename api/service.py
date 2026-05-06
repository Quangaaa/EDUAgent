from agent.react import EducationAgent
from chat.react import EducationChat
from model.factory import get_model_init_status
from plan.react import EducationPlan
from rag.vector_store import VectorStoreService
from typing import Optional

_kb_service: Optional[VectorStoreService] = None # konwledgebase 参考文献数据库处理（内部添加知识库用）
_kb_init_error: Optional[str] = None # 初始化知识库错误信息，如果初始化失败则无法使用相关功能，需通过接口反馈给用户
_chat_service: Optional[EducationChat] = None
_chat_init_error: Optional[str] = None # 初始化对话服务错误信息，如果初始化失败则无法使用相关功能，需通过接口反馈给用户
_agent_service: Optional[EducationAgent] = None
_agent_init_error: Optional[str] = None # 初始化 agent 服务错误信息，如果初始化失败则无法使用相关功能，需通过接口反馈给用户
_plan_service: Optional[EducationPlan] = None
_plan_init_error: Optional[str] = None # 初始化规划服务错误信息，如果初始化失败则无法使用相关功能，需通过接口反馈给用户


def get_kb_service() -> VectorStoreService:
    global _kb_service, _kb_init_error
    if _kb_service is None and _kb_init_error is None:
        try:
            _kb_service = VectorStoreService()
        except Exception as e:
            _kb_init_error = str(e)
    if _kb_service is None and _kb_init_error is not None:
        raise RuntimeError(f"知识库服务初始化失败: {_kb_init_error}")
    return _kb_service

def get_chat_service() -> EducationChat:
    global _chat_service, _chat_init_error
    if _chat_service is None and _chat_init_error is None:
        try:
            _chat_service = EducationChat()
        except Exception as e:
            _chat_init_error = str(e)
    if _chat_service is None and _chat_init_error is not None:
        raise RuntimeError(f"对话服务初始化失败: {_chat_init_error}")
    return _chat_service

def get_agent_service() -> EducationAgent:
    global _agent_service, _agent_init_error
    if _agent_service is None and _agent_init_error is None:
        try:
            _agent_service = EducationAgent()
        except Exception as e:
            _agent_init_error = str(e)
    if _agent_service is None and _agent_init_error is not None:
        raise RuntimeError(f"Agent服务初始化失败: {_agent_init_error}")
    return _agent_service

def get_plan_service() -> EducationPlan:
    global _plan_service, _plan_init_error
    if _plan_service is None and _plan_init_error is None:
        try:
            _plan_service = EducationPlan()
        except Exception as e:
            _plan_init_error = str(e)
    if _plan_service is None and _plan_init_error is not None:
        raise RuntimeError(f"规划服务初始化失败: {_plan_init_error}")
    return _plan_service

def get_init_status() -> dict:
    status = {
        "kb_ready": _kb_service is not None,
        "kb_error": _kb_init_error,
        "chat_ready": _chat_service is not None,
        "chat_error": _chat_init_error,
        "agent_ready": _agent_service is not None,
        "agent_error": _agent_init_error,
        "plan_ready": _plan_service is not None,
        "plan_error": _plan_init_error,
    }
    status.update(get_model_init_status())
    return status