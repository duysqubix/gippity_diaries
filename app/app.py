# pyright: reportMissingImports=false, reportImplicitRelativeImport=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUntypedFunctionDecorator=false, reportUnknownParameterType=false, reportMissingTypeArgument=false, reportArgumentType=false

import os
import queue

from flask import Flask, Response, abort, render_template

from parser import parse_journal
from watcher import add_listener, remove_listener, start_watcher

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "..", "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "..", "static"),
)

JOURNAL_PATH = os.environ.get("JOURNAL_PATH", "/journal/JOURNAL.md")

_journal_dir = os.path.dirname(os.path.abspath(JOURNAL_PATH))
start_watcher(_journal_dir)


@app.route("/")
def index():
    articles = list(reversed(parse_journal(JOURNAL_PATH)))
    return render_template("index.html", articles=articles)


@app.route("/article/<slug>")
def article(slug: str):
    articles = parse_journal(JOURNAL_PATH)
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
    app.run(host="0.0.0.0", port=8080, debug=False, threaded=True)
