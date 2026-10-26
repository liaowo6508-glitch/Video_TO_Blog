from __future__ import annotations

import re

from videoblog.config.settings import settings


def _sanitize_filename(name: str) -> str:
    """移除文件名非法字符，保留中文、字母、数字。"""
    return re.sub(r"[\\/:*?\"<>|]", "", name).strip()


def _safe_filename(name: str, max_len: int = 60) -> str:
    safe = _sanitize_filename(name)
    return safe[:max_len] if len(safe) > max_len else safe


def _extract_article_title(blog_content: str) -> str | None:
    match = re.search(r"^#\s+(.+)\s*$", blog_content, re.MULTILINE)
    return match.group(1).strip() if match else None


def save_subtitle(task_id: str, video_title: str, content: str) -> str:
    """保存清洗后的字幕纯文本。"""
    subtitles_dir = settings.resolve_path(settings.subtitles_dir)
    subtitles_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{_safe_filename(video_title or 'unknown')}_{task_id}.txt"
    output_path = subtitles_dir / filename
    output_path.write_text(content, encoding="utf-8")
    return str(output_path)


def save_blog(
    task_id: str,
    content: str,
    article_title: str | None = None,
    created_at: str | None = None,
) -> str:
    """保存 Markdown 博客。"""
    blogs_dir = settings.resolve_path(settings.blogs_dir)
    blogs_dir.mkdir(parents=True, exist_ok=True)

    title = article_title or _extract_article_title(content)
    date = created_at[:10] if created_at else settings.beijing_now().strftime("%Y-%m-%d")

    if title:
        filename = f"{date}_{_safe_filename(title)}.md"
    else:
        filename = f"{date}_{task_id}.md"

    output_path = blogs_dir / filename
    output_path.write_text(content, encoding="utf-8")
    return str(output_path)
