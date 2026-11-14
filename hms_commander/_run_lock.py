"""
Cross-process locks and no-replace moves for HmsCmdr's run verification.

HmsCmdr proves that a run computed by comparing the run's log and results DSS
file before and after HEC-HMS runs. That proof only holds if no other compute
writes the same files in between. :class:`OutputLock` takes one OS-level lock
per output path (and per copied destination folder), from before the
snapshot until verification and clean-up are done.

How a lock works:

- Each locked path ``P`` has a lock file ``P.hms-commander-lock`` beside it.
- The lock is an OS lock on that file: ``msvcrt.locking`` (a byte-range lock)
  on Windows, ``fcntl.flock`` elsewhere. The operating system releases it when
  the holding process exits for any reason, so a crashed holder never blocks
  the project. The next holder finds the dead holder's record still in the
  file, logs a warning that it is taking over a stale lock, and proceeds.
- **Lock files are persistent.** On release the holder clears its record and
  unlocks, but never deletes the file, on any platform. Deleting it would let
  two processes hold "the" lock at once on POSIX: a waiter can lock the old
  file just before the releasing process removes its name, and a third
  process then creates and locks a new file under the same name. With
  persistent files every process always locks the same file. An empty lock
  file is an unlocked lock; it can be deleted by hand when no compute runs.
- After locking, a holder checks that the path still names the file it
  locked (for example, if someone deleted the lock file by hand) and
  otherwise tries again.
- Threads in one process conflict like separate processes. A thread that
  asks again for a lock it already holds gets ``RuntimeError`` at once
  instead of waiting for itself.
- Waiting is bounded by a deadline (``time.monotonic()``); when it passes,
  ``TimeoutError`` is raised, naming the current holder.

Locks on a network share depend on the server, protocol and every client
honouring the locks. Tools that do not use these locks (the HEC-HMS GUI, for
example) are not kept out.
"""

from __future__ import annotations

import ctypes
import errno
import json
import os
import shutil
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


def remaining(deadline: float) -> float:
    """Seconds left until ``deadline`` (a ``time.monotonic()`` value); never negative."""
    return max(0.0, deadline - time.monotonic())


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


