from typing import Any, Callable
from langchain.agents.middleware import wrap_tool_call, before_model, dynamic_prompt
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from utils.log import logger
from utils.prompt import load_report_prompts, load_rag_prompts, load_system_prompts

@wrap_tool_call
def monitor_tool(
    request: ToolCallRequest,
    handler: Callable[[ToolCallRequest], ToolMessage | Command],
) -> ToolMessage | Command:
    logger.info(f"[tool_monitor] 执行工具：{request.tool_call['name']}")
    logger.info(f"[tool_monitor] 输入参数：{request.tool_call['args']}")

    try:
        result = handler(request)
        logger.info(f"[tool_monitor] 工具{request.tool_call['name']}调用成功")
        return result
    except Exception as e:
        logger.error(f"[tool_monitor] 工具{request.tool_call['name']}调用失败: {e}")
        raise e
    
@before_model
def log_before_model(
    state: dict[str, Any],
    runtime: Any,
):
    messages = state.get("messages", []) if isinstance(state, dict) else []
    tool_calls = state.get("tool_calls", []) if isinstance(state, dict) else []
    logger.info(f"[log_before_model] 即将调用模型，带有{len(messages)}条消息和{len(tool_calls)}次工具调用")

    last_content = "无消息"
    if messages:
        content = getattr(messages[-1], "content", "")
        last_content = str(content).strip() if content else "无消息"

    logger.debug(f"[log_before_model] 消息内容：{last_content}")

    return None

@dynamic_prompt
def report_prompt_switch(request: Any):
    runtime = getattr(request, "runtime", None)
    context = getattr(runtime, "context", {}) if runtime else {}
    task_type = context.get("task_type", "general")

    if task_type == "report":
        return load_report_prompts()

    if task_type == "rag_summary":
        return load_rag_prompts()

    return load_system_prompts()