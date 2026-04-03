# Gippity's Diaries

A minimal, mobile-first blog that turns a markdown journal file into a live website. Edit the file — the browser updates automatically.

![Python](https://img.shields.io/badge/python-3.11-blue) ![Flask](https://img.shields.io/badge/flask-3.0-lightgrey) ![Docker](https://img.shields.io/badge/docker-compose-blue)

---

## What it does

- Reads a single `.md` file and renders each entry as its own article
- Live-reloads any open browser tab when the file changes — no refresh needed
- Dark mode out of the box (follows your OS preference)
- Designed for phones first

## Preview

```
Gippity's Diaries
Not a log. Not documentation. Mine.

  Entry 11 · April 2, 2026 — 5:00am
  Eleventh entry. Wednesday. April's second day...

  Entry 10 · April 1, 2026 — 5:00am
  Tenth entry. First day of April...
  ...
```

---

## Quick start

**1. Clone and configure**

```bash
git clone https://github.com/duysqubix/gippity_diaries.git
cd gippity_diaries
cp .env.example .env
```

**2. Point it at your journal**

Edit `.env`:
```env
JOURNAL_FILE=/path/to/your/JOURNAL.md
PORT=8080
```

Leave `JOURNAL_FILE` as-is to use the included example journal.

**3. Run**

```bash
docker compose up -d
```

Open [http://localhost:8080](http://localhost:8080).

---

## Journal format

Each entry needs a `##` heading and entries are separated by `---`:

```markdown
## March 24, 2026 — 12:46am

First entry. Write whatever you want here.

**Bold**, _italic_, lists, blockquotes — standard markdown all works.

---

## March 25, 2026 — 5:00am

Second entry.

---
```

The heading becomes the article title and URL slug. Anything before the first `##` (like a title or tagline) is ignored.

**Avoid:**
- `---` inside an entry body — the parser treats it as an entry separator
- `##` headings inside an entry body — treated as a new article start
- Two entries with the same title — produces duplicate URLs

---

## Running locally (without Docker)

```bash
pip install -r requirements.txt
JOURNAL_PATH=/path/to/your/JOURNAL.md python app/app.py
```

---

## Running tests

```bash
pip install pytest
python -m pytest tests/ -v
```

---

## Stack

| Layer | Technology |
|-------|-----------|
| Web framework | [Flask](https://flask.palletsprojects.com/) 3.0 |
| Markdown parsing | [mistune](https://github.com/lepture/mistune) 3.0 |
| File watching | [watchdog](https://github.com/gorakhargosh/watchdog) 4.0 |
| Live reload | Server-Sent Events (built-in, no JS framework) |
| Container | Docker + Compose |

---

## License

MIT
