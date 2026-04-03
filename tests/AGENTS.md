# AGENTS.md — tests/

## OVERVIEW

19 tests across two files with two completely different import strategies. Understand which pattern to use before adding tests.

## TWO TEST PATTERNS — USE THE RIGHT ONE

### Pattern A — `test_parser.py`: sys.path hack

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.parser import parse_journal_text
```

**Use when**: testing `parser.py` in isolation with no Flask/watcher involvement. Simple, direct.

**Don't use when**: testing anything that imports `parser` or `watcher` via the implicit relative import in `app.py` — the module names will collide.

### Pattern B — `test_app_task3.py`: importlib + sys.modules monkeypatching

```python
def load_module(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

def load_app_module(monkeypatch, journal_path, articles):
    fake_parser = types.ModuleType("parser")
    fake_parser.parse_journal = lambda _: articles
    fake_watcher = types.ModuleType("watcher")
    # ... wire fakes
    monkeypatch.setitem(sys.modules, "parser", fake_parser)
    monkeypatch.setitem(sys.modules, "watcher", fake_watcher)
    module = load_module("gippity_task3_app", APP_FILE)
    return module, started_paths, listeners
```

**Use when**: testing Flask routes, the SSE endpoint, or anything in `app.py`. The fakes intercept the implicit `from parser import` and `from watcher import` inside `app.py` before it executes.

**Key**: inject fakes into `sys.modules` **before** calling `load_module()` — `app.py` runs `start_watcher()` at import time and the module-level code resolves imports immediately.

## FIXTURES IN USE

| Fixture | Source | Used for |
|---------|--------|---------|
| `monkeypatch` | pytest built-in | Patching `sys.modules`, env vars, module attributes |
| `tmp_path` | pytest built-in | Temp journal file paths |
| `load_app_module()` | local helper | Wiring fake modules + loading app.py per test |

No `conftest.py` — all fixtures are inline per file.

## RUNNING TESTS

```bash
# From repo root only — sys.path hack in test_parser.py breaks from subdirs
python -m pytest tests/ -v
```

## ADDING NEW TESTS

- For `parser.py` logic → extend `test_parser.py` using Pattern A
- For routes / SSE / watcher → extend `test_app_task3.py` using Pattern B
- Use `module.app.test_request_context("/path")` for route tests
- Use `module.app.test_client()` for full HTTP tests (see `test_events_stream_sends_connected_then_ping`)
- Article dicts need all 5 fields: `slug`, `title`, `body_html`, `preview`, `entry_number`
