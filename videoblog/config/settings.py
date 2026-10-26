from __future__ import annotations

import configparser
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config.ini"
CONFIG_EXAMPLE_PATH = PROJECT_ROOT / "config.example.ini"


def _read_config() -> configparser.ConfigParser:
    """读取 config.ini；首次运行时从示例文件自动创建。"""
    if not CONFIG_PATH.exists() and CONFIG_EXAMPLE_PATH.exists():
        CONFIG_PATH.write_text(
            CONFIG_EXAMPLE_PATH.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    parser = configparser.ConfigParser(interpolation=None)
    if CONFIG_PATH.exists():
        # utf-8-sig 兼容记事本保存的 BOM
        parser.read(CONFIG_PATH, encoding="utf-8-sig")
    return parser


def _value(
    parser: configparser.ConfigParser,
    section: str,
    option: str,
    default: str = "",
) -> str:
    try:
        return parser.get(section, option).strip()
    except (configparser.NoSectionError, configparser.NoOptionError):
        return default


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on", "是"}


class Settings:
    def __init__(self) -> None:
        parser = _read_config()

        self.workspace_dir = PROJECT_ROOT
        self.data_dir = Path("data")
        self.subtitles_dir = Path("data/subtitles")
        self.blogs_dir = Path("data/blogs")
        # 订阅功能的本地状态（可选功能，不影响视频转博客）
        self.subscriptions_dir = Path("data/subscriptions")
        self.videos_dir = Path("data/videos")

        self.yt_dlp_user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        )
        self.bilibili_referer = "https://www.bilibili.com/"
        self.bilibili_cookie_file = _value(parser, "bilibili", "cookie_file") or None
        self.bilibili_no_proxy = _as_bool(_value(parser, "bilibili", "no_proxy", "false"))
        self.bilibili_sessdata = _value(parser, "bilibili", "sessdata") or None

        self.llm_provider = "deepseek"
        self.deepseek_api_key = _value(parser, "deepseek", "api_key") or None
        self.deepseek_model = _value(parser, "deepseek", "model", "deepseek-chat")
        self.deepseek_base_url = _value(
            parser, "deepseek", "base_url", "https://api.deepseek.com"
        )

        self.default_pipeline = _value(parser, "run", "pipeline", "video_to_blog")
        prompt_path = _value(parser, "run", "prompt_config", "prompts.yaml")
        self.prompt_config_path = Path(prompt_path) if prompt_path else None

    def beijing_now(self) -> datetime:
        return datetime.now(ZoneInfo("Asia/Shanghai"))

    def ensure_directories(self) -> None:
        for path in [
            self.data_dir,
            self.subtitles_dir,
            self.blogs_dir,
            self.subscriptions_dir,
            self.videos_dir,
        ]:
            (self.workspace_dir / path).mkdir(parents=True, exist_ok=True)

    def resolve_path(self, path: Path | str) -> Path:
        path_obj = Path(path)
        return path_obj if path_obj.is_absolute() else self.workspace_dir / path_obj


settings = Settings()
settings.ensure_directories()
