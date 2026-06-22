from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional, Union

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class OutputFormat(BaseModel):
    """LLM 输出格式配置。"""

    type: str = Field(
        default="markdown",
        description="输出类型：markdown | json",
    )
    json_schema: Optional[str] = Field(
        default=None,
        description="当 type=json 时，描述 JSON 结构（用于 few-shot 或 response_format）。",
    )


class BlogPromptConfig(BaseModel):
    """博客生成提示词配置。"""

    system_prompt: str = Field(
        default=(
            "你是一名中文技术内容编辑。请将输入内容整理成结构清晰、适合发布的中文博客文章。\n"
            "要求：\n"
            "1. 输出 Markdown。\n"
            "2. 自动提炼标题、摘要、小节结构。\n"
            "3. 保留关键信息和时间顺序。\n"
            "4. 如果是口语化转写，转换为书面表达。\n"
            "5. 在结尾补充\"总结\"小节。"
        ),
        description="System prompt，定义 LLM 的角色与核心要求。",
    )

    user_template: str = Field(
        default=(
            "请将以下视频内容整理为一篇结构化中文博客文章。\n\n"
            "视频标题：{video_title}\n"
            "来源链接：{video_url}\n\n"
            "内容如下：\n{source_text}"
        ),
        description=(
            "User prompt 模板。占位符：\n"
            "  {video_title}  - 视频标题\n"
            "  {video_url}   - 视频链接\n"
            "  {source_text} - 字幕或转写文本"
        ),
    )

    output_format: OutputFormat = Field(
        default_factory=lambda: OutputFormat(type="markdown"),
        description="输出格式配置（markdown 或 json）。",
    )

    max_tokens: Optional[int] = Field(
        default=None,
        description="LLM 最大生成长度（token）。None 表示使用模型默认值。",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="生成温度，控制创造性。",
    )


def load_prompt_config(
    config_path: Optional[Union[str, Path]] = None,
) -> BlogPromptConfig:
    """
    加载提示词配置。

    优先级：``config_path`` 参数 > 环境变量 ``PROMPT_CONFIG_PATH``
    > ``settings.prompt_config_path`` > 默认文件 ``config/prompts.yaml`` > 内置默认值。

    - 若显式指定了配置路径（参数或环境变量）但文件不存在，抛出 ``FileNotFoundError``。
    - 若完全没配置，则使用内置默认值 ``BlogPromptConfig()``。
    - 若文件存在，以 YAML 格式解析并与默认配置合并（未填字段使用默认值）。
    """
    from config.settings import settings

    import yaml

    explicit = False
    if config_path is not None:
        explicit = True
    else:
        config_path = os.environ.get("PROMPT_CONFIG_PATH")
        if config_path:
            explicit = True
        else:
            config_path = getattr(settings, "prompt_config_path", None)
            if config_path:
                explicit = True
    if not config_path:
        config_path = Path("config/prompts.yaml")
        explicit = False  # 默认路径若不存在，允许回退到内置默认值

    path = Path(config_path)
    if not path.is_absolute():
        path = settings.workspace_dir / path

    if not path.exists():
        if explicit:
            raise FileNotFoundError(
                f"Prompt config file not found: {path}. "
                "请检查 PROMPT_CONFIG_PATH / settings.prompt_config_path 配置。"
            )
        logger.warning(
            "[prompts] 配置文件 %s 不存在，使用内置默认 system_prompt（长度 %d）。"
            "如需自定义提示词，请在 config/prompts.yaml 中维护。",
            path,
            len(BlogPromptConfig().system_prompt),
        )
        return BlogPromptConfig()

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    cfg = BlogPromptConfig(**raw)
    logger.info(
        "[prompts] 已加载配置: path=%s system_prompt 长度=%d user_template 长度=%d",
        path,
        len(cfg.system_prompt),
        len(cfg.user_template),
    )
    logger.debug("[prompts] system_prompt 前 80 字符: %s", cfg.system_prompt[:80])
    return cfg


# ---------------------------------------------------------------------------
# 默认配置单例（Lazy load，首次访问时从文件读取）
# ---------------------------------------------------------------------------
_default_config: Optional[BlogPromptConfig] = None


def get_prompt_config(
    config_path: Optional[Union[str, Path]] = None,
) -> BlogPromptConfig:
    """
    获取提示词配置单例。

    ``config_path`` 仅在首次调用时生效；后续调用忽略该参数。
    优先级：显式传入 > 环境变量 ``PROMPT_CONFIG_PATH`` > 默认文件 ``config/prompts.yaml`` > 内置默认值。

    如需在运行时重新加载（例如调试提示词），调用 ``reset_prompt_config()`` 清除单例缓存。
    """
    global _default_config
    if _default_config is None:
        _default_config = load_prompt_config(config_path)
    return _default_config


def reset_prompt_config() -> None:
    """清除提示词配置单例缓存。下次调用 ``get_prompt_config()`` 时将重新读盘。"""
    global _default_config
    _default_config = None
    logger.info("[prompts] 已重置提示词配置缓存，下次访问时将重新加载。")
