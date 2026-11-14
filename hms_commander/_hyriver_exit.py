"""Bounded interpreter exit after HyRiver (async-retriever) requests.

``HmsHuc`` (and ``HmsGaugeStudy`` through it) query the USGS Watershed Boundary Dataset
with pygeohydro, which runs its requests on async-retriever's singleton event-loop
thread. async-retriever 0.19.3 registers an ``atexit`` cleanup, ``_cleanup()``, that calls
``_AsyncLoopThread.stop()``. That method checks ``_running.is_set()``, asks the loop to
stop, then calls ``_running.wait()``. When the loop thread clears the event between the
check and the wait, nothing sets it again, so the process never exits.

Why not a dependency constraint
-------------------------------
async-retriever 0.19.1 has no loop thread and no such cleanup, but no current HyRiver
release accepts it: pygeohydro 0.19.3+ and pynhd 0.19.3+ (including pynhd 0.20.0) require
``async-retriever>=0.19.3``. Excluding 0.19.3 resolves only to pygeohydro 0.19.0 and pynhd
0.19.0, and pynhd 0.19.0's ``NLDI`` client fails against the current USGS service. There is
no async-retriever release after 0.19.3.

What the guard does
-------------------
After hms-commander has used that path, :func:`guard_async_retriever_exit` registers
:func:`install_bounded_stop` with ``atexit``, once, and only after async-retriever has
registered its own cleanup. ``atexit`` runs handlers in reverse order of registration, so
at exit :func:`install_bounded_stop` runs first. It replaces ``_AsyncLoopThread.stop`` with
:func:`_bounded_stop` and returns; it waits for nothing. async-retriever's own
``_cleanup()`` then runs unchanged, with its own lock, on whichever loop thread is the
singleton at that moment, and calls the replacement:

1. It lets tasks already on the loop finish, for up to :data:`DRAIN_TIMEOUT_S` (less if
   the budget is smaller), then cancels what is still pending and gives the
   cancellations up to :data:`CANCEL_GRACE_S` to run their ``except``/``finally`` blocks.
2. It stops the loop and joins the thread with the time that remains of
   :data:`EXIT_TIMEOUT_S`. It never waits on ``_running``.

The guard does not touch async-retriever's lock, its singleton or the ``atexit``
registry. It changes one method, and only at exit.

Scope (fails closed)
--------------------
It acts only when all of these hold, and otherwise does nothing and logs the reason at
DEBUG:

- the installed distribution is async-retriever 0.19.3 (the only release with this loop
  thread; 0.19.0 and 0.19.1 have none, and there is no 0.19.2);
- the loaded ``async_retriever/_utils.py`` is byte-identical to the file in the published
  0.19.3 wheel (SHA-256 :data:`STOCK_UTILS_SHA256`), so a patched or source-stripped
  installation is left alone;
- ``_AsyncLoopThread.stop``, ``_cleanup`` and ``run`` are still the functions defined in
  that file (not replaced at run time).

Limits
------
- async-retriever's ``_cleanup()`` takes its class lock with no time limit. If another
  thread holds that lock at exit and never releases it, the exit blocks there, as it
  would without the guard. In 0.19.3 the lock is held only while a loop thread is
  created and started.
- The hook does not guarantee that all work on the shared loop completes. Callers that
  need a result must wait for it before the interpreter exits. At exit, a task still
  running after the drain window is cancelled (whoever waits on it gets
  ``CancelledError``); a task that ignores cancellation, or whose cleanup outlasts the
  grace period, is left unfinished; ``call_later``/``call_at`` callbacks not yet due do
  not run; and if the loop thread is stuck in blocking (non-async) code, nothing on it
  runs again: the stop gives up after its budget and the daemon thread ends with the
  interpreter.
- Without a call to :func:`guard_async_retriever_exit` (for example, pygeohydro used
  directly rather than through ``HmsHuc``), async-retriever's behaviour is unchanged.

The guard's functions never raise an ``Exception``. ``KeyboardInterrupt`` and
``SystemExit`` derive from ``BaseException`` and are not caught.
"""

from __future__ import annotations

import asyncio
import atexit
import hashlib
import os
import sys
import threading
import time
from typing import Any, Optional, Tuple

from .LoggingConfig import get_logger

logger = get_logger(__name__)

