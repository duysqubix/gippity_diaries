# AGENTS.md — Gippity's Diaries

**Generated:** 2026-04-03
**Commit:** 73bc5fc | **Branch:** master

## OVERVIEW

Mobile-first Flask blog that renders any markdown journal file into articles and live-reloads connected browsers when the file changes. No database — every request re-reads and re-parses the file. Docker-deployed.

## STRUCTURE

```
gippity_diaries/
├── app/           # Flask app, parser, file watcher — see app/AGENTS.md
├── templates/     # Jinja2 templates (base, index, article) — see templates/AGENTS.md
├── static/css/    # Single CSS file; mobile-first, CSS custom properties for theming
├── tests/         # Two distinct test patterns — see tests/AGENTS.md
├── example/       # Example JOURNAL.md — used by default when no .env is configured
├── .env.example   # Copy to .env and set JOURNAL_FILE to your own markdown file
├── Dockerfile     # python:3.11-slim, runs `python app/app.py`
├── docker-compose.yml
└── requirements.txt
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add/change a route | `app/app.py` | |
| Change how markdown is parsed | `app/parser.py` | `parse_journal_text()` |
| Change what triggers a browser reload | `app/watcher.py` | `_JournalHandler` |
| Change page layout/markup | `templates/base.html` | |
| Change colors, fonts, spacing | `static/css/style.css` | Edit `:root` vars |
| Change dark mode palette | `static/css/style.css` | `@media (prefers-color-scheme: dark)` block |
| Add a Python dependency | `requirements.txt` | Rebuild Docker image |
| Change which file is watched | `.env` | `JOURNAL_FILE` path |

## COMMANDS

```bash
# Run locally (without Docker)
JOURNAL_PATH=/path/to/your/JOURNAL.md python app/app.py

# Run in Docker (port 8080 on host → 8080 in container)
docker compose up -d

# Rebuild after code changes
docker compose up -d --build

# Run all tests
python -m pytest tests/ -v

# Run a single test file
python -m pytest tests/test_parser.py -v

# Run a single test function
python -m pytest tests/test_parser.py::test_first_article_title -v

# Run tests matching a keyword
python -m pytest tests/ -k "slug" -v
```

There is no linter, formatter, or type checker configured. No `pyproject.toml`, `ruff.toml`, `.flake8`, or `mypy.ini` exists. Follow the style conventions below by hand.

## CODE STYLE

### Imports

Three groups separated by blank lines: stdlib → third-party → local. Not strictly alphabetical within groups. `from X import` items are alphabetical (see `app/app.py:6`).

```python
import os                                          # stdlib
import queue

from flask import Flask, Response, abort           # third-party

from parser import parse_journal                   # local (implicit relative)
from watcher import add_listener, remove_listener
```

**Critical**: `app/app.py` uses implicit relative imports (`from parser import ...`, NOT `from app.parser import ...`). This only works because `app.py` runs as `__main__`. Never change to absolute imports without updating the Dockerfile CMD and all test mocking.

### Strings

Double quotes everywhere. Single quotes do not appear in this codebase.

### Type Hints

Modern syntax only. No `typing.List`, `typing.Optional`, or `typing.Union`.

```python
list[Article]          # not List[Article]
Observer | None        # not Optional[Observer]
Callable[[str], str]   # from collections.abc, not typing
```

`TypedDict` is used for the `Article` type in `app/parser.py:8-13`. All public functions have parameter and return type hints.

### Naming

| Convention | Where |
|------------|-------|
| `snake_case` | Functions, variables, parameters |
| `PascalCase` | Classes (`Article`, `_JournalHandler`) |
| `UPPER_CASE` | Module-level constants (`JOURNAL_PATH`, `SAMPLE`, `ROOT`) |
| `_leading_underscore` | Private/internal (`_listeners`, `_lock`, `_markdown`, `_JournalHandler`) |

### Formatting

- Soft line limit ~88 chars. Pyright pragmas on line 1 are exempt.
- Trailing commas in all multi-line structures (function args, dicts, lists).
- No trailing commas in single-line structures or TypedDict fields.
- Two blank lines between top-level definitions. One blank line inside classes.

### Error Handling

Catch specific exceptions only. Silent fallback with `pass` for expected errors. No bare `except:`. No re-raising. No logging (this app has none).

```python
except (FileNotFoundError, PermissionError):  # specific, returns []
except queue.Full:                             # expected, pass
except ValueError:                             # expected, pass
except GeneratorExit:                          # client disconnect, pass
except queue.Empty:                            # timeout, send keepalive
```

### Pyright Pragmas

Files that use implicit relative imports or untyped third-party libs start with a `# pyright: reportMissingImports=false,...` pragma on line 1. Suppressions are file-specific. **Do not remove these.** Files with clean types (`parser.py`, `test_parser.py`) have no pragma.

## TESTING

19 tests across two files using **two different import strategies**:

| File | Pattern | Use for |
|------|---------|---------|
| `test_parser.py` | `sys.path.insert` + `from app.parser import` | Parser logic in isolation |
| `test_app_task3.py` | `importlib` + `sys.modules` monkeypatching | Flask routes, SSE, watcher |

When adding tests: extend the existing file that matches your target. Use `test_parser.py` for parser changes. Use `test_app_task3.py` for anything touching `app.py` or `watcher.py`. Article dicts in tests need all 5 fields: `slug`, `title`, `body_html`, `preview`, `entry_number`.

Tests must run from the repo root: `python -m pytest tests/ -v`.

## ANTI-PATTERNS

- **Don't add `---` inside a journal entry body.** The parser splits on it — the entry gets silently truncated.
- **Don't add `##` headings inside an entry body.** Parser treats them as new article starts.
- **Don't use two journal entries with identical titles.** Produces duplicate slugs; second entry is unreachable.
- **Don't cache parsed articles at module level.** Would break live reload.
- **Don't use `from app.parser import ...`** in `app/app.py` — see Imports section above.
- **Don't suppress types with `as any` or `# type: ignore`.** Add to the file-level pyright pragma if needed.

## JOURNAL FORMAT

```
## [Any title here]        ← becomes article title + URL slug

[Body — any markdown]

---                        ← entry separator (3+ dashes, own line)
```

Preamble before the first `##` is silently ignored. See `app/parser.py` for exact regex.
