from memory.store import transcript_store


def test_append_and_grep_found():
    transcript_store.append_turn("s1", "user", "tôi thích ăn phở")
    results = transcript_store.grep("phở")
    assert len(results) == 1
    assert results[0]["content"] == "tôi thích ăn phở"
    assert results[0]["role"] == "user"


def test_grep_not_found():
    transcript_store.append_turn("s1", "user", "tôi thích ăn phở")
    results = transcript_store.grep("bún bò")
    assert results == []


def test_grep_case_insensitive():
    transcript_store.append_turn("s1", "user", "Tôi Thích Phở")
    results = transcript_store.grep("thích phở")
    assert len(results) == 1


def test_grep_multiple_sessions():
    transcript_store.append_turn("s1", "user", "tôi dị ứng tôm")
    transcript_store.append_turn("s2", "assistant", "tôi nhớ bạn dị ứng tôm")
    results = transcript_store.grep("dị ứng tôm")
    assert len(results) == 2


def test_grep_max_results():
    for i in range(25):
        transcript_store.append_turn("s1", "user", f"keyword lần {i}")
    results = transcript_store.grep("keyword", max_results=20)
    assert len(results) == 20


def test_all_turns_since_no_filter():
    transcript_store.append_turn("s1", "user", "tin nhắn 1")
    transcript_store.append_turn("s1", "assistant", "trả lời 1")
    turns = transcript_store.all_turns_since(since=None)
    assert len(turns) == 2


def test_all_turns_since_filters_old():
    from datetime import datetime, timezone, timedelta
    transcript_store.append_turn("s1", "user", "tin nhắn cũ")
    future = (datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat()
    transcript_store.append_turn("s1", "user", "tin nhắn mới")
    turns = transcript_store.all_turns_since(since=future)
    # chỉ lấy turns sau mốc future — tin nhắn mới ghi sau future
    contents = [t["content"] for t in turns]
    assert "tin nhắn cũ" not in contents