def _same_file(fd: int, path: Path) -> bool:
    try:
        return os.path.samestat(os.fstat(fd), os.stat(path))
    except OSError:
        return False


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

    @property
    def _target(self) -> str:
        return self.path.name[:-len(LOCK_SUFFIX)]

    def acquire(self, deadline: float) -> None:
        key = _key(self.path)
        me = threading.get_ident()
        with _held_guard:
            if _held.get(key) == me:
                raise RuntimeError(
                    f"This thread is already computing with {self._target} locked; "
                    "a nested compute on the same outputs cannot be verified."
                )
        waited_logged = False
        while True:
            fd = os.open(str(self.path), os.O_RDWR | os.O_CREAT, 0o644)
            if _try_lock(fd):
                if _same_file(fd, self.path):
                    break
                # The lock file was deleted or replaced after it was opened
                # (by hand; HMS Commander never deletes it): lock the file the
                # path names now.
                _unlock(fd)
                os.close(fd)
                continue
            os.close(fd)
            if time.monotonic() >= deadline:
                holder = _read_record(self.path) or "unknown holder"
                raise TimeoutError(
                    f"Timed out waiting for another compute that is using "
                    f"{self._target} ({self.path.parent}). Holder: {holder}"
                )
            if not waited_logged:
                holder = _read_record(self.path) or "unknown holder"
                logger.info(
                    f"Waiting for another compute that is using {self._target}. "
                    f"Holder: {holder}"
                )
                waited_logged = True
            time.sleep(min(_POLL_SECONDS, max(0.01, remaining(deadline))))

        self.fd = fd
        previous = _read_record(self.path)
        if previous:
            logger.warning(
                f"Taking over a stale lock on {self._target} left by a compute "
                f"that ended without releasing it: {previous}"
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
        """Clear the record and unlock. The lock file itself is kept (see the module docstring)."""
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


class OutputLock:
    """
    Exclusive use of a set of paths across threads and processes.

    Args:
        paths: The output files or folders to guard. Duplicates and None are
            ignored; locks are taken in a fixed (sorted) order, so two
            computes that need overlapping sets cannot deadlock.
        deadline: ``time.monotonic()`` value after which waiting stops with
            ``TimeoutError``. The caller's whole time budget, so that time
            spent waiting is not given again to the work that follows.
        purpose: Text recorded in the lock file, shown to waiters.
    """

    def __init__(self, paths: Iterable[Optional[Path]], deadline: float, purpose: str = ""):
        keys: Dict[str, Path] = {}
        for p in paths:
            if p is not None:
                keys.setdefault(_key(p), Path(p))
        self._locks: List[_OneLock] = [
            _OneLock(lock_path_for(keys[k]), purpose) for k in sorted(keys)
        ]
        self._deadline = deadline

    def __enter__(self) -> "OutputLock":
        taken: List[_OneLock] = []
        try:
            for lock in self._locks:
                lock.acquire(self._deadline)
                taken.append(lock)
        except BaseException:
            for lock in reversed(taken):
                lock.release()
            raise
        return self

    def __exit__(self, *exc) -> None:
        for lock in reversed(self._locks):
            lock.release()


# ---------------------------------------------------------------------------
# Moving a file without ever replacing the destination
# ---------------------------------------------------------------------------

_AT_FDCWD = -100
_RENAME_NOREPLACE = 1


def _renameat2_noreplace(src: Path, dst: Path) -> bool:
    """
    Linux ``renameat2(..., RENAME_NOREPLACE)``: an atomic rename that fails if
    ``dst`` exists (as any kind of entry, including a dangling symlink).

    Returns:
        True if moved; False if this system or file system does not provide it.

    Raises:
        FileExistsError: If ``dst`` exists.
    """
    if not os.uname().sysname == "Linux":
        return False
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        fn = libc.renameat2
    except (OSError, AttributeError):
        return False
    fn.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    fn.restype = ctypes.c_int
    if fn(_AT_FDCWD, os.fsencode(str(src)), _AT_FDCWD, os.fsencode(str(dst)), _RENAME_NOREPLACE) == 0:
        return True
    err = ctypes.get_errno()
    if err == errno.EEXIST:
        raise FileExistsError(err, os.strerror(err), str(dst))
    if err in (errno.ENOSYS, errno.EINVAL, getattr(errno, "ENOTSUP", -1), getattr(errno, "EOPNOTSUPP", -1)):
        return False
    raise OSError(err, os.strerror(err), str(src))


def _exclusive_copy(src: Path, dst: Path) -> None:
    """Create ``dst`` with ``O_CREAT | O_EXCL`` (fails if it exists, or is a symlink), copy ``src`` into it."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(str(dst), flags, 0o644)
    try:
        with os.fdopen(fd, "wb") as out, open(src, "rb") as inp:
            shutil.copyfileobj(inp, out, 1024 * 1024)
            out.flush()
            os.fsync(out.fileno())
    except BaseException:
        try:
            os.unlink(dst)          # only the file this call created
        except OSError:
            pass
        raise
    shutil.copystat(src, dst)


def move_no_replace(src: Path, dst: Path) -> None:
    """
    Move ``src`` to ``dst``, never replacing an existing ``dst``.

    In order, the first operation the system supports is used; each fails
    with ``FileExistsError`` if ``dst`` exists:

    1. ``os.link(src, dst)`` then ``os.unlink(src)``;
    2. Windows: ``os.rename``, which does not replace an existing file;
       Linux: ``renameat2(RENAME_NOREPLACE)``;
    3. otherwise (POSIX without hard links or renameat2): create ``dst`` with
       ``O_CREAT | O_EXCL | O_NOFOLLOW``, copy ``src`` into it, then delete
       ``src``.

    There is never a check-then-rename. If no step works, ``src`` is left
    where it was and the error propagates.

    Raises:
        FileExistsError: If ``dst`` exists.
        OSError: If the move fails for another reason.
    """
    src, dst = Path(src), Path(dst)
    try:
        os.link(src, dst)
    except FileExistsError:
        raise
    except OSError:
        pass            # no hard links here; try the next operation
    else:
        os.unlink(src)
        return
    if os.name == "nt":
        os.rename(src, dst)         # MoveFileEx without REPLACE_EXISTING
        return
    if _renameat2_noreplace(src, dst):
        return
    _exclusive_copy(src, dst)
    os.unlink(src)
