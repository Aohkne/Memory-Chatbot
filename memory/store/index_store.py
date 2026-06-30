import re

import config
from memory.core import paths

HEADER = "# MEMORY INDEX\n\n"
ENTRY_RE = re.compile(r"^- \[(?P<title>.*?)\]\((?P<filename>.*?)\) — (?P<hook>.*)$")


def read_index() -> str:
    paths.ensure_dirs()
    if not config.INDEX_PATH.exists():
        config.INDEX_PATH.write_text(HEADER, encoding="utf-8")
    return config.INDEX_PATH.read_text(encoding="utf-8")


def parse_entries() -> list[dict]:
    entries = []
    for line in read_index().splitlines():
        m = ENTRY_RE.match(line.strip())
        if m:
            entries.append(m.groupdict())
    return entries


def append_entry(title: str, filename: str, hook: str) -> None:
    content = read_index()
    line = f"- [{title}]({filename}) — {hook}\n"
    if line.strip() in content:
        return
    if not content.endswith("\n"):
        content += "\n"
    config.INDEX_PATH.write_text(content + line, encoding="utf-8")


def rewrite_index(entries: list[dict]) -> None:
    lines = [HEADER]
    for e in entries:
        lines.append(f"- [{e['title']}]({e['filename']}) — {e['hook']}\n")
    config.INDEX_PATH.write_text("".join(lines), encoding="utf-8")
