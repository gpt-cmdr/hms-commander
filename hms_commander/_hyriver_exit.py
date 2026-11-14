"""Bounded interpreter exit after HyRiver (async-retriever) requests.

``HmsHuc`` (and ``HmsGaugeStudy`` through it) query the USGS Watershed Boundary Dataset
with pygeohydro, which runs its requests on async-retriever's singleton event-loop
thread. async-retriever 0.19.3 registers an ``atexit`` cleanup for that thread that can
wait for ever: ``_AsyncLoopThread.stop()`` checks ``_running.is_set()``, asks the loop to
stop, then calls ``_running.wait()``. When the loop thread clears the event between the
check and the wait, nothing sets it again, so the process never exits.

After hms-commander has used that path, :func:`guard_async_retriever_exit` registers
:func:`stop_async_retriever_loop` with ``atexit``, once. ``atexit`` runs handlers in
reverse order of registration, and async-retriever registers its own cleanup when its
loop thread first starts, so the guard is registered only after that has happened and
runs first.

Scope
-----
The guard acts only on the implementation it was written against: the installed
distribution must be async-retriever **0.19.3** (the only release with this loop thread;
0.19.0 and 0.19.1 have none, and there is no 0.19.2), and the compiled ``stop()``,
``_cleanup()`` and ``run()`` must reference exactly the names of that release. Any other
version, a changed method, an unexpected singleton or a missing name makes it do nothing,
and it logs the reason at DEBUG. It does not depend on the source being readable.

What the exit hook guarantees
-----------------------------
Every wait is bounded by ``timeout`` (default :data:`EXIT_TIMEOUT_S`) in total:

1. It takes async-retriever's class lock with a time limit. If another thread holds that
   lock for longer, the hook replaces it with a new, unlocked lock, so async-retriever's
   own cleanup (which takes the lock without a time limit and runs next) cannot block on
   it either.
2. It removes the singleton, so async-retriever's cleanup finds nothing to stop and never
   reaches the racy ``stop()``.
3. It lets tasks already on the loop finish, for up to :data:`DRAIN_TIMEOUT_S` (less if
   the budget is smaller). It then cancels what is still pending and gives the
   cancellations up to :data:`CANCEL_GRACE_S` to run their ``except``/``finally`` blocks.
4. It stops the loop and joins the thread with the time that remains. It never waits on
   ``_running``.

What can be abandoned at exit
-----------------------------
The hook does not guarantee that all work on the shared loop completes. Callers that need
a result must wait for it before the interpreter exits. At exit:

- a task still running after the drain window is cancelled; whoever waits on it gets
  ``CancelledError``;
- a task that ignores cancellation, or whose cleanup outlasts the grace period, is left
  unfinished when the loop stops;
- callbacks scheduled with ``call_later``/``call_at`` that are not yet due do not run;
- if the loop thread is stuck in blocking (non-async) code, nothing on it runs again: the
  hook gives up after its budget and the daemon thread ends with the interpreter;
- if the lock had to be replaced, the thread that held it keeps the old lock and is not
  waited for.

The hook never raises an ``Exception``. ``KeyboardInterrupt`` and ``SystemExit`` derive
from ``BaseException`` and are not caught.
"""

from __future__ import annotations

import asyncio
import atexit
import inspect
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

#: Total seconds the exit hook may spend.
EXIT_TIMEOUT_S = 30.0
#: Longest wait for async-retriever's class lock.
LOCK_TIMEOUT_S = 5.0
#: Longest wait for tasks already on the loop to finish.
DRAIN_TIMEOUT_S = 20.0
#: Time given to cancelled tasks to run their cleanup.
CANCEL_GRACE_S = 2.0

#: Names the 0.19.3 methods reference, in the order the compiler records them.
#: A release that changes any of these methods no longer matches and is left alone.
_FINGERPRINT = {
    "stop": ("_running", "is_set", "loop", "call_soon_threadsafe", "stop", "wait", "join"),
    "_cleanup": ("_lock", "_instance", "stop"),
    "run": ("asyncio", "set_event_loop", "loop", "_running", "set", "run_forever",
            "run_until_complete", "shutdown_asyncgens", "close", "clear"),
}
#: Text of the unbounded wait, checked as well when the source is readable.
_RACY_WAIT = "_running.wait()"

_lock = threading.Lock()
_registered = False


def _installed_version() -> Optional[str]:
    try:
        from importlib.metadata import version

        return version(ASYNC_RETRIEVER_DIST)
    except Exception:
        package = sys.modules.get("async_retriever")
        found = getattr(package, "__version__", None)
        return found if isinstance(found, str) else None


