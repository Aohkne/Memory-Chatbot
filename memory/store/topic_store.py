import yaml

from memory.core import paths

FRONTMATTER_RE_START = "---\n"


def write_topic(slug: str, name: str, description: str, mem_type: str, content: str) -> None:
    paths.ensure_dirs()
    frontmatter = yaml.safe_dump(
        {"name": name, "description": description, "metadata": {"type": mem_type}},
        allow_unicode=True,
        sort_keys=False,
    )
    text = f"---\n{frontmatter}---\n\n{content.strip()}\n"
    paths.topic_path(slug).write_text(text, encoding="utf-8")


def read_topic(slug: str) -> dict | None:
    path = paths.topic_path(slug)
    if not path.exists():
        return None
    raw = path.read_text(encoding="utf-8")
    parts = raw.split("---\n", 2)
    if len(parts) < 3:
        return {"frontmatter": {}, "content": raw.strip()}
    frontmatter = yaml.safe_load(parts[1]) or {}
    return {"frontmatter": frontmatter, "content": parts[2].strip()}


def list_topics() -> list[str]:
    paths.ensure_dirs()
    from config import MEMORY_DIR
    return sorted(p.stem for p in MEMORY_DIR.glob("*.md") if p.name != "MEMORY.md")


def delete_topic(slug: str) -> None:
    path = paths.topic_path(slug)
    if path.exists():
        path.unlink()
