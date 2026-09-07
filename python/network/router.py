from typing import Protocol

from network.message import MessageType, MessageValidationError, TelemetryMessage
from services.alarm_service import AlarmService


class ReportClient(Protocol):
    def send_to_notion_daily(
        self, machine_id: int, vibration_val: float, error_code: int
    ) -> bool: ...


class FactoryRouter:
    def __init__(
        self,
        notion_client: ReportClient | None = None,
        alarm_service: type[AlarmService] = AlarmService,
    ):
        """외부 전송 기능을 주입받아 데이터 라우터를 구성한다."""
        self.notion_client = notion_client
        self.alarm_service = alarm_service

    def parse_and_route(self, raw_message: str) -> bool:
        """수신 메시지를 검증하고 유형에 맞는 작업을 실행한다."""
        try:
            message = TelemetryMessage.parse(raw_message)
        except MessageValidationError as error:
            print(f"⚠️ 유효하지 않은 메시지를 무시합니다: {error}")
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
            self._send_report(message)
            return True

        print(
            f"🚨 [위험] {message.machine_id}호기 Zone D "
            f"({message.vibration_value} mm/s RMS)"
        )
        self._send_report(message)
        self.alarm_service.send_to_kakao_sos(
            message.machine_id,
            message.vibration_value,
            message.error_code,
        )
        return True

    def _send_report(self, message: TelemetryMessage) -> None:
        if self.notion_client is None:
            print("  ➔ ℹ️ Notion 설정이 없어 외부 보고를 생략합니다.")
            return
        self.notion_client.send_to_notion_daily(
            message.machine_id,
            message.vibration_value,
            message.error_code,
        )
