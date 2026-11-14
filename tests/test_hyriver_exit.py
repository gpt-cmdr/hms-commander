"""The exit guard for async-retriever's event-loop thread (``hms_commander._hyriver_exit``).

async-retriever 0.19.3's atexit cleanup can wait for ever when its loop thread clears
``_running`` between ``stop()``'s ``is_set()`` check and its ``wait()``. The subprocess
tests force that interleaving deterministically (no network): the ``wait()`` of the
affected release is made to run only after the loop thread has finished, which is the
losing side of the race. Without the guard the process hangs at exit; with it the
process exits.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import textwrap
import types

import pytest

from hms_commander import _hyriver_exit

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Starts async-retriever's loop thread with a trivial coroutine (no network), then makes
# the thread lose the race in stop(): Event.wait() runs only after the thread has ended
# and cleared the event.
LOSING_RACE = textwrap.dedent(
    """
    import asyncio, sys, threading
    import async_retriever._utils as u

    u.run_in_event_loop(asyncio.sleep(0))
    instance = u._AsyncLoopThread._instance
    assert instance is not None and instance.is_alive()
    assert u._AsyncLoopThread._cleanup_registered

    class LosingEvent(threading.Event):
        def wait(self, timeout=None):
            instance.join()          # the loop thread ends and clears the event first
            return super().wait(timeout)

    racy = LosingEvent()
    racy.set()
    instance._running = racy
    """
)


def _run(code: str, timeout: float):
    env = dict(os.environ)
    env["PYTHONPATH"] = REPO + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run([sys.executable, "-c", code], cwd=REPO, env=env, timeout=timeout,
                          capture_output=True, text=True)


@pytest.fixture
def async_retriever():
    return pytest.importorskip("async_retriever._utils")


@pytest.mark.slow
def test_losing_the_race_hangs_without_the_guard(async_retriever):
    """The reproduction: async-retriever's own atexit cleanup never returns."""
    if not _hyriver_exit.stop_needs_guard(async_retriever._AsyncLoopThread):
        pytest.skip("the installed async-retriever no longer has the unbounded wait")
    with pytest.raises(subprocess.TimeoutExpired) as hung:
        _run(LOSING_RACE + "print('done', flush=True)\n", timeout=20)
    output = hung.value.stdout or b""
    if isinstance(output, bytes):
        output = output.decode(errors="replace")
    assert "done" in output, "the script did not reach its end before the timeout"


@pytest.mark.slow
def test_the_guard_lets_the_process_exit(async_retriever):
    code = LOSING_RACE + textwrap.dedent(
        """
        from hms_commander._hyriver_exit import guard_async_retriever_exit
        assert guard_async_retriever_exit() is True
        assert guard_async_retriever_exit() is True   # registered once
        print('done', flush=True)
        """
    )
    result = _run(code, timeout=60)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "done"
    assert "Traceback" not in result.stderr


def test_guard_does_nothing_before_the_loop_thread_exists(async_retriever):
    """Imported but unused: async-retriever has registered no cleanup, so the guard
    waits (it must be registered after async-retriever's cleanup to run before it)."""
    code = textwrap.dedent(
        """
        import async_retriever._utils as u
        from hms_commander import _hyriver_exit as g
        assert u._AsyncLoopThread._instance is None
        assert g.guard_async_retriever_exit() is False
        assert g._registered is False
        assert g.stop_async_retriever_loop() is False
        print('ok')
        """
    )
    result = _run(code, timeout=60)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def test_guard_is_a_no_op_without_async_retriever():
    code = textwrap.dedent(
        """
        import sys
        from hms_commander import _hyriver_exit as g
        assert 'async_retriever._utils' not in sys.modules
        assert g.guard_async_retriever_exit() is False
        assert g.stop_async_retriever_loop() is False
        print('ok')
        """
    )
    result = _run(code, timeout=60)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def test_stop_is_safe_when_the_thread_is_gone(async_retriever):
    """The thread already ended (or the loop closed): nothing to stop, no error."""
    code = textwrap.dedent(
        """
        import asyncio
        import async_retriever._utils as u
        from hms_commander import _hyriver_exit as g

        u.run_in_event_loop(asyncio.sleep(0))
        instance = u._AsyncLoopThread._instance
        instance.loop.call_soon_threadsafe(instance.loop.stop)
        instance.join(10)
        assert not instance.is_alive()
        assert g.stop_async_retriever_loop() is False
        assert u._AsyncLoopThread._instance is None   # the atexit cleanup has nothing to do
        assert g.stop_async_retriever_loop() is False  # twice
        print('ok')
        """
    )
    result = _run(code, timeout=60)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def _fake_module(monkeypatch, stop):
    loop_class = type("_AsyncLoopThread", (), {
        "_instance": None, "_lock": __import__("threading").Lock(),
        "_cleanup_registered": True, "stop": stop})
    module = types.ModuleType("async_retriever._utils")
    module._AsyncLoopThread = loop_class
    monkeypatch.setitem(sys.modules, "async_retriever._utils", module)
    return loop_class


