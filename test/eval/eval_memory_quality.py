"""
Eval 2: Memory Quality
Đánh giá memory lưu đúng, nhớ đúng, và xử lý conflict không.

Chạy: python -m test.eval.eval_memory_quality
"""

import sys
import tempfile
import pathlib
from unittest.mock import MagicMock, patch

# Thêm project root vào sys.path để import config, memory, v.v.
_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Stub langchain trước khi import bất cứ module nào dùng llm_client
sys.modules.setdefault("langchain_nvidia_ai_endpoints", MagicMock())

import config
from memory.store import index_store, topic_store
from memory.write import manual_write


# Setup / teardown

def _setup_env(tmp_path: pathlib.Path):
    memory_dir = tmp_path / "memory"
    transcripts_dir = tmp_path / "transcripts"
    memory_dir.mkdir()
    transcripts_dir.mkdir()
    config.MEMORY_DIR = memory_dir
    config.TRANSCRIPTS_DIR = transcripts_dir
    config.INDEX_PATH = memory_dir / "MEMORY.md"
    config.LOCK_PATH = memory_dir / ".consolidation.lock"


def _mock_llm(content: str):
    mock_model = MagicMock()
    mock_model.invoke.return_value = MagicMock(content=content)
    return mock_model


# Test cases

class Result:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.details = []

    def ok(self, name: str):
        self.passed += 1
        self.details.append(f"  [PASS] {name}")

    def fail(self, name: str, reason: str):
        self.failed += 1
        self.details.append(f"  [FAIL] {name}\n         → {reason}")


def test_precision_new_fact(r: Result, tmp_path: pathlib.Path):
    """Lưu fact mới → phải xuất hiện đúng trong topic file và index."""
    _setup_env(tmp_path)
    response = '{"slug": "di_ung", "title": "Dị ứng thực phẩm", "hook": "dị ứng tôm", "type": "user", "content": "Người dùng bị dị ứng với tôm."}'
    with patch("memory.write.manual_write.llm_client") as m:
        m.get_classifier_model.return_value = _mock_llm(response)
        manual_write.handle_remember("tôi bị dị ứng tôm")

    topic = topic_store.read_topic("di_ung")
    entries = index_store.parse_entries()

    if topic is None:
        r.fail("precision: fact mới tạo topic", "topic_store.read_topic() trả None")
    elif "tôm" not in topic["content"]:
        r.fail("precision: fact mới tạo topic", f"Content không có 'tôm': {topic['content']!r}")
    elif not any(e["title"] == "Dị ứng thực phẩm" for e in entries):
        r.fail("precision: fact mới tạo topic", "MEMORY.md không có entry 'Dị ứng thực phẩm'")
    else:
        r.ok("precision: fact mới tạo topic")


def test_precision_no_duplicate_index(r: Result, tmp_path: pathlib.Path):
    """Ghi cùng slug 2 lần → chỉ có 1 entry trong index."""
    _setup_env(tmp_path)
    response = '{"slug": "ten", "title": "Tên", "hook": "tên Khoa", "type": "user", "content": "Tên người dùng là Khoa."}'
    with patch("memory.write.manual_write.llm_client") as m:
        m.get_classifier_model.return_value = _mock_llm(response)
        manual_write.handle_remember("tôi tên Khoa")
        manual_write.handle_remember("tôi tên Khoa")  # lần 2

    entries = index_store.parse_entries()
    count = sum(1 for e in entries if e["filename"] == "ten.md")
    if count != 1:
        r.fail("precision: không duplicate index", f"Có {count} entry cho 'ten.md', kỳ vọng 1")
    else:
        r.ok("precision: không duplicate index")


