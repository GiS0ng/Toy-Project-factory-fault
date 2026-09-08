import sqlite3
import threading
from pathlib import Path

from config.database import connect, connect_readonly
from network.message import TelemetryMessage


class EventStore:
    """검증된 텔레메트리 이벤트를 SQLite에 기록하고 조회한다.

    한 이벤트를 넣을 때 telemetry_events INSERT와 machine_state UPSERT를 한
    트랜잭션으로 처리한다. 쓰기는 락으로 직렬화한다 — 3단계에서 라우터가 여러
    수신 스레드에서 호출하기 때문이며, 4단계에서 전용 writer 스레드로 옮기면
    이 락은 사라진다.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._write_lock = threading.Lock()

    @classmethod
    def open(cls, db_path: str | Path) -> "EventStore":
        """경로(또는 ':memory:')로 쓰기 연결을 만들어 저장소를 연다."""
        return cls(connect(db_path))

    @classmethod
    def open_readonly(cls, db_path: str | Path) -> "EventStore":
        """읽기 전용 연결로 저장소를 연다. 조회 메서드만 쓴다(대시보드용)."""
        return cls(connect_readonly(db_path))

    def close(self) -> None:
        self._connection.close()

    def record_event(
        self,
        message: TelemetryMessage,
        *,
        observed_at: str,
        received_at: str,
        zone_d_consecutive_count: int | None,
    ) -> int:
        """이벤트를 기록하고 machine_state를 갱신한다. 새 이벤트의 id를 돌려준다."""
        params = (
            observed_at,
            received_at,
            message.machine_id,
            message.message_type.value,
            message.zone,
            message.vibration_value,
            message.error_code,
            zone_d_consecutive_count,
        )
        with self._write_lock:
            cursor = self._connection.cursor()
            cursor.execute("BEGIN")
            try:
                cursor.execute(
                    """
                    INSERT INTO telemetry_events (
                        observed_at, received_at, machine_id, message_type,
                        zone, vibration_value, error_code, zone_d_consecutive_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    params,
                )
                event_id = int(cursor.lastrowid or 0)
                cursor.execute(
                    """
                    INSERT INTO machine_state (
                        machine_id, updated_at, last_event_id, zone,
                        vibration_value, zone_d_consecutive_count, message_type, lifecycle
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
                    ON CONFLICT(machine_id) DO UPDATE SET
                        updated_at = excluded.updated_at,
                        last_event_id = excluded.last_event_id,
                        zone = excluded.zone,
                        vibration_value = excluded.vibration_value,
                        zone_d_consecutive_count = excluded.zone_d_consecutive_count,
                        message_type = excluded.message_type
                    """,
                    (
                        message.machine_id,
                        received_at,
                        event_id,
                        message.zone,
                        message.vibration_value,
                        zone_d_consecutive_count,
                        message.message_type.value,
                    ),
                )
                cursor.execute("COMMIT")
            except sqlite3.Error:
                cursor.execute("ROLLBACK")
                raise
            return event_id

    def recent_events(self, *, limit: int = 50) -> list[sqlite3.Row]:
        """최근 이벤트를 id 내림차순으로 돌려준다."""
        return list(
            self._connection.execute(
                "SELECT * FROM telemetry_events ORDER BY id DESC LIMIT ?",
                (limit,),
            )
        )

    def machine_states(self) -> list[sqlite3.Row]:
        """장비별 최신 상태를 machine_id 오름차순으로 돌려준다."""
        return list(
            self._connection.execute("SELECT * FROM machine_state ORDER BY machine_id")
        )

    def events(
        self,
        *,
        machine_id: int | None = None,
        message_type: str | None = None,
        limit: int = 100,
    ) -> list[sqlite3.Row]:
        """필터를 걸어 이벤트를 최신순으로 돌려준다."""
        clauses: list[str] = []
        params: list[object] = []
        if machine_id is not None:
            clauses.append("machine_id = ?")
            params.append(machine_id)
        if message_type is not None:
            clauses.append("message_type = ?")
            params.append(message_type)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(max(1, min(limit, 1000)))
        return list(
            self._connection.execute(
                f"SELECT * FROM telemetry_events {where} ORDER BY id DESC LIMIT ?",
                params,
            )
        )

    def timeseries(
        self, *, machine_id: int, since_iso: str, limit: int = 2000
    ) -> list[sqlite3.Row]:
        """한 장비의 since_iso 이후 진동값 시계열을 오래된 순으로 돌려준다.

        구간이 길어 행이 limit을 넘으면 **최근** limit개를 취한다(오래된 쪽을 버림).
        긴 구간의 다운샘플링은 이후 단계 과제.
        """
        rows = self._connection.execute(
            """
            SELECT observed_at, vibration_value, message_type, zone
            FROM telemetry_events
            WHERE machine_id = ? AND observed_at >= ?
            ORDER BY observed_at DESC
            LIMIT ?
            """,
            (machine_id, since_iso, max(1, min(limit, 10000))),
        ).fetchall()
        rows.reverse()
        return rows
