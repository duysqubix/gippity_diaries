# AGENTS.md — app/

## OVERVIEW

Flask app + markdown parser + file watcher. Three modules, no __init__.py exports, no package install required.

## FILES

| File | Role |
|------|------|
| `app.py` | Flask routes (`/`, `/article/<slug>`, `/events`), entry point |
| `parser.py` | Reads + parses JOURNAL.md → `list[Article]` |
| `watcher.py` | watchdog observer + SSE listener registry |
| `__init__.py` | Empty — this package exposes nothing |

## CRITICAL: IMPORT CONVENTION

`app.py` uses **implicit relative imports** — no dots, no package prefix:

```python
from parser import parse_journal          # NOT from app.parser
from watcher import add_listener, ...     # NOT from app.watcher
```

This only works because `app.py` runs as `__main__` (Python adds its own dir to `sys.path`). **Never change these to `from app.parser import ...`** without also updating the Dockerfile CMD and all test mocking.

Tests work around this differently — see `tests/AGENTS.md`.

## PYRIGHT SUPPRESSIONS

Every `app/` file starts with a `# pyright: reportMissingImports=false,...` pragma. **Keep it.** The implicit imports above would cause false pyright errors without it. Do not remove or move the line.

## MODULE-LEVEL SIDE EFFECT

`app.py` line 20 calls `start_watcher()` at import time:

```python
_journal_dir = os.path.dirname(os.path.abspath(JOURNAL_PATH))
start_watcher(_journal_dir)
```

This starts a background watchdog thread the moment the module is imported. Tests must mock `watcher` in `sys.modules` **before** importing `app.py` — see `tests/test_app_task3.py:load_app_module()`.

## SSE STREAMING PATTERN

`watcher.py` holds a module-level `_listeners: list[queue.Queue]` registry. Each `/events` client connection gets its own `Queue` via `add_listener()`. When watchdog fires `on_modified`, it iterates the registry and `put_nowait("reload")` to each queue. The SSE generator in `app.py` drains its queue and yields SSE frames. On disconnect (`GeneratorExit`), `finally` calls `remove_listener()`.

Key numbers: queue `maxsize=10`, keepalive `timeout=20s`.

## PARSER — WHAT IT DOES AND DOESN'T DO

- Splits on `\n-{3,}\n` (3+ dashes on own line)
- Extracts first `## heading` per section as `title`
- Renders everything below that heading as `body_html` (mistune, `escape=False`)
- Generates a URL-safe `slug` from the title
- Returns `list[Article]` in **file order** (index route reverses it for display)
- **No caching** — re-reads disk on every call. Intentional.
- Returns `[]` silently on `FileNotFoundError` / `PermissionError`

## ARTICLE TYPEDDICT

```python
class Article(TypedDict):
    title: str        # Raw heading text: "March 24, 2026 — 12:46am"
    slug: str         # URL-safe: "march-24-2026-1246am"
    body_html: str    # Rendered HTML, may contain any tags
    preview: str      # Plain-text excerpt ≤160 chars, "—" if body is empty
    entry_number: int # 1-based position in file
```

## ANTI-PATTERNS

- Don't add `debug=True` to `app.run()` in the Docker build — it enables the Werkzeug reloader which conflicts with the watchdog thread.
- Don't call `start_watcher()` more than once — it's idempotent but the guard is a simple `is not None` check on a module global; reloading the module resets it.
- Don't make `_listeners` a set — order doesn't matter but `queue.Queue` isn't hashable.
