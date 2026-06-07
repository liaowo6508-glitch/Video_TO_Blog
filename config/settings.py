from pathlib import Path
from zoneinfo import ZoneInfo
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "AI Pipeline Platform"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    workspace_dir: Path = Path(__file__).resolve().parent.parent
    data_dir: Path = Field(default_factory=lambda: Path("data"))
    video_down_dir: Path = Field(default_factory=lambda: Path("data/video_down"))
    audio_dir: Path = Field(default_factory=lambda: Path("data/audio"))
    subtitles_dir: Path = Field(default_factory=lambda: Path("data/subtitles"))
    results_dir: Path = Field(default_factory=lambda: Path("data/results"))
    blogs_dir: Path = Field(default_factory=lambda: Path("data/blogs"))
    tasks_dir: Path = Field(default_factory=lambda: Path("data/tasks"))

    yt_dlp_format: str = "bv*+ba/b"
    yt_dlp_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )
    bilibili_cookie_file: str | None = None
    bilibili_referer: str = "https://www.bilibili.com/"
    bilibili_no_proxy: bool = False
    ffmpeg_binary: str = "ffmpeg"
    ffmpeg_location: str | None = None
    asr_provider: str = "local_whisper"
    local_whisper_model: str = "small"
    groq_model: str = "whisper-large-v3-turbo"
    llm_provider: str = "deepseek"
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com"

    groq_api_key: str | None = None
    deepseek_api_key: str | None = None
    bilibili_sessdata: str | None = None
    # csdn_editor_url: str = "https://editor.csdn.net/mdeditor"       # [CSDN发布-技术储备]
    # csdn_auto_publish: bool = False                                   # [CSDN发布-技术储备]

    prompt_config_path: Path | None = Field(
        default=None,
        description=(
            "提示词配置文件路径（支持相对路径，相对于 workspace_dir）。"
            "若为 None，优先从环境变量 PROMPT_CONFIG_PATH 读取；"
            "若也未设置，默认使用 config/prompts.yaml。"
        ),
    )

    def beijing_now(self):
        return __import__("datetime").datetime.now(ZoneInfo("Asia/Shanghai"))

    def ensure_directories(self) -> None:
        for path in [
            self.data_dir,
            self.video_down_dir,
            self.audio_dir,
            self.subtitles_dir,
            self.results_dir,
            self.blogs_dir,
            self.tasks_dir,
        ]:
            (self.workspace_dir / path).mkdir(parents=True, exist_ok=True)

    def resolve_path(self, path: Path | str) -> Path:
        path_obj = Path(path)
        return path_obj if path_obj.is_absolute() else self.workspace_dir / path_obj


settings = Settings()
settings.ensure_directories()
