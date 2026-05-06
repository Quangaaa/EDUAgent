import yaml
try:
    from utils.path import get_abs_path
except ModuleNotFoundError:
    # 兼容直接运行 `python utils/*.py` 的场景
    from path import get_abs_path


def _safe_load_yaml(config_file: str, encoding: str = "utf-8") -> dict:
    with open(get_abs_path(config_file), "r", encoding=encoding) as f:
        return yaml.load(f, Loader=yaml.FullLoader) or {}

def load_rag_config(config_file: str = get_abs_path("config/rag.yaml"), encoding: str = "utf-8"):
    return _safe_load_yaml(config_file, encoding)
    
def load_chroma_config(config_file: str = get_abs_path("config/chroma.yaml"), encoding: str = "utf-8"):
    return _safe_load_yaml(config_file, encoding)
    
def load_prompts_config(config_file: str = get_abs_path("config/prompts.yaml"), encoding: str = "utf-8"):
    return _safe_load_yaml(config_file, encoding)
    
def load_agent_config(config_file: str = get_abs_path("config/agent.yaml"), encoding: str = "utf-8"):
    return _safe_load_yaml(config_file, encoding)
    
def load_dialogue_config(config_file: str = get_abs_path("config/dialogue.yaml"), encoding: str = "utf-8"):
    return _safe_load_yaml(config_file, encoding)

def load_chat_config(config_file: str = get_abs_path("config/chat.yaml"), encoding: str = "utf-8"):
    return _safe_load_yaml(config_file, encoding)


def load_plan_config(config_file: str = get_abs_path("config/plan.yaml"), encoding: str = "utf-8"):
    return _safe_load_yaml(config_file, encoding)


def load_control_config(config_file: str = get_abs_path("config/control.yaml"), encoding: str = "utf-8"):
    return _safe_load_yaml(config_file, encoding)
    
def load_sign_config(config_file: str = get_abs_path("config/sign.yaml"), encoding: str = "utf-8"):
    return _safe_load_yaml(config_file, encoding)

rag_conf = load_rag_config()
chroma_conf = load_chroma_config()
prompts_conf = load_prompts_config()
agent_conf = load_agent_config()
sign_conf = load_sign_config()
dialogue_conf = load_dialogue_config()
chat_conf = load_chat_config()
plan_conf = load_plan_config()
control_conf = load_control_config()