import sqlite3

import pytest

from network.message import TelemetryMessage
from persistence.event_store import EventStore
from persistence.event_writer import EventWriter, IngestedEvent


@pytest.fixture
def store():
    """인메모리 SQLite로 연 저장소를 제공한다."""
    store = EventStore.open(":memory:")
    yield store
    store.close()


def _event(raw: str, *, received_at: str = "2026-09-08T00:00:00Z", count: int = 0):
    return IngestedEvent(TelemetryMessage.parse(raw), received_at, count)


def test_ingested_event_observed_at_prefers_message_timestamp():
    csv = _event("PERIODIC,1,1.0,0", received_at="2026-09-08T10:00:00Z")
    assert csv.observed_at == "2026-09-08T10:00:00Z"

    payload = (
        '{"version":1,"type":"PERIODIC","timestamp":"2026-01-01T00:00:00Z",'
        '"machine_id":1,"standard":"x","unit":"mm/s RMS","max_velocity_rms":1.0,'
        '"zone":"A","error_code":0,"readings":[]}'
    )
    js = IngestedEvent(TelemetryMessage.parse(payload), "2026-09-08T10:00:00Z", 0)
    assert js.observed_at == "2026-01-01T00:00:00Z"


def test_writer_persists_submitted_events_in_order(store):
    writer = EventWriter(store)
    writer.start()
    try:
        for index in range(50):
            assert writer.submit(_event(f"PERIODIC,1,{index}.0,0")) is True
        writer.wait_idle()
    finally:
        writer.stop()

    values = [row["vibration_value"] for row in store.recent_events(limit=100)]
    assert values == [float(index) for index in reversed(range(50))]


def test_submit_rejects_when_queue_is_full(store):
    # 스레드를 시작하지 않으므로 큐가 소비되지 않는다.
    writer = EventWriter(store, max_queue_size=1)

    assert writer.submit(_event("PERIODIC,1,1.0,0")) is True
    assert writer.submit(_event("PERIODIC,1,2.0,0")) is False
    assert writer.submit(_event("PERIODIC,1,3.0,0")) is False
    assert writer.dropped_count == 2


def test_stop_drains_pending_events(store):
    writer = EventWriter(store)
    for index in range(20):
        writer.submit(_event(f"PERIODIC,7,{index}.0,0"))

    writer.start()
    writer.stop()  # 큐에 남은 20건을 모두 처리한 뒤 종료해야 한다

    assert len(store.recent_events(limit=100)) == 20


def test_writer_survives_db_error_and_keeps_processing(store, monkeypatch):
    real_record = store.record_event
    calls = {"n": 0}

    def flaky(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise sqlite3.OperationalError("disk I/O error")
        return real_record(*args, **kwargs)

    monkeypatch.setattr(store, "record_event", flaky)

    writer = EventWriter(store)
    writer.start()
    try:
        writer.submit(_event("CRITICAL,1,9.0,2", count=1))  # 첫 기록은 실패
        writer.submit(_event("WARNING,1,4.5,1"))  # 두 번째는 성공해야 한다
        writer.wait_idle()
    finally:
        writer.stop()

    rows = store.recent_events()
    assert len(rows) == 1
    assert rows[0]["message_type"] == "WARNING"


def test_double_start_raises(store):
    writer = EventWriter(store)
    writer.start()
    try:
        with pytest.raises(RuntimeError):
            writer.start()
    finally:
        writer.stop()


def test_zero_queue_size_rejected(store):
    with pytest.raises(ValueError, match="양수"):
        EventWriter(store, max_queue_size=0)
