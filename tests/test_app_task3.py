# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportAny=false, reportUnannotatedClassAttribute=false, reportUnusedCallResult=false, reportUnusedParameter=false

import importlib.util
import queue
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest
from werkzeug.exceptions import NotFound


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"
WATCHER_FILE = APP_DIR / "watcher.py"
APP_FILE = APP_DIR / "app.py"


def load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_app_module(monkeypatch: pytest.MonkeyPatch, journal_path: Path, articles):
    fake_parser = types.ModuleType("parser")
    fake_parser.parse_journal = lambda _: articles

    listeners = []
    started_paths = []

    fake_watcher = types.ModuleType("watcher")
    fake_watcher.start_watcher = lambda path: started_paths.append(path)
    fake_watcher.add_listener = lambda q: listeners.append(q)
    fake_watcher.remove_listener = lambda q: listeners.remove(q)

    monkeypatch.setenv("JOURNAL_PATH", str(journal_path))
    monkeypatch.setitem(sys.modules, "parser", fake_parser)
    monkeypatch.setitem(sys.modules, "watcher", fake_watcher)

    module = load_module("gippity_task3_app", APP_FILE)
    return module, started_paths, listeners


def test_watcher_notifies_registered_listener():
    watcher = load_module("gippity_task3_watcher_notify", WATCHER_FILE)
    q = queue.Queue(maxsize=1)

    watcher.add_listener(q)
    try:
        watcher._JournalHandler().on_modified(SimpleNamespace(is_directory=False))
        assert q.get_nowait() == "reload"
    finally:
        watcher.remove_listener(q)


def test_start_watcher_only_starts_once(monkeypatch: pytest.MonkeyPatch):
    watcher = load_module("gippity_task3_watcher_start", WATCHER_FILE)

    class FakeObserver:
        def __init__(self):
            self.scheduled = []
            self.started = 0
            self.daemon = False

        def schedule(self, handler, path, recursive):
            self.scheduled.append((handler, path, recursive))

        def start(self):
            self.started += 1

    created = []

    def make_observer():
        observer = FakeObserver()
        created.append(observer)
        return observer

    monkeypatch.setattr(watcher, "Observer", make_observer)
    watcher._observer = None

    watcher.start_watcher("/tmp/journal-dir")
    watcher.start_watcher("/tmp/journal-dir")

    assert len(created) == 1
    assert created[0].started == 1
    assert created[0].daemon is True
    assert created[0].scheduled[0][1:] == ("/tmp/journal-dir", False)


def test_index_renders_articles_in_reverse_order(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    articles = [
        {
            "slug": "first",
            "title": "First",
            "body_html": "",
            "preview": "",
            "entry_number": 1,
        },
        {
            "slug": "second",
            "title": "Second",
            "body_html": "",
            "preview": "",
            "entry_number": 2,
        },
    ]
    journal_path = tmp_path / "JOURNAL.md"
    journal_path.write_text("", encoding="utf-8")
    module, started_paths, _ = load_app_module(monkeypatch, journal_path, articles)

    captured = {}

    def fake_render(template, **context):
        captured["template"] = template
        captured.update(context)
        return "rendered-index"

    monkeypatch.setattr(module, "render_template", fake_render)

    with module.app.test_request_context("/"):
        result = module.index()

    assert result == "rendered-index"
    assert captured["template"] == "index.html"
    assert [article["slug"] for article in captured["articles"]] == ["second", "first"]
    assert started_paths == [str(tmp_path.resolve())]


def test_article_route_sets_prev_and_next(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    articles = [
        {
            "slug": "first",
            "title": "First",
            "body_html": "",
            "preview": "",
            "entry_number": 1,
        },
        {
            "slug": "second",
            "title": "Second",
            "body_html": "",
            "preview": "",
            "entry_number": 2,
        },
        {
            "slug": "third",
            "title": "Third",
            "body_html": "",
            "preview": "",
            "entry_number": 3,
        },
    ]
    journal_path = tmp_path / "JOURNAL.md"
    journal_path.write_text("", encoding="utf-8")
    module, _, _ = load_app_module(monkeypatch, journal_path, articles)

    captured = {}

    def fake_render(template, **context):
        captured["template"] = template
        captured.update(context)
        return "rendered-article"

    monkeypatch.setattr(module, "render_template", fake_render)

    with module.app.test_request_context("/article/second"):
        result = module.article("second")

    assert result == "rendered-article"
    assert captured["template"] == "article.html"
    assert captured["article"]["slug"] == "second"
    assert captured["prev"]["slug"] == "first"
    assert captured["next"]["slug"] == "third"


def test_article_route_raises_404_for_unknown_slug(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    journal_path = tmp_path / "JOURNAL.md"
    journal_path.write_text("", encoding="utf-8")
    module, _, _ = load_app_module(monkeypatch, journal_path, [])

    with module.app.test_request_context("/article/missing"):
        with pytest.raises(NotFound):
            module.article("missing")


def test_events_stream_sends_connected_then_ping(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    journal_path = tmp_path / "JOURNAL.md"
    journal_path.write_text("", encoding="utf-8")
    module, _, listeners = load_app_module(monkeypatch, journal_path, [])

    class FakeListenerQueue:
        def __init__(self, maxsize=10):
            self.maxsize = maxsize

        def get(self, timeout):
            raise queue.Empty

    monkeypatch.setattr(module.queue, "Queue", FakeListenerQueue)

    client = module.app.test_client()
    response = client.get("/events", buffered=False)

    chunks = [next(response.response).decode(), next(response.response).decode()]
    response.close()

    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"
    assert chunks == ["data: connected\n\n", "data: ping\n\n"]
    assert listeners == []


def test_flask_app_registers_expected_routes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    journal_path = tmp_path / "JOURNAL.md"
    journal_path.write_text("", encoding="utf-8")
    module, _, _ = load_app_module(monkeypatch, journal_path, [])

    routes = {rule.rule for rule in module.app.url_map.iter_rules()}

    assert "/" in routes
    assert "/article/<slug>" in routes
    assert "/events" in routes
