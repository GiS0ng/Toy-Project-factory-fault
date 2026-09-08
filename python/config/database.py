import sqlite3
from pathlib import Path

# 시작 시점 스키마 (2테이블). 상세 근거는 docs/plan-realtime-dashboard.md §3.
# telemetry_events: 검증된 이벤트 원장. machine_state: 장비별 최신 상태 스냅샷.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS telemetry_events (
    id                        INTEGER PRIMARY KEY,
    observed_at               TEXT NOT NULL,   -- JSON은 원본 timestamp, CSV는 수신 시각. UTC ISO8601
    received_at               TEXT NOT NULL,   -- 브리지 수신 시각. UTC ISO8601
    machine_id                INTEGER NOT NULL,
    message_type              TEXT NOT NULL,   -- PERIODIC | WARNING | CRITICAL
    zone                      TEXT,            -- A | B | C | D | NULL
    vibration_value           REAL NOT NULL,
    error_code                INTEGER NOT NULL,
    zone_d_consecutive_count  INTEGER          -- 브리지가 재계산한 연속 CRITICAL 수
);
CREATE INDEX IF NOT EXISTS ix_events_machine_time ON telemetry_events(machine_id, observed_at);
CREATE INDEX IF NOT EXISTS ix_events_type_time    ON telemetry_events(message_type, observed_at);

CREATE TABLE IF NOT EXISTS machine_state (
    machine_id                INTEGER PRIMARY KEY,
    updated_at                TEXT NOT NULL,   -- 마지막 이벤트의 수신 시각
    last_event_id             INTEGER,
    zone                      TEXT,
    vibration_value           REAL,
    zone_d_consecutive_count  INTEGER,
    message_type              TEXT,
    lifecycle                 TEXT             -- running | stopped | offline. 5단계에서 읽기 시점에 계산
);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    """WAL과 busy_timeout을 적용하고 스키마를 보장한 쓰기 연결을 돌려준다.

    check_same_thread=False 는 writer 스레드가 소유하지만 조립부(메인 스레드)에서
    만들어 넘기기 때문이다. 실제 쓰기는 EventWriter 한 스레드에서만 일어난다.
    """
    is_memory = str(db_path) == ":memory:"
    if not is_memory:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(
        db_path,
        check_same_thread=False,
        isolation_level=None,  # 자동 커밋. 다중 문장 트랜잭션은 BEGIN/COMMIT으로 명시
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA busy_timeout=5000")
    connection.executescript(_SCHEMA)
    return connection


def connect_readonly(db_path: str | Path) -> sqlite3.Connection:
    """읽기 전용 연결을 돌려준다. 대시보드 조회가 writer와 연결을 공유하지 않게 한다.

    WAL 모드라 writer가 쓰는 동안에도 막히지 않고 읽는다. 스키마는 만들지 않으므로
    쓰기 연결이 먼저 파일을 생성해 두어야 한다(조립 순서로 보장).
    """
    if str(db_path) == ":memory:":
        raise ValueError(":memory: 는 읽기 전용 연결로 공유할 수 없습니다")
    uri = f"file:{Path(db_path)}?mode=ro"
    connection = sqlite3.connect(
        uri, uri=True, check_same_thread=False, isolation_level=None
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout=5000")
    return connection
