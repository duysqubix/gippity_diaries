import re
from collections.abc import Callable
from typing import TypedDict, cast

import mistune


class Article(TypedDict):
    title: str
    slug: str
    body_html: str
    preview: str
    entry_number: int


create_markdown = cast(
    Callable[..., Callable[[str], str]], getattr(mistune, "create_markdown")
)

_markdown: Callable[[str], str] = create_markdown(
    escape=False,
    plugins=["strikethrough", "table"],
)


def slugify(title: str) -> str:
    slug = title.lower()
    slug = (
        slug.replace("—", "")
        .replace("–", "")
        .replace(":", "")
        .replace(",", "")
        .replace(".", "")
    )
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def extract_preview(html: str, max_chars: int = 160) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return "—"
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars].rsplit(" ", 1)[0]
    return truncated + "…"


def parse_journal_text(text: str) -> list[Article]:
    sections = re.split(r"\n-{3,}\n", text)

    articles: list[Article] = []
    for section in sections:
        section = section.strip()
        if not section:
            continue

        match = re.search(r"^##\s+(.+?)$", section, re.MULTILINE)
        if not match:
            continue

        title = match.group(1).strip()
        slug = slugify(title)

        body_md = section[match.end() :].strip()
        body_html = _markdown(body_md)

        articles.append(
            {
                "title": title,
                "slug": slug,
                "body_html": body_html,
                "preview": extract_preview(body_html),
                "entry_number": len(articles) + 1,
            }
        )

    return articles


def parse_journal(filepath: str) -> list[Article]:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return parse_journal_text(f.read())
    except (FileNotFoundError, PermissionError):
        return []
