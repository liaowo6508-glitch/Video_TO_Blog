from __future__ import annotations

import os
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlparse, urlencode, parse_qs

import yt_dlp
from yt_dlp.utils import DownloadError

from config.settings import settings
from monitor import make_progress_hook, task_log


def _strip_bilibili_tracking_params(url: str) -> str:
    """去掉 B站 URL 中的来源追踪参数，返回纯净视频 URL。"""
    parsed = urlparse(url)
    if parsed.netloc not in {"www.bilibili.com", "bilibili.com"}:
        return url

    match = re.match(r"^/video/([Bb][Vv]\w+)", parsed.path)
    if not match:
        return url

    clean_path = f"/video/{match.group(1)}"
    return f"{parsed.scheme}://{parsed.netloc}{clean_path}"


def _is_412_error(exc: Exception) -> bool:
    """判断异常是否由 B站 412 引起。"""
    msg = str(exc)
    return "412" in msg and ("Bilibili" in msg or "[BiliBili]" in msg)


class YtDlpTool:
    def __init__(self, output_dir: Path | None = None) -> None:
        self.output_dir = settings.resolve_path(
            output_dir or settings.video_down_dir
        )

    def cleanup_old_task_dirs(self, max_keep: int) -> int:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if max_keep < 0:
            max_keep = 0

        task_dirs = sorted(
            (path for path in self.output_dir.iterdir() if path.is_dir()),
            key=lambda path: path.name,
            reverse=True,
        )

        removed = 0
        for path in task_dirs[max_keep:]:
            shutil.rmtree(path, ignore_errors=True)
            task_log("🗑️ 清理过期视频目录: %s", path.name)
            removed += 1
        return removed

    def _build_base_options(
        self, *, quiet: bool, skip_download: bool
    ) -> dict:
        opts: dict = {
            "quiet": quiet,
            "no_warnings": True,
            "skip_download": skip_download,
            "http_headers": {
                "Referer": settings.bilibili_referer,
                "User-Agent": settings.yt_dlp_user_agent,
            },
        }
        if settings.bilibili_no_proxy:
            opts["proxy"] = ""
        if settings.ffmpeg_location:
            opts["ffmpeg_location"] = str(settings.resolve_path(settings.ffmpeg_location))
        return opts

    def _resolve_cookie_file(self) -> tuple[str | None, bool]:
        cookie_file = settings.bilibili_cookie_file
        if cookie_file:
            resolved = settings.resolve_path(cookie_file)
            if resolved.exists():
                return str(resolved), False

        cookies = settings.bilibili_sessdata
        if cookies:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False
            ) as f:
                f.write("# Netscape HTTP Cookie File\n")
                f.write(
                    f".bilibili.com\tTRUE\t/\tFALSE\t0\tSESSDATA\t{cookies}\n"
                )
            return f.name, True
        return None, False

    def extract_info(self, url: str) -> dict:
        task_log("开始抓取视频元信息: %s", url)
        opts = self._build_base_options(quiet=True, skip_download=True)
        cookie_path, should_delete = self._resolve_cookie_file()
        if cookie_path:
            opts["cookiefile"] = cookie_path
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False) or {}
        except Exception as exc:
            import traceback
            task_log("extract_info 异常: type=%s msg=%s", type(exc).__name__, str(exc)[:200])
            if _is_412_error(exc):
                clean_url = _strip_bilibili_tracking_params(url)
                task_log("412 拦截，尝试纯净 URL: %s", clean_url)
                try:
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        return ydl.extract_info(clean_url, download=False) or {}
                except Exception:
                    task_log("纯净 URL 重试仍失败:\n%s", traceback.format_exc())
                    raise
            raise
        finally:
            if cookie_path and should_delete:
                os.unlink(cookie_path)

    def download_audio_only(self, url: str, video_id: str, task_dir: str) -> str:
        task_log("准备下载音频: video_id=%s task_dir=%s", video_id, task_dir)
        base_dir = settings.resolve_path(settings.video_down_dir)
        folder = base_dir / task_dir
        folder.mkdir(parents=True, exist_ok=True)
        outtmpl = str(folder / f"{video_id}.%(ext)s")

        ydl_opts = self._build_base_options(quiet=False, skip_download=False)
        ydl_opts.update(
            {
                "format": "bestaudio/best",
                "outtmpl": outtmpl,
                "progress_hooks": [make_progress_hook("audio", video_id)],
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "wav",
                    }
                ],
            }
        )

        cookie_path, should_delete = self._resolve_cookie_file()
        if cookie_path:
            ydl_opts["cookiefile"] = cookie_path

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                audio_path = str(Path(filename).with_suffix(".wav"))
        except DownloadError as exc:
            message = str(exc)
            if "ffprobe and ffmpeg not found" in message:
                hint = (
                    "缺少 ffmpeg/ffprobe。请先安装 ffmpeg，"
                    "或在 .env 中配置 FFMPEG_LOCATION 指向其可执行文件目录或二进制路径。"
                )
                raise RuntimeError(f"{hint} 原始错误: {message}") from exc
            raise
        finally:
            if cookie_path and should_delete:
                os.unlink(cookie_path)

        return audio_path

    def download_subtitle_text(
        self, url: str, video_id: str, task_dir: str
    ) -> tuple[str | None, list[dict]]:
        task_log("开始尝试下载字幕: video_id=%s task_dir=%s", video_id, task_dir)
        base_dir = settings.resolve_path(settings.video_down_dir)
        folder = base_dir / task_dir
        folder.mkdir(parents=True, exist_ok=True)

        downloaded: list[dict] = []
        subtitle_path: str | None = None

        ydl_opts = self._build_base_options(quiet=True, skip_download=True)
        ydl_opts.update(
            {
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": ["zh-CN", "zh-Hans", "zh", "en"],
                "outtmpl": str(folder / f"{video_id}.%(id)s.%(ext)s"),
                "skip_download": True,
            }
        )

        cookie_path, should_delete = self._resolve_cookie_file()
        if cookie_path:
            ydl_opts["cookiefile"] = cookie_path

        info: dict | None = None
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                extracted = ydl.extract_info(url, download=False) or {}
                if not isinstance(extracted, dict):
                    task_log(
                        "video_id=%s 字幕元信息结构异常: %s",
                        video_id,
                        type(extracted).__name__,
                    )
                    return None, []

                info = extracted
                subtitles = info.get("subtitles") or {}
                auto_subs = info.get("automatic_captions") or {}
                candidates = self._filter_subtitle_candidates({**subtitles, **auto_subs})

                if not candidates:
                    task_log("video_id=%s 未发现可用字幕或自动字幕", video_id)
                    return None, []

                chosen_lang = self._pick_subtitle_lang(candidates)
                if not chosen_lang:
                    task_log("video_id=%s 字幕候选为空，跳过字幕下载", video_id)
                    return None, []

                sub_info = candidates[chosen_lang]
                sub_ext = self._best_subtitle_ext(sub_info)

                task_log(
                    "video_id=%s 选择字幕语言=%s 扩展名=%s",
                    video_id,
                    chosen_lang,
                    sub_ext,
                )

                sub_ydl_opts = self._build_base_options(quiet=True, skip_download=True)
                sub_ydl_opts.update(
                    {
                        "writesubtitles": True,
                        "writeautomaticsub": True,
                        "subtitleslangs": [chosen_lang],
                        "skip_download": True,
                        "outtmpl": str(folder / f"{video_id}.%(id)s.%(ext)s"),
                    }
                )
                if cookie_path:
                    sub_ydl_opts["cookiefile"] = cookie_path

                with yt_dlp.YoutubeDL(sub_ydl_opts) as sub_ydl:
                    sub_ydl.download([url])

                matched_files = self._find_downloaded_subtitle_files(
                    folder=folder,
                    video_id=video_id,
                    lang=chosen_lang,
                    preferred_ext=sub_ext,
                )
                if matched_files:
                    subtitle_path = str(matched_files[0])
                    task_log("video_id=%s 字幕下载完成: %s", video_id, subtitle_path)
                    downloaded = [
                        {
                            "lang": chosen_lang,
                            "path": str(path),
                            "ext": path.suffix.lstrip("."),
                        }
                        for path in matched_files
                    ]
                else:
                    task_log(
                        "video_id=%s 字幕下载后未找到目标文件: lang=%s ext=%s dir=%s",
                        video_id,
                        chosen_lang,
                        sub_ext,
                        folder,
                    )
        finally:
            if cookie_path and should_delete:
                os.unlink(cookie_path)

        return subtitle_path, downloaded

    def _find_downloaded_subtitle_files(
        self,
        *,
        folder: Path,
        video_id: str,
        lang: str,
        preferred_ext: str,
    ) -> list[Path]:
        allowed_exts = {"vtt", "srt", "ass", "srv1", "srv2", "srv3", "json3", "ttml"}
        candidates = sorted(
            path
            for path in folder.iterdir()
            if path.is_file()
            and path.name.startswith(f"{video_id}.")
            and f".{lang}." in path.name
            and path.suffix.lstrip(".") in allowed_exts
        )
        if not candidates:
            return []

        preferred_matches = [
            path for path in candidates if path.suffix.lstrip(".") == preferred_ext
        ]
        return preferred_matches or candidates

    def _filter_subtitle_candidates(self, candidates: dict) -> dict[str, list[dict]]:
        filtered: dict[str, list[dict]] = {}
        for lang, entries in candidates.items():
            if not isinstance(lang, str) or lang == "danmaku":
                continue
            if not isinstance(entries, list):
                continue

            valid_entries = [
                entry
                for entry in entries
                if isinstance(entry, dict) and entry.get("ext") in {"vtt", "srt", "ass", "srv1", "srv2", "srv3", "json3", "ttml"}
            ]
            if valid_entries:
                filtered[lang] = valid_entries
        return filtered

    def _pick_subtitle_lang(self, candidates: dict) -> str | None:
        priority = ["zh-Hans", "zh-CN", "zh", "en"]
        for lang in priority:
            if lang in candidates:
                return lang
        return next(iter(candidates.keys()), None)

    def _best_subtitle_ext(self, sub_info: list[dict]) -> str:
        if isinstance(sub_info, list):
            for s in sub_info:
                if isinstance(s, dict) and "ext" in s:
                    return s["ext"]
        return "vtt"

    def list_subtitles(self, url: str) -> dict:
        opts = self._build_base_options(quiet=True, skip_download=True)
        opts["list_subs"] = True
        cookie_path, should_delete = self._resolve_cookie_file()
        if cookie_path:
            opts["cookiefile"] = cookie_path
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.extract_info(url, download=False)
        finally:
            if cookie_path and should_delete:
                os.unlink(cookie_path)
        return {}

    def download_video(self, url: str) -> tuple[str, str]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        outtmpl = str(self.output_dir / "%(id)s.%(ext)s")

        ydl_opts = self._build_base_options(quiet=False, skip_download=False)
        ydl_opts.update(
            {
                "format": settings.yt_dlp_format,
                "outtmpl": outtmpl,
                "consoletitle": True,
            }
        )

        cookie_path, should_delete = self._resolve_cookie_file()
        if cookie_path:
            ydl_opts["cookiefile"] = cookie_path

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                video_path = str(Path(filename))
        finally:
            if cookie_path and should_delete:
                os.unlink(cookie_path)

        title = info.get("title", "unknown") if info else "unknown"
        return video_path, title


_yt_dlp_tool: YtDlpTool | None = None


def get_ytdlp_tool() -> YtDlpTool:
    global _yt_dlp_tool
    if _yt_dlp_tool is None:
        _yt_dlp_tool = YtDlpTool()
    return _yt_dlp_tool
