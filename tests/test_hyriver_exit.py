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
    with pytest.raises(subprocess.TimeoutExpired):
        _run(LOSING_RACE + "print('done', flush=True)\n", timeout=20)


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
    class Broken:
        def is_alive(self):
            raise RuntimeError("boom")

    def stop(self):
        self._running.wait()

    loop_class = _fake_module(monkeypatch, stop)
    loop_class._instance = Broken()
    assert _hyriver_exit.stop_async_retriever_loop() is False


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
