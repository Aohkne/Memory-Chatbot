from unittest.mock import MagicMock, patch

from memory.write import manual_write
from memory.store import index_store, topic_store


def _mock_llm(content: str):
    mock_model = MagicMock()
    mock_model.invoke.return_value = MagicMock(content=content)
    return mock_model


CLASSIFY_RESPONSE = '{"slug": "di_ung", "title": "Dị ứng thực phẩm", "hook": "dị ứng tôm", "type": "user", "content": "Người dùng bị dị ứng với tôm."}'
FORGET_RESPONSE = '{"slug": "di_ung"}'


# --- handle_remember ---

def test_remember_creates_topic():
    with patch("memory.manual_write.llm_client") as mock_client:
        mock_client.get_classifier_model.return_value = _mock_llm(CLASSIFY_RESPONSE)
        result = manual_write.handle_remember("tôi bị dị ứng tôm")

    assert "Dị ứng thực phẩm" in result
    assert topic_store.read_topic("di_ung") is not None


def test_remember_updates_memory_index():
    with patch("memory.manual_write.llm_client") as mock_client:
        mock_client.get_classifier_model.return_value = _mock_llm(CLASSIFY_RESPONSE)
        manual_write.handle_remember("tôi bị dị ứng tôm")

    entries = index_store.parse_entries()
    assert any(e["title"] == "Dị ứng thực phẩm" for e in entries)


def test_remember_appends_to_existing():
    topic_store.write_topic("di_ung", "Dị ứng thực phẩm", "dị ứng tôm", "user", "Dị ứng tôm.")
    index_store.append_entry("Dị ứng thực phẩm", "di_ung.md", "dị ứng tôm")

    new_response = '{"slug": "di_ung", "title": "Dị ứng thực phẩm", "hook": "dị ứng tôm và bò", "type": "user", "content": "Thêm: dị ứng bò."}'
    with patch("memory.manual_write.llm_client") as mock_client:
        mock_client.get_classifier_model.return_value = _mock_llm(new_response)
        manual_write.handle_remember("tôi bị dị ứng thêm bò")

    result = topic_store.read_topic("di_ung")
    assert "Dị ứng tôm" in result["content"]
    assert "dị ứng bò" in result["content"]


# --- handle_forget ---

def test_forget_removes_topic():
    topic_store.write_topic("di_ung", "Dị ứng thực phẩm", "dị ứng tôm", "user", "content")
    index_store.append_entry("Dị ứng thực phẩm", "di_ung.md", "dị ứng tôm")

    with patch("memory.manual_write.llm_client") as mock_client:
        mock_client.get_classifier_model.return_value = _mock_llm(FORGET_RESPONSE)
        manual_write.handle_forget("dị ứng tôm")

    assert topic_store.read_topic("di_ung") is None
    assert index_store.parse_entries() == []


def test_forget_not_found():
    with patch("memory.manual_write.llm_client") as mock_client:
        mock_client.get_classifier_model.return_value = _mock_llm('{"slug": ""}')
        result = manual_write.handle_forget("thứ không tồn tại")

    assert "Không tìm thấy" in result
