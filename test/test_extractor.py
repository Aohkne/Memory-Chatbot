from unittest.mock import MagicMock, patch

from memory.write import extractor
from memory.store import index_store, topic_store


def _mock_llm_response(content: str):
    mock_model = MagicMock()
    mock_model.invoke.return_value = MagicMock(content=content)
    return mock_model


# --- test _extract_json ---

def test_extract_json_valid():
    text = '{"should_save": true, "slug": "test", "title": "T", "hook": "h", "type": "user", "content": "c"}'
    result = extractor._extract_json(text)
    assert result["should_save"] is True
    assert result["slug"] == "test"


def test_extract_json_embedded_in_text():
    text = 'some prefix {"should_save": false} some suffix'
    result = extractor._extract_json(text)
    assert result["should_save"] is False


def test_extract_json_invalid_returns_false():
    result = extractor._extract_json("không có json gì hết")
    assert result == {"should_save": False}


def test_extract_json_malformed_returns_false():
    result = extractor._extract_json("{này không phải json}")
    assert result == {"should_save": False}


# --- test _run (mock LLM) ---

def test_run_saves_when_should_save_true():
    response_json = '{"should_save": true, "slug": "ten_nguoi_dung", "title": "Tên người dùng", "hook": "tên Hữu Khoa", "type": "user", "content": "Người dùng tên Hữu Khoa."}'

    with patch("memory.extractor.llm_client") as mock_client:
        mock_client.get_classifier_model.return_value = _mock_llm_response(response_json)
        extractor._run("tôi tên là Hữu Khoa", "Xin chào Hữu Khoa!")

    assert topic_store.read_topic("ten_nguoi_dung") is not None
    entries = index_store.parse_entries()
    assert any(e["title"] == "Tên người dùng" for e in entries)


def test_run_skips_when_should_save_false():
    response_json = '{"should_save": false}'

    with patch("memory.extractor.llm_client") as mock_client:
        mock_client.get_classifier_model.return_value = _mock_llm_response(response_json)
        extractor._run("helo", "Xin chào!")

    assert topic_store.list_topics() == []
    assert index_store.parse_entries() == []


def test_run_appends_to_existing_topic():
    topic_store.write_topic("di_ung", "Dị ứng", "dị ứng tôm", "user", "Dị ứng tôm.")
    index_store.append_entry("Dị ứng", "di_ung.md", "dị ứng tôm")

    response_json = '{"should_save": true, "slug": "di_ung", "title": "Dị ứng", "hook": "dị ứng tôm và bò", "type": "user", "content": "Dị ứng bò."}'

    with patch("memory.extractor.llm_client") as mock_client:
        mock_client.get_classifier_model.return_value = _mock_llm_response(response_json)
        extractor._run("tôi bị dị ứng bò", "Đã lưu.")

    result = topic_store.read_topic("di_ung")
    assert "Dị ứng tôm" in result["content"]
    assert "Dị ứng bò" in result["content"]
