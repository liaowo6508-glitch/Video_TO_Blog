from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re

DEFAULT_TAGS = ["AI", "编程", "技术博客", "教程", "工具使用"]

KEYWORD_TO_TAG = {
    "C++": "C++",
    "Python": "Python",
    "Java": "Java",
    "AI": "AI",
    "Claude": "AI",
    "DeepSeek": "AI",
    "LangGraph": "LangGraph",
    "FastAPI": "FastAPI",
    "游戏开发": "游戏开发",
    "算法": "算法",
    "教程": "教程",
    "博客": "博客",
    "视频": "视频",
    "B站": "B站",
}


@dataclass
class CSDNPayload:
    title: str
    body: str
    summary: str
    tags: list[str]
    content_type: str = "original"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def extract_title(markdown: str) -> str:
    match = re.search(r"^#\s+(.+)\s*$", markdown, re.MULTILINE)
    return match.group(1).strip() if match else "未命名文章"


def _strip_markdown_noise(text: str) -> str:
    compact = re.sub(r"```[\s\S]*?```", "", text)
    compact = re.sub(r"[`*_>#-]", " ", compact)
    compact = re.sub(r"\s+", " ", compact)
    return compact.strip()


def extract_summary(markdown: str, max_len: int = 200) -> str:
    match = re.search(
        r"^##\s*摘要\s*\n+(.*?)(?=\n##\s|\Z)",
        markdown,
        re.MULTILINE | re.DOTALL,
    )
    if match:
        text = _strip_markdown_noise(match.group(1))
    else:
        body = re.sub(r"^#\s+.+$", "", markdown, flags=re.MULTILINE).strip()
        text = _strip_markdown_noise(body)
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + "..."


def extract_tags(markdown: str, limit: int = 5) -> list[str]:
    found: list[str] = []
    scan_text = markdown[:3000]
    for keyword, tag in KEYWORD_TO_TAG.items():
        if keyword in scan_text and tag not in found:
            found.append(tag)
        if len(found) >= limit:
            break
    return found or DEFAULT_TAGS[:limit]


def format_csdn_body(markdown: str) -> str:
    return markdown.strip() + "\n"


def format_csdn_payload(markdown_file: str | Path, **overrides: object) -> CSDNPayload:
    content = Path(markdown_file).read_text(encoding="utf-8")
    tags_override = overrides.get("tags")
    tags = list(tags_override) if isinstance(tags_override, list) else extract_tags(content)
    return CSDNPayload(
        title=str(overrides.get("title") or extract_title(content)),
        body=str(overrides.get("body") or format_csdn_body(content)),
        summary=str(overrides.get("summary") or extract_summary(content)),
        tags=tags,
        content_type=str(overrides.get("content_type") or "original"),
    )
