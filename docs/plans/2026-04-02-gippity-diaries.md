# Gippity's Diaries Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers/executing-plans to implement this plan task-by-task.

**Goal:** Build a Docker-hosted, mobile-optimized blog web app that parses `/home/duys/.openclaw/workspace/JOURNAL.md` into individual articles and live-reloads the browser when the file changes.

**Architecture:** Flask serves two routes (index + article detail). A `watchdog` file watcher monitors the journal file in a background thread; when the file changes it notifies all connected SSE clients, which trigger a browser `location.reload()`. The journal file is mounted read-only as a Docker volume. No database — every request re-reads and re-parses the file.

**Tech Stack:** Python 3.11, Flask 3, mistune 3 (markdown), watchdog 4, Jinja2 templates, vanilla CSS (no framework, mobile-first)

---

## Journal Entry Format (reference)

The file begins with a `# JOURNAL.md` heading and subtitle, followed by entries separated by `---`. Each entry starts with `## [Day], [Year] — [Time]` and ends with `— G`. The parser must handle this specific structure.

```
# JOURNAL.md — Gippity's Journal
_Not a log. Not documentation. Mine._

## March 24, 2026 — 12:46am

[body content with markdown]

— G

---

## March 24, 2026 — 5:00am
...
```

---

## File Structure

```
gippity_diaries/
├── app/
│   ├── __init__.py        (empty)
│   ├── app.py             (Flask routes + SSE endpoint)
│   ├── parser.py          (journal markdown parser)
│   └── watcher.py         (watchdog file watcher + SSE listener registry)
├── templates/
│   ├── base.html          (shared layout + SSE JS)
│   ├── index.html         (article list)
│   └── article.html       (single article view)
├── static/
│   └── css/
│       └── style.css      (mobile-first warm diary aesthetic)
├── tests/
│   └── test_parser.py     (parser unit tests)
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

### Task 1: Project scaffold

**Files:**
- Create: `requirements.txt`
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `app/__init__.py`
- Create: `tests/__init__.py`

**Step 1: Create directory structure**
```bash
mkdir -p app templates static/css tests
touch app/__init__.py tests/__init__.py
```

**Step 2: Write requirements.txt**
```
Flask==3.0.3
mistune==3.0.2
watchdog==4.0.1
```

**Step 3: Write Dockerfile**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["python", "app/app.py"]
```

**Step 4: Write docker-compose.yml**
```yaml
services:
  gippity-diaries:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - /home/duys/.openclaw/workspace/JOURNAL.md:/journal/JOURNAL.md:ro
    environment:
      - JOURNAL_PATH=/journal/JOURNAL.md
    restart: unless-stopped
```

**Step 5: Verify files exist**
```bash
ls -la requirements.txt Dockerfile docker-compose.yml app/__init__.py
```
Expected: all 4 files listed

**Step 6: Commit**
```bash
git init && git add . && git commit -m "chore: initialize project scaffold"
```

---

### Task 2: Journal parser

**Files:**
- Create: `app/parser.py`
- Create: `tests/test_parser.py`

**Step 1: Write the failing tests**

```python
# tests/test_parser.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
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
    assert articles[0]['title'] == 'March 24, 2026 — 12:46am'

def test_second_article_title():
    articles = parse_journal_text(SAMPLE)
    assert articles[1]['title'] == 'March 24, 2026 — 5:00am'

def test_articles_have_slugs():
    articles = parse_journal_text(SAMPLE)
    for a in articles:
        assert 'slug' in a
        assert len(a['slug']) > 0

def test_articles_have_html_body():
    articles = parse_journal_text(SAMPLE)
    assert '<p>' in articles[0]['body_html']

def test_articles_have_bold_rendered():
    articles = parse_journal_text(SAMPLE)
    assert '<strong>' in articles[0]['body_html']

def test_articles_have_preview():
    articles = parse_journal_text(SAMPLE)
    assert 'preview' in articles[0]
    assert len(articles[0]['preview']) > 0

def test_articles_have_entry_numbers():
    articles = parse_journal_text(SAMPLE)
    assert articles[0]['entry_number'] == 1
    assert articles[1]['entry_number'] == 2

def test_slug_is_url_safe():
    articles = parse_journal_text(SAMPLE)
    import re
    for a in articles:
        assert re.match(r'^[a-z0-9\-]+$', a['slug']), f"Bad slug: {a['slug']}"
```

**Step 2: Run test to verify it fails**
```bash
python -m pytest tests/test_parser.py -v
```
Expected: ImportError or similar — `parse_journal_text` doesn't exist yet

