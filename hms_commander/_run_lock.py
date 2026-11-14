"""
Cross-process locks that give one compute exclusive use of its output files.

HmsCmdr proves that a run computed by comparing the run's log and results DSS
file before and after HEC-HMS runs. That proof only holds if no other compute
writes the same files in between. :class:`OutputLock` takes one OS-level lock
per output path (and per copied destination folder), from before the
snapshot until verification and clean-up are done.

How a lock works:

- Each locked path ``P`` has a lock file ``P.hms-commander-lock`` beside it.
- The lock is an OS byte-range lock on that file: ``msvcrt.locking`` on
  Windows, ``fcntl.flock`` elsewhere. The operating system releases it when
  the holding process exits for any reason, so a crashed holder never blocks
  the project. The next holder finds the dead holder's details still in the
  file, logs a warning that it is taking over a stale lock, and proceeds.
- On release the holder clears the file, unlocks it and deletes it. On POSIX,
  a waiter that then locks the deleted file notices that the path no longer
  names the file it holds and tries again, so two holders cannot result.
- Threads in one process conflict like separate processes. A thread that
  asks again for a lock it already holds gets ``RuntimeError`` at once
  instead of waiting for itself.
- Waiting is bounded: after ``timeout`` seconds, ``TimeoutError`` is raised,
  naming the current holder.

Locks on a network share depend on the share honouring byte-range locks
(SMB does; NFS ``flock`` may be local to one client).
"""

from __future__ import annotations

import json
import os
import socket
import threading
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .LoggingConfig import get_logger

logger = get_logger(__name__)

LOCK_SUFFIX = ".hms-commander-lock"
_POLL_SECONDS = 0.2
# Windows locks one byte far beyond the owner record, so other processes can
# still read the record to report who holds the lock.
_WINDOWS_LOCK_OFFSET = 0x7FFF0000

if os.name == "nt":
    import msvcrt
else:
    import fcntl

# Lock files held by this process: normalized path -> thread ident
_held: Dict[str, int] = {}
_held_guard = threading.Lock()


def lock_path_for(path: Path) -> Path:
    """The lock file that guards ``path``."""
    path = Path(path)
    return path.with_name(path.name + LOCK_SUFFIX)


def _key(path: Path) -> str:
    text = os.path.abspath(str(path))
    return os.path.normcase(text)


def _try_lock(fd: int) -> bool:
    try:
        if os.name == "nt":
            os.lseek(fd, _WINDOWS_LOCK_OFFSET, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def _unlock(fd: int) -> None:
    if os.name == "nt":
        os.lseek(fd, _WINDOWS_LOCK_OFFSET, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(fd, fcntl.LOCK_UN)


def _read_record(path: Path) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read(4096).strip("\x00 \r\n")
    except OSError:
        return ""


class _OneLock:
    def __init__(self, path: Path, purpose: str):
        self.path = Path(path)
        self.purpose = purpose
        self.fd: Optional[int] = None

    def acquire(self, deadline: float) -> None:
        key = _key(self.path)
        me = threading.get_ident()
        with _held_guard:
            if _held.get(key) == me:
                raise RuntimeError(
                    f"This thread is already computing with {self.path.name[:-len(LOCK_SUFFIX)]} "
                    "locked; a nested compute on the same outputs cannot be verified."
                )
        waited_logged = False
        while True:
            fd = os.open(str(self.path), os.O_RDWR | os.O_CREAT, 0o644)
            if _try_lock(fd):
                if os.name != "nt":
                    # The file may have been deleted by its previous holder
                    # after this process opened it; then try again.
                    try:
                        same = os.path.samestat(os.fstat(fd), os.stat(self.path))
                    except FileNotFoundError:
                        same = False
                    if not same:
                        _unlock(fd)
                        os.close(fd)
                        continue
                break
            os.close(fd)
            if time.monotonic() >= deadline:
                holder = _read_record(self.path) or "unknown holder"
                raise TimeoutError(
                    f"Timed out waiting for another compute that is using "
                    f"{self.path.name[:-len(LOCK_SUFFIX)]} ({self.path.parent}). "
                    f"Holder: {holder}"
                )
            if not waited_logged:
                holder = _read_record(self.path) or "unknown holder"
                logger.info(
                    f"Waiting for another compute that is using "
                    f"{self.path.name[:-len(LOCK_SUFFIX)]}. Holder: {holder}"
                )
                waited_logged = True
            time.sleep(_POLL_SECONDS)

        self.fd = fd
        previous = _read_record(self.path)
        if previous:
            logger.warning(
                f"Taking over a stale lock on {self.path.name[:-len(LOCK_SUFFIX)]} "
                f"left by a compute that ended without releasing it: {previous}"
            )
        record = json.dumps({
            "pid": os.getpid(),
            "host": socket.gethostname(),
            "thread": me,
            "purpose": self.purpose,
            "since": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        })
        os.lseek(fd, 0, os.SEEK_SET)
        os.ftruncate(fd, 0)
        os.write(fd, record.encode("utf-8"))
        with _held_guard:
            _held[key] = me

    def release(self) -> None:
        if self.fd is None:
            return
        fd, self.fd = self.fd, None
        with _held_guard:
            _held.pop(_key(self.path), None)
        try:
            os.ftruncate(fd, 0)
        except OSError:
            pass
        try:
            _unlock(fd)
        finally:
            os.close(fd)
        try:
            # On Windows this fails while another process has the file open
            # (waiting for it); that waiter then holds and later deletes it.
            self.path.unlink()
        except OSError:
            pass


class OutputLock:
    """
    Exclusive use of a set of paths across threads and processes.

    Args:
        paths: The output files or folders to guard. Duplicates and None are
            ignored; locks are taken in a fixed (sorted) order, so two
            computes that need overlapping sets cannot deadlock.
        timeout: Seconds to wait for all locks before ``TimeoutError``.
        purpose: Text recorded in the lock file, shown to waiters.
    """

    def __init__(self, paths: Iterable[Optional[Path]], timeout: float, purpose: str = ""):
        keys: Dict[str, Path] = {}
        for p in paths:
            if p is not None:
                keys.setdefault(_key(p), Path(p))
        self._locks: List[_OneLock] = [
            _OneLock(lock_path_for(keys[k]), purpose) for k in sorted(keys)
        ]
        self._timeout = max(0.0, float(timeout))

    def __enter__(self) -> "OutputLock":
        deadline = time.monotonic() + self._timeout
        taken: List[_OneLock] = []
        try:
            for lock in self._locks:
                lock.acquire(deadline)
                taken.append(lock)
        except BaseException:
            for lock in reversed(taken):
                lock.release()
            raise
        return self

    def __exit__(self, *exc) -> None:
        for lock in reversed(self._locks):
            lock.release()