def test_a_fixed_release_is_left_alone(monkeypatch):
    def stop(self):
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.join(timeout=5)

    loop_class = _fake_module(monkeypatch, stop)
    loop_class._instance = object()      # touched only if the guard wrongly applied
    monkeypatch.setattr(_hyriver_exit, "_registered", False)
    registered = []
    monkeypatch.setattr(_hyriver_exit.atexit, "register", registered.append)
    assert _hyriver_exit.stop_needs_guard(loop_class) is False
    assert _hyriver_exit.guard_async_retriever_exit() is False
    assert _hyriver_exit.stop_async_retriever_loop() is False
    assert registered == [] and loop_class._instance is not None


def test_an_unrecognised_layout_is_left_alone(monkeypatch):
    module = types.ModuleType("async_retriever._utils")
    module._AsyncLoopThread = type("_AsyncLoopThread", (), {})
    monkeypatch.setitem(sys.modules, "async_retriever._utils", module)
    monkeypatch.setattr(_hyriver_exit, "_registered", False)
    assert _hyriver_exit.guard_async_retriever_exit() is False
    assert _hyriver_exit.stop_async_retriever_loop() is False


def test_the_hook_never_raises(monkeypatch):
    def stop(self):
        self._running.wait()

    loop_class = _fake_module(monkeypatch, stop)
    # Recognised, but its lock raises: the hook swallows the error.
    monkeypatch.setattr(_hyriver_exit, "recognise_affected", lambda cls: (True, ""))

    class BrokenLock:
        def acquire(self, timeout=-1):
            raise RuntimeError("boom")

    loop_class._lock = BrokenLock()
    assert _hyriver_exit.stop_async_retriever_loop() is False


def test_an_unexpected_singleton_keeps_its_cleanup_handle(monkeypatch):
    """A recognised class with a singleton of the wrong shape is not cleared."""
    loop_class = _fake_module(monkeypatch, lambda self: None)
    monkeypatch.setattr(_hyriver_exit, "recognise_affected", lambda cls: (True, ""))
    sentinel = object()
    loop_class._instance = sentinel
    assert _hyriver_exit.stop_async_retriever_loop(timeout=1) is False
    assert loop_class._instance is sentinel


# --- Review 1 regressions -------------------------------------------------------------

def _real_affected(async_retriever):
    affected, reason = _hyriver_exit.recognise_affected(async_retriever._AsyncLoopThread)
    if not affected:
        pytest.skip(f"the installed async-retriever is not the affected release: {reason}")


HOLD_LOCK = """
held = threading.Event()

def hold():
    with u._AsyncLoopThread._lock:
        held.set()
        threading.Event().wait()

threading.Thread(target=hold, daemon=True).start()
assert held.wait(10)
"""


