from memory.store import index_store, topic_store
from memory.read import retrieval


def _setup_topic(slug, title, hook, content):
    topic_store.write_topic(slug, title, hook, "user", content)
    index_store.append_entry(title, f"{slug}.md", hook)


def test_relevant_topics_match():
    _setup_topic("di_ung", "Dị ứng", "dị ứng tôm bò", "Người dùng dị ứng tôm và bò.")
    slugs = retrieval.relevant_topics("tôi ăn tôm được không")
    assert "di_ung" in slugs


def test_relevant_topics_no_match():
    _setup_topic("di_ung", "Dị ứng", "dị ứng tôm", "Người dùng dị ứng tôm.")
    slugs = retrieval.relevant_topics("thời tiết hôm nay thế nào")
    assert "di_ung" not in slugs


def test_relevant_topics_stopwords_ignored():
    _setup_topic("so_thich", "Sở thích", "thích phở", "Người dùng thích ăn phở.")
    # "tôi", "là", "và" là stopwords — không được tính overlap
    slugs = retrieval.relevant_topics("tôi là ai")
    assert "so_thich" not in slugs


def test_relevant_topics_sorted_by_overlap():
    _setup_topic("a", "A", "phở bò tái", "content a")
    _setup_topic("b", "B", "phở", "content b")
    slugs = retrieval.relevant_topics("tôi thích ăn phở bò")
    # "a" overlap nhiều hơn → phải đứng trước
    assert slugs.index("a") < slugs.index("b")


def test_build_context_block_empty_when_no_match():
    _setup_topic("di_ung", "Dị ứng", "dị ứng tôm", "content")
    block = retrieval.build_context_block("thời tiết hôm nay")
    assert block == ""


def test_build_context_block_includes_content():
    _setup_topic("di_ung", "Dị ứng", "dị ứng tôm", "Người dùng dị ứng tôm.")
    block = retrieval.build_context_block("tôi ăn tôm được không")
    assert "Người dùng dị ứng tôm" in block


def test_build_context_block_max_topics():
    for i in range(5):
        _setup_topic(f"topic_{i}", f"Topic {i}", f"phở {i}", f"content {i}")
    block = retrieval.build_context_block("phở", max_topics=2)
    # chỉ tối đa 2 topic được load
    assert block.count("###") <= 2
