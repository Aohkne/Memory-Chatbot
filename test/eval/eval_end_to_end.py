"""
Eval 4: End-to-End Conversational Quality
Đánh giá xem bot có thực sự dùng memory để trả lời đúng không — cấp độ người dùng cảm nhận.

Cách đánh giá:
  - Không gọi LLM thật (tránh tốn API)
  - Thay vào đó: kiểm tra system prompt được build có chứa đúng memory không
  - Vì nếu memory được inject vào system prompt đúng → bot có đủ thông tin để trả lời đúng

Chạy: python -m test.eval.eval_end_to_end
"""

import sys
import tempfile
import pathlib
from unittest.mock import MagicMock

# Thêm project root vào sys.path để import config, memory, v.v.
_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

sys.modules.setdefault("langchain_nvidia_ai_endpoints", MagicMock())

import config
from memory.store import index_store, topic_store
from memory.read import retrieval
import main as main_module


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


def _seed_memory(slug, title, hook, content):
    """Giả lập memory đã được lưu từ session trước."""
    topic_store.write_topic(slug, title, hook, "user", content)
    index_store.append_entry(title, f"{slug}.md", hook)


class Result:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.details = []

    def ok(self, name: str, note: str = ""):
        self.passed += 1
        suffix = f"\n         ✓ {note}" if note else ""
        self.details.append(f"  [PASS] {name}{suffix}")

    def fail(self, name: str, reason: str):
        self.failed += 1
        self.details.append(f"  [FAIL] {name}\n         → {reason}")


# Scenarios

def scenario_allergy_remembered(r: Result, tmp_path: pathlib.Path):
    """
    Session trước: user nói dị ứng tôm.
    Session mới: hỏi "tôi ăn tôm được không?"
    → System prompt phải chứa thông tin dị ứng tôm.
    """
    _setup_env(tmp_path)
    _seed_memory("di_ung", "Dị ứng thực phẩm", "dị ứng tôm bò",
                 "Người dùng bị dị ứng với tôm và bò.")

    system_prompt = main_module.build_system_prompt("tôi ăn tôm được không")

    if "tôm" in system_prompt.lower():
        r.ok(
            "Dị ứng được nhớ qua session",
            "System prompt chứa 'tôm' → bot có đủ thông tin để cảnh báo"
        )
    else:
        r.fail(
            "Dị ứng được nhớ qua session",
            f"System prompt không chứa thông tin dị ứng tôm.\nPrompt (200 chars): {system_prompt[:200]!r}"
        )


def scenario_name_not_injected_for_irrelevant_query(r: Result, tmp_path: pathlib.Path):
    """
    Memory có tên user.
    Query về thời tiết — topic tên không liên quan → không nên inject vào prompt.
    Kiểm tra MEMORY.md index luôn được inject (layer 1), nhưng topic detail thì không.
    """
    _setup_env(tmp_path)
    _seed_memory("ten", "Tên người dùng", "tên Khoa", "Người dùng tên Hữu Khoa.")

    system_prompt = main_module.build_system_prompt("thời tiết hôm nay thế nào")
    context_block = retrieval.build_context_block("thời tiết hôm nay thế nào")

    if context_block == "":
        r.ok(
            "No false injection: thời tiết không kéo topic tên",
            "context_block rỗng → topic detail không bị inject sai"
        )
    else:
        r.fail(
            "No false injection",
            f"Topic 'tên' bị inject vào query thời tiết.\nContext block: {context_block!r}"
        )


def scenario_index_always_in_context(r: Result, tmp_path: pathlib.Path):
    """
    MEMORY.md (layer 1) phải luôn có trong system prompt dù query là gì.
    Đây là cơ chế đảm bảo bot luôn biết 'mình đã biết gì về user'.
    """
    _setup_env(tmp_path)
    _seed_memory("so_thich", "Sở thích ăn uống", "thích phở", "Thích ăn phở.")

    system_prompt = main_module.build_system_prompt("2 + 2 bằng bao nhiêu")

    if "MEMORY INDEX" in system_prompt or "Sở thích" in system_prompt:
        r.ok(
            "MEMORY.md luôn được inject (layer 1)",
            "Index có trong system prompt dù query không liên quan"
        )
    else:
        r.fail(
            "MEMORY.md luôn được inject",
            f"MEMORY.md không có trong system prompt.\nPrompt: {system_prompt[:300]!r}"
        )


