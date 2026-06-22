from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SubtitleEntry:
    index: int
    start_sec: float
    end_sec: float
    text: str

    def format_clean(self, include_time: bool = False) -> str:
        if include_time:
            return f"[{_format_timestamp(self.start_sec)}] {self.text}"
        return self.text


def _format_timestamp(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _parse_srt_time(time_str: str) -> float:
    """解析 SRT 时间格式: 00:00:01,120 -> 秒数"""
    match = re.match(r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})", time_str.strip())
    if not match:
        return 0.0
    h, m, s, ms = match.groups()
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def _parse_vtt_time(time_str: str) -> float:
    """解析 VTT 时间格式: 00:00:01.120 -> 秒数"""
    time_str = time_str.strip()
    if "." not in time_str and "," not in time_str:
        match = re.match(r"(\d{2}):(\d{2}):(\d{2})", time_str)
        if match:
            h, m, s = match.groups()
            return int(h) * 3600 + int(m) * 60 + int(s)
    match = re.match(r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})", time_str)
    if not match:
        return 0.0
    h, m, s, ms = match.groups()
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_srt(content: str) -> list[SubtitleEntry]:
    """解析 SRT 字幕内容，返回字幕条目列表"""
    entries: list[SubtitleEntry] = []
    blocks = re.split(r"\n\s*\n", content.strip())

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue

        try:
            index = int(lines[0].strip())
            time_line = lines[1]
            text = "\n".join(lines[2:])

            time_match = re.match(
                r"(.+?)\s*-->\s*(.+)", time_line
            )
            if not time_match:
                continue

            start_str, end_str = time_match.groups()
            start_sec = _parse_srt_time(start_str)
            end_sec = _parse_srt_time(end_str)

            entries.append(SubtitleEntry(
                index=index,
                start_sec=start_sec,
                end_sec=end_sec,
                text=text.strip(),
            ))
        except (ValueError, IndexError):
            continue

    return entries


def parse_vtt(content: str) -> list[SubtitleEntry]:
    """解析 VTT 字幕内容，返回字幕条目列表"""
    entries: list[SubtitleEntry] = []
    lines = content.strip().split("\n")

    i = 0
    while i < len(lines) and not lines[i].startswith("NOTE"):
        if lines[i].strip() == "":
            i += 1
            continue
        if lines[i].startswith("WEBVTT"):
            i += 1
            continue
        if re.match(r"\d{2}:\d{2}:\d{2}", lines[i]):
            time_line = lines[i]
            i += 1
            text_lines = []
            while i < len(lines) and lines[i].strip() != "":
                if "-->" in lines[i]:
                    break
                text_lines.append(lines[i])
                i += 1

            time_match = re.match(r"(.+?)\s*-->\s*(.+)", time_line)
            if time_match:
                start_str, end_str = time_match.groups()
                start_sec = _parse_vtt_time(start_str)
                end_sec = _parse_vtt_time(end_str)
                text = "\n".join(text_lines).strip()
                if text:
                    entries.append(SubtitleEntry(
                        index=len(entries) + 1,
                        start_sec=start_sec,
                        end_sec=end_sec,
                        text=text,
                    ))
        else:
            i += 1

    return entries


def parse_subtitle(file_path: str | Path) -> list[SubtitleEntry]:
    """根据文件扩展名自动解析 SRT 或 VTT 字幕"""
    path = Path(file_path)
    content = path.read_text(encoding="utf-8")

    suffix = path.suffix.lower()
    if suffix == ".srt":
        return parse_srt(content)
    elif suffix == ".vtt":
        return parse_vtt(content)
    else:
        return parse_srt(content)


def clean_subtitle(entries: list[SubtitleEntry], include_time: bool = False) -> str:
    """将字幕条目清洗为纯文本，抹除多余的视频时间信息"""
    lines = [entry.format_clean(include_time=include_time) for entry in entries]
    return "\n".join(lines)


def process_subtitle_file(
    file_path: str | Path,
    include_time: bool = False,
) -> str:
    """读取字幕文件，清洗并返回纯文本内容"""
    entries = parse_subtitle(file_path)
    return clean_subtitle(entries, include_time=include_time)
