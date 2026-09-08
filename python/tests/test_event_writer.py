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


def _event(raw: str, *, received_at: str = "2026-09-08T00:00:00Z"):
    return IngestedEvent(TelemetryMessage.parse(raw), received_at)


def test_ingested_event_observed_at_prefers_message_timestamp():
    csv = _event("PERIODIC,1,1.0,0", received_at="2026-09-08T10:00:00Z")
    assert csv.observed_at == "2026-09-08T10:00:00Z"

    payload = (
        '{"version":1,"type":"PERIODIC","timestamp":"2026-01-01T00:00:00Z",'
        '"machine_id":1,"standard":"x","unit":"mm/s RMS","max_velocity_rms":1.0,'
        '"zone":"A","error_code":0,"readings":[]}'
    )
    js = IngestedEvent(TelemetryMessage.parse(payload), "2026-09-08T10:00:00Z")
    assert js.observed_at == "2026-01-01T00:00:00Z"


def test_writer_persists_submitted_events_in_order(store):
    writer = EventWriter(store)
    writer.start()
    try:
        for index in range(50):
            assert writer.submit(_event(f"PERIODIC,1,{index}.0,0")) is True
        writer.wait_idle()
        values = [row["vibration_value"] for row in store.recent_events(limit=100)]
    finally:
        writer.stop()

    assert values == [float(index) for index in reversed(range(50))]


def test_writer_computes_zone_d_streak(store):
    writer = EventWriter(store)
    writer.start()
    try:
        for raw in (
            "CRITICAL,1,7.0,2",
            "CRITICAL,1,7.1,2",
            "WARNING,1,4.5,1",
            "CRITICAL,1,7.2,2",
        ):
            writer.submit(_event(raw))
        writer.wait_idle()
        counts = [row["zone_d_consecutive_count"] for row in store.recent_events()]
    finally:
        writer.stop()

    # recent_events는 최신순
    assert counts == [1, 0, 2, 1]


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
    writer.wait_idle()
    count = len(store.recent_events(limit=100))
    writer.stop()

    assert count == 20


def test_writer_survives_sqlite_error_and_keeps_processing(store, monkeypatch):
    import sqlite3

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
        writer.submit(_event("CRITICAL,1,9.0,2"))  # 첫 기록은 실패
        writer.submit(_event("WARNING,1,4.5,1"))  # 두 번째는 성공해야 한다
        writer.wait_idle()
        rows = store.recent_events()
    finally:
        writer.stop()

    assert [row["message_type"] for row in rows] == ["WARNING"]
    assert writer.write_error_count == 1


def test_writer_survives_non_sqlite_error(store, monkeypatch):
    def boom(*args, **kwargs):
        raise OverflowError("Python int too large to convert to SQLite INTEGER")

    monkeypatch.setattr(store, "record_event", boom)

    writer = EventWriter(store)
    writer.start()
    try:
        writer.submit(_event("PERIODIC,1,1.0,0"))
        writer.wait_idle()
        assert writer._thread is not None and writer._thread.is_alive()
        assert writer.write_error_count == 1
    finally:
        writer.stop()


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


def test_owns_store_closes_connection_on_stop(tmp_path):
    store = EventStore.open(str(tmp_path / "f.db"))
    writer = EventWriter(store, owns_store=True)
    writer.start()
    writer.stop()

    import sqlite3

    with pytest.raises(sqlite3.ProgrammingError):
        store.recent_events()
