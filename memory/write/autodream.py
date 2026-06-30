import json
import re
import threading

import llm_client
import state as state_module
from memory.core import lock, paths
from memory.store import index_store, topic_store, transcript_store

CONSOLIDATE_PROMPT = """Bạn đang chạy autoDream — consolidation nền định kỳ cho memory của chatbot.

Phase 1 (Orient) — Index hiện có:
{index}

Nội dung đầy đủ các topic hiện có:
{topics_dump}

Phase 2 (Gather signal) — Các lượt hội thoại mới kể từ lần consolidate trước:
{recent_turns}

Phase 3 (Consolidate): Hãy đề xuất các thay đổi cần ghi vào memory: tạo topic mới cho fact chưa có, cập nhật/hợp nhất topic trùng lặp. Bỏ qua nếu không có gì đáng cập nhật.

Trả lời CHỈ JSON:
{{"updates": [{{"slug": "...", "title": "...", "hook": "...", "type": "user|project|reference", "content": "nội dung đầy đủ sau khi hợp nhất"}}]}}
Nếu không có gì cần cập nhật, trả {{"updates": []}}.
"""

PRUNE_PROMPT = """Phase 4 (Prune & index) của autoDream.

Danh sách topic hiện có (sau khi consolidate):
{topics_dump}

Hãy rà soát: topic nào lỗi thời, trùng lặp, hoặc không còn giá trị thì đánh dấu xóa. Với các topic còn giữ, viết lại "hook" (tóm tắt 1 dòng) cho gọn nếu cần.

Trả lời CHỈ JSON:
{{"keep": [{{"slug": "...", "title": "...", "hook": "..."}}], "delete": ["slug1", "slug2"]}}
"""


def _extract_json(text: str, default: dict) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return default
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return default


def _dump_topics() -> str:
    parts = []
    for slug in topic_store.list_topics():
        topic = topic_store.read_topic(slug)
        if topic:
            parts.append(f"## {slug}\n{topic['content']}")
    return "\n\n".join(parts) if parts else "(chưa có topic nào)"


def _dump_recent_turns(since: str | None) -> str:
    turns = transcript_store.all_turns_since(since)
    if not turns:
        return "(không có lượt hội thoại mới)"
    lines = [f"[{t['session_id']}] {t['role']}: {t['content']}" for t in turns]
    return "\n".join(lines)


def _phase_consolidate(since: str | None) -> None:
    prompt = CONSOLIDATE_PROMPT.format(
        index=index_store.read_index(),
        topics_dump=_dump_topics(),
        recent_turns=_dump_recent_turns(since),
    )
    response = llm_client.get_classifier_model().invoke([{"role": "user", "content": prompt}])
    data = _extract_json(response.content, {"updates": []})

    for update in data.get("updates", []):
        slug = paths.slugify(update["slug"])
        topic_store.write_topic(
            slug, update["title"], update["hook"], update.get("type", "user"), update["content"]
        )
        index_store.append_entry(update["title"], f"{slug}.md", update["hook"])


def _phase_prune_and_index() -> None:
    prompt = PRUNE_PROMPT.format(topics_dump=_dump_topics())
    response = llm_client.get_classifier_model().invoke([{"role": "user", "content": prompt}])
    data = _extract_json(response.content, {"keep": [], "delete": []})

    for slug in data.get("delete", []):
        topic_store.delete_topic(paths.slugify(slug))

    keep = data.get("keep")
    if keep:
        entries = [{"title": k["title"], "filename": f"{paths.slugify(k['slug'])}.md", "hook": k["hook"]} for k in keep]
        index_store.rewrite_index(entries)


def _run(state: dict) -> None:
    with lock.consolidation_lock(timeout_seconds=60):
        since = state.get("last_autodream_at")
        _phase_consolidate(since)
        _phase_prune_and_index()
    state_module.mark_autodream_ran(state)


def maybe_run_async(state: dict) -> threading.Thread | None:
    if not state_module.should_run_autodream(state):
        return None
    thread = threading.Thread(target=_run, args=(state,), daemon=False)
    thread.start()
    return thread