**Step 3: Write the parser implementation**

```python
# app/parser.py
import re
import mistune
from typing import Optional

_markdown = mistune.create_markdown(
    escape=False,
    plugins=['strikethrough', 'table'],
)


def slugify(title: str) -> str:
    """Convert 'March 24, 2026 — 12:46am' to 'march-24-2026-1246am'."""
    slug = title.lower()
    # Replace em dash and common punctuation
    slug = slug.replace('—', '').replace('–', '').replace(':', '').replace(',', '').replace('.', '')
    # Replace any non-alphanumeric except spaces with nothing
    slug = re.sub(r'[^\w\s-]', '', slug)
    # Collapse whitespace to hyphens
    slug = re.sub(r'[\s_]+', '-', slug)
    # Collapse multiple hyphens
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug


def extract_preview(html: str, max_chars: int = 160) -> str:
    """Strip HTML tags and truncate to max_chars for a plain-text preview."""
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars].rsplit(' ', 1)[0]
    return truncated + '…'


def parse_journal_text(text: str) -> list[dict]:
    """
    Parse journal markdown text into a list of article dicts.

    Each article dict contains:
      - title: str          "March 24, 2026 — 12:46am"
      - slug: str           "march-24-2026-1246am"
      - body_html: str      rendered HTML of the body
      - preview: str        plain-text excerpt (~160 chars)
      - entry_number: int   1-based position in the file
    """
    # Split on horizontal rules (--- or ----)
    sections = re.split(r'\n-{3,}\n', text)

    articles = []
    for section in sections:
        section = section.strip()
        if not section:
            continue

        # Must contain a ## heading to be a journal entry
        match = re.match(r'^##\s+(.+?)$', section, re.MULTILINE)
        if not match:
            continue

        title = match.group(1).strip()
        slug = slugify(title)

        # Body = everything after the heading line
        body_md = section[match.end():].strip()
        body_html = _markdown(body_md)

        articles.append({
            'title': title,
            'slug': slug,
            'body_html': body_html,
            'preview': extract_preview(body_html),
        })

    # Assign 1-based entry numbers (preserving file order)
    for i, article in enumerate(articles, 1):
        article['entry_number'] = i

    return articles


def parse_journal(filepath: str) -> list[dict]:
    """Read and parse a journal file. Returns [] if file not found."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return parse_journal_text(f.read())
    except (FileNotFoundError, PermissionError):
        return []
```

**Step 4: Run tests — all must pass**
```bash
python -m pytest tests/test_parser.py -v
```
Expected: 9 tests PASSED

**Step 5: Commit**
```bash
git add app/parser.py tests/test_parser.py
git commit -m "feat: add journal markdown parser with full test coverage"
```

---

### Task 3: File watcher + Flask app

**Files:**
- Create: `app/watcher.py`
- Create: `app/app.py`

**Step 1: Write the file watcher**

```python
# app/watcher.py
"""
Watchdog-based file watcher that notifies SSE listeners when the journal changes.
"""
import queue
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

_listeners: list[queue.Queue] = []
_lock = threading.Lock()
_observer: Observer | None = None


class _JournalHandler(FileSystemEventHandler):
    def _notify(self, event):
        if not event.is_directory:
            with _lock:
                for q in _listeners[:]:
                    try:
                        q.put_nowait('reload')
                    except queue.Full:
                        pass  # Skip lagging clients

    on_modified = _notify
    on_created = _notify


def add_listener(q: queue.Queue) -> None:
    with _lock:
        _listeners.append(q)


def remove_listener(q: queue.Queue) -> None:
    with _lock:
        try:
            _listeners.remove(q)
        except ValueError:
            pass


def start_watcher(watch_path: str) -> None:
    """Start the background file watcher. Safe to call multiple times."""
    global _observer
    if _observer is not None:
        return
    handler = _JournalHandler()
    _observer = Observer()
    _observer.schedule(handler, path=watch_path, recursive=False)
    _observer.daemon = True
    _observer.start()
```

**Step 2: Write the Flask app**

