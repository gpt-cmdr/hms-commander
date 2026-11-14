"""The exit guard for async-retriever's event-loop thread (``hms_commander._hyriver_exit``).

async-retriever 0.19.3's atexit cleanup can wait for ever when its loop thread clears
``_running`` between ``stop()``'s ``is_set()`` check and its ``wait()``. The subprocess
tests force that interleaving deterministically (no network): the ``wait()`` of the
affected release is made to run only after the loop thread has finished, which is the
losing side of the race. Without the guard the process hangs at exit; with it the
process exits.

The guard replaces only ``_AsyncLoopThread.stop`` at exit, and only for the stock 0.19.3
file. async-retriever's own ``_cleanup()`` keeps its lock and singleton protocol.
"""

from __future__ import annotations

import os
import shutil
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


def _run(code: str, timeout: float, pythonpath: str = ""):
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (pythonpath, REPO, env.get("PYTHONPATH", "")) if p)
    return subprocess.run([sys.executable, "-c", code], cwd=REPO, env=env, timeout=timeout,
                          capture_output=True, text=True)


def _stdout(exc: subprocess.TimeoutExpired) -> str:
    output = exc.stdout or b""
    return output.decode(errors="replace") if isinstance(output, bytes) else output


@pytest.fixture
def async_retriever():
    return pytest.importorskip("async_retriever._utils")


def _real_affected(async_retriever):
    loop_class = getattr(async_retriever, "_AsyncLoopThread", None)
    if loop_class is None:
        pytest.skip("the installed async-retriever has no loop thread")
    affected, reason = _hyriver_exit.recognise_affected(loop_class)
    if not affected:
        pytest.skip(f"the installed async-retriever is not the affected release: {reason}")


@pytest.mark.slow
def test_losing_the_race_hangs_without_the_guard(async_retriever):
    """The reproduction: async-retriever's own atexit cleanup never returns."""
    _real_affected(async_retriever)
    with pytest.raises(subprocess.TimeoutExpired) as hung:
        _run(LOSING_RACE + "print('done', flush=True)\n", timeout=20)
    assert "done" in _stdout(hung.value), \
        "the script did not reach its end before the timeout"


@pytest.mark.slow
def test_the_guard_lets_the_process_exit(async_retriever):
    _real_affected(async_retriever)
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


@pytest.mark.slow
def test_the_installed_async_retriever_does_not_hang_at_exit(async_retriever):
    """Canary: whatever async-retriever is installed, a process that lost the race exits.

    For the stock 0.19.3 the guard covers it. For any other implementation the guard
    does nothing, so this fails if a release that still hangs is installed and the
    guard's allowlist needs review.
    """
    loop_class = getattr(async_retriever, "_AsyncLoopThread", None)
    if loop_class is None or not hasattr(loop_class, "get_instance"):
        code = "import async_retriever\nprint('done', flush=True)\n"
    else:
        code = LOSING_RACE + textwrap.dedent(
            """
            from hms_commander._hyriver_exit import guard_async_retriever_exit
            guard_async_retriever_exit()
            print('done', flush=True)
            """
        )
    try:
        result = _run(code, timeout=60)
    except subprocess.TimeoutExpired:
        affected, reason = _hyriver_exit.recognise_affected(loop_class)
        pytest.fail("the installed async-retriever hangs at exit after losing the race "
                    f"and the guard does not cover it: {reason}")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "done"


