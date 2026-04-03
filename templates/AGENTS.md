# AGENTS.md — templates/

## OVERVIEW

Three Jinja2 templates. `base.html` is the layout; `index.html` and `article.html` extend it.

## TEMPLATE VARIABLES

### `index.html`
Rendered by `app.py:index()` with:
```python
articles  # list[Article], already reversed (newest first)
```
Each article: `slug`, `title`, `entry_number`, `preview` (plain text ≤160 chars).

### `article.html`
Rendered by `app.py:article()` with:
```python
article   # Article dict for the current entry
prev      # Article dict or None  (previous in file order, i.e. older)
next      # Article dict or None  (next in file order, i.e. newer)
```

## CRITICAL: `body_html | safe`

`article.html` renders the body as:
```html
{{ article.body_html | safe }}
```

The `safe` filter **must stay** — `body_html` is pre-rendered HTML from mistune. Removing it double-escapes every `<p>`, `<strong>`, etc. and breaks the article view entirely.

This is safe because the HTML is generated from a local markdown file the owner controls, not from user input.

## SSE AUTO-RELOAD

The live-reload JavaScript lives in `base.html` and is included on every page:

```javascript
const es = new EventSource('/events');
es.onmessage = function(e) {
  if (e.data === 'reload') { window.location.reload(); }
};
es.onerror = function() {
  setTimeout(function() { window.location.reload(); }, 3000);
};
```

No opt-out per page — it's always active. If you need a page without it, add a `{% block scripts %}{% endblock %}` override.

## STATIC ASSETS

CSS is linked via `url_for`:
```html
{{ url_for('static', filename='css/style.css') }}
```

Never hardcode `/static/css/style.css` — `url_for` handles path prefix changes automatically.

## DARK MODE

No template logic involved. Dark mode is pure CSS via `@media (prefers-color-scheme: dark)` in `style.css`. To change dark palette, edit `static/css/style.css` only.

## JINJA2 BLOCKS

| Block | Defined in | Purpose |
|-------|-----------|---------|
| `title` | `base.html` | `<title>` content |
| `content` | `base.html` | Main page body |

Both child templates override both blocks.