```python
# app/app.py
import os
import queue

from flask import Flask, render_template, Response, abort

from parser import parse_journal
from watcher import start_watcher, add_listener, remove_listener

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'),
    static_folder=os.path.join(os.path.dirname(__file__), '..', 'static'),
)

JOURNAL_PATH = os.environ.get('JOURNAL_PATH', '/journal/JOURNAL.md')

# Start file watcher pointed at the journal's directory
_journal_dir = os.path.dirname(os.path.abspath(JOURNAL_PATH))
start_watcher(_journal_dir)


@app.route('/')
def index():
    articles = list(reversed(parse_journal(JOURNAL_PATH)))
    return render_template('index.html', articles=articles)


@app.route('/article/<slug>')
def article(slug: str):
    articles = parse_journal(JOURNAL_PATH)
    art = next((a for a in articles if a['slug'] == slug), None)
    if art is None:
        abort(404)
    # Prev/next navigation (in file order, so reversed for display)
    idx = articles.index(art)
    prev_art = articles[idx - 1] if idx > 0 else None
    next_art = articles[idx + 1] if idx < len(articles) - 1 else None
    return render_template('article.html', article=art, prev=prev_art, next=next_art)


@app.route('/events')
def events():
    """Server-Sent Events endpoint. Sends 'reload' when the journal file changes."""
    def stream():
        q: queue.Queue = queue.Queue(maxsize=10)
        add_listener(q)
        try:
            yield 'data: connected\n\n'
            while True:
                try:
                    msg = q.get(timeout=20)
                    yield f'data: {msg}\n\n'
                except queue.Empty:
                    yield 'data: ping\n\n'  # keepalive
        except GeneratorExit:
            pass
        finally:
            remove_listener(q)

    return Response(
        stream(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        },
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)
```

**Step 3: Verify app starts locally**
```bash
JOURNAL_PATH=/home/duys/.openclaw/workspace/JOURNAL.md python app/app.py &
sleep 2
curl -s http://localhost:8080/ | head -5
kill %1
```
Expected: HTML output starting with `<!DOCTYPE html>` or `<html`

**Step 4: Commit**
```bash
git add app/app.py app/watcher.py
git commit -m "feat: add Flask app with SSE live-reload and file watcher"
```

---

### Task 4: HTML templates

**Files:**
- Create: `templates/base.html`
- Create: `templates/index.html`
- Create: `templates/article.html`

**Step 1: Write base.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}Gippity's Diaries{% endblock %}</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
  <header class="site-header">
    <a href="/" class="site-title">Gippity's Diaries</a>
    <p class="site-tagline">Not a log. Not documentation. Mine.</p>
  </header>

  <main class="main-content">
    {% block content %}{% endblock %}
  </main>

  <footer class="site-footer">
    <p>— G</p>
  </footer>

  <script>
    // Live reload via Server-Sent Events
    (function () {
      const es = new EventSource('/events');
      es.onmessage = function (e) {
        if (e.data === 'reload') {
          window.location.reload();
        }
      };
      es.onerror = function () {
        // Reconnect after 3s on error
        setTimeout(function () {
          window.location.reload();
        }, 3000);
      };
    })();
  </script>
</body>
</html>
```

**Step 2: Write index.html**

```html
{% extends "base.html" %}
{% block title %}Gippity's Diaries{% endblock %}
{% block content %}
  {% if articles %}
    <ul class="article-list">
      {% for article in articles %}
        <li class="article-card">
          <a href="{{ url_for('article', slug=article.slug) }}" class="article-card-link">
            <span class="entry-number">Entry {{ article.entry_number }}</span>
            <h2 class="article-title">{{ article.title }}</h2>
            <p class="article-preview">{{ article.preview }}</p>
          </a>
        </li>
      {% endfor %}
    </ul>
  {% else %}
    <p class="empty-state">No entries yet.</p>
  {% endif %}
{% endblock %}
```

**Step 3: Write article.html**

```html
{% extends "base.html" %}
{% block title %}{{ article.title }} — Gippity's Diaries{% endblock %}
{% block content %}
  <article class="article">
    <header class="article-header">
      <span class="entry-number">Entry {{ article.entry_number }}</span>
      <h1 class="article-title">{{ article.title }}</h1>
    </header>

    <div class="article-body">
      {{ article.body_html | safe }}
    </div>

    <nav class="article-nav">
      {% if prev %}
        <a href="{{ url_for('article', slug=prev.slug) }}" class="nav-prev">
          <span class="nav-label">← Previous</span>
          <span class="nav-title">{{ prev.title }}</span>
        </a>
      {% else %}
        <span></span>
      {% endif %}
      {% if next %}
        <a href="{{ url_for('article', slug=next.slug) }}" class="nav-next">
          <span class="nav-label">Next →</span>
          <span class="nav-title">{{ next.title }}</span>
        </a>
      {% endif %}
    </nav>

    <div class="back-link">
      <a href="/">← All Entries</a>
    </div>
  </article>
{% endblock %}
```

**Step 4: Verify pages load locally**
```bash
JOURNAL_PATH=/home/duys/.openclaw/workspace/JOURNAL.md python app/app.py &
sleep 2
curl -s http://localhost:8080/ | grep -c "article-card"
curl -s http://localhost:8080/article/march-24-2026-1246am | grep -c "article-body"
kill %1
```
Expected: first command prints `11`, second prints `1`

**Step 5: Commit**
```bash
git add templates/
git commit -m "feat: add Jinja2 templates for index and article pages"
```

---

### Task 5: CSS — mobile-first warm diary aesthetic

**Files:**
- Create: `static/css/style.css`

Design tokens:
- Background: `#faf8f4` (warm cream)
- Text: `#2c2825` (warm near-black)
- Accent: `#7c5c3a` (aged leather brown)
- Muted: `#9e9188` (warm gray)
- Border: `#e8e0d5` (very light warm gray)
- Font body: Georgia, 'Times New Roman', serif
- Font UI: system-ui, -apple-system, sans-serif
- Max width: 680px
- Base font size: 18px (mobile), comfortable reading

