from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Request

from network.message import MessageType
from persistence.event_store import EventStore

router = APIRouter(prefix="/api")


def get_reader(request: Request) -> Iterator[EventStore]:
    """요청마다 읽기 전용 연결을 새로 연다. writer 스레드와 연결을 공유하지 않는다."""
    store = EventStore.open_readonly(request.app.state.settings.factory_db_path)
    try:
        yield store
    finally:
        store.close()


def _now_iso(now: datetime) -> str:
    return now.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None


def compute_lifecycle(
    updated_at: str | None,
    zone_d_consecutive_count: int | None,
    *,
    now: datetime,
    offline_after_seconds: float,
    zone_d_limit: int,
) -> str:
    """§4 결정: running / stopped(Zone D 한도 도달) / offline(last_seen 초과)."""
    moment = _parse_iso(updated_at)
    if moment is None:
        return "offline"
    age = (now - moment).total_seconds()
    if age <= offline_after_seconds:
        return "running"
    if (zone_d_consecutive_count or 0) >= zone_d_limit:
        return "stopped"
    return "offline"


@router.get("/machines")
def list_machines(
    request: Request, reader: EventStore = Depends(get_reader)
) -> list[dict]:
    """장비별 최신 상태 + 계산된 lifecycle."""
    settings = request.app.state.settings
    now = datetime.now(timezone.utc)
    offline_after = settings.sample_interval_ms * 5 / 1000
    machines = []
    for row in reader.machine_states():
        item = dict(row)
        item["lifecycle"] = compute_lifecycle(
            item.get("updated_at"),
            item.get("zone_d_consecutive_count"),
            now=now,
            offline_after_seconds=offline_after,
            zone_d_limit=settings.consecutive_zone_d_limit,
        )
        machines.append(item)
    return machines


@router.get("/events")
def list_events(
    machine_id: int | None = Query(default=None, ge=1),
    message_type: MessageType | None = Query(default=None, alias="type"),
    limit: int = Query(default=100, ge=1, le=1000),
    reader: EventStore = Depends(get_reader),
) -> list[dict]:
    """필터를 건 이벤트 이력, 최신순."""
    rows = reader.events(
        machine_id=machine_id,
        message_type=message_type.value if message_type else None,
        limit=limit,
    )
    return [dict(row) for row in rows]


@router.get("/timeseries")
def get_timeseries(
    machine_id: int = Query(ge=1),
    hours: float = Query(default=1.0, gt=0, le=168),
    reader: EventStore = Depends(get_reader),
) -> dict:
    """한 장비의 진동값 시계열, 오래된 순."""
    now = datetime.now(timezone.utc)
    since_iso = _now_iso(now - timedelta(hours=hours))
    rows = reader.timeseries(machine_id=machine_id, since_iso=since_iso)
    return {
        "machine_id": machine_id,
        "since": since_iso,
        "points": [dict(row) for row in rows],
    }
