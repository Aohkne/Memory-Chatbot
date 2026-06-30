import json
from datetime import datetime, timezone

import config

DEFAULT_STATE = {
    "session_count": 0,
    "last_autodream_at": None,
    "last_autodream_session_count": 0,
}


def load_state() -> dict:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not config.STATE_PATH.exists():
        return dict(DEFAULT_STATE)
    with open(config.STATE_PATH, "r", encoding="utf-8") as f:
        return {**DEFAULT_STATE, **json.load(f)}


def save_state(state: dict) -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def should_run_autodream(state: dict) -> bool:
    if state["last_autodream_at"] is None:
        sessions_since = state["session_count"] - state["last_autodream_session_count"]
        return sessions_since >= config.AUTODREAM_MIN_SESSIONS

    last_run = datetime.fromisoformat(state["last_autodream_at"])
    hours_since = (datetime.now(timezone.utc) - last_run).total_seconds() / 3600
    sessions_since = state["session_count"] - state["last_autodream_session_count"]
    return hours_since >= config.AUTODREAM_MIN_HOURS and sessions_since >= config.AUTODREAM_MIN_SESSIONS


def mark_autodream_ran(state: dict) -> None:
    state["last_autodream_at"] = datetime.now(timezone.utc).isoformat()
    state["last_autodream_session_count"] = state["session_count"]
    save_state(state)
