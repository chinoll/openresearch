"""
Prompt loader - 从文件加载 prompt 模板，并替换 {{var}} 占位符
"""

import re
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


def load(name: str, **kwargs: str) -> str:
    """
    加载 prompt 模板并替换变量。

    Args:
        name: 模板路径（相对于 prompts/），例如 "extractor/contributions"
        **kwargs: 变量名和对应的值，替换模板中的 {{var_name}}

    Returns:
        替换变量后的 prompt 字符串

    Example:
        load("extractor/contributions", title="Attention Is All You Need", abstract="...")
    """
    path = _PROMPTS_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")

    template = path.read_text(encoding="utf-8")

    def replacer(match: re.Match) -> str:
        var = match.group(1)
        if var not in kwargs:
            raise KeyError(f"Missing variable '{{{{ {var} }}}}' for prompt '{name}'")
        return str(kwargs[var])

    return re.sub(r"\{\{(\w+)\}\}", replacer, template)