def test_guard_does_nothing_before_the_loop_thread_exists(async_retriever):
    """Imported but unused: async-retriever has registered no cleanup, so the guard
    waits (it must be registered after async-retriever's cleanup to run before it)."""
    if not hasattr(async_retriever, "_AsyncLoopThread"):
        pytest.skip("the installed async-retriever has no loop thread")
    code = textwrap.dedent(
        """
        import async_retriever._utils as u
        from hms_commander import _hyriver_exit as g
        assert u._AsyncLoopThread._instance is None
        assert g.guard_async_retriever_exit() is False
        assert g._registered is False
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
        assert g.install_bounded_stop() is False
        print('ok')
        """
    )
    result = _run(code, timeout=60)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def test_the_hook_touches_only_stop(async_retriever):
    """The exit hook replaces ``stop`` and nothing else: lock, singleton and the
    registered cleanup are async-retriever's own. Idempotent."""
    _real_affected(async_retriever)
    code = textwrap.dedent(
        """
        import asyncio
        import async_retriever._utils as u
        from hms_commander import _hyriver_exit as g

        u.run_in_event_loop(asyncio.sleep(0))
        cls = u._AsyncLoopThread
        lock, instance, cleanup = cls._lock, cls._instance, cls.__dict__['_cleanup']
        original_stop = cls.stop
        assert g.install_bounded_stop() is True
        assert g.install_bounded_stop() is True
        assert cls.stop is g._bounded_stop and g._replaced == (cls, original_stop)
        assert cls._lock is lock and cls._instance is instance
        assert cls.__dict__['_cleanup'] is cleanup
        cls._cleanup()                       # what atexit runs
        assert not instance.is_alive() and cls._instance is None
        print('ok')
        """
    )
    result = _run(code, timeout=60)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def test_stop_is_safe_when_the_thread_is_gone(async_retriever):
    """The thread already ended (or the loop closed): the bounded stop returns."""
    _real_affected(async_retriever)
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
        assert g.install_bounded_stop() is True
        instance.stop()
        instance.stop()                      # twice
        print('ok')
        """
    )
    result = _run(code, timeout=60)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def _fake_module(monkeypatch, stop):
    loop_class = type("_AsyncLoopThread", (), {
        "_instance": None, "_lock": __import__("threading").Lock(),
        "_cleanup_registered": True, "_cleanup": classmethod(lambda cls: None),
        "run": lambda self: None, "stop": stop})
    loop_class.__module__ = "async_retriever._utils"
    module = types.ModuleType("async_retriever._utils")
    module._AsyncLoopThread = loop_class
    monkeypatch.setitem(sys.modules, "async_retriever._utils", module)
    return loop_class


def test_a_fixed_release_is_left_alone(monkeypatch):
    def stop(self):
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.join(timeout=5)

    loop_class = _fake_module(monkeypatch, stop)
    monkeypatch.setattr(_hyriver_exit, "_registered", False)
    registered = []
    monkeypatch.setattr(_hyriver_exit.atexit, "register", registered.append)
    assert _hyriver_exit.stop_needs_guard(loop_class) is False
    assert _hyriver_exit.guard_async_retriever_exit() is False
    assert _hyriver_exit.install_bounded_stop() is False
    assert registered == [] and loop_class.stop is stop


def test_an_unrecognised_layout_is_left_alone(monkeypatch):
    module = types.ModuleType("async_retriever._utils")
    module._AsyncLoopThread = type("_AsyncLoopThread", (), {})
    monkeypatch.setitem(sys.modules, "async_retriever._utils", module)
    monkeypatch.setattr(_hyriver_exit, "_registered", False)
    assert _hyriver_exit.guard_async_retriever_exit() is False
    assert _hyriver_exit.install_bounded_stop() is False


def test_the_hook_and_the_bounded_stop_never_raise(monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(_hyriver_exit, "_loop_class", broken)
    monkeypatch.setitem(sys.modules, "async_retriever._utils", None)
    assert _hyriver_exit.install_bounded_stop() is False
    monkeypatch.setattr(_hyriver_exit, "_registered", False)
    assert _hyriver_exit.guard_async_retriever_exit() is False

    class Broken:
        loop = None

        def is_alive(self):
            raise RuntimeError("boom")

    assert _hyriver_exit._bounded_stop(Broken()) is None


# --- Review 1 and 2 regressions -------------------------------------------------------

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
def test_a_hung_lock_does_not_block_the_hook(async_retriever):
    """F1: another thread holds async-retriever's lock for ever. The hook waits for
    nothing, returns at once and leaves the lock alone. (async-retriever's own cleanup
    would then wait for that lock, as it does without the guard: the documented limit,
    so the script ends with os._exit.)"""
    _real_affected(async_retriever)
    code = textwrap.dedent(
        """
        import asyncio, os, threading, time
        import async_retriever._utils as u
        from hms_commander import _hyriver_exit as g

        u.run_in_event_loop(asyncio.sleep(0))
        """
    ) + HOLD_LOCK + textwrap.dedent(
        """
        lock = u._AsyncLoopThread._lock
        start = time.monotonic()
        assert g.install_bounded_stop() is True
        elapsed = time.monotonic() - start
        assert elapsed < 1, elapsed
        assert u._AsyncLoopThread._lock is lock and lock.locked()
        print('done', flush=True)
        os._exit(0)
        """
    )
    result = _run(code, timeout=60)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "done"


@pytest.mark.slow
def test_a_singleton_published_late_still_gets_the_bounded_stop(async_retriever):
    """F1 (review 2): a thread inside the real ``get_instance()`` holds the lock while the
    exit hook runs, then publishes a new live loop thread that would lose the race.
    async-retriever's cleanup takes the lock after it, finds that thread and stops it
    with the bounded stop: the process exits."""
    _real_affected(async_retriever)
    code = textwrap.dedent(
        """
        import asyncio, atexit, threading
        import async_retriever._utils as u
        from hms_commander import _hyriver_exit as g

        u.run_in_event_loop(asyncio.sleep(0))
        assert g.guard_async_retriever_exit() is True
        cls = u._AsyncLoopThread
        old = cls._instance
        old.loop.call_soon_threadsafe(old.loop.stop)
        old.join(5)
        entered, release, published = threading.Event(), threading.Event(), threading.Event()
        original_start = cls.start

        def paused_start(self):
            original_start(self)
            entered.set()
            assert release.wait(10)

        cls.start = paused_start

        def creator():
            inst = cls.get_instance()

            class LosingEvent(threading.Event):
                def wait(self, timeout=None):
                    inst.join()
                    return super().wait(timeout)

            event = LosingEvent()
            event.set()
            inst._running = event
            published.set()

        threading.Thread(target=creator, daemon=True).start()
        assert entered.wait(10)

        def publish_first():
            # Registered after the guard, so it runs before it (LIFO): the holder
            # publishes, then the registered hook runs, then async-retriever's cleanup.
            release.set()
            assert published.wait(10)
            print('late_live_singleton', cls._instance is not None
                  and cls._instance.is_alive(), flush=True)

        atexit.register(publish_first)
        print('reached_end', flush=True)
        """
    )
    try:
        result = _run(code, timeout=60)
    except subprocess.TimeoutExpired as exc:
        pytest.fail("the process hung at exit: " + _stdout(exc))
    assert result.returncode == 0, result.stderr
    assert "reached_end" in result.stdout
    assert "late_live_singleton True" in result.stdout


@pytest.mark.slow
def test_a_late_publication_after_the_hook_ran(async_retriever):
    """F1 (review 2), the reviewer's order: the hook runs while the holder still has the
    lock; the holder publishes afterwards; async-retriever's cleanup then stops the late
    thread with the bounded stop and the process exits."""
    _real_affected(async_retriever)
    code = textwrap.dedent(
        """
        import asyncio, atexit, threading
        import async_retriever._utils as u
        from hms_commander import _hyriver_exit as g

        u.run_in_event_loop(asyncio.sleep(0))
        cls = u._AsyncLoopThread
        old = cls._instance
        old.loop.call_soon_threadsafe(old.loop.stop)
        old.join(5)
        entered, release, published = threading.Event(), threading.Event(), threading.Event()
        original_start = cls.start

        def paused_start(self):
            original_start(self)
            entered.set()
            assert release.wait(10)

        cls.start = paused_start

        def creator():
            inst = cls.get_instance()

            class LosingEvent(threading.Event):
                def wait(self, timeout=None):
                    inst.join()
                    return super().wait(timeout)

            event = LosingEvent()
            event.set()
            inst._running = event
            published.set()

        threading.Thread(target=creator, daemon=True).start()
        assert entered.wait(10)

        def exit_guard():
            # Stands in for the registered hook, run while the old lock is still held.
            print('hook_installed', g.install_bounded_stop(), flush=True)
            release.set()
            assert published.wait(10)
            print('late_live_singleton', cls._instance is not None
                  and cls._instance.is_alive(), flush=True)

        atexit.register(exit_guard)
        print('reached_end', flush=True)
        """
    )
    try:
        result = _run(code, timeout=60)
    except subprocess.TimeoutExpired as exc:
        pytest.fail("the process hung at exit: " + _stdout(exc))
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "reached_end" in out
    assert "hook_installed True" in out
    assert "late_live_singleton True" in out


SAME_NAME_FIXED_STOP = """
def fixed_stop(self):
    if self._running.is_set():
        self.loop.call_soon_threadsafe(self.loop.stop)
        self._running.wait(timeout=0.01)
        self.join(timeout=1)
