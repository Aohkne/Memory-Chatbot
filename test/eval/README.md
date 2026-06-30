# Eval Suite
```bash
python test/eval/eval_memory_quality.py
python test/eval/eval_retrieval.py
python test/eval/eval_end_to_end.py
```

---

## Tại sao cần eval ngoài unit test?

Unit test kiểm tra **code chạy đúng** — nhưng không trả lời được:
- Bot có thực sự nhớ thông tin user không?
- Memory có được kéo ra đúng lúc không?
- User hỏi khác từ thì có miss không?

Eval scripts kiểm tra **hành vi thực tế** từ góc nhìn người dùng.

---

## 4 tầng đánh giá

| Tầng | File | Câu hỏi |
|------|------|---------|
| 1 | `test/` (pytest) | Code đúng không? |
| 2 | `eval_memory_quality.py` | Lưu đúng, nhớ đúng, quên đúng không? |
| 3 | `eval_retrieval.py` | Kéo memory ra đúng lúc không? |
| 4 | `eval_end_to_end.py` | Bot có dùng memory để trả lời đúng không? |

---

## Chạy

```bash
# Chạy từng file
python -m test.eval.eval_memory_quality
python -m test.eval.eval_retrieval
python -m test.eval.eval_end_to_end

# Hoặc chạy tất cả
python -m test.eval.eval_memory_quality && \
python -m test.eval.eval_retrieval && \
python -m test.eval.eval_end_to_end
```

Các script không cần API key, không gọi LLM thật — chạy nhanh hoàn toàn offline.

---

## Chi tiết từng file

---

### `eval_memory_quality.py` — Tầng 2: Memory Quality

**Câu hỏi:** Memory có lưu đúng fact, không trùng, xử lý conflict như thế nào?

**Cách đánh giá:** Mock LLM trả về JSON fact cố định → inspect file thật trong temp dir.

| Test | Kiểm tra gì |
|------|------------|
| `test_precision_new_fact` | Fact mới → topic file + MEMORY.md đều được tạo |
| `test_precision_no_duplicate_index` | Cùng slug ghi 2 lần → chỉ 1 entry trong index |
| `test_conflict_resolution_append` | Fact mới mâu thuẫn fact cũ → cả 2 được giữ (merge) |
| `test_recall_obvious_fact` | Fact rõ ràng phải được lưu khi LLM trả `should_save=true` |
| `test_forget_removes_completely` | `/forget` → xóa sạch cả topic file lẫn index entry |

**Điểm cần lưu ý:** `manual_write` và `extractor` chỉ append — không tự giải conflict. autoDream Phase 3 mới là nơi LLM hợp nhất và loại bỏ fact lỗi thời.

---

### `eval_retrieval.py` — Tầng 3: Retrieval Accuracy

**Câu hỏi:** Với query của user, hệ thống có kéo đúng topic vào context không?

**Cách đánh giá:** Tạo topic với hook cụ thể → query với nhiều dạng từ → đo hit/miss.

| Test | Kiểm tra gì | Kết quả kỳ vọng |
|------|------------|----------------|
| `test_exact_keyword_hit` | Từ khóa chính xác trong hook | Hit |
| `test_no_match_irrelevant_query` | Query hoàn toàn không liên quan | Miss (không false positive) |
| `test_stopwords_not_counted` | Query chỉ là stopword ("tôi là ai") | Miss |
| `test_ranking_by_overlap` | Nhiều topic cùng match | Topic overlap nhiều xếp trước |
| `test_multi_topic_max_cap` | Có 5 topic match | Chỉ inject tối đa `max_topics` |
| `test_synonym_miss` | Lưu "bò", hỏi "beef" | **Miss** — điểm yếu đã biết |
| `test_partial_match_in_title` | Từ khóa có trong title (không chỉ hook) | Hit |

**Điểm yếu đã biết:** Keyword overlap không hiểu ngữ nghĩa — "bò" ≠ "beef". Fix cần vector embeddings (semantic search). Test này được ghi nhận là `[LIMIT]`, không tính vào failed.

---

### `eval_end_to_end.py` — Tầng 4: Conversational Quality

**Câu hỏi:** Bot có thực sự dùng memory để trả lời đúng không?

**Cách đánh giá:** Giả lập memory đã lưu từ session trước → kiểm tra `build_system_prompt()` có inject đúng thông tin không. Nếu system prompt chứa đúng memory → bot có đủ thông tin để trả lời đúng.

| Scenario | Tình huống | Kiểm tra |
|----------|-----------|---------|
| `scenario_allergy_remembered` | Session trước: dị ứng tôm. Hỏi: "tôi ăn tôm được không?" | System prompt chứa thông tin dị ứng |
| `scenario_name_not_injected_for_irrelevant_query` | Hỏi thời tiết → topic tên không liên quan | Context block rỗng (không inject sai) |
| `scenario_index_always_in_context` | Query bất kỳ | MEMORY.md index luôn có trong prompt (layer 1) |
| `scenario_multi_topic_relevant` | Có 3 topic, hỏi về dị ứng | Chỉ topic dị ứng được inject, không kéo hết |
| `scenario_empty_memory_no_crash` | Memory hoàn toàn rỗng | Bot không crash, system prompt vẫn hợp lệ |
---
