# Memory Chatbot — Triển khai theo sơ đồ kiến trúc (Python / CLI / NVIDIA DeepSeek)

## Context

Người dùng đang nghiên cứu cơ chế memory của LLM và muốn xây một chatbot CLI có khả năng "nhớ" giống hệ thống memory trong ảnh sơ đồ: 3 write path (manual / autoDream / extractMemories), 3 storage layer (MEMORY.md index / topic files / session transcripts), 1 lock chống race, và 1 read path nạp memory vào context theo độ liên quan. Dự án bắt đầu từ thư mục trống — đây là greenfield, không có code cũ cần tái sử dụng.

Lựa chọn nền tảng người dùng đã chốt:
- **Ngôn ngữ**: Python
- **LLM**: NVIDIA NIM endpoint qua `langchain_nvidia_ai_endpoints.ChatNVIDIA`, model `deepseek-ai/deepseek-v4-pro`
- **Giao diện**: CLI (terminal)

## Quyết định kỹ thuật quan trọng (và lý do)

**Read path dùng heuristic keyword-overlap, KHÔNG dùng LLM tool-calling cho MVP.**
Sơ đồ gốc cho thấy "FileReadTool" và "Targeted grep" được LLM gọi như tool. Nhưng chưa rõ NVIDIA NIM cho model `deepseek-ai/deepseek-v4-pro` qua `ChatNVIDIA` có hỗ trợ `.bind_tools()` ổn định hay không — đây là rủi ro tích hợp lớn nhất nếu làm sai từ đầu. Vì vậy MVP sẽ:
- Luôn nạp `MEMORY.md` (index) vào system prompt — đúng "always" trong sơ đồ.
- Trước khi gọi LLM, so khớp từ khóa đơn giản giữa câu hỏi user và các "hook" trong index để tự động nạp thêm nội dung topic file liên quan — đúng tinh thần "if relevant" mà không cần model tự gọi tool.
- Layer 3 (transcript) chỉ được "grep" khi user dùng lệnh rõ ràng `/search <từ khóa>`, hoặc khi câu hỏi chứa tham chiếu thời gian (hôm qua, tuần trước...) — đúng "grep only, narrow terms".
- Nâng cấp lên tool-calling thật (model tự quyết gọi tool) có thể làm ở v2 sau khi xác nhận model hỗ trợ.

**"Background/async" trong CLI = Python thread, không phải subagent/process riêng.**
Sơ đồ dùng "forked subagent" cho autoDream vì đó là ngữ cảnh agent harness. Trong CLI Python đơn giản, "background" được mô phỏng bằng `threading.Thread` (non-daemon, join với timeout ngắn khi thoát) để không chặn input của user nhưng vẫn đảm bảo ghi xong trước khi process kết thúc.

## Cấu trúc thư mục

```
memory_chatbot/
  requirements.txt
  .env.example
  config.py                  # đường dẫn, ngưỡng autoDream, model config
  state.py                   # session_count, last_autodream_at (data/state.json)
  llm_client.py              # khởi tạo ChatNVIDIA (chat + classification instance)
  main.py                    # CLI entrypoint — chat loop
  memory/
    __init__.py
    paths.py                 # đảm bảo data/memory, data/transcripts tồn tại
    index_store.py           # đọc/ghi MEMORY.md (Layer 1)
    topic_store.py           # đọc/ghi/list topic *.md có frontmatter (Layer 2)
    transcript_store.py      # append jsonl + grep (Layer 3)
    lock.py                  # consolidation lock (race protection)
    manual_write.py          # /remember, /forget — ghi đồng bộ ngay lập tức
    extractor.py             # extractMemories — bắt theo turn, ghi nền (async)
    autodream.py             # 4 phase: Orient → Gather signal → Consolidate → Prune & index
    retrieval.py             # heuristic chọn topic file liên quan để nạp vào context
  data/                       # gitignored, sinh ra lúc runtime
    memory/MEMORY.md
    memory/<topic>.md
    transcripts/<session_id>.jsonl
    state.json
```

## Chi tiết từng module

**config.py** — đọc `NVIDIA_API_KEY` từ `.env` (qua `python-dotenv`), hằng số: `MEMORY_DIR`, `TRANSCRIPTS_DIR`, `STATE_PATH`, `AUTODREAM_MIN_HOURS=24`, `AUTODREAM_MIN_SESSIONS=5`, `LOCK_STALE_MINUTES=10`.

**state.py** — `load_state()/save_state()` đọc/ghi `data/state.json` dạng `{session_count, last_autodream_at, last_autodream_session_count}`. Hàm `should_run_autodream(state) -> bool` kiểm tra cả 2 điều kiện (>=24h **và** >=5 session) đúng như chú thích trong sơ đồ.

**memory/lock.py** — file lock tại `data/memory/.consolidation.lock` chứa `{pid, started_at}`. Context manager `consolidation_lock()`: acquire (ghi file nếu chưa tồn tại hoặc lock đã stale quá `LOCK_STALE_MINUTES`), release khi xong (try/finally). Dùng để bọc mọi đường ghi vào Layer 1/2 (manual_write, extractor, autodream) — đúng vai trò "race protection" trong sơ đồ.

