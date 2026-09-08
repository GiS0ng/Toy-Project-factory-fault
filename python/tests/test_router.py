import json
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from network.router import FactoryRouter
from persistence.event_store import EventStore
from persistence.event_writer import EventWriter

FIXED_NOW = datetime(2026, 9, 8, 12, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def store():
    """인메모리 SQLite로 연 저장소를 제공한다."""
    store = EventStore.open(":memory:")
    yield store
    store.close()


@pytest.fixture
def writer(store):
    """실제 EventWriter를 시작해 두고, 테스트가 끝나면 큐를 비운 뒤 정지한다."""
    writer = EventWriter(store)
    writer.start()
    yield writer
    writer.stop()


@pytest.fixture
def router(writer):
    """고정 시계와 실제 writer를 쓰는 라우터를 제공한다."""
    return FactoryRouter(writer, clock=lambda: FIXED_NOW)


def test_periodic_message_is_recorded_without_alarm(router, writer, store, monkeypatch):
    """정기 데이터가 저장되고 긴급 알림은 전송되지 않는지 검증한다."""
    alarm = Mock()
    monkeypatch.setattr("network.router.send_to_kakao_sos", alarm)

    assert router.parse_and_route("PERIODIC,1,1.23,0") is True
    writer.wait_idle()

    row = store.recent_events()[0]
    assert row["message_type"] == "PERIODIC"
    assert row["machine_id"] == 1
    alarm.assert_not_called()


def test_warning_message_is_recorded_without_alarm(router, writer, store, monkeypatch):
    """경고 데이터가 저장되고 긴급 알림은 생략되는지 검증한다."""
    alarm = Mock()
    monkeypatch.setattr("network.router.send_to_kakao_sos", alarm)

    router.parse_and_route("WARNING,2,4.5,1")
    writer.wait_idle()

    assert store.recent_events()[0]["message_type"] == "WARNING"
    alarm.assert_not_called()


def test_critical_message_is_recorded_and_alarms(router, writer, store, monkeypatch):
    """위험 데이터가 저장되고 긴급 알림도 전송되는지 검증한다."""
    alarm = Mock()
    monkeypatch.setattr("network.router.send_to_kakao_sos", alarm)

    router.parse_and_route("CRITICAL,3,7.0,2")
    writer.wait_idle()

    row = store.recent_events()[0]
    assert row["message_type"] == "CRITICAL"
    assert row["zone_d_consecutive_count"] == 1
    alarm.assert_called_once_with(3, 7.0, 2)


def test_critical_alarm_fires_even_when_queue_is_full(store, monkeypatch):
    """저장 큐가 가득 차도 긴급 알림은 즉시 발송되는지 검증한다."""
    alarm = Mock()
    monkeypatch.setattr("network.router.send_to_kakao_sos", alarm)
    writer = EventWriter(store, max_queue_size=1)  # 스레드 미시작 → 큐가 곧 가득 참
    router = FactoryRouter(writer, clock=lambda: FIXED_NOW)

    router.parse_and_route("CRITICAL,1,7.0,2")  # 큐 1칸 채움
    assert router.parse_and_route("CRITICAL,1,7.1,2") is False  # 큐 오버플로

    assert alarm.call_count == 2


def test_zone_d_streak_counts_consecutive_criticals_and_resets(router, writer, store):
    """연속 CRITICAL은 누적되고 다른 유형이 오면 0으로 리셋되는지 검증한다."""
    router.parse_and_route("CRITICAL,1,7.0,2")
    router.parse_and_route("CRITICAL,1,7.1,2")
    router.parse_and_route("WARNING,1,4.5,1")
    router.parse_and_route("CRITICAL,1,7.2,2")
    writer.wait_idle()

    # recent_events는 최신순이므로 마지막 이벤트부터
    counts = [row["zone_d_consecutive_count"] for row in store.recent_events()]
    assert counts == [1, 0, 2, 1]


def test_csv_uses_received_time_json_keeps_its_timestamp(router, writer, store):
    """CSV는 수신 시각을, JSON은 자체 timestamp를 observed_at으로 쓰는지 검증한다."""
    router.parse_and_route("PERIODIC,1,1.0,0")
    payload = {
        "version": 1,
        "type": "PERIODIC",
        "timestamp": "2026-01-01T00:00:00Z",
        "machine_id": 2,
        "standard": "ISO 20816-3:2022",
        "unit": "mm/s RMS",
        "max_velocity_rms": 1.0,
        "zone": "A",
        "error_code": 0,
        "readings": [],
    }
    router.parse_and_route(json.dumps(payload))
    writer.wait_idle()

    by_machine = {row["machine_id"]: row for row in store.recent_events()}
    assert by_machine[1]["observed_at"] == "2026-09-08T12:30:00Z"
    assert by_machine[1]["received_at"] == "2026-09-08T12:30:00Z"
    assert by_machine[2]["observed_at"] == "2026-01-01T00:00:00Z"
    assert by_machine[2]["received_at"] == "2026-09-08T12:30:00Z"


@pytest.mark.parametrize(
    "message",
    ["", "WARNING,1,500", "UNKNOWN,1,500,9", "CRITICAL,1,500,1"],
)
def test_invalid_or_unknown_messages_are_ignored(
    router, writer, store, monkeypatch, message
):
    """불완전하거나 알 수 없는 메시지가 기록·알림 없이 무시되는지 검증한다."""
    alarm = Mock()
    monkeypatch.setattr("network.router.send_to_kakao_sos", alarm)

    assert router.parse_and_route(message) is False
    writer.wait_idle()

    assert store.recent_events() == []
    alarm.assert_not_called()
