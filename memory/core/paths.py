import re

import config


def ensure_dirs() -> None:
    config.MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    config.TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_")
    return slug or "topic"


def topic_path(slug: str):
    return config.MEMORY_DIR / f"{slug}.md"


def transcript_path(session_id: str):
    return config.TRANSCRIPTS_DIR / f"{session_id}.jsonl"
