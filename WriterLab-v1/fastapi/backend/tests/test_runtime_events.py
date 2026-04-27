"""runtime_events 直测。

该模块用模块级 list + 锁缓冲最近的 workflow 运行事件，被前端 SSE/WS 消费。
关键不变量：
- publish_runtime_event 写入字段填充顺序
- 超出 _MAX_EVENTS 后旧事件被丢弃，最新事件保留
- get_runtime_events 的 after_index 切片语义、负值容忍
- 多线程并发安全
"""

import threading

from app.services import runtime_events as re_mod


def setup_function():
    # 该模块是 process-wide singleton；每个用例前清空缓冲。
    with re_mod._EVENT_LOCK:
        re_mod._EVENTS.clear()


def test_publish_event_normalizes_payload_fields():
    re_mod.publish_runtime_event(
        {
            "event": "step_started",
            "run_id": "r1",
            "step": "plan",
            "provider": "openai",
            "model": "gpt-4o-mini",
            "queue_depth": 3,
            "can_cancel": True,
            "message": "ok",
        }
    )
    events, next_index = re_mod.get_runtime_events()
    assert next_index == 1
    assert len(events) == 1
    e = events[0]
    assert e["event"] == "step_started"
    assert e["run_id"] == "r1"
    assert e["step"] == "plan"
    assert e["provider"] == "openai"
    assert e["model"] == "gpt-4o-mini"
    assert e["queue_depth"] == 3
    assert e["can_cancel"] is True
    assert e["message"] == "ok"
    assert "created_at" in e and e["created_at"]


def test_publish_event_uses_defaults_when_fields_missing():
    re_mod.publish_runtime_event({})
    events, _ = re_mod.get_runtime_events()
    e = events[0]
    assert e["event"] == "runtime"
    assert e["source"] == "workflow"
    assert e["queue_depth"] == 0
    assert e["can_cancel"] is False
    assert e["run_id"] is None
    assert e["step"] is None


def test_get_runtime_events_with_after_index_only_returns_new():
    re_mod.publish_runtime_event({"event": "a"})
    re_mod.publish_runtime_event({"event": "b"})
    re_mod.publish_runtime_event({"event": "c"})
    first_batch, idx_after_first = re_mod.get_runtime_events()
    assert len(first_batch) == 3
    assert idx_after_first == 3
    re_mod.publish_runtime_event({"event": "d"})
    new_batch, idx_after_d = re_mod.get_runtime_events(after_index=idx_after_first)
    assert [e["event"] for e in new_batch] == ["d"]
    assert idx_after_d == 4


def test_get_runtime_events_clamps_negative_after_index_to_zero():
    re_mod.publish_runtime_event({"event": "x"})
    events, _ = re_mod.get_runtime_events(after_index=-99)
    assert [e["event"] for e in events] == ["x"]


def test_get_runtime_events_after_too_high_index_returns_empty():
    re_mod.publish_runtime_event({"event": "x"})
    events, idx = re_mod.get_runtime_events(after_index=999)
    assert events == []
    assert idx == 1


def test_buffer_caps_at_max_events_and_keeps_most_recent():
    cap = re_mod._MAX_EVENTS
    for i in range(cap + 50):
        re_mod.publish_runtime_event({"event": f"e{i}"})
    events, idx = re_mod.get_runtime_events()
    assert len(events) == cap
    # 最早的 50 条应已被裁掉；保留的第 1 条应是 e50。
    assert events[0]["event"] == "e50"
    assert events[-1]["event"] == f"e{cap + 49}"
    assert idx == cap


def test_publish_event_is_thread_safe_and_does_not_lose_writes():
    threads = []
    per_thread = 50
    n_threads = 8

    def worker(tag: str):
        for i in range(per_thread):
            re_mod.publish_runtime_event({"event": f"{tag}-{i}"})

    for t in range(n_threads):
        thread = threading.Thread(target=worker, args=(f"t{t}",))
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()

    events, _ = re_mod.get_runtime_events()
    assert len(events) == per_thread * n_threads
