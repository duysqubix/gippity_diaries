import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.parser import parse_journal_text

SAMPLE = """# JOURNAL.md — Gippity's Journal

_Not a log. Not documentation. Mine._

## March 24, 2026 — 12:46am

First entry content here.

**Bold text** and a list:
- item one
- item two

— G

---

## March 24, 2026 — 5:00am

Second entry content here.

— G

---
"""


def test_parse_returns_two_articles():
    articles = parse_journal_text(SAMPLE)
    assert len(articles) == 2, f"Expected 2, got {len(articles)}"


def test_first_article_title():
    articles = parse_journal_text(SAMPLE)
    assert articles[0]["title"] == "March 24, 2026 — 12:46am"


def test_second_article_title():
    articles = parse_journal_text(SAMPLE)
    assert articles[1]["title"] == "March 24, 2026 — 5:00am"


def test_articles_have_slugs():
    articles = parse_journal_text(SAMPLE)
    for a in articles:
        assert "slug" in a
        assert len(a["slug"]) > 0


def test_articles_have_html_body():
    articles = parse_journal_text(SAMPLE)
    assert "<p>" in articles[0]["body_html"]


def test_articles_have_bold_rendered():
    articles = parse_journal_text(SAMPLE)
    assert "<strong>" in articles[0]["body_html"]


def test_articles_have_preview():
    articles = parse_journal_text(SAMPLE)
    assert "preview" in articles[0]
    assert len(articles[0]["preview"]) > 0


def test_articles_have_entry_numbers():
    articles = parse_journal_text(SAMPLE)
    assert articles[0]["entry_number"] == 1
    assert articles[1]["entry_number"] == 2


def test_slug_is_url_safe():
    articles = parse_journal_text(SAMPLE)
    import re

    for a in articles:
        assert re.match(r"^[a-z0-9\-]+$", a["slug"]), f"Bad slug: {a['slug']}"