assert fixed_stop.__code__.co_names == u._AsyncLoopThread.stop.__code__.co_names
u._AsyncLoopThread.stop = fixed_stop
"""

FIXED_SHAPES = {
    # Review 2: a bounded stop() whose referenced names equal the original's exactly.
    "same-names-replaced-at-run-time": SAME_NAME_FIXED_STOP,
    # The same code reporting a later version: not in the allowlist.
    "later-version": "g._installed_version = lambda: '0.19.4'\n",
    # Unknown version (no metadata and no __version__).
    "unknown-version": "g._installed_version = lambda: None\n",
}


def _check_left_alone(code_before: str, shape_code: str, pythonpath: str = ""):
    code = textwrap.dedent(
        """
        import asyncio, logging
        logging.basicConfig(level=logging.DEBUG, format='%(levelname)s %(message)s')
        import async_retriever._utils as u
        from hms_commander import _hyriver_exit as g
        g.logger.setLevel(logging.DEBUG)   # importing hms_commander sets the root to INFO
        """
    ) + code_before + textwrap.dedent(
        """
        u.run_in_event_loop(asyncio.sleep(0))
        instance = u._AsyncLoopThread._instance
        """
    ) + shape_code + textwrap.dedent(
        """
        stop_before = u._AsyncLoopThread.stop
        assert g.stop_needs_guard(u._AsyncLoopThread) is False
        assert g.guard_async_retriever_exit() is False
        assert g._registered is False
        assert g.install_bounded_stop() is False
        assert u._AsyncLoopThread.stop is stop_before
        assert u._AsyncLoopThread._instance is instance and instance.is_alive()
        # Leave a clean exit: stop the loop here instead of in the racy cleanup.
        instance.loop.call_soon_threadsafe(instance.loop.stop)
        instance.join(10)
        u._AsyncLoopThread._instance = None
        print('done', flush=True)
        """
    )
    result = _run(code, timeout=60, pythonpath=pythonpath)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "done"
    assert "DEBUG async-retriever exit guard:" in result.stderr
    assert "doing nothing" in result.stderr
    return result


@pytest.mark.parametrize("shape", sorted(FIXED_SHAPES))
def test_a_fixed_upstream_shape_is_left_alone(async_retriever, shape):
    """F2: anything other than the stock 0.19.3 implementation is not touched, and the
    reason is logged at DEBUG."""
    _real_affected(async_retriever)
    _check_left_alone("", FIXED_SHAPES[shape])


def _copy_package(async_retriever, destination):
    source = os.path.dirname(async_retriever.__file__)
    target = os.path.join(destination, "async_retriever")
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__"))
    return target


def test_a_patched_0193_file_is_left_alone(async_retriever, tmp_path):
    """F2: async-retriever 0.19.3 metadata, but ``_utils.py`` fixed in place (vendor
    patch): the file is not the stock file, so nothing is touched."""
    _real_affected(async_retriever)
    target = _copy_package(async_retriever, str(tmp_path))
    utils = os.path.join(target, "_utils.py")
    with open(utils, "rb") as handle:
        text = handle.read()
    patched = text.replace(b"self._running.wait()  # Wait", b"self._running.wait(1)  # Wait")
    assert patched != text
    with open(utils, "wb") as handle:
        handle.write(patched)
    result = _check_left_alone(
        f"assert u.__file__.startswith({str(tmp_path)!r}), u.__file__\n", "",
        pythonpath=str(tmp_path))
    assert "is not the stock async-retriever" in result.stderr


def test_a_source_stripped_install_is_left_alone(async_retriever, tmp_path):
    """F2: only compiled ``.pyc`` files (source stripped): the file cannot be verified,
    so nothing is touched, even though the code is the stock code."""
    _real_affected(async_retriever)
    import compileall

    target = _copy_package(async_retriever, str(tmp_path))
    assert compileall.compile_dir(target, legacy=True, quiet=1)
    for name in os.listdir(target):
        if name.endswith(".py"):
            os.remove(os.path.join(target, name))
    result = _check_left_alone(
        f"assert u.__file__.endswith('.pyc') and u.__file__.startswith({str(tmp_path)!r})\n",
        "", pythonpath=str(tmp_path))
    assert "source file is not available" in result.stderr


@pytest.mark.slow
def test_pending_work_drains_before_the_loop_stops(async_retriever):
    """F3: a coroutine already running on the shared loop finishes, and its future
    resolves, before async-retriever's cleanup (with the bounded stop) stops the loop."""
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
        g.EXIT_TIMEOUT_S = 10
        assert g.install_bounded_stop() is True
        u._AsyncLoopThread._cleanup()
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
    stop returns within its budget, and asyncio reports no destroyed pending task."""
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
        g.EXIT_TIMEOUT_S = 2
        assert g.install_bounded_stop() is True
        start = time.monotonic()
        u._AsyncLoopThread._cleanup()
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
