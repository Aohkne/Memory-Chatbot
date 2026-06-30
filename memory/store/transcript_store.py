import json
from datetime import datetime, timezone

import config
from memory.core import paths


def append_turn(session_id: str, role: str, content: str) -> None:
    paths.ensure_dirs()
    line = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "role": role,
        "content": content,
    }
    with open(paths.transcript_path(session_id), "a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


def grep(query: str, since: str | None = None, max_results: int = 20) -> list[dict]:
    """Search across all transcript files for a substring match. Never loads full files into context."""
    paths.ensure_dirs()
    query_lower = query.lower()
    since_dt = datetime.fromisoformat(since) if since else None
    results = []

    for path in sorted(config.TRANSCRIPTS_DIR.glob("*.jsonl")):
        session_id = path.stem
        with open(path, "r", encoding="utf-8") as f:
            for raw_line in f:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    entry = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                if query_lower not in entry["content"].lower():
                    continue
                if since_dt and datetime.fromisoformat(entry["timestamp"]) < since_dt:
                    continue
                results.append({**entry, "session_id": session_id})
                if len(results) >= max_results:
                    return results
    return results


def all_turns_since(since: str | None = None) -> list[dict]:
    """Used by autoDream's Gather signal phase — still filtered by time, never the full raw log."""
    paths.ensure_dirs()
    since_dt = datetime.fromisoformat(since) if since else None
    results = []
    for path in sorted(config.TRANSCRIPTS_DIR.glob("*.jsonl")):
        session_id = path.stem
        with open(path, "r", encoding="utf-8") as f:
            for raw_line in f:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    entry = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                if since_dt and datetime.fromisoformat(entry["timestamp"]) < since_dt:
                    continue
                results.append({**entry, "session_id": session_id})
    return results
