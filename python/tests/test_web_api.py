from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from config.settings import Settings
from network.message import TelemetryMessage
from persistence.event_store import EventStore
from web.api import compute_lifecycle
from web.app import build_app


def _iso(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.fixture
def client(tmp_path):
    """임시 SQLite에 표본 데이터를 넣고 브리지 없이 조회 API만 띄운다."""
    db_path = str(tmp_path / "factory.db")
    store = EventStore.open(db_path)
    now = datetime.now(timezone.utc)

    # 2호기: 오래된 CRITICAL 연속 (stopped: 한도 도달 + last_seen 초과). 먼저 발생.
    old = now - timedelta(hours=2)
    store.record_event(
        TelemetryMessage.parse("CRITICAL,2,9.0,2"),
        observed_at=_iso(old),
        received_at=_iso(old),
        zone_d_consecutive_count=4,
    )
    # 1호기: 방금 수신한 PERIODIC 여러 건 (running).
    for index in range(4):
        moment = now - timedelta(seconds=5 - index)
        store.record_event(
            TelemetryMessage.parse(f"PERIODIC,1,{1.0 + index / 10},0"),
            observed_at=_iso(moment),
            received_at=_iso(moment),
            zone_d_consecutive_count=0,
        )
    store.close()

    settings = Settings(factory_db_path=db_path)
    with TestClient(build_app(settings, run_bridge=False)) as test_client:
        yield test_client


def test_index_serves_html(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "진동 모니터링" in response.text


def test_machines_returns_state_with_lifecycle(client):
    machines = client.get("/api/machines").json()
    by_id = {m["machine_id"]: m for m in machines}

    assert by_id[1]["lifecycle"] == "running"
    assert by_id[1]["message_type"] == "PERIODIC"
    assert by_id[2]["lifecycle"] == "stopped"
    assert by_id[2]["zone_d_consecutive_count"] == 4


def test_events_filters_and_limits(client):
    assert len(client.get("/api/events").json()) == 5

    only_one = client.get("/api/events?machine_id=1").json()
    assert {row["machine_id"] for row in only_one} == {1}

    criticals = client.get("/api/events?type=CRITICAL").json()
    assert [row["message_type"] for row in criticals] == ["CRITICAL"]

    assert len(client.get("/api/events?limit=2").json()) == 2

    # 최신순
    newest = client.get("/api/events?limit=1").json()[0]
    assert newest["machine_id"] == 1


def test_events_rejects_bad_type(client):
    assert client.get("/api/events?type=BOGUS").status_code == 422


def test_timeseries_returns_ascending_points(client):
    body = client.get("/api/timeseries?machine_id=1&hours=1").json()
    assert body["machine_id"] == 1
    times = [point["observed_at"] for point in body["points"]]
    assert times == sorted(times)
    assert len(body["points"]) == 4


def test_timeseries_requires_machine_id(client):
    assert client.get("/api/timeseries").status_code == 422


def test_compute_lifecycle_rules():
    now = datetime(2026, 9, 8, 12, 0, 0, tzinfo=timezone.utc)
    fresh = "2026-09-08T11:59:50Z"
    stale = "2026-09-08T11:00:00Z"

    assert (
        compute_lifecycle(fresh, 0, now=now, offline_after_seconds=15, zone_d_limit=4)
        == "running"
    )
    assert (
        compute_lifecycle(stale, 4, now=now, offline_after_seconds=15, zone_d_limit=4)
        == "stopped"
    )
    assert (
        compute_lifecycle(stale, 1, now=now, offline_after_seconds=15, zone_d_limit=4)
        == "offline"
    )
    assert (
        compute_lifecycle(None, 0, now=now, offline_after_seconds=15, zone_d_limit=4)
        == "offline"
    )