**Write static/css/style.css:**

```css
/* ===== Reset & Base ===== */
*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

:root {
  --bg: #faf8f4;
  --surface: #f3ede6;
  --text: #2c2825;
  --accent: #7c5c3a;
  --muted: #9e9188;
  --border: #e8e0d5;
  --max-width: 680px;
  --font-serif: Georgia, 'Times New Roman', serif;
  --font-sans: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

html {
  font-size: 18px;
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-serif);
  line-height: 1.7;
  -webkit-text-size-adjust: 100%;
}

body {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

a {
  color: var(--accent);
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}

/* ===== Layout ===== */
.site-header,
.main-content,
.site-footer {
  width: 100%;
  max-width: var(--max-width);
  margin: 0 auto;
  padding: 0 1.25rem;
}

/* ===== Header ===== */
.site-header {
  padding-top: 2.5rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: 2rem;
  text-align: center;
}

.site-title {
  font-family: var(--font-serif);
  font-size: 1.75rem;
  font-weight: normal;
  color: var(--text);
  letter-spacing: 0.01em;
}

.site-title:hover {
  text-decoration: none;
  color: var(--accent);
}

.site-tagline {
  margin-top: 0.4rem;
  font-style: italic;
  font-size: 0.9rem;
  color: var(--muted);
}

/* ===== Main ===== */
.main-content {
  flex: 1;
  padding-bottom: 3rem;
}

/* ===== Article List ===== */
.article-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.article-card {
  border: 1px solid var(--border);
  border-radius: 8px;
  background: white;
  overflow: hidden;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.article-card:hover {
  border-color: var(--accent);
  box-shadow: 0 2px 12px rgba(124, 92, 58, 0.08);
}

.article-card-link {
  display: block;
  padding: 1.25rem 1.5rem;
  color: inherit;
  text-decoration: none;
}

.entry-number {
  display: block;
  font-family: var(--font-sans);
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 0.35rem;
}

.article-list .article-title {
  font-size: 1.05rem;
  font-weight: normal;
  color: var(--text);
  margin-bottom: 0.5rem;
  line-height: 1.4;
}

.article-preview {
  font-size: 0.9rem;
  color: var(--muted);
  line-height: 1.6;
  font-family: var(--font-sans);
}

/* ===== Empty state ===== */
.empty-state {
  text-align: center;
  color: var(--muted);
  font-style: italic;
  margin-top: 3rem;
}

/* ===== Article Page ===== */
.article {
  padding-top: 0.5rem;
}

.article-header {
  margin-bottom: 2rem;
  padding-bottom: 1.25rem;
  border-bottom: 1px solid var(--border);
}

.article-header .article-title {
  font-size: 1.6rem;
  font-weight: normal;
  line-height: 1.3;
  margin-top: 0.5rem;
}

/* ===== Article Body (rendered markdown) ===== */
.article-body {
  font-size: 1rem;
  line-height: 1.8;
  color: var(--text);
}

.article-body p {
  margin-bottom: 1.25rem;
}

.article-body strong {
  font-weight: 700;
  color: var(--text);
}

.article-body em {
  font-style: italic;
}

.article-body h1,
.article-body h2,
.article-body h3 {
  margin-top: 2rem;
  margin-bottom: 0.75rem;
  font-weight: normal;
  color: var(--text);
}

.article-body ul,
.article-body ol {
  margin-left: 1.5rem;
  margin-bottom: 1.25rem;
}

.article-body li {
  margin-bottom: 0.35rem;
}

.article-body blockquote {
  border-left: 3px solid var(--accent);
  padding-left: 1rem;
  margin: 1.5rem 0;
  color: var(--muted);
  font-style: italic;
}

.article-body hr {
  border: none;
  border-top: 1px solid var(--border);
  margin: 2rem 0;
}

.article-body code {
  font-family: 'Courier New', monospace;
  font-size: 0.85em;
  background: var(--surface);
  padding: 0.1em 0.35em;
  border-radius: 3px;
}

.article-body pre {
  background: var(--surface);
  padding: 1rem;
  border-radius: 6px;
  overflow-x: auto;
  margin-bottom: 1.25rem;
  font-size: 0.85rem;
}

/* The signature line "— G" */
.article-body p:last-child {
  margin-bottom: 0;
}

/* ===== Article Navigation ===== */
.article-nav {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  margin-top: 3rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--border);
}

.nav-prev,
.nav-next {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  flex: 1;
  text-decoration: none;
  color: var(--text);
  font-size: 0.9rem;
}

.nav-next {
  text-align: right;
}

.nav-label {
  font-family: var(--font-sans);
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--accent);
  font-weight: 600;
}

.nav-title {
  color: var(--muted);
  font-size: 0.85rem;
}

.nav-prev:hover .nav-title,
.nav-next:hover .nav-title {
  color: var(--accent);
}

.back-link {
  margin-top: 2rem;
  font-family: var(--font-sans);
  font-size: 0.9rem;
}

/* ===== Footer ===== */
.site-footer {
  text-align: center;
  padding-top: 1.5rem;
  padding-bottom: 2rem;
  border-top: 1px solid var(--border);
  margin-top: auto;
  color: var(--muted);
  font-style: italic;
  font-size: 0.9rem;
}

/* ===== Mobile tweaks (already mobile-first, these enhance larger screens) ===== */
@media (min-width: 480px) {
  html {
    font-size: 19px;
  }

  .article-list .article-title {
    font-size: 1.1rem;
  }

  .article-header .article-title {
    font-size: 1.9rem;
  }
}

@media (min-width: 640px) {
  .site-header {
    padding-top: 3rem;
  }

  .article-card-link {
    padding: 1.5rem 1.75rem;
  }
}
```