def test_conflict_resolution_append(r: Result, tmp_path: pathlib.Path):
    """Fact mới mâu thuẫn fact cũ → cả 2 được giữ (merge), không xóa cái cũ."""
    _setup_env(tmp_path)

    resp1 = '{"slug": "di_ung", "title": "Dị ứng", "hook": "dị ứng tôm", "type": "user", "content": "Dị ứng tôm."}'
    resp2 = '{"slug": "di_ung", "title": "Dị ứng", "hook": "dị ứng bò", "type": "user", "content": "Đã hết dị ứng tôm. Bây giờ dị ứng bò."}'

    with patch("memory.write.manual_write.llm_client") as m:
        m.get_classifier_model.return_value = _mock_llm(resp1)
        manual_write.handle_remember("tôi dị ứng tôm")

    with patch("memory.write.manual_write.llm_client") as m:
        m.get_classifier_model.return_value = _mock_llm(resp2)
        manual_write.handle_remember("tôi hết dị ứng tôm, giờ dị ứng bò")

    topic = topic_store.read_topic("di_ung")
    if topic is None:
        r.fail("conflict: merge hai fact", "topic bị xóa sau lần 2")
    elif "Dị ứng tôm" not in topic["content"]:
        r.fail("conflict: merge hai fact", f"Fact cũ bị mất. Content: {topic['content']!r}")
    elif "dị ứng bò" not in topic["content"].lower():
        r.fail("conflict: merge hai fact", f"Fact mới không được lưu. Content: {topic['content']!r}")
    else:
        r.ok("conflict: merge hai fact (cả 2 được giữ — autoDream cần prune sau)")


def test_recall_obvious_fact(r: Result, tmp_path: pathlib.Path):
    """Fact rõ ràng về user phải được lưu khi LLM trả should_save=true."""
    _setup_env(tmp_path)
    response = '{"slug": "nghe_nghiep", "title": "Nghề nghiệp", "hook": "kỹ sư phần mềm", "type": "user", "content": "Người dùng là kỹ sư phần mềm."}'
    with patch("memory.write.manual_write.llm_client") as m:
        m.get_classifier_model.return_value = _mock_llm(response)
        manual_write.handle_remember("tôi là kỹ sư phần mềm")

    topic = topic_store.read_topic("nghe_nghiep")
    if topic is None:
        r.fail("recall: fact nghề nghiệp", "Không tìm thấy topic 'nghe_nghiep'")
    else:
        r.ok("recall: fact nghề nghiệp được lưu")


def test_forget_removes_completely(r: Result, tmp_path: pathlib.Path):
    """Sau /forget, cả topic file lẫn entry trong MEMORY.md phải biến mất."""
    _setup_env(tmp_path)
    topic_store.write_topic("di_ung", "Dị ứng", "dị ứng tôm", "user", "Dị ứng tôm.")
    index_store.append_entry("Dị ứng", "di_ung.md", "dị ứng tôm")

    with patch("memory.write.manual_write.llm_client") as m:
        m.get_classifier_model.return_value = _mock_llm('{"slug": "di_ung"}')
        manual_write.handle_forget("dị ứng tôm")

    topic_gone = topic_store.read_topic("di_ung") is None
    index_gone = index_store.parse_entries() == []

    if not topic_gone:
        r.fail("forget: xóa hoàn toàn", "Topic file vẫn còn sau /forget")
    elif not index_gone:
        r.fail("forget: xóa hoàn toàn", "Entry trong MEMORY.md vẫn còn sau /forget")
    else:
        r.ok("forget: xóa hoàn toàn (topic + index)")


# Runner

def main():
    print("=" * 55)
    print("Eval 2: Memory Quality")
    print("=" * 55)

    r = Result()
    tests = [
        test_precision_new_fact,
        test_precision_no_duplicate_index,
        test_conflict_resolution_append,
        test_recall_obvious_fact,
        test_forget_removes_completely,
    ]

    for test_fn in tests:
        with tempfile.TemporaryDirectory() as tmp:
            test_fn(r, pathlib.Path(tmp))

    print()
    for line in r.details:
        print(line)

    total = r.passed + r.failed
    print()
    print(f"Kết quả: {r.passed}/{total} passed")

    if r.failed > 0:
        print()
        print("Lưu ý về conflict resolution:")
        print("  Manual write KHÔNG tự giải conflict — nó append cả 2 fact.")
        print("  autoDream Phase 3 mới là nơi LLM hợp nhất và loại bỏ fact lỗi thời.")

    return r.failed


if __name__ == "__main__":
    sys.exit(main())
