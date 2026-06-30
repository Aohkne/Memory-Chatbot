from datetime import datetime, timezone, timedelta

import config
import state as state_module


def _make_state(session_count=0, last_autodream_at=None, last_autodream_session_count=0):
    return {
        "session_count": session_count,
        "last_autodream_at": last_autodream_at,
        "last_autodream_session_count": last_autodream_session_count,
    }


# --- Lần đầu tiên (last_autodream_at = None) ---

def test_first_run_enough_sessions(monkeypatch):
    monkeypatch.setattr(config, "AUTODREAM_MIN_SESSIONS", 5)
    s = _make_state(session_count=5)
    assert state_module.should_run_autodream(s) is True


def test_first_run_not_enough_sessions(monkeypatch):
    monkeypatch.setattr(config, "AUTODREAM_MIN_SESSIONS", 5)
    s = _make_state(session_count=4)
    assert state_module.should_run_autodream(s) is False


# --- Các lần sau (cần cả 2 điều kiện) ---

def test_both_conditions_met(monkeypatch):
    monkeypatch.setattr(config, "AUTODREAM_MIN_HOURS", 24)
    monkeypatch.setattr(config, "AUTODREAM_MIN_SESSIONS", 5)
    last = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    s = _make_state(session_count=10, last_autodream_at=last, last_autodream_session_count=5)
    assert state_module.should_run_autodream(s) is True


def test_hours_not_met(monkeypatch):
    monkeypatch.setattr(config, "AUTODREAM_MIN_HOURS", 24)
    monkeypatch.setattr(config, "AUTODREAM_MIN_SESSIONS", 5)
    last = (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat()
    s = _make_state(session_count=10, last_autodream_at=last, last_autodream_session_count=5)
    assert state_module.should_run_autodream(s) is False


def test_sessions_not_met(monkeypatch):
    monkeypatch.setattr(config, "AUTODREAM_MIN_HOURS", 24)
    monkeypatch.setattr(config, "AUTODREAM_MIN_SESSIONS", 5)
    last = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    s = _make_state(session_count=7, last_autodream_at=last, last_autodream_session_count=5)
    # sessions_since = 7 - 5 = 2 < 5
    assert state_module.should_run_autodream(s) is False


def test_mark_autodream_ran_updates_state(tmp_path):
    s = _make_state(session_count=10)
    state_module.mark_autodream_ran(s)
    assert s["last_autodream_at"] is not None
    assert s["last_autodream_session_count"] == 10
