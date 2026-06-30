# Test Suite

57 tests, tổ chức theo layer — mỗi file test một cơ chế riêng biệt.

```bash
python -m pytest test/ -v
```

---

## Hạ tầng chung

### `conftest.py`

Chạy tự động trước mỗi test (`autouse=True`):

- Tạo thư mục tạm (`tmp_path`) cho `memory/` và `transcripts/`
- Monkeypatch các path trong `config` → mỗi test chạy trong môi trường sạch, không đụng data thật
- Stub `langchain_nvidia_ai_endpoints` vào `sys.modules` để tránh version conflict khi import (tests mock `llm_client` trực tiếp nên không cần package thật)

---

## Từng file test

### `test_index_store.py` — Layer 1: MEMORY.md

Đánh giá file index luôn được inject vào system prompt mỗi lượt chat.

| Test | Đánh giá gì |
|------|------------|
| `test_read_index_creates_file_if_missing` | File tự tạo nếu chưa có |
| `test_append_entry_adds_line` | Ghi entry mới vào index |
| `test_append_entry_no_duplicate` | Không ghi trùng cùng 1 entry |
| `test_parse_entries_returns_correct_fields` | Parse ra đúng title / filename / hook |
| `test_rewrite_index_replaces_all` | Ghi đè toàn bộ index (dùng trong autoDream Phase 4) |
| `test_rewrite_index_empty` | Xóa sạch index về rỗng hoàn toàn |

---

### `test_topic_store.py` — Layer 2: Topic files `*.md`

Đánh giá các file chi tiết từng chủ đề, được load on-demand khi query có keyword trùng.

| Test | Đánh giá gì |
|------|------------|
| `test_write_and_read_topic` | Ghi → đọc lại đúng content + frontmatter |
| `test_read_topic_not_found` | Slug không tồn tại → trả `None` |
| `test_write_topic_overwrites` | Ghi lại slug cũ → content bị thay hoàn toàn |
| `test_list_topics_excludes_memory_md` | `MEMORY.md` không lẫn vào danh sách topic |
| `test_delete_topic` | Xóa topic file theo slug |
| `test_delete_topic_not_found_no_error` | Xóa slug không tồn tại → không crash |

---

### `test_transcript_store.py` — Layer 3: Session transcripts `.jsonl`

Đánh giá lưu trữ lịch sử chat thô — dùng để grep (`/search`) và autoDream Phase 2 (`all_turns_since`).

| Test | Đánh giá gì |
|------|------------|
| `test_append_and_grep_found` | Ghi turn → grep tìm thấy đúng content |
| `test_grep_not_found` | Từ không có trong transcript → kết quả rỗng |
| `test_grep_case_insensitive` | Grep không phân biệt hoa thường |
| `test_grep_multiple_sessions` | Grep xuyên nhiều session file |
| `test_grep_max_results` | Giới hạn số kết quả trả về |
| `test_all_turns_since_no_filter` | Lấy tất cả turns khi `since=None` |
| `test_all_turns_since_filters_old` | Lọc đúng mốc timestamp — dùng trong autoDream Phase 2 |

---

### `test_retrieval.py` — Read path

Đánh giá `retrieval.py` — quyết định topic nào được inject vào prompt dựa trên keyword overlap.

| Test | Đánh giá gì |
|------|------------|
| `test_relevant_topics_match` | Query có keyword trùng hook → trả topic đó |
| `test_relevant_topics_no_match` | Query không liên quan → không trả gì |
| `test_relevant_topics_stopwords_ignored` | "tôi", "là", "và" không được tính overlap |
| `test_relevant_topics_sorted_by_overlap` | Topic overlap nhiều hơn xếp trước |
| `test_build_context_block_empty_when_no_match` | Không có match → context block rỗng |
| `test_build_context_block_includes_content` | Có match → content của topic xuất hiện trong block |
| `test_build_context_block_max_topics` | Giới hạn `max_topics` khi build prompt |

---

### `test_extractor.py` — Write path: per-turn extraction

Đánh giá `extractMemories` — thread nền hỏi LLM "có fact nào đáng lưu không?" sau mỗi lượt chat. LLM được mock bằng `unittest.mock.patch`.

| Test | Đánh giá gì |
|------|------------|
| `test_extract_json_valid` | Parse JSON hợp lệ từ LLM response |
| `test_extract_json_embedded_in_text` | Parse JSON dù LLM có thêm text xung quanh |
| `test_extract_json_invalid_returns_false` | Response không có JSON → fallback `{"should_save": false}` |
| `test_extract_json_malformed_returns_false` | JSON sai cú pháp → fallback an toàn |
| `test_run_saves_when_should_save_true` | LLM nói có fact → ghi vào topic file + index |
| `test_run_skips_when_should_save_false` | LLM nói không có fact → không ghi gì |
| `test_run_appends_to_existing_topic` | Slug đã tồn tại → merge nội dung, không ghi đè |

---

### `test_manual_write.py` — Write path: `/remember` và `/forget`

Đánh giá thao tác thủ công của user. LLM được mock để trả về JSON phân loại topic.

| Test | Đánh giá gì |
|------|------------|
| `test_remember_creates_topic` | `/remember` → tạo topic mới |
| `test_remember_updates_memory_index` | MEMORY.md được cập nhật sau khi remember |
| `test_remember_appends_to_existing` | Slug đã có → append, không xóa nội dung cũ |
| `test_forget_removes_topic` | `/forget` → xóa cả topic file lẫn entry trong index |
| `test_forget_not_found` | Slug trống → trả thông báo "Không tìm thấy" |

---

### `test_lock.py` — Race condition protection

Đánh giá `.consolidation.lock` — ngăn `extractor` và `autoDream` ghi đồng thời vào cùng file.

| Test | Đánh giá gì |
|------|------------|
| `test_lock_creates_and_removes_file` | Lock tạo file → xóa file khi thoát context manager |
| `test_lock_releases_on_exception` | Exception bên trong lock → file vẫn bị xóa, không treo |
| `test_lock_blocks_sequential_access` | Thread B không vào được khi A đang giữ lock |
| `test_lock_timeout_raises` | Lock bị giữ quá lâu → raise `TimeoutError` |

---

### `test_state.py` — autoDream trigger logic

Đánh giá điều kiện `should_run_autodream()` — khi nào batch consolidation được kích hoạt.

| Test | Đánh giá gì |
|------|------------|
| `test_first_run_enough_sessions` | Lần đầu chạy, chỉ cần đủ session (chưa có timestamp) |
| `test_first_run_not_enough_sessions` | Lần đầu, chưa đủ session → không chạy |
| `test_both_conditions_met` | ≥24h VÀ ≥5 session mới → chạy |
| `test_hours_not_met` | Đủ session nhưng chưa đủ giờ → không chạy |
| `test_sessions_not_met` | Đủ giờ nhưng chưa đủ session mới → không chạy |
| `test_mark_autodream_ran_updates_state` | Sau khi chạy, timestamp và session count được cập nhật |

---

## Coverage map

```
conftest.py           → hạ tầng (fixture, mock, stub)
test_index_store      → Layer 1 (MEMORY.md)
test_topic_store      → Layer 2 (*.md topic files)
test_transcript_store → Layer 3 (.jsonl session transcripts)
test_retrieval        → Read path (keyword overlap → inject vào prompt)
test_extractor        → Write path per-turn (async sau mỗi lượt chat)
test_manual_write     → Write path manual (/remember, /forget)
test_lock             → Race condition protection
test_state            → autoDream trigger conditions
```
