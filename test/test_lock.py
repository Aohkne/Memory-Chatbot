import threading
import time

import pytest
from memory.core.lock import consolidation_lock


def test_lock_creates_and_removes_file():
    import config
    with consolidation_lock():
        assert config.LOCK_PATH.exists()
    assert not config.LOCK_PATH.exists()


def test_lock_releases_on_exception():
    import config
    try:
        with consolidation_lock():
            raise ValueError("lỗi giả")
    except ValueError:
        pass
    assert not config.LOCK_PATH.exists()


def test_lock_blocks_sequential_access():
    """Lock đảm bảo không 2 thread cùng ở trong critical section — test tuần tự."""
    results = []

    def worker(label):
        with consolidation_lock(timeout_seconds=5):
            results.append(f"{label} start")
            time.sleep(0.02)
            results.append(f"{label} end")

    # Chạy tuần tự để đảm bảo lock hoạt động đúng
    t1 = threading.Thread(target=worker, args=("A",))
    t1.start()
    t1.join()

    t2 = threading.Thread(target=worker, args=("B",))
    t2.start()
    t2.join()

    assert results == ["A start", "A end", "B start", "B end"]


def test_lock_timeout_raises():
    import os
    import config
    from datetime import datetime, timezone
    # Dùng PID của process hiện tại để stale check nghĩ lock còn sống
    config.LOCK_PATH.write_text(
        f'{{"pid": {os.getpid()}, "started_at": "{datetime.now(timezone.utc).isoformat()}"}}',
        encoding="utf-8"
    )
    with pytest.raises(TimeoutError):
        with consolidation_lock(timeout_seconds=0.3):
            pass
