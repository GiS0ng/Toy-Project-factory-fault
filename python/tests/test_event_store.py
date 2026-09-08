import json

import pytest

from network.message import TelemetryMessage
from persistence.event_store import EventStore


@pytest.fixture
def store():
    """인메모리 SQLite로 연 저장소를 제공한다."""
    store = EventStore.open(":memory:")
    yield store
    store.close()


def _message(raw: str) -> TelemetryMessage:
    return TelemetryMessage.parse(raw)


def test_record_event_persists_row_and_returns_id(store):
    event_id = store.record_event(
        _message("WARNING,2,4.5,1"),
        observed_at="2026-09-08T00:00:00Z",
        received_at="2026-09-08T00:00:01Z",
        zone_d_consecutive_count=0,
    )

    events = store.recent_events()
    assert event_id == events[0]["id"]
    assert events[0]["machine_id"] == 2
    assert events[0]["message_type"] == "WARNING"
    assert events[0]["vibration_value"] == 4.5
    assert events[0]["observed_at"] == "2026-09-08T00:00:00Z"
    assert events[0]["received_at"] == "2026-09-08T00:00:01Z"


def test_record_event_keeps_json_zone_and_count(store):
    payload = {
        "version": 1,
        "type": "CRITICAL",
        "timestamp": "2026-09-08T01:00:00Z",
        "machine_id": 3,
        "standard": "ISO 20816-3:2022",
        "unit": "mm/s RMS",
        "max_velocity_rms": 7.2,
        "zone": "D",
        "error_code": 2,
        "readings": [{"sensor_id": 1, "velocity_rms": 7.2}],
    }
    store.record_event(
        _message(json.dumps(payload)),
        observed_at="2026-09-08T01:00:00Z",
        received_at="2026-09-08T01:00:02Z",
        zone_d_consecutive_count=3,
    )

    row = store.recent_events()[0]
    assert row["zone"] == "D"
    assert row["zone_d_consecutive_count"] == 3


def test_machine_state_upserts_latest_snapshot(store):
    store.record_event(
        _message("PERIODIC,5,1.0,0"),
        observed_at="2026-09-08T00:00:00Z",
        received_at="2026-09-08T00:00:00Z",
        zone_d_consecutive_count=0,
    )
    last_id = store.record_event(
        _message("CRITICAL,5,8.0,2"),
        observed_at="2026-09-08T00:00:03Z",
        received_at="2026-09-08T00:00:03Z",
        zone_d_consecutive_count=1,
    )

    states = store.machine_states()
    assert len(states) == 1
    assert states[0]["machine_id"] == 5
    assert states[0]["message_type"] == "CRITICAL"
    assert states[0]["vibration_value"] == 8.0
    assert states[0]["zone_d_consecutive_count"] == 1
    assert states[0]["last_event_id"] == last_id
    assert states[0]["updated_at"] == "2026-09-08T00:00:03Z"


def test_recent_events_orders_newest_first_and_limits(store):
    for index in range(5):
        store.record_event(
            _message(f"PERIODIC,1,{index}.0,0"),
            observed_at=f"2026-09-08T00:00:0{index}Z",
            received_at=f"2026-09-08T00:00:0{index}Z",
            zone_d_consecutive_count=0,
        )

    events = store.recent_events(limit=2)
    assert [row["vibration_value"] for row in events] == [4.0, 3.0]


def test_timeseries_returns_newest_when_truncated_but_ascending(store):
    for index in range(6):
        store.record_event(
            _message(f"PERIODIC,1,{index}.0,0"),
            observed_at=f"2026-09-08T00:00:0{index}Z",
            received_at=f"2026-09-08T00:00:0{index}Z",
            zone_d_consecutive_count=0,
        )

    points = store.timeseries(machine_id=1, since_iso="2026-09-08T00:00:00Z", limit=3)
    # limit을 넘으면 최근 3건을 취하되, 반환은 오래된 순
    assert [row["vibration_value"] for row in points] == [3.0, 4.0, 5.0]
