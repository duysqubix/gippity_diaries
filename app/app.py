# pyright: reportMissingImports=false, reportImplicitRelativeImport=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUntypedFunctionDecorator=false, reportUnknownParameterType=false, reportMissingTypeArgument=false, reportArgumentType=false

import os
import queue

from flask import Flask, Response, abort, render_template, request

from parser import parse_journals
from watcher import add_listener, remove_listener, start_watcher

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "..", "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "..", "static"),
)

JOURNAL_PATH = os.environ.get("JOURNAL_PATH", "/journal/JOURNAL.md")
PER_PAGE = 5

_journal_dir = os.path.dirname(os.path.abspath(JOURNAL_PATH))
start_watcher(_journal_dir)


@app.route("/")
def index():
    all_articles = list(reversed(parse_journals(_journal_dir)))
    page = request.args.get("page", 1, type=int)
    page = max(1, page)
    total = len(all_articles)
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = min(page, total_pages)
    start = (page - 1) * PER_PAGE
    articles = all_articles[start : start + PER_PAGE]
    return render_template(
        "index.html",
        articles=articles,
        page=page,
        total_pages=total_pages,
    )


@app.route("/article/<slug>")
def article(slug: str):
    articles = parse_journals(_journal_dir)
    art = next((a for a in articles if a["slug"] == slug), None)
    if art is None:
        abort(404)
    idx = articles.index(art)
    prev_art = articles[idx - 1] if idx > 0 else None
    next_art = articles[idx + 1] if idx < len(articles) - 1 else None
    return render_template("article.html", article=art, prev=prev_art, next=next_art)


@app.route("/events")
def events():
    """Server-Sent Events endpoint. Sends 'reload' when the journal file changes."""

    def stream():
        q: queue.Queue = queue.Queue(maxsize=10)
        add_listener(q)
        try:
            yield "data: connected\n\n"
            while True:
                try:
                    msg = q.get(timeout=20)
                    yield f"data: {msg}\n\n"
                except queue.Empty:
                    yield "data: ping\n\n"
        except GeneratorExit:
            pass
        finally:
            remove_listener(q)

    return Response(
        stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