@pytest.mark.slow
def test_a_hung_lock_does_not_hang_the_hook(async_retriever):
    """F1: another thread holds async-retriever's lock for ever. The hook returns within
    its budget, and async-retriever's own cleanup (which takes the lock with no time
    limit, after the hook) does not hang the exit either."""
    _real_affected(async_retriever)
    code = textwrap.dedent(
        """
        import asyncio, threading, time
        import async_retriever._utils as u
        from hms_commander import _hyriver_exit as g

        u.run_in_event_loop(asyncio.sleep(0))
        instance = u._AsyncLoopThread._instance
        """
    ) + HOLD_LOCK + textwrap.dedent(
        """
        g.LOCK_TIMEOUT_S = 0.5
        start = time.monotonic()
        assert g.stop_async_retriever_loop(timeout=2) is True
        elapsed = time.monotonic() - start
        assert elapsed < 3, elapsed
        assert u._AsyncLoopThread._instance is None
        assert not instance.is_alive()
        print('done', flush=True)
        """
    )
    try:
        result = _run(code, timeout=60)
    except subprocess.TimeoutExpired:
        pytest.fail("the process hung with the lock held")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "done"
    assert "replaced it so exit is not blocked" in result.stderr


@pytest.mark.slow
def test_a_hung_lock_at_real_exit_with_the_guard_registered(async_retriever):
    """F1, end to end: the lock is held while the interpreter exits with the guard
    registered; both atexit hooks complete."""
    _real_affected(async_retriever)
    code = textwrap.dedent(
        """
        import asyncio, threading
        import async_retriever._utils as u
        from hms_commander import _hyriver_exit as g

        u.run_in_event_loop(asyncio.sleep(0))
        assert g.guard_async_retriever_exit() is True
        g.LOCK_TIMEOUT_S = 0.5
        """
    ) + HOLD_LOCK + "print('done', flush=True)\n"
    try:
        result = _run(code, timeout=60)
    except subprocess.TimeoutExpired:
        pytest.fail("the process hung at exit with the lock held")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "done"


FIXED_SHAPES = {
    # A bounded stop() with the class names unchanged, and the source unreadable
    # (frozen or source-stripped installation): the compiled check rejects it.
    "fixed-stop-unreadable-source": """
        def fixed_stop(self):
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.join(timeout=1)
        u._AsyncLoopThread.stop = fixed_stop
        def unreadable(obj):
            raise OSError('source unavailable')
        g.inspect.getsource = unreadable
        """,
    # The same code reporting a later version: not in the allowlist.
    "later-version": """
        g._installed_version = lambda: '0.19.4'
        """,
    # Unknown version (no metadata and no __version__).
    "unknown-version": """
        g._installed_version = lambda: None
        """,
}


@pytest.mark.parametrize("shape", sorted(FIXED_SHAPES))
def test_a_fixed_upstream_shape_is_left_alone(async_retriever, shape):
    """F2: anything other than the exact 0.19.3 implementation is not touched, and the
    reason is logged at DEBUG."""
    _real_affected(async_retriever)
    code = textwrap.dedent(
        """
        import asyncio, logging
        logging.basicConfig(level=logging.DEBUG, format='%(levelname)s %(message)s')
        import async_retriever._utils as u
        from hms_commander import _hyriver_exit as g
        g.logger.setLevel(logging.DEBUG)   # importing hms_commander sets the root to INFO

        u.run_in_event_loop(asyncio.sleep(0))
        instance = u._AsyncLoopThread._instance
        """
    ) + textwrap.dedent(FIXED_SHAPES[shape]) + textwrap.dedent(
        """
        assert g.stop_needs_guard(u._AsyncLoopThread) is False
        assert g.guard_async_retriever_exit() is False
        assert g._registered is False
        assert g.stop_async_retriever_loop(timeout=1) is False
        assert u._AsyncLoopThread._instance is instance and instance.is_alive()
        # Leave a clean exit: stop the loop here instead of in the racy cleanup.
        instance.loop.call_soon_threadsafe(instance.loop.stop)
        instance.join(10)
        u._AsyncLoopThread._instance = None
        print('done', flush=True)
        """
    )
    result = _run(code, timeout=60)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "done"
    assert "DEBUG async-retriever exit guard:" in result.stderr
    assert "doing nothing" in result.stderr


