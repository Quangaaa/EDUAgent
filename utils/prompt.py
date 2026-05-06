try:
    from utils.config import prompts_conf
    from utils.path import get_abs_path
    from utils.log import logger
except ModuleNotFoundError:
    # 兼容直接运行
    from config import prompts_conf
    from path import get_abs_path
    from log import logger

def load_system_prompts():
    try:
        system_prompt_path = get_abs_path(prompts_conf["main_prompt_path"])
    except KeyError as e:
        logger.error(f"Key {e} not found in prompts configuration.")
        raise e
    
    try:
        return open(system_prompt_path, "r", encoding="utf-8").read()
    except Exception as e:
        logger.error(f"System prompt file not found at {system_prompt_path}.")
        raise e

def load_rag_prompts():
    try:
        rag_prompt_path = get_abs_path(prompts_conf["rag_summarize_prompt_path"])
    except KeyError as e:
        logger.error(f"Key {e} not found in prompts configuration.")
        raise e

    try:
        return open(rag_prompt_path, "r", encoding="utf-8").read()
    except Exception as e:
        logger.error(f"RAG prompt file not found at {rag_prompt_path}.")
        raise e

def load_report_prompts():
    try:
        report_prompt_path = get_abs_path(prompts_conf["report_prompt_path"])
    except KeyError as e:
        logger.error(f"Key {e} not found in prompts configuration.")
        raise e
    
    try:
        return open(report_prompt_path, "r", encoding="utf-8").read()
    except Exception as e:
        logger.error(f"Report prompt file not found at {report_prompt_path}.")
        raise e