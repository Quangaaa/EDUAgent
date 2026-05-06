import logging
import os
try:
    from utils.path import get_abs_path
except ModuleNotFoundError:
    # 兼容直接运行 `python utils/*.py` 的场景
    from path import get_abs_path

# 日志保存的根目录
LOG_ROOT = get_abs_path("logs")
os.makedirs(LOG_ROOT, exist_ok=True)

DEFAULT_LOG_FORMAT = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s")

def get_logger(name: str = "agent",
               console_level: int=logging.INFO,
               file_level: int=logging.DEBUG,
               log_file: str = None,
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # 设置最低日志级别为DEBUG
    if logger.handlers:
        return logger  # 清除已有的处理器，避免重复日志

    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(DEFAULT_LOG_FORMAT)
    logger.addHandler(console_handler)

    # 创建文件处理器
    if log_file is not None:
        file_handler = logging.FileHandler(os.path.join(LOG_ROOT, log_file))
        file_handler.setLevel(file_level)
        file_handler.setFormatter(DEFAULT_LOG_FORMAT)
        logger.addHandler(file_handler)

    return logger

# 快捷获取日志管理
logger = get_logger()