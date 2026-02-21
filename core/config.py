"""
Shared config loader - 统一配置加载

加载 config.yaml 并应用环境变量覆盖。
CLI (main.py) 和 FastAPI (backend/main.py) 均使用此函数。

优先级：环境变量 > config.yaml > 内置默认值
"""
import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

_DEFAULT_LLM_CONFIG = {
    'provider': 'anthropic',
    'model': 'claude-sonnet-4-5-20250929',
    'api_key': '',
    'base_url': '',
    'max_tokens': 4096,
    'temperature': 0.7,
}

_ENV_MAP = {
    'LLM_PROVIDER': 'provider',
    'LLM_MODEL': 'model',
    'LLM_API_KEY': 'api_key',
    'LLM_BASE_URL': 'base_url',
}

# Fallback env vars for api_key (when LLM_API_KEY is not set)
_API_KEY_FALLBACKS = ['ANTHROPIC_API_KEY', 'OPENAI_API_KEY']

_cached_config: Optional[dict] = None


def load_app_config(config_path: Optional[Path] = None) -> dict:
    """
    加载应用配置：config.yaml + 环境变量覆盖。

    Args:
        config_path: 配置文件路径，默认为 config/config.yaml

    Returns:
        合并后的配置字典
    """
    global _cached_config

    config = {}

    if config_path is None:
        config_path = Path("config/config.yaml")

    if config_path.exists():
        try:
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}")

    # Ensure llm section has all defaults
    llm = config.setdefault('llm', {})
    for key, default_value in _DEFAULT_LLM_CONFIG.items():
        llm.setdefault(key, default_value)

    # Environment variable overrides (highest priority)
    _apply_env_overrides(llm)

    _cached_config = config
    return config


def _apply_env_overrides(llm: dict):
    """应用环境变量覆盖"""
    for env_var, config_key in _ENV_MAP.items():
        value = os.environ.get(env_var)
        if value:
            llm[config_key] = value

    # api_key fallback: if still empty, try provider-specific env vars
    if not llm.get('api_key'):
        for fallback_var in _API_KEY_FALLBACKS:
            value = os.environ.get(fallback_var)
            if value:
                llm['api_key'] = value
                break


def get_app_config() -> dict:
    """获取已加载的应用配置（lazy load）"""
    global _cached_config
    if _cached_config is None:
        _cached_config = load_app_config()
    return _cached_config
