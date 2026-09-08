from collections.abc import Callable
from datetime import datetime, timezone

from network.message import MessageType, MessageValidationError, TelemetryMessage
from persistence.event_writer import EventWriter, IngestedEvent
from services.alarm_service import send_to_kakao_sos


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(moment: datetime) -> str:
    """UTC ISO8601. C++가 보내는 timestamp와 같은 'Z' 접미사 형식으로 맞춘다."""
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class FactoryRouter:
    def __init__(
        self,
        writer: EventWriter,
        *,
        clock: Callable[[], datetime] = _utc_now,
    ):
        """검증한 이벤트를 저장 큐로 넘기는 수신측 라우터를 구성한다.

        이 라우터는 DB를 직접 건드리지 않고 상태도 들지 않는다. 파싱·검증·로그·
        긴급 알림만 수신 스레드에서 처리하고, 저장과 Zone D 연속 카운트 계산은
        EventWriter(단일 스레드)가 전담한다.
        """
        self._writer = writer
        self._clock = clock

    def parse_and_route(self, raw_message: str) -> bool:
        """수신 메시지를 검증하고 로그·긴급 알림 후 저장 큐에 넣는다.

        반환값은 "처리 대상으로 받아들였는가"이다. 검증 실패나 큐 오버플로면 False.
        큐에 들어간 뒤의 저장 성공 여부는 EventWriter가 책임진다.
        """
        try:
            message = TelemetryMessage.parse(raw_message)
        except MessageValidationError as error:
            print(f"⚠️ 유효하지 않은 메시지를 무시합니다: {error}")
            return False

        received_at = _to_iso(self._clock())

        if message.message_type == MessageType.PERIODIC:
            print(
                f"📊 [정기] {message.machine_id}호기 Zone "
                f"{message.zone or 'A/B'} ({message.vibration_value} mm/s RMS)"
            )
        elif message.message_type == MessageType.WARNING:
            print(
                f"🟡 [경고] {message.machine_id}호기 Zone C "
                f"({message.vibration_value} mm/s RMS)"
            )
        else:
            print(
                f"🚨 [위험] {message.machine_id}호기 Zone D "
                f"({message.vibration_value} mm/s RMS)"
            )
            # 긴급 알림은 큐 상태와 무관하게 즉시 발송한다.
            send_to_kakao_sos(
                message.machine_id,
                message.vibration_value,
                message.error_code,
            )

        return self._writer.submit(IngestedEvent(message, received_at))
