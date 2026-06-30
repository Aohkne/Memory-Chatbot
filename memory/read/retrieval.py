import re

from memory.store import index_store, topic_store

STOPWORDS = {
    "tôi", "bạn", "là", "của", "và", "có", "không", "gì", "thì", "à",
    "ơi", "nhé", "vậy", "rồi", "cho", "với", "này", "đó", "the", "a", "is", "are",
}
TIME_HINTS = ("hôm qua", "hôm nay", "tuần trước", "tuần này", "tháng trước", "lúc trước", "trước đây", "đã từng")


def _tokenize(text: str) -> set[str]:
    words = re.findall(r"[\w]+", text.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 1}


def relevant_topics(query: str, min_overlap: int = 1) -> list[str]:
    """Heuristic keyword-overlap retrieval — picks topic slugs whose hook shares words with the query."""
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    matches = []
    for entry in index_store.parse_entries():
        hook_tokens = _tokenize(entry["hook"]) | _tokenize(entry["title"])
        overlap = len(query_tokens & hook_tokens)
        if overlap >= min_overlap:
            slug = entry["filename"].removesuffix(".md")
            matches.append((overlap, slug))

    matches.sort(reverse=True)
    return [slug for _, slug in matches]


def build_context_block(query: str, max_topics: int = 3) -> str:
    slugs = relevant_topics(query)[:max_topics]
    if not slugs:
        return ""

    blocks = []
    for slug in slugs:
        topic = topic_store.read_topic(slug)
        if topic:
            blocks.append(f"### {topic['frontmatter'].get('name', slug)}\n{topic['content']}")

    if not blocks:
        return ""
    return "Thông tin liên quan đã ghi nhớ trước đó:\n\n" + "\n\n".join(blocks)


def mentions_time_reference(query: str) -> bool:
    query_lower = query.lower()
    return any(hint in query_lower for hint in TIME_HINTS)
