import uuid

import llm_client
import state as state_module
from memory.write import autodream, extractor, manual_write
from memory.store import index_store, transcript_store
from memory.read import retrieval
from memory.core import paths

SYSTEM_PROMPT_TEMPLATE = """Bạn là một trợ lý AI có trí nhớ dài hạn. Đây là index các điều bạn đã biết về người dùng:

{index}

Khi trả lời, hãy tận dụng thông tin liên quan bên dưới (nếu có) mà không cần hỏi lại người dùng những gì đã biết.
"""


def build_system_prompt(query: str) -> str:
    index = index_store.read_index()
    prompt = SYSTEM_PROMPT_TEMPLATE.format(index=index)
    context_block = retrieval.build_context_block(query)
    if context_block:
        prompt += "\n" + context_block
    return prompt


def handle_search(query: str) -> str:
    results = transcript_store.grep(query)
    if not results:
        return f"Không tìm thấy gì khớp với '{query}' trong lịch sử chat."
    lines = [f"[{r['timestamp']}] {r['role']}: {r['content']}" for r in results]
    return "\n".join(lines)


def main() -> None:
    paths.ensure_dirs()
    state = state_module.load_state()
    state["session_count"] += 1
    state_module.save_state(state)
    session_id = f"{uuid.uuid4().hex[:8]}"

    autodream_thread = autodream.maybe_run_async(state)
    if autodream_thread:
        print("(đang chạy autoDream consolidation ở nền...)")

    pending_threads = []
    chat_model = llm_client.get_chat_model()

    print("Memory Chatbot — gõ /remember, /forget, /search, hoặc /exit để thoát.")
    while True:
        try:
            user_input = input("\nBạn: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue
        if user_input in ("/exit", "/quit"):
            break

        if user_input.startswith("/remember "):
            print(manual_write.handle_remember(user_input[len("/remember "):].strip()))
            continue
        if user_input.startswith("/forget "):
            print(manual_write.handle_forget(user_input[len("/forget "):].strip()))
            continue
        if user_input.startswith("/search "):
            print(handle_search(user_input[len("/search "):].strip()))
            continue

        system_prompt = build_system_prompt(user_input)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]
        try:
            response = chat_model.invoke(messages)
            answer = response.content
        except Exception as e:
            if "ReadTimeout" in type(e).__name__ or "timeout" in str(e).lower():
                print("\nBot: (Server NVIDIA đang chậm, thử lại nhé!)")
            else:
                print(f"\nBot: (Lỗi: {e})")
            continue
        print(f"\nBot: {answer}")

        transcript_store.append_turn(session_id, "user", user_input)
        transcript_store.append_turn(session_id, "assistant", answer)
        pending_threads.append(extractor.maybe_extract_async(user_input, answer))

    print("\nĐang lưu nốt memory nền trước khi thoát...")
    for t in pending_threads:
        t.join(timeout=15)
    if autodream_thread:
        autodream_thread.join(timeout=30)


if __name__ == "__main__":
    main()
