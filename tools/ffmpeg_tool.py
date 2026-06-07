from __future__ import annotations

import subprocess
from pathlib import Path

from config.settings import settings


class FFmpegTool:
    def __init__(self, ffmpeg_binary: str | None = None) -> None:
        self.ffmpeg = ffmpeg_binary or settings.ffmpeg_binary

    def convert_to_wav(
        self,
        video_path: str,
        output_path: str | None = None,
        sample_rate: int = 16000,
        channels: int = 1,
    ) -> str:
        video_p = Path(video_path)
        if not video_p.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        if output_path is None:
            audio_dir = settings.resolve_path(settings.audio_dir)
            audio_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(audio_dir / f"{video_p.stem}.wav")

        cmd = [
            self.ffmpeg,
            "-y",
            "-i", str(video_path),
            "-acodec", "pcm_s16le",
            "-ar", str(sample_rate),
            "-ac", str(channels),
            output_path,
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr}")
        return output_path

    def extract_audio_stream(
        self,
        video_path: str,
        output_path: str | None = None,
    ) -> str:
        video_p = Path(video_path)
        if not video_p.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        if output_path is None:
            audio_dir = settings.resolve_path(settings.audio_dir)
            audio_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(audio_dir / f"{video_p.stem}_audio.wav")

        cmd = [
            self.ffmpeg,
            "-y",
            "-i", str(video_path),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            output_path,
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg audio extract failed: {result.stderr}")
        return output_path


_ffmpeg_tool: FFmpegTool | None = None


def get_ffmpeg_tool() -> FFmpegTool:
    global _ffmpeg_tool
    if _ffmpeg_tool is None:
        _ffmpeg_tool = FFmpegTool()
    return _ffmpeg_tool
