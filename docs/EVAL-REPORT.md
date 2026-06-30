# Eval Report — Product Evaluation

**Ngày chạy:** 2026-06-30
**Môi trường:** Python 3.11.15 · conda env `ml`
**Tổng kết:** 16/16 passed · 1 limitation đã biết · không gọi LLM thật

```bash
python test/eval/eval_memory_quality.py
python test/eval/eval_retrieval.py
python test/eval/eval_end_to_end.py
```

---

## Tại sao cần eval ngoài unit test?

Unit test kiểm tra **code chạy đúng** — nhưng không trả lời được câu hỏi sản phẩm:
- Bot có thực sự nhớ thông tin user không?
- Memory có được kéo ra đúng lúc không?
- User hỏi khác từ thì có miss không?

Eval scripts kiểm tra **hành vi thực tế** từ góc nhìn người dùng.

---

## Kết quả tổng hợp

| Tầng | File | Passed | Failed | Limitation |
|------|------|--------|--------|------------|
| 2 | `eval_memory_quality.py` | 5/5 | 0 | — |
| 3 | `eval_retrieval.py` | 6/6 | 0 | 1 (đã biết) |
| 4 | `eval_end_to_end.py` | 5/5 | 0 | — |
| **Tổng** | | **16/16** | **0** | **1** |

---

## Eval 2: Memory Quality — 5/5 PASS

**Câu hỏi:** Memory có lưu đúng fact, không trùng, xử lý conflict như thế nào?

**Phương pháp:** Mock LLM trả về JSON fact cố định → inspect file thật trong temp dir.

| Test | Kết quả | Ghi chú |
|------|---------|---------|
| `test_precision_new_fact` | PASS | Fact mới → topic file + MEMORY.md đều được tạo đúng |
| `test_precision_no_duplicate_index` | PASS | Cùng slug ghi 2 lần → chỉ 1 entry trong index |
| `test_conflict_resolution_append` | PASS | Fact mới mâu thuẫn fact cũ → cả 2 được giữ (append) |
| `test_recall_obvious_fact` | PASS | Fact rõ ràng → được lưu khi LLM trả `should_save=true` |
| `test_forget_removes_completely` | PASS | `/forget` → xóa sạch cả topic file lẫn index entry |

**Quan sát quan trọng:**
`manual_write` và `extractor` chỉ **append** — không tự giải conflict. Khi user nói "hết dị ứng tôm, giờ dị ứng bò", cả 2 fact đều được giữ trong cùng topic file. autoDream Phase 3 mới là nơi LLM hợp nhất và loại bỏ fact lỗi thời.

---

## Eval 3: Retrieval Accuracy — 6/6 PASS · 1 LIMITATION

**Câu hỏi:** Với query của user, hệ thống có kéo đúng topic vào context không?

**Phương pháp:** Tạo topic với hook cụ thể → query với nhiều dạng từ → đo hit/miss.

| Test | Kết quả | Ghi chú |
|------|---------|---------|
| `test_exact_keyword_hit` | PASS | Từ khóa chính xác trong hook → hit |
| `test_no_match_irrelevant_query` | PASS | Query không liên quan → không false positive |
| `test_stopwords_not_counted` | PASS | "tôi là ai" (toàn stopword) → không match bất kỳ topic |
| `test_ranking_by_overlap` | PASS | Topic overlap nhiều từ xếp trước |
| `test_multi_topic_max_cap` | PASS | Chỉ inject tối đa `max_topics`, không inject tất cả |
| `test_synonym_miss` | LIMIT | Lưu "bò", hỏi "beef" → MISS (xem bên dưới) |
| `test_partial_match_in_title` | PASS | Keyword trong title cũng được tính, không chỉ hook |

**Limitation đã biết — Synonym miss:**

```
Lưu trong memory: "dị ứng bò"
User hỏi:         "tôi có thể ăn beef không"
Kết quả:          MISS — topic không được kéo vào context
```

Nguyên nhân: retrieval dùng **keyword overlap** — so sánh chính xác từng từ, không hiểu ngữ nghĩa. "bò" ≠ "beef" dù cùng nghĩa.

Fix đề xuất: thay keyword overlap bằng **vector embeddings** (semantic search) — tính cosine similarity giữa query vector và hook vector. Đây là hướng đi của các hệ thống memory production (MemGPT, LangMem).

---

## Eval 4: End-to-End Conversational Quality — 5/5 PASS

**Câu hỏi:** Bot có thực sự dùng memory để trả lời đúng không?

**Phương pháp:** Giả lập memory đã lưu từ session trước → kiểm tra `build_system_prompt()` có inject đúng thông tin không. Nếu system prompt chứa đúng memory → bot có đủ thông tin để trả lời đúng. Không gọi LLM thật.

| Scenario | Tình huống | Kết quả | Ghi chú |
|----------|-----------|---------|---------|
| `allergy_remembered` | Session trước: dị ứng tôm. Hỏi: ăn tôm được không? | PASS | System prompt chứa 'tôm' → bot có đủ thông tin để cảnh báo |
| `no_false_injection` | Hỏi thời tiết → topic tên không liên quan | PASS | Context block rỗng, không inject sai topic |
| `index_always_in_context` | Query bất kỳ (kể cả toán học) | PASS | MEMORY.md index luôn có trong prompt (layer 1) |
| `multi_topic_relevant` | Có 3 topic, hỏi về dị ứng | PASS | Chỉ topic dị ứng được inject, không kéo nghề nghiệp hay sở thích |
| `empty_memory_no_crash` | Memory hoàn toàn rỗng | PASS | Bot không crash, system prompt hợp lệ |

**Quan sát:**
- Layer 1 (MEMORY.md index) luôn được inject bất kể query là gì — đây là thiết kế đúng, đảm bảo bot luôn biết "mình đã biết gì về user"
- Layer 2 (topic files) chỉ được inject khi có keyword overlap — tránh nhồi context không cần thiết

---

## Hạn chế của bộ eval hiện tại

| Hạn chế | Mô tả |
|---------|-------|
| Không test LLM response thật | Eval 4 chỉ kiểm tra system prompt được build, không kiểm tra bot có thực sự dùng memory trong câu trả lời |
| Synonym miss chưa được fix | Retrieval bỏ sót query dùng từ đồng nghĩa (xem Eval 3) |
| Không test autoDream end-to-end | Chưa có eval cho toàn bộ flow autoDream (4 phase) |
| Không đo latency | Thời gian extractMemories, autoDream chưa được đo |

---

## Bước tiếp theo nếu muốn đánh giá sâu hơn

| Hướng | Mô tả | Chi phí |
|-------|-------|---------|
| **LLM-as-judge** | Dùng Claude/GPT chấm response có dùng memory đúng không | Tốn API credit |
| **Human eval** | Người thật đọc và chấm điểm từng scenario | Tốn thời gian |
| **A/B test** | Bot có memory vs bot không có memory — so sánh user satisfaction | Cần user thật |
| **Vector embeddings** | Thay keyword overlap bằng semantic search để fix synonym miss | Refactor retrieval.py |