**Step 4: Verify CSS is served**
```bash
JOURNAL_PATH=/home/duys/.openclaw/workspace/JOURNAL.md python app/app.py &
sleep 2
curl -s http://localhost:8080/static/css/style.css | head -3
kill %1
```
Expected: outputs `/* ===== Reset & Base ===== */` or similar CSS

**Step 5: Commit**
```bash
git add static/css/style.css
git commit -m "feat: add mobile-first CSS with warm diary aesthetic"
```

---

### Task 6: Docker build & end-to-end verification

**Step 1: Build the Docker image**
```bash
docker build -t gippity-diaries .
```
Expected: `Successfully built` (or `Successfully tagged gippity-diaries:latest`)

**Step 2: Run with docker-compose**
```bash
docker compose up -d
sleep 3
docker compose ps
```
Expected: container shows `running` / `Up`

**Step 3: Verify index page**
```bash
curl -s http://localhost:8080/ | grep -c "article-card"
```
Expected: `11` (one per journal entry)

**Step 4: Verify an article page loads**
```bash
curl -s http://localhost:8080/article/march-24-2026-1246am | grep "entry-number"
```
Expected: line containing `Entry 1`

**Step 5: Verify SSE endpoint responds**
```bash
curl -s -N --max-time 3 http://localhost:8080/events
```
Expected: `data: connected` followed by `data: ping` within 3 seconds

**Step 6: Verify 404 for unknown slug**
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/article/does-not-exist
```
Expected: `404`

**Step 7: Manual live-reload test**
```
1. Open http://localhost:8080/ in a browser
2. In another terminal: echo "" >> /home/duys/.openclaw/workspace/JOURNAL.md
3. Browser should auto-reload within 1-2 seconds
4. Verify new content appears if you added an entry
```

**Step 8: Final commit**
```bash
git add .
git commit -m "chore: verified Docker deployment and live-reload"
```

---

## Success Criteria

- [ ] `python -m pytest tests/` — all tests pass
- [ ] `docker compose up` — container starts without errors
- [ ] `http://localhost:8080/` — shows all 11 journal entries as cards
- [ ] `http://localhost:8080/article/<slug>` — renders full entry with markdown
- [ ] Editing JOURNAL.md causes browser to reload within ~2 seconds
- [ ] Site is readable and usable on a 375px-wide screen (iPhone SE)
- [ ] Prev/next navigation works between articles
