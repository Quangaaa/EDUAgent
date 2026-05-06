"""
为整个工程提供统一绝对路径
"""

import os

def get_project_root_path():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_abs_path(relative_path: str) -> str:
    return os.path.join(get_project_root_path(), relative_path)