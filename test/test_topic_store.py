from memory.store import topic_store


def test_write_and_read_topic():
    topic_store.write_topic("di_ung", "Dị ứng", "dị ứng tôm", "user", "Người dùng dị ứng với tôm.")
    result = topic_store.read_topic("di_ung")
    assert result is not None
    assert "dị ứng với tôm" in result["content"]
    assert result["frontmatter"]["name"] == "Dị ứng"


def test_read_topic_not_found():
    assert topic_store.read_topic("khong_ton_tai") is None


def test_write_topic_overwrites():
    topic_store.write_topic("test", "Test", "hook cũ", "user", "nội dung cũ")
    topic_store.write_topic("test", "Test", "hook mới", "user", "nội dung mới")
    result = topic_store.read_topic("test")
    assert "nội dung mới" in result["content"]
    assert "nội dung cũ" not in result["content"]


def test_list_topics_empty():
    assert topic_store.list_topics() == []


def test_list_topics_excludes_memory_md():
    import config
    (config.MEMORY_DIR / "MEMORY.md").write_text("# index", encoding="utf-8")
    topic_store.write_topic("so_thich", "Sở thích", "hook", "user", "content")
    topics = topic_store.list_topics()
    assert "so_thich" in topics
    assert "MEMORY" not in topics


def test_delete_topic():
    topic_store.write_topic("xoa_toi", "Xóa tôi", "hook", "user", "content")
    topic_store.delete_topic("xoa_toi")
    assert topic_store.read_topic("xoa_toi") is None


def test_delete_topic_not_found_no_error():
    topic_store.delete_topic("khong_ton_tai")  # không raise exception
