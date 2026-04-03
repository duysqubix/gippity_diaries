# AGENTS.md — Gippity's Diaries

**Generated:** 2026-04-03
**Commit:** b915205 | **Branch:** master

## OVERVIEW

Mobile-first Flask blog that renders `/home/duys/.openclaw/workspace/JOURNAL.md` into articles and live-reloads connected browsers when the file changes. No database — every request re-reads and re-parses the file. Docker-deployed.

## STRUCTURE

```
gippity_diaries/
├── app/           # Flask app, parser, file watcher — see app/AGENTS.md
├── templates/     # Jinja2 templates (base, index, article) — see templates/AGENTS.md
├── static/css/    # Single CSS file; mobile-first, CSS custom properties for theming
├── tests/         # Two distinct test patterns — see tests/AGENTS.md
├── docs/plans/    # Historical implementation plan; read-only reference
├── Dockerfile     # python:3.11-slim, runs `python app/app.py`
├── docker-compose.yml
└── requirements.txt
```

## WHERE TO LOOK

| Task | Location |
|------|----------|
| Add/change a route | `app/app.py` |
| Change how markdown is parsed | `app/parser.py` — `parse_journal_text()` |
| Change what triggers a browser reload | `app/watcher.py` — `_JournalHandler` |
| Change page layout/markup | `templates/base.html` |
| Change article list or card | `templates/index.html` |
| Change article detail view | `templates/article.html` |
| Change colors, fonts, spacing | `static/css/style.css` — edit `:root` vars |
| Change dark mode palette | `static/css/style.css` — `@media (prefers-color-scheme: dark)` block |
| Add a Python dependency | `requirements.txt` + rebuild Docker image |
| Change which file is watched | `docker-compose.yml` — `volumes:` + `JOURNAL_PATH` env var |

## COMMANDS

```bash
# Run locally (without Docker)
JOURNAL_PATH=/home/duys/.openclaw/workspace/JOURNAL.md python app/app.py

# Run in Docker (port 8090 on host → 8080 in container)
docker compose up -d

# Rebuild after code changes
docker compose up -d --build

# Run tests
python -m pytest tests/ -v

# Push to GitHub
git push
```

## ENVIRONMENT VARIABLES

| Var | Default | Set in |
|-----|---------|--------|
| `JOURNAL_PATH` | `/journal/JOURNAL.md` | `docker-compose.yml` |
| `PORT` | `8080` | runtime only |

## CONVENTIONS

- **No caching.** `parse_journal()` re-reads the file on every HTTP request. Intentional — enables live reload without invalidation logic.
- **Pinned deps.** `requirements.txt` uses exact versions. Don't loosen without testing.
- **CSS custom properties only.** All colors/fonts are `var(--*)`. Never hardcode hex values outside `:root`.
- **Dark mode is automatic.** Driven by `prefers-color-scheme: dark`. No JS toggle, no class toggling.
- **Pyright suppressions at file top.** `app/` files start with `# pyright: reportMissingImports=false,...`. Keep this — implicit relative imports (`from parser import ...`) would otherwise cause false positives.

## ANTI-PATTERNS

- **Don't add `---` inside a journal entry body.** The parser splits on it — the entry gets silently truncated.
- **Don't add `##` headings inside an entry body.** Parser treats them as new article starts.
- **Don't use two journal entries with identical titles.** Produces duplicate slugs; second entry is unreachable via URL.
- **Don't cache parsed articles at module level.** Would break live reload.
- **Don't import `app` as a package** (e.g. `from app.parser import ...`) when running `app/app.py` as `__main__` — imports must match what `app.py` itself uses: `from parser import ...`.

## JOURNAL FORMAT

```
## [Any title here]        ← becomes article title + URL slug

[Body — any markdown]

---                        ← entry separator (3+ dashes, own line)
```

Preamble before the first `##` is silently ignored. See `app/parser.py` for exact regex.