**memory/index_store.py** — `read_index()`, `append_entry(title, filename, hook)`, `rewrite_index(entries)` (dùng ở Phase 4 của autoDream).

**memory/topic_store.py** — frontmatter đơn giản bằng `pyyaml` (`---\nname:...\ndescription:...\nmetadata:\n  type:...\n---\n<content>`). `write_topic()`, `read_topic()`, `list_topics()`.

**memory/transcript_store.py** — `append_turn(session_id, role, content)` ghi 1 dòng jsonl ngay (đồng bộ, rẻ). `grep(query, since=None)` chỉ trả các dòng khớp, không bao giờ load nguyên file vào context — đúng "grepped, never fully read".

**memory/manual_write.py** — lệnh CLI rõ ràng `/remember <nội dung>` và `/forget <từ khóa>`. Gọi LLM (classification instance, temperature thấp) để quyết định: cập nhật topic file có sẵn hay tạo mới, rồi ghi **ngay** (trong lock) — khớp đường nét liền "Immediate write".

**memory/extractor.py** — sau mỗi lượt assistant trả lời, spawn thread gọi LLM nhỏ: "dựa trên lượt chat này + index hiện có, có fact nào đáng lưu không, nếu có thuộc topic nào?" Nếu có → ghi qua `topic_store` + `index_store` trong lock. Đây là đường nét đứt "Per-turn capture" → Layer 1+2.

**memory/autodream.py** — `maybe_run_async(state)`: nếu `should_run_autodream` true, spawn thread chạy 4 phase trong 1 lock:
1. *Orient*: đọc MEMORY.md + list topic files.
2. *Gather signal*: `transcript_store.grep` các session từ `last_autodream_at` đến nay.
3. *Consolidate*: gọi LLM tổng hợp — hợp nhất/cập nhật topic files trùng lặp.
4. *Prune & index*: gọi LLM rà soát mâu thuẫn/lỗi thời, xóa/sửa, rồi `rewrite_index`.
Cập nhật `state.last_autodream_at`, `last_autodream_session_count` khi xong.

**memory/retrieval.py** — heuristic: tách từ khóa trong câu hỏi user, so với "hook" của từng dòng trong index (overlap đơn giản hoặc `difflib`), trả về danh sách topic file liên quan để nạp full nội dung vào context trước khi gọi LLM.

**llm_client.py** — 2 instance `ChatNVIDIA` theo đúng snippet người dùng cung cấp: một cho chat chính (temperature=1, top_p=0.95, max_tokens=16384, thinking=False), một cho các tác vụ phân loại/consolidate (temperature thấp ~0.2 để output ổn định).

**main.py** — vòng lặp:
- Khởi động: `load_state()`, tăng `session_count`, tạo `session_id`; gọi `autodream.maybe_run_async(state)`.
- Build system prompt = nội dung `MEMORY.md` + hướng dẫn ngắn cho model.
- Mỗi lượt: nếu input là `/remember`, `/forget`, `/search` → xử lý riêng (đồng bộ); ngược lại → `retrieval` chọn topic liên quan, ghép context, gọi LLM, in câu trả lời.
- Ghi transcript đồng bộ; spawn thread `extractor` chạy nền.
- Khi `/exit`/Ctrl+C: join các thread nền còn lại (timeout ngắn) trước khi thoát để không mất ghi memory.

## Thứ tự build (để test tăng dần, không làm hết 1 lần)

1. `config.py`, `state.py`, `llm_client.py` + `main.py` bản tối giản: chat loop không có memory gì cả — xác nhận gọi NVIDIA API chạy được trước.
2. `memory/paths.py`, `index_store.py`, `topic_store.py`, `manual_write.py` — thêm `/remember`, `/forget`, xác nhận ghi/đọc MEMORY.md + topic file đúng format.
3. `memory/lock.py` — bọc bước 2 trong lock.
4. `memory/transcript_store.py` + ghi log mỗi lượt chat + lệnh `/search`.
5. `memory/retrieval.py` — nạp topic liên quan vào context trước khi gọi LLM, test hỏi lại fact đã `/remember`.
6. `memory/extractor.py` — bắt fact tự động không cần `/remember`, chạy nền.
7. `memory/autodream.py` — 4 phase, test bằng cách chỉnh tay `data/state.json` để giả lập đủ điều kiện trigger.

## Kiểm thử cuối (verification)

- `python main.py` → gõ "tôi tên An, tôi thích ăn phở" → đợi vài giây → kiểm tra `data/memory/MEMORY.md` và topic file mới xuất hiện.
- `/remember tôi dị ứng tôm` → kiểm tra ghi ngay (không cần đợi).
- Hỏi lại "tôi thích ăn gì?" ở câu tiếp theo hoặc session mới → xác nhận câu trả lời đúng nhờ retrieval nạp topic file.
- `/search phở` → xác nhận chỉ trả dòng transcript khớp, không in toàn bộ log.
- Sửa tay `data/state.json` (lùi `last_autodream_at` >24h, `session_count` +5) → khởi động lại → quan sát log 4 phase autoDream chạy, kiểm tra `MEMORY.md` được viết lại gọn hơn.