def scenario_multi_topic_relevant(r: Result, tmp_path: pathlib.Path):
    """
    Có nhiều topic trong memory. Query liên quan đến 1 topic cụ thể
    → chỉ topic đó được inject vào context block, không phải tất cả.
    """
    _setup_env(tmp_path)
    _seed_memory("di_ung", "Dị ứng", "dị ứng tôm", "Người dùng dị ứng tôm.")
    _seed_memory("nghe_nghiep", "Nghề nghiệp", "kỹ sư backend", "Người dùng là kỹ sư backend.")
    _seed_memory("so_thich", "Sở thích", "thích chạy bộ", "Người dùng thích chạy bộ.")

    context_block = retrieval.build_context_block("tôi ăn tôm được không")

    has_allergy = "tôm" in context_block.lower()
    no_job = "kỹ sư" not in context_block
    no_hobby = "chạy bộ" not in context_block

    if has_allergy and no_job and no_hobby:
        r.ok(
            "Chỉ inject topic liên quan",
            "Context block chỉ chứa topic dị ứng, không có nghề nghiệp hay sở thích"
        )
    else:
        details = []
        if not has_allergy:
            details.append("thiếu topic dị ứng")
        if not no_job:
            details.append("inject cả topic nghề nghiệp (không cần)")
        if not no_hobby:
            details.append("inject cả topic sở thích (không cần)")
        r.fail("Chỉ inject topic liên quan", ", ".join(details))


def scenario_empty_memory_no_crash(r: Result, tmp_path: pathlib.Path):
    """
    Memory hoàn toàn trống → bot vẫn hoạt động, không crash, system prompt vẫn hợp lệ.
    """
    _setup_env(tmp_path)
    try:
        system_prompt = main_module.build_system_prompt("xin chào")
        if isinstance(system_prompt, str) and len(system_prompt) > 0:
            r.ok("Empty memory không crash", "Trả về system prompt hợp lệ dù memory rỗng")
        else:
            r.fail("Empty memory không crash", f"system_prompt không hợp lệ: {system_prompt!r}")
    except Exception as e:
        r.fail("Empty memory không crash", f"Exception: {e}")


# Runner

SCENARIOS = [
    scenario_allergy_remembered,
    scenario_name_not_injected_for_irrelevant_query,
    scenario_index_always_in_context,
    scenario_multi_topic_relevant,
    scenario_empty_memory_no_crash,
]


def main():
    print("=" * 55)
    print("Eval 4: End-to-End Conversational Quality")
    print("=" * 55)
    print()
    print("Phương pháp: kiểm tra system prompt được build")
    print("  → Nếu memory đúng được inject → bot có đủ thông tin để trả lời đúng")
    print("  → Không gọi LLM thật (tránh tốn API)")

    r = Result()
    for scenario_fn in SCENARIOS:
        with tempfile.TemporaryDirectory() as tmp:
            scenario_fn(r, pathlib.Path(tmp))

    print()
    for line in r.details:
        print(line)

    total = r.passed + r.failed
    print()
    print(f"Kết quả: {r.passed}/{total} passed")

    if r.passed == total:
        print()
        print("Bước tiếp theo nếu muốn đánh giá sâu hơn:")
        print("  - LLM-as-judge: dùng Claude/GPT chấm response có dùng memory đúng không")
        print("  - Human eval: người thật đọc và chấm điểm từng scenario")
        print("  - A/B test: bot có memory vs bot không có memory — so sánh user satisfaction")

    return r.failed


if __name__ == "__main__":
    sys.exit(main())