@pytest.mark.slow
def test_pending_work_drains_before_the_loop_stops(async_retriever):
    """F3: a coroutine already running on the shared loop finishes, and its future
    resolves, before the hook stops the loop."""
    _real_affected(async_retriever)
    code = textwrap.dedent(
        """
        import asyncio, threading
        import async_retriever._utils as u
        from hms_commander import _hyriver_exit as g

        u.run_in_event_loop(asyncio.sleep(0))
        started = threading.Event()

        async def work():
            started.set()
            await asyncio.sleep(1)
            return 'finished'

        future = asyncio.run_coroutine_threadsafe(work(), u._AsyncLoopThread._instance.loop)
        assert started.wait(10)
        assert g.stop_async_retriever_loop(timeout=10) is True
        assert future.done() and future.result() == 'finished'
        print('done', flush=True)
        """
    )
    result = _run(code, timeout=60)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "done"
    assert "Task was destroyed but it is pending" not in result.stderr


@pytest.mark.slow
def test_work_past_the_budget_is_cancelled_with_cleanup(async_retriever):
    """F3: a task that outlives the drain window is cancelled, its ``finally`` runs, the
    hook returns within its budget, and asyncio reports no destroyed pending task."""
    _real_affected(async_retriever)
    code = textwrap.dedent(
        """
        import asyncio, threading, time
        import async_retriever._utils as u
        from hms_commander import _hyriver_exit as g

        u.run_in_event_loop(asyncio.sleep(0))
        started = threading.Event()
        cleaned = threading.Event()

        async def forever():
            started.set()
            try:
                await asyncio.sleep(1000)
            finally:
                cleaned.set()

        future = asyncio.run_coroutine_threadsafe(forever(), u._AsyncLoopThread._instance.loop)
        assert started.wait(10)
        start = time.monotonic()
        assert g.stop_async_retriever_loop(timeout=2) is True
        elapsed = time.monotonic() - start
        assert elapsed < 3, elapsed
        assert cleaned.is_set()
        assert future.cancelled()
        print('done', flush=True)
        """
    )
    result = _run(code, timeout=60)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "done"
    assert "cancelled 1 task(s)" in result.stderr
    assert "Task was destroyed but it is pending" not in result.stderr


@pytest.mark.parametrize("method, args", [
    ("get_huc12_for_bounds", ((-95.1, 35.0, -95.0, 35.1),)),
    ("get_huc8_for_bounds", ((-95.1, 35.0, -95.0, 35.1),)),
    ("get_huc_by_ids", ("huc8", ["11110103"])),
])
def test_hmshuc_registers_the_guard_even_when_the_query_fails(monkeypatch, method, args):
    pygeohydro = pytest.importorskip("pygeohydro")
    pytest.importorskip("geopandas")
    from hms_commander import HmsHuc
    huc_module = sys.modules["hms_commander.HmsHuc"]

    calls = []
    monkeypatch.setattr(huc_module, "guard_async_retriever_exit", lambda: calls.append(1))

    class FailingWBD:
        def __init__(self, *a, **k):
            raise ConnectionError("service down")

    monkeypatch.setattr(pygeohydro, "WBD", FailingWBD)
    with pytest.raises(ConnectionError):
        getattr(HmsHuc, method)(*args)
    assert calls == [1]


def _online(host="hydro.nationalmap.gov") -> bool:
    if os.environ.get("HMS_COMMANDER_TEST_OFFLINE") == "1":
        return False
    try:
        socket.create_connection((host, 443), timeout=5).close()
        return True
    except OSError:
        return False


@pytest.mark.slow
@pytest.mark.requires_network
@pytest.mark.requires_gis
def test_a_real_hmshuc_query_exits_cleanly():
    """A user script: one WBD query, then interpreter exit with the guard in place."""
    pytest.importorskip("pygeohydro")
    if not _online():
        pytest.skip("no network access to the USGS WBD service")
    code = textwrap.dedent(
        """
        from hms_commander import HmsHuc, _hyriver_exit
        gdf = HmsHuc.get_huc_by_ids("huc8", ["11110103"])
        assert len(gdf) == 1
        assert _hyriver_exit._registered
        print('done', flush=True)
        """
    )
    try:
        result = _run(code, timeout=300)
    except subprocess.TimeoutExpired:
        pytest.fail("the script did not exit within 300 s")
    if result.returncode != 0 and ("502" in result.stderr or "ServiceError" in result.stderr):
        pytest.skip("USGS WBD service error: " + result.stderr.strip().splitlines()[-1])
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("done")
