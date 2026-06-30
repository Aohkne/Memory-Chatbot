import json
import re

import llm_client
from memory.core import lock, paths
from memory.store import index_store, topic_store

CLASSIFY_PROMPT = """Bạn là bộ phân loại memory cho một chatbot. Dưới đây là index các chủ đề (topic) đã biết:

{index}

Người dùng vừa yêu cầu ghi nhớ nội dung sau:
"{text}"

Hãy quyết định nội dung này thuộc topic nào. Nếu khớp với topic đã có trong index, dùng lại đúng "filename" (bỏ phần .md) làm slug. Nếu không khớp, đề xuất slug mới ngắn gọn bằng tiếng Anh, không dấu, dùng dấu gạch dưới.

Trả lời CHỈ một JSON object theo đúng format, không thêm chữ nào khác:
{{"slug": "...", "title": "Tiêu đề ngắn bằng tiếng Việt", "hook": "tóm tắt 1 dòng bằng tiếng Việt", "type": "user|project|reference", "content": "nội dung đầy đủ cần lưu, viết lại súc tích bằng tiếng Việt"}}
"""


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"Không tìm thấy JSON trong phản hồi LLM: {text!r}")
    return json.loads(match.group(0))


def handle_remember(text: str) -> str:
    index = index_store.read_index()
    prompt = CLASSIFY_PROMPT.format(index=index, text=text)
    response = llm_client.get_classifier_model().invoke([{"role": "user", "content": prompt}])
    data = _extract_json(response.content)

    slug = paths.slugify(data["slug"])
    with lock.consolidation_lock():
        existing = topic_store.read_topic(slug)
        if existing:
            merged_content = existing["content"] + "\n\n" + data["content"]
        else:
            merged_content = data["content"]
        topic_store.write_topic(slug, data["title"], data["hook"], data.get("type", "user"), merged_content)
        index_store.append_entry(data["title"], f"{slug}.md", data["hook"])

    return f"Đã ghi nhớ vào chủ đề '{data['title']}' ({slug}.md)."


FORGET_PROMPT = """Index các chủ đề (topic) đã biết:

{index}

Người dùng muốn quên thông tin liên quan đến: "{query}"

Trả lời CHỈ JSON: {{"slug": "slug_phu_hop_nhat_hoac_rong_neu_khong_co"}}
"""


def handle_forget(query: str) -> str:
    index = index_store.read_index()
    prompt = FORGET_PROMPT.format(index=index, query=query)
    response = llm_client.get_classifier_model().invoke([{"role": "user", "content": prompt}])
    data = _extract_json(response.content)
    raw_slug = data.get("slug", "").strip()
    if not raw_slug:
        return "Không tìm thấy chủ đề nào khớp để quên."
    slug = paths.slugify(raw_slug.removesuffix(".md"))

    with lock.consolidation_lock():
        topic_store.delete_topic(slug)
        entries = [e for e in index_store.parse_entries() if e["filename"] != f"{slug}.md"]
        index_store.rewrite_index(entries)

    return f"Đã quên chủ đề '{slug}'."
