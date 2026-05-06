from typing import Any, Callable

from langchain.agents.middleware import before_model, wrap_tool_call
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.types import Command

from utils.log import logger


@wrap_tool_call
def monitor_plan_tool(
	request: ToolCallRequest,
	handler: Callable[[ToolCallRequest], ToolMessage | Command],
) -> ToolMessage | Command:
	logger.info(f"[plan_tool] 执行工具：{request.tool_call['name']}")
	logger.debug(f"[plan_tool] 输入参数：{request.tool_call['args']}")
	try:
		result = handler(request)
		logger.info(f"[plan_tool] 工具{request.tool_call['name']}调用成功")
		return result
	except Exception as e:
		logger.error(f"[plan_tool] 工具{request.tool_call['name']}调用失败: {e}")
		raise


@before_model
def log_before_plan_model(state: dict[str, Any], runtime: Any):
	messages = state.get("messages", []) if isinstance(state, dict) else []
	tool_calls = state.get("tool_calls", []) if isinstance(state, dict) else []
	logger.info(f"[plan_before_model] 即将调用模型，消息数={len(messages)}，工具调用数={len(tool_calls)}")
	return None
