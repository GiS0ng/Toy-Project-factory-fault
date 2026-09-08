import sqlite3
from collections.abc import Callable
from datetime import datetime, timezone

from network.message import MessageType, MessageValidationError, TelemetryMessage
from persistence.event_store import EventStore
from services.alarm_service import send_to_kakao_sos


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(moment: datetime) -> str:
    """UTC ISO8601. C++가 보내는 timestamp와 같은 'Z' 접미사 형식으로 맞춘다."""
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class FactoryRouter:
    def __init__(
        self,
        event_store: EventStore,
        *,
        clock: Callable[[], datetime] = _utc_now,
    ):
        """이벤트 저장소를 주입받아 데이터 라우터를 구성한다."""
        self._event_store = event_store
        self._clock = clock
        # 장비별 연속 CRITICAL 수. C++ MachineMonitor의 consecutiveZoneDCount_와 같은 역할.
        # CSV v1에는 zone이 없으므로 zone 문자열이 아니라 message_type으로 판별한다.
        self._zone_d_streak: dict[int, int] = {}

    def parse_and_route(self, raw_message: str) -> bool:
        """수신 메시지를 검증·기록하고 유형에 맞는 작업을 실행한다."""
        try:
            message = TelemetryMessage.parse(raw_message)
        except MessageValidationError as error:
            print(f"⚠️ 유효하지 않은 메시지를 무시합니다: {error}")
            return False

        received_at = _to_iso(self._clock())
        # CSV v1은 timestamp가 없으므로 수신 시각을 이벤트 시각으로 쓴다.
        observed_at = message.timestamp or received_at
        streak = self._advance_zone_d_streak(message)

        try:
            self._event_store.record_event(
                message,
                observed_at=observed_at,
                received_at=received_at,
                zone_d_consecutive_count=streak,
            )
        except sqlite3.Error as error:
            print(f"  ➔ 🔴 [저장 실패] 이벤트를 기록하지 못했습니다: {error}")
            return False

        if message.message_type == MessageType.PERIODIC:
            print(
                f"📊 [정기] {message.machine_id}호기 Zone "
                f"{message.zone or 'A/B'} ({message.vibration_value} mm/s RMS)"
            )
            return True

        if message.message_type == MessageType.WARNING:
            print(
                f"🟡 [경고] {message.machine_id}호기 Zone C "
                f"({message.vibration_value} mm/s RMS)"
            )
            return True

        print(
            f"🚨 [위험] {message.machine_id}호기 Zone D "
            f"({message.vibration_value} mm/s RMS) — 연속 {streak}회"
        )
        send_to_kakao_sos(
            message.machine_id,
            message.vibration_value,
            message.error_code,
        )
        return True

    def _advance_zone_d_streak(self, message: TelemetryMessage) -> int:
        """C++ MachineMonitor와 동일: CRITICAL이면 +1, 아니면 0으로 리셋한다."""
        if message.message_type == MessageType.CRITICAL:
            self._zone_d_streak[message.machine_id] = (
                self._zone_d_streak.get(message.machine_id, 0) + 1
            )
        else:
            self._zone_d_streak[message.machine_id] = 0
        return self._zone_d_streak[message.machine_id]