#: Module that holds the loop thread class.
ASYNC_RETRIEVER_MODULE = "async_retriever._utils"
#: Distribution name used to read the installed version.
ASYNC_RETRIEVER_DIST = "async-retriever"
#: Releases whose ``stop()`` has the unbounded wait. Only 0.19.3 has the loop thread.
AFFECTED_VERSIONS = frozenset({"0.19.3"})
#: SHA-256 of ``async_retriever/_utils.py`` in async_retriever-0.19.3-py3-none-any.whl
#: (matches the wheel's RECORD entry ``52BXN39G06hFDFC3Blh1LSuUtHh9veXX8OTaJF6XZhU``).
STOCK_UTILS_SHA256 = "e76057377f46d3a8450c50b70658752d2b94b4787dbde5d7f0e4da245e976615"
#: First line of each method's code object in that file.
_STOCK_FIRST_LINES = {"stop": 83, "_cleanup": 48, "run": 72}

#: Total seconds one bounded stop may spend.
EXIT_TIMEOUT_S = 30.0
#: Longest wait for tasks already on the loop to finish.
DRAIN_TIMEOUT_S = 20.0
#: Time given to cancelled tasks to run their cleanup.
CANCEL_GRACE_S = 2.0

_lock = threading.Lock()
_registered = False
#: The class whose ``stop`` was replaced, and the original method, for diagnostics/tests.
_replaced: Optional[Tuple[Any, Any]] = None


def _installed_version() -> Optional[str]:
    try:
        from importlib.metadata import version

        return version(ASYNC_RETRIEVER_DIST)
    except Exception:
        package = sys.modules.get("async_retriever")
        found = getattr(package, "__version__", None)
        return found if isinstance(found, str) else None


