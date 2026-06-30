# Test Report — Unit Tests

**Ngày chạy:** 2026-06-30
**Môi trường:** Python 3.11.15 · pytest 9.0.3 · conda env `ml`
**Kết quả:** 57/57 passed · 0 failed · 0.64s

```
python -m pytest test/ -v
```

---

## Kết quả tổng hợp

| File | Tests | Kết quả |
|------|-------|---------|
| `test_extractor.py` | 7 | PASS |
| `test_index_store.py` | 7 | PASS |
| `test_lock.py` | 4 | PASS |
| `test_manual_write.py` | 5 | PASS |
| `test_paths.py` | 7 | PASS |
| `test_retrieval.py` | 7 | PASS |
| `test_state.py` | 6 | PASS |
| `test_topic_store.py` | 7 | PASS |
| `test_transcript_store.py` | 7 | PASS |
| **Tổng** | **57** | **57 PASS** |

---

## Chi tiết từng file

### test_extractor.py — 7/7 PASS

| Test | Kết quả |
|------|---------|
| `test_extract_json_valid` | PASS |
| `test_extract_json_embedded_in_text` | PASS |
| `test_extract_json_invalid_returns_false` | PASS |
| `test_extract_json_malformed_returns_false` | PASS |
| `test_run_saves_when_should_save_true` | PASS |
| `test_run_skips_when_should_save_false` | PASS |
| `test_run_appends_to_existing_topic` | PASS |

### test_index_store.py — 7/7 PASS

| Test | Kết quả |
|------|---------|
| `test_read_index_creates_file_if_missing` | PASS |
| `test_append_entry_adds_line` | PASS |
| `test_append_entry_no_duplicate` | PASS |
| `test_parse_entries_empty` | PASS |
| `test_parse_entries_returns_correct_fields` | PASS |
| `test_rewrite_index_replaces_all` | PASS |
| `test_rewrite_index_empty` | PASS |

### test_lock.py — 4/4 PASS

| Test | Kết quả |
|------|---------|
| `test_lock_creates_and_removes_file` | PASS |
| `test_lock_releases_on_exception` | PASS |
| `test_lock_blocks_sequential_access` | PASS |
| `test_lock_timeout_raises` | PASS |

### test_manual_write.py — 5/5 PASS

| Test | Kết quả |
|------|---------|
| `test_remember_creates_topic` | PASS |
| `test_remember_updates_memory_index` | PASS |
| `test_remember_appends_to_existing` | PASS |
| `test_forget_removes_topic` | PASS |
| `test_forget_not_found` | PASS |

### test_paths.py — 7/7 PASS

| Test | Kết quả |
|------|---------|
| `test_slugify_basic` | PASS |
| `test_slugify_uppercase` | PASS |
| `test_slugify_special_chars` | PASS |
| `test_slugify_empty` | PASS |
| `test_slugify_only_special` | PASS |
| `test_slugify_underscores` | PASS |
| `test_slugify_numbers` | PASS |

### test_retrieval.py — 7/7 PASS

| Test | Kết quả |
|------|---------|
| `test_relevant_topics_match` | PASS |
| `test_relevant_topics_no_match` | PASS |
| `test_relevant_topics_stopwords_ignored` | PASS |
| `test_relevant_topics_sorted_by_overlap` | PASS |
| `test_build_context_block_empty_when_no_match` | PASS |
| `test_build_context_block_includes_content` | PASS |
| `test_build_context_block_max_topics` | PASS |

### test_state.py — 6/6 PASS

| Test | Kết quả |
|------|---------|
| `test_first_run_enough_sessions` | PASS |
| `test_first_run_not_enough_sessions` | PASS |
| `test_both_conditions_met` | PASS |
| `test_hours_not_met` | PASS |
| `test_sessions_not_met` | PASS |
| `test_mark_autodream_ran_updates_state` | PASS |

### test_topic_store.py — 7/7 PASS

| Test | Kết quả |
|------|---------|
| `test_write_and_read_topic` | PASS |
| `test_read_topic_not_found` | PASS |
| `test_write_topic_overwrites` | PASS |
| `test_list_topics_empty` | PASS |
| `test_list_topics_excludes_memory_md` | PASS |
| `test_delete_topic` | PASS |
| `test_delete_topic_not_found_no_error` | PASS |

### test_transcript_store.py — 7/7 PASS

| Test | Kết quả |
|------|---------|
| `test_append_and_grep_found` | PASS |
| `test_grep_not_found` | PASS |
| `test_grep_case_insensitive` | PASS |
| `test_grep_multiple_sessions` | PASS |
| `test_grep_max_results` | PASS |
| `test_all_turns_since_no_filter` | PASS |
| `test_all_turns_since_filters_old` | PASS |

---

## Ghi chú kỹ thuật

**Fixture isolation:** Mỗi test chạy với `tmp_path` riêng (pytest built-in), config path được monkeypatch → không có test nào đụng vào data thật.

**LLM mock:** `test_extractor` và `test_manual_write` dùng `unittest.mock.patch` để thay thế `llm_client` bằng object giả — không gọi API thật, không tốn credit.

**langchain stub:** `conftest.py` inject `sys.modules["langchain_nvidia_ai_endpoints"] = MagicMock()` trước khi pytest collect bất kỳ test module nào — tránh `ImportError: cannot import name 'ModelProfile'` do version conflict giữa `langchain_nvidia_ai_endpoints` và `langchain_core` trong môi trường hiện tại.
