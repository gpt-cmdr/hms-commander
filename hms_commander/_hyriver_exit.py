"""Safe interpreter exit after HyRiver (async-retriever) requests.

``HmsHuc`` (and ``HmsGaugeStudy`` through it) query the USGS Watershed Boundary Dataset
with pygeohydro, which runs its requests on async-retriever's singleton event-loop
thread. async-retriever registers an ``atexit`` cleanup for that thread, and in
async-retriever 0.19.3 (the latest release when this was written) the cleanup can wait
for ever: ``_AsyncLoopThread.stop()`` checks ``_running.is_set()``, asks the loop to
stop, then calls ``_running.wait()``. When the loop thread clears the event between the
check and the wait, nothing sets it again, so the process never exits.

After hms-commander has used that path, :func:`guard_async_retriever_exit` registers
:func:`stop_async_retriever_loop` with ``atexit``, once. ``atexit`` runs handlers in
reverse order of registration, and async-retriever registers its own cleanup when its
loop thread first starts, so the guard is registered only after that has happened. At
exit the guard runs first: it takes the singleton away (so async-retriever's cleanup
finds nothing to stop), asks the loop to stop and joins the thread with a time limit,
never waiting on the event.

The guard uses async-retriever's private names. It does nothing when async-retriever is
not loaded, when those names are absent, or when ``stop()`` no longer has the unbounded
wait (a fixed release). It never raises.
"""

from __future__ import annotations

import atexit
import inspect
import sys
import threading
from typing import Any, Optional

#: Module that holds the loop thread class (async-retriever 0.19.x).
ASYNC_RETRIEVER_MODULE = "async_retriever._utils"
#: Seconds the exit hook waits for the loop thread to finish.
JOIN_TIMEOUT_S = 30.0
#: Text of the unbounded wait in the affected ``stop()``.
_RACY_WAIT = "_running.wait()"

_lock = threading.Lock()
_registered = False


def _loop_class() -> Optional[Any]:
    """async-retriever's ``_AsyncLoopThread`` when loaded and recognised, else None."""
    module = sys.modules.get(ASYNC_RETRIEVER_MODULE)
    loop_class = getattr(module, "_AsyncLoopThread", None) if module is not None else None
    if loop_class is None:
        return None
    if not all(hasattr(loop_class, name) for name in ("_instance", "_lock", "stop")):
        return None
    return loop_class


def stop_needs_guard(loop_class: Any) -> bool:
    """True when ``loop_class.stop`` has the unbounded ``_running.wait()``.

    When the source cannot be read, the guard is applied: stopping the loop thread with
    a bounded join is safe for any release that keeps these names.
    """
    try:
        source = inspect.getsource(loop_class.stop)
    except (OSError, TypeError):
        return True
    return _RACY_WAIT in source.replace(" ", "")


def stop_async_retriever_loop(timeout: float = JOIN_TIMEOUT_S) -> bool:
    """Stop async-retriever's loop thread without its racy wait. Never raises.

    Returns True when a running thread was asked to stop, False when there was nothing
    to do (async-retriever not loaded, no thread, a fixed release, or an error).
    """
    try:
        loop_class = _loop_class()
        if loop_class is None or not stop_needs_guard(loop_class):
            return False
        with loop_class._lock:
            instance = loop_class._instance
            loop_class._instance = None
        if instance is None or not instance.is_alive():
            return False
        loop = getattr(instance, "loop", None)
        if loop is None or loop.is_closed():
            return False
        loop.call_soon_threadsafe(loop.stop)
        instance.join(timeout=timeout)
        if instance.is_alive():
            try:
                sys.__stderr__.write(
                    "hms_commander: async-retriever's event-loop thread did not stop within "
                    f"{timeout:g} s; it is a daemon thread and does not block exit\n")
            except Exception:
                pass
        return True
    except Exception:
        return False


def guard_async_retriever_exit() -> bool:
    """Register :func:`stop_async_retriever_loop` with ``atexit`` once. Never raises.

    Call it after a HyRiver request. It registers nothing until async-retriever has
    registered its own cleanup (its loop thread has started), so that the guard runs
    before that cleanup. Returns True when the guard is registered.
    """
    global _registered
    if _registered:
        return True
    try:
        loop_class = _loop_class()
        if loop_class is None or not getattr(loop_class, "_cleanup_registered", False):
            return False
        if not stop_needs_guard(loop_class):
            return False
        with _lock:
            if not _registered:
                atexit.register(stop_async_retriever_loop)
                _registered = True
        return True
    except Exception:
        return False