def _file_sha256(path: str) -> Optional[str]:
    try:
        with open(path, "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()
    except OSError:
        return None


def _same_file(a: Optional[str], b: Optional[str]) -> bool:
    if not a or not b:
        return False
    try:
        return os.path.samefile(a, b)
    except OSError:
        return False


def recognise_affected(loop_class: Any) -> Tuple[bool, str]:
    """Whether ``loop_class`` is the stock async-retriever 0.19.3 ``_AsyncLoopThread``.

    Returns ``(True, "")`` when every check in the module docstring's *Scope* passes;
    otherwise ``(False, reason)``.
    """
    if not all(hasattr(loop_class, name)
               for name in ("_instance", "_lock", "_cleanup", "stop", "run")):
        return False, "async-retriever's _AsyncLoopThread does not have the expected names"
    version = _installed_version()
    if version not in AFFECTED_VERSIONS:
        return False, (f"async-retriever {version or '(version unknown)'} is not a release "
                       "known to have the unbounded wait")
    module = sys.modules.get(getattr(loop_class, "__module__", ""), None)
    path = getattr(module, "__file__", None)
    if not path or not path.endswith(".py"):
        return False, f"async-retriever's source file is not available ({path!r})"
    digest = _file_sha256(path)
    if digest != STOCK_UTILS_SHA256:
        return False, (f"{path} is not the stock async-retriever {version} file "
                       f"(sha256 {digest})")
    for name, first_line in _STOCK_FIRST_LINES.items():
        function = getattr(getattr(loop_class, name), "__func__", getattr(loop_class, name))
        code = getattr(function, "__code__", None)
        if (code is None
                or getattr(function, "__qualname__", None) != f"_AsyncLoopThread.{name}"
                or code.co_firstlineno != first_line
                or not _same_file(code.co_filename, path)):
            return False, f"_AsyncLoopThread.{name} is not the method defined in {path}"
    return True, ""


def stop_needs_guard(loop_class: Any) -> bool:
    """True when ``loop_class`` is the affected implementation (see :func:`recognise_affected`)."""
    try:
        return recognise_affected(loop_class)[0]
    except Exception:
        return False


def _loop_class() -> Optional[Any]:
    """The affected ``_AsyncLoopThread`` when loaded, else None (reason logged at DEBUG)."""
    module = sys.modules.get(ASYNC_RETRIEVER_MODULE)
    if module is None:
        logger.debug("async-retriever exit guard: async-retriever is not loaded")
        return None
    loop_class = getattr(module, "_AsyncLoopThread", None)
    if loop_class is None:
        logger.debug("async-retriever exit guard: no _AsyncLoopThread; doing nothing")
        return None
    affected, reason = recognise_affected(loop_class)
    if not affected:
        logger.debug("async-retriever exit guard: %s; doing nothing", reason)
        return None
    return loop_class


async def _drain(wait_s: float, grace_s: float) -> Tuple[int, int]:
    """Wait for the loop's other tasks, then cancel what is left.

    Returns ``(cancelled, unfinished)``: tasks cancelled after the wait, and tasks still
    not done after the grace period.
    """
    me = asyncio.current_task()
    loop = asyncio.get_running_loop()
    end = loop.time() + max(wait_s, 0.0)
    while True:
        pending = {task for task in asyncio.all_tasks() if task is not me}
        if not pending:
            return 0, 0
        left = end - loop.time()
        if left <= 0:
            break
        await asyncio.wait(pending, timeout=left)
    for task in pending:
        task.cancel()
    if grace_s > 0:
        await asyncio.wait(pending, timeout=grace_s)
    return len(pending), sum(1 for task in pending if not task.done())


def _bounded_stop(self: Any) -> None:
    """Replacement for ``_AsyncLoopThread.stop``: drain, stop and join within a budget.

    Called by async-retriever's own ``_cleanup()``. Never waits on ``_running`` and never
    raises an ``Exception``.
    """
    try:
        budget = float(EXIT_TIMEOUT_S)
        deadline = time.monotonic() + max(budget, 0.0)

        def remaining() -> float:
            return max(deadline - time.monotonic(), 0.0)

        loop = getattr(self, "loop", None)
        if (not isinstance(loop, asyncio.AbstractEventLoop) or loop.is_closed()
                or not self.is_alive()):
            return

        # The drain, the cancellation grace, slack for the drain to report back, and at
        # least one grace period for stopping and joining the thread.
        grace_s = min(CANCEL_GRACE_S, remaining() / 5)
        drain_s = min(DRAIN_TIMEOUT_S, max(remaining() - 3 * grace_s, 0.0))
        drained = None
        try:
            drained = asyncio.run_coroutine_threadsafe(_drain(drain_s, grace_s), loop)
            cancelled, unfinished = drained.result(
                timeout=min(drain_s + 2 * grace_s, remaining()))
            if cancelled:
                logger.warning("async-retriever exit guard: cancelled %d task(s) still "
                               "running after %.3g s; %d did not finish", cancelled,
                               drain_s, unfinished)
        except Exception as exc:   # the loop is stuck or closed; stop it anyway
            if drained is not None:
                drained.cancel()
            logger.warning("async-retriever exit guard: pending work on the loop was not "
                           "drained (%s)", type(exc).__name__)
        try:
            loop.call_soon_threadsafe(loop.stop)
        except RuntimeError:   # the loop closed in the meantime
            pass
        self.join(timeout=remaining())
        if self.is_alive():
            logger.warning("async-retriever exit guard: the event-loop thread did not stop "
                           "within %.3g s; it is a daemon thread and does not block exit",
                           budget)
    except Exception as exc:
        logger.debug("async-retriever exit guard: bounded stop failed (%r)", exc)


def install_bounded_stop() -> bool:
    """Replace the affected ``_AsyncLoopThread.stop`` with :func:`_bounded_stop`.

    This is the exit hook. It waits for nothing and never raises an ``Exception``.
    Returns True when the bounded stop is in place.
    """
    global _replaced
    try:
        module = sys.modules.get(ASYNC_RETRIEVER_MODULE)
        loop_class = getattr(module, "_AsyncLoopThread", None)
        if loop_class is not None and getattr(loop_class, "stop", None) is _bounded_stop:
            return True
        loop_class = _loop_class()
        if loop_class is None:
            return False
        _replaced = (loop_class, loop_class.__dict__["stop"])
        loop_class.stop = _bounded_stop
        logger.debug("async-retriever exit guard: replaced _AsyncLoopThread.stop with a "
                     "bounded stop")
        return True
    except Exception as exc:
        logger.debug("async-retriever exit guard: not installed (%r)", exc)
        return False


def guard_async_retriever_exit() -> bool:
    """Register :func:`install_bounded_stop` with ``atexit`` once. Never raises.

    Call it after a HyRiver request. It registers nothing until async-retriever has
    registered its own cleanup (its loop thread has started), so that the hook runs
    before that cleanup, and nothing for an implementation it does not recognise.
    Returns True when the hook is registered.
    """
    global _registered
    if _registered:
        return True
    try:
        loop_class = _loop_class()
        if loop_class is None or not getattr(loop_class, "_cleanup_registered", False):
            return False
        with _lock:   # held only for the check-and-register below
            if not _registered:
                atexit.register(install_bounded_stop)
                _registered = True
        return True
    except Exception:
        return False
