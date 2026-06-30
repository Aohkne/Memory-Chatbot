import json
import re
import threading

import llm_client
from memory.core import lock, paths
from memory.store import index_store, topic_store

EXTRACT_PROMPT = """Bạn là bộ trích xuất memory chạy nền cho một chatbot. Index các chủ đề đã biết:

{index}

Lượt hội thoại vừa xảy ra:
User: {user_message}
Assistant: {assistant_message}

Có fact nào về người dùng đáng lưu lâu dài không (sở thích, thông tin cá nhân, dự án đang làm, v.v.)? Bỏ qua câu hỏi vu vơ, lời chào, hay thông tin chỉ có giá trị tức thời.

Trả lời CHỈ một JSON object, không thêm chữ nào khác:
{{"should_save": true/false, "slug": "...", "title": "...", "hook": "...", "type": "user|project|reference", "content": "..."}}
Nếu should_save là false, các trường còn lại có thể để rỗng.
"""


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {"should_save": False}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {"should_save": False}


def _run(user_message: str, assistant_message: str) -> None:
    index = index_store.read_index()
    prompt = EXTRACT_PROMPT.format(index=index, user_message=user_message, assistant_message=assistant_message)
    response = llm_client.get_classifier_model().invoke([{"role": "user", "content": prompt}])
    data = _extract_json(response.content)

    if not data.get("should_save"):
        return

    slug = paths.slugify(data["slug"])
    with lock.consolidation_lock():
        existing = topic_store.read_topic(slug)
        content = data["content"]
        if existing:
            content = existing["content"] + "\n\n" + content
        topic_store.write_topic(slug, data["title"], data["hook"], data.get("type", "user"), content)
        index_store.append_entry(data["title"], f"{slug}.md", data["hook"])


def maybe_extract_async(user_message: str, assistant_message: str) -> threading.Thread:
    thread = threading.Thread(target=_run, args=(user_message, assistant_message), daemon=False)
    thread.start()
    return thread
