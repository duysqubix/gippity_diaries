# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUntypedBaseClass=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnannotatedClassAttribute=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false

"""
Watchdog-based file watcher that notifies SSE listeners when the journal changes.
"""

import queue
import threading

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

_listeners: list[queue.Queue] = []
_lock = threading.Lock()
_observer: Observer | None = None


class _JournalHandler(FileSystemEventHandler):
    def _notify(self, event):
        if not event.is_directory:
            with _lock:
                for q in _listeners[:]:
                    try:
                        q.put_nowait("reload")
                    except queue.Full:
                        pass

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