def _code_names(function: Any) -> Optional[tuple]:
    function = getattr(function, "__func__", function)
    code = getattr(function, "__code__", None)
    return getattr(code, "co_names", None)


def recognise_affected(loop_class: Any) -> Tuple[bool, str]:
    """Whether ``loop_class`` is async-retriever 0.19.3's ``_AsyncLoopThread``.

    Returns ``(True, "")`` when the version is in :data:`AFFECTED_VERSIONS` and every
    fingerprinted method matches; otherwise ``(False, reason)``.
    """
    if not all(hasattr(loop_class, name)
               for name in ("_instance", "_lock", "_cleanup", "stop", "run")):
        return False, "async-retriever's _AsyncLoopThread does not have the expected names"
    version = _installed_version()
    if version not in AFFECTED_VERSIONS:
        return False, (f"async-retriever {version or '(version unknown)'} is not a release "
                       "known to have the unbounded wait")
    for name, expected in _FINGERPRINT.items():
        names = _code_names(getattr(loop_class, name, None))
        if names != expected:
            return False, (f"_AsyncLoopThread.{name} differs from async-retriever "
                           f"{version} (references {names!r})")
    try:
        source = inspect.getsource(loop_class.stop)
    except (OSError, TypeError):
        source = None   # the compiled check above is sufficient
    if source is not None and _RACY_WAIT not in source.replace(" ", ""):
        return False, "_AsyncLoopThread.stop no longer contains the unbounded wait"
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


def _valid_instance(loop_class: Any, instance: Any) -> bool:
    return (isinstance(instance, loop_class)
            and isinstance(instance, threading.Thread)
            and isinstance(getattr(instance, "loop", None), asyncio.AbstractEventLoop))


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


def stop_async_retriever_loop(timeout: float = EXIT_TIMEOUT_S) -> bool:
    """Stop async-retriever's loop thread within ``timeout`` seconds. Never raises.

    See the module docstring for the guarantees and for what can be abandoned. Returns
    True when a running loop thread was asked to stop, False when there was nothing to do
    (async-retriever not loaded or not recognised, no live thread, or an error).
    """
    try:
        deadline = time.monotonic() + max(float(timeout), 0.0)

        def remaining() -> float:
            return max(deadline - time.monotonic(), 0.0)

        loop_class = _loop_class()
        if loop_class is None:
            return False

        class_lock = loop_class._lock
        acquired = class_lock.acquire(timeout=min(LOCK_TIMEOUT_S, remaining()))
        try:
            if not acquired:
                # Another thread holds the lock. async-retriever's cleanup takes it with
                # no time limit and runs after this hook, so give the class a free lock.
                loop_class._lock = threading.Lock()
                logger.warning("async-retriever exit guard: the loop-thread lock was held "
                               "by another thread; replaced it so exit is not blocked")
            instance = loop_class._instance
            if instance is None:
                logger.debug("async-retriever exit guard: no loop thread to stop")
                return False
            if not _valid_instance(loop_class, instance):
                logger.debug("async-retriever exit guard: unexpected singleton %r; "
                             "doing nothing", type(instance))
                return False
            loop_class._instance = None
        finally:
            if acquired:
                class_lock.release()

        loop = instance.loop
        if not instance.is_alive() or loop.is_closed():
            return False

        # Split what is left: the drain, the cancellation grace, slack for the drain to
        # report back, and at least one grace period for stopping and joining the thread.
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
        instance.join(timeout=remaining())
        if instance.is_alive():
            logger.warning("async-retriever exit guard: the event-loop thread did not stop "
                           "within %.3g s; it is a daemon thread and does not block exit",
                           float(timeout))
        return True
    except Exception:
        return False


def guard_async_retriever_exit() -> bool:
    """Register :func:`stop_async_retriever_loop` with ``atexit`` once. Never raises.

    Call it after a HyRiver request. It registers nothing until async-retriever has
    registered its own cleanup (its loop thread has started), so that the guard runs
    before that cleanup, and nothing for an implementation it does not recognise.
    Returns True when the guard is registered.
    """
    global _registered
    if _registered:
        return True
    try:
        loop_class = _loop_class()
        if loop_class is None or not getattr(loop_class, "_cleanup_registered", False):
            return False
        if not _lock.acquire(timeout=LOCK_TIMEOUT_S):
            return False
        try:
            if not _registered:
                atexit.register(stop_async_retriever_loop)
                _registered = True
        finally:
            _lock.release()
        return True
    except Exception:
        return False
