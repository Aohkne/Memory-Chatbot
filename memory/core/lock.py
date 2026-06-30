import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone

import config
from memory.core import paths


def _is_stale(lock_data: dict) -> bool:
    started_at = datetime.fromisoformat(lock_data["started_at"])
    age_minutes = (datetime.now(timezone.utc) - started_at).total_seconds() / 60
    if age_minutes > config.LOCK_STALE_MINUTES:
        return True
    try:
        os.kill(lock_data["pid"], 0)
        return False
    except OSError:
        return True


@contextmanager
def consolidation_lock(timeout_seconds: float = 30, poll_interval: float = 0.2):
    paths.ensure_dirs()
    deadline = time.time() + timeout_seconds
    acquired = False
    try:
        while time.time() < deadline:
            if config.LOCK_PATH.exists():
                try:
                    lock_data = json.loads(config.LOCK_PATH.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    lock_data = None
                if lock_data and not _is_stale(lock_data):
                    time.sleep(poll_interval)
                    continue
            config.LOCK_PATH.write_text(
                json.dumps({"pid": os.getpid(), "started_at": datetime.now(timezone.utc).isoformat()}),
                encoding="utf-8",
            )
            acquired = True
            break
        if not acquired:
            raise TimeoutError("Không lấy được consolidation lock sau khi chờ.")
        yield
    finally:
        if acquired and config.LOCK_PATH.exists():
            config.LOCK_PATH.unlink()
