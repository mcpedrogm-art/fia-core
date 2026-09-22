"""TEST records: execution output plus integrity hashes, without a larger evidence system."""

import contextlib
import datetime as dt
import json
import os
import subprocess
import threading
import time
from pathlib import Path

from .model import file_sha256

TEST_DIR = Path(".fia") / "tests"
LOCK_NAME = ".lock"
DEFAULT_TIMEOUT = None  # seconds; None = no limit (opt in via `fia test --timeout`)
_STALE_LOCK_AFTER = 120.0  # seconds; recovers from a crashed process holding the lock


def _now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _dir(root, create=True):
    path = Path(root) / TEST_DIR
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


@contextlib.contextmanager
def _locked(root, timeout=10.0, poll=0.05):
    """A simple cross-platform mutual-exclusion lock for `.fia/tests/`.

    Prevents two concurrent `fia test` runs (e.g. two agents working on the
    same project) from computing the same TEST-NNN id and overwriting each
    other's record. The holder refreshes the lock while it runs, so a test
    longer than the stale window is never mistaken for a crashed holder.
    """
    lock_path = _dir(root) / LOCK_NAME
    deadline = time.monotonic() + timeout
    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            break
        except FileExistsError:
            try:
                if time.monotonic() - lock_path.stat().st_mtime > _STALE_LOCK_AFTER:
                    lock_path.unlink(missing_ok=True)
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() > deadline:
                raise TimeoutError(
                    "No se pudo adquirir el lock de .fia/tests/ (otro `fia test` en curso)")
            time.sleep(poll)
    stop = threading.Event()

    def heartbeat():
        while not stop.wait(_STALE_LOCK_AFTER / 4):
            try:
                os.utime(lock_path, None)
            except OSError:
                return

    keeper = threading.Thread(target=heartbeat, daemon=True)
    keeper.start()
    try:
        yield
    finally:
        stop.set()
        keeper.join(timeout=1.0)
        lock_path.unlink(missing_ok=True)


def next_id(root):
    numbers = []
    for path in _dir(root).glob("TEST-*.json"):
        try:
            numbers.append(int(path.stem.split("-")[1]))
        except (IndexError, ValueError):
            pass
    return f"TEST-{(max(numbers) + 1) if numbers else 1:03d}"


def _record_path(root, test_id, create=True):
    return _dir(root, create=create) / f"{test_id}.json"


def load(root, test_id):
    path = _record_path(root, test_id, create=False)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def records(root):
    result = []
    directory = _dir(root, create=False)
    if not directory.exists():
        return result
    for path in sorted(directory.glob("TEST-*.json")):
        item = load(root, path.stem)
        result.append(item or {"id": path.stem, "invalid": True})
    return result


def validate(root, record):
    errors = []
    required = ("id", "command", "exit_code", "task_sha256", "stdout_sha256",
                "stderr_sha256", "stdout_file", "stderr_file", "started_at",
                "finished_at")
    test_id = record.get("id", "?")
    for field in required:
        if field not in record:
            errors.append(f"{test_id}: falta {field}")
    for field in ("stdout_file", "stderr_file"):
        name = record.get(field)
        if not name:
            continue
        path = _dir(root, create=False) / name
        if not path.exists():
            errors.append(f"{test_id}: falta {name}")
        elif file_sha256(path) != record.get(field.replace("_file", "_sha256")):
            errors.append(f"{test_id}: {name} no coincide con su hash")
    return errors


def run(root, command, timeout=DEFAULT_TIMEOUT):
    """Run a command in the project and persist a TEST record.

    If `timeout` (seconds) elapses, the command is killed, the record is
    still written (exit_code=None, timed_out=True) so there is always a
    trace, and it can never count as a passing TEST.
    """
    root = Path(root).resolve()
    with _locked(root):
        test_id = next_id(root)
        started = _now()
        start = time.monotonic()
        timed_out = False
        try:
            completed = subprocess.run(command, cwd=str(root), capture_output=True, timeout=timeout)
            exit_code, stdout, stderr = completed.returncode, completed.stdout, completed.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            exit_code = None
            stdout = exc.stdout or b""
            stderr = (exc.stderr or b"") + f"\n[fia] comando cancelado tras {timeout}s (timeout)".encode()
        finished = _now()
        out_name, err_name = f"{test_id}.stdout.txt", f"{test_id}.stderr.txt"
        directory = _dir(root)
        (directory / out_name).write_bytes(stdout)
        (directory / err_name).write_bytes(stderr)
        task_path = root / "TASK.md"
        record = {
            "schema": 1,
            "id": test_id,
            "command": list(command),
            "exit_code": exit_code,
            "timed_out": timed_out,
            "duration_s": round(time.monotonic() - start, 3),
            "started_at": started,
            "finished_at": finished,
            "task_sha256": file_sha256(task_path) if task_path.exists() else None,
            "stdout_file": out_name,
            "stderr_file": err_name,
            "stdout_sha256": file_sha256(directory / out_name),
            "stderr_sha256": file_sha256(directory / err_name),
        }
        _record_path(root, test_id).write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return record
