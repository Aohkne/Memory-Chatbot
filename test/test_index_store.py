from memory.store import index_store


def test_read_index_creates_file_if_missing():
    content = index_store.read_index()
    assert "# MEMORY INDEX" in content


def test_append_entry_adds_line():
    index_store.append_entry("Dị ứng", "di_ung.md", "dị ứng tôm và bò")
    content = index_store.read_index()
    assert "Dị ứng" in content
    assert "di_ung.md" in content
    assert "dị ứng tôm và bò" in content


def test_append_entry_no_duplicate():
    index_store.append_entry("Dị ứng", "di_ung.md", "dị ứng tôm")
    index_store.append_entry("Dị ứng", "di_ung.md", "dị ứng tôm")
    content = index_store.read_index()
    assert content.count("di_ung.md") == 1


def test_parse_entries_empty():
    entries = index_store.parse_entries()
    assert entries == []


def test_parse_entries_returns_correct_fields():
    index_store.append_entry("Sở thích", "so_thich.md", "thích ăn phở")
    entries = index_store.parse_entries()
    assert len(entries) == 1
    assert entries[0]["title"] == "Sở thích"
    assert entries[0]["filename"] == "so_thich.md"
    assert entries[0]["hook"] == "thích ăn phở"


def test_rewrite_index_replaces_all():
    index_store.append_entry("Cũ", "cu.md", "thông tin cũ")
    index_store.rewrite_index([
        {"title": "Mới", "filename": "moi.md", "hook": "thông tin mới"},
    ])
    content = index_store.read_index()
    assert "Cũ" not in content
    assert "Mới" in content


def test_rewrite_index_empty():
    index_store.append_entry("Cũ", "cu.md", "hook")
    index_store.rewrite_index([])
    assert index_store.parse_entries() == []
