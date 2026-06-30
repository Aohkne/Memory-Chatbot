"""
Eval 3: Retrieval Accuracy
Đánh giá keyword-overlap retrieval — topic nào được kéo vào context, topic nào bị bỏ sót.

Chạy: python -m test.eval.eval_retrieval
"""

import sys
import tempfile
import pathlib

# Thêm project root vào sys.path để import config, memory, v.v.
_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from unittest.mock import MagicMock
sys.modules.setdefault("langchain_nvidia_ai_endpoints", MagicMock())

import config
from memory.store import index_store, topic_store
from memory.read import retrieval


# Setup

def _setup_env(tmp_path: pathlib.Path):
    memory_dir = tmp_path / "memory"
    transcripts_dir = tmp_path / "transcripts"
    memory_dir.mkdir()
    transcripts_dir.mkdir()
    config.MEMORY_DIR = memory_dir
    config.TRANSCRIPTS_DIR = transcripts_dir
    config.INDEX_PATH = memory_dir / "MEMORY.md"
    config.LOCK_PATH = memory_dir / ".consolidation.lock"


def _add_topic(slug, title, hook, content):
    topic_store.write_topic(slug, title, hook, "user", content)
    index_store.append_entry(title, f"{slug}.md", hook)


class Result:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.limitations = []
        self.details = []

    def ok(self, name: str):
        self.passed += 1
        self.details.append(f"  [PASS] {name}")

    def fail(self, name: str, reason: str):
        self.failed += 1
        self.details.append(f"  [FAIL] {name}\n         → {reason}")

    def limitation(self, name: str, reason: str):
        # Đây là điểm yếu đã biết — không tính vào failed
        self.limitations.append(f"  [LIMIT] {name}\n          → {reason}")
        self.details.append(f"  [LIMIT] {name} (điểm yếu đã biết)")


# Test cases

def test_exact_keyword_hit(r: Result, tmp_path: pathlib.Path):
    """Query chứa từ khóa chính xác trong hook → phải hit."""
    _setup_env(tmp_path)
    _add_topic("di_ung", "Dị ứng", "dị ứng tôm bò", "Người dùng dị ứng tôm và bò.")
    slugs = retrieval.relevant_topics("tôi ăn tôm được không")
    if "di_ung" in slugs:
        r.ok("exact keyword hit: 'tôm' trong query → topic dị ứng")
    else:
        r.fail("exact keyword hit", f"'di_ung' không có trong {slugs}")


def test_no_match_irrelevant_query(r: Result, tmp_path: pathlib.Path):
    """Query hoàn toàn không liên quan → không được kéo topic sai vào context."""
    _setup_env(tmp_path)
    _add_topic("di_ung", "Dị ứng", "dị ứng tôm", "Người dùng dị ứng tôm.")
    slugs = retrieval.relevant_topics("thời tiết hôm nay thế nào")
    if "di_ung" not in slugs:
        r.ok("no false positive: query thời tiết không kéo topic dị ứng")
    else:
        r.fail("no false positive", f"Topic dị ứng bị kéo sai khi hỏi thời tiết. Slugs: {slugs}")


def test_stopwords_not_counted(r: Result, tmp_path: pathlib.Path):
    """Query chỉ chứa stopword ('tôi là ai') → không được match bất kỳ topic nào."""
    _setup_env(tmp_path)
    _add_topic("so_thich", "Sở thích", "thích phở", "Người dùng thích ăn phở.")
    slugs = retrieval.relevant_topics("tôi là ai")
    if "so_thich" not in slugs:
        r.ok("stopwords bị loại: 'tôi là ai' không match topic sở thích")
    else:
        r.fail("stopwords bị loại", f"Topic sở thích bị match bởi stopwords: {slugs}")


def test_ranking_by_overlap(r: Result, tmp_path: pathlib.Path):
    """Topic overlap nhiều từ hơn phải xếp trước trong kết quả."""
    _setup_env(tmp_path)
    _add_topic("a", "Phở bò tái", "phở bò tái nạm", "content a")
    _add_topic("b", "Phở", "phở thôi", "content b")
    slugs = retrieval.relevant_topics("tôi thích ăn phở bò tái")
    if not slugs:
        r.fail("ranking", "Không có topic nào match")
    elif slugs.index("a") < slugs.index("b"):
        r.ok("ranking: topic overlap nhiều hơn xếp trước")
    else:
        r.fail("ranking", f"Topic 'b' (overlap ít) xếp trước 'a'. Thứ tự: {slugs}")


def test_multi_topic_max_cap(r: Result, tmp_path: pathlib.Path):
    """build_context_block với max_topics=2 không được inject quá 2 topic."""
    _setup_env(tmp_path)
    for i in range(5):
        _add_topic(f"topic_{i}", f"Topic {i}", f"phở {i}", f"content {i}")
    block = retrieval.build_context_block("phở", max_topics=2)
    count = block.count("###")
    if count <= 2:
        r.ok(f"max_topics cap: chỉ inject {count}/5 topic")
    else:
        r.fail("max_topics cap", f"Inject {count} topic, vượt giới hạn max_topics=2")


def test_synonym_miss(r: Result, tmp_path: pathlib.Path):
    """
    Điểm yếu đã biết: lưu 'bò' nhưng hỏi 'beef' → MISS vì keyword overlap không hiểu ngữ nghĩa.
    Cần vector embedding để fix (được ghi nhận, không tính vào failed).
    """
    _setup_env(tmp_path)
    _add_topic("di_ung", "Dị ứng", "dị ứng bò", "Người dùng dị ứng bò.")
    slugs = retrieval.relevant_topics("tôi có thể ăn beef không")
    if "di_ung" not in slugs:
        r.limitation(
            "synonym miss: 'bò' vs 'beef'",
            "Keyword overlap không bắt được từ đồng nghĩa. Fix: dùng vector embeddings."
        )
    else:
        r.ok("synonym: 'beef' match 'bò' (unexpected hit)")


def test_partial_match_in_title(r: Result, tmp_path: pathlib.Path):
    """Từ khóa trùng với title (không chỉ hook) cũng phải match."""
    _setup_env(tmp_path)
    _add_topic("nghe_nghiep", "Kỹ sư phần mềm", "lập trình backend", "Người dùng làm kỹ sư.")
    slugs = retrieval.relevant_topics("công việc kỹ sư thế nào")
    if "nghe_nghiep" in slugs:
        r.ok("title match: 'kỹ sư' trong title cũng được tính")
    else:
        r.fail("title match", f"'nghe_nghiep' không match dù title chứa 'kỹ sư'. Slugs: {slugs}")


# Runner

def main():
    print("=" * 55)
    print("Eval 3: Retrieval Accuracy")
    print("=" * 55)

    r = Result()
    tests = [
        test_exact_keyword_hit,
        test_no_match_irrelevant_query,
        test_stopwords_not_counted,
        test_ranking_by_overlap,
        test_multi_topic_max_cap,
        test_synonym_miss,
        test_partial_match_in_title,
    ]

    for test_fn in tests:
        with tempfile.TemporaryDirectory() as tmp:
            test_fn(r, pathlib.Path(tmp))

    print()
    for line in r.details:
        print(line)

    if r.limitations:
        print()
        print("Điểm yếu đã biết (không tính vào score):")
        for line in r.limitations:
            print(line)

    total = r.passed + r.failed
    print()
    print(f"Kết quả: {r.passed}/{total} passed  ({len(r.limitations)} limitation đã biết)")
    return r.failed


if __name__ == "__main__":
    sys.exit(main())
