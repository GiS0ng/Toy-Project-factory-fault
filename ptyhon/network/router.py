from config.notion_client import NotionClient
from services.alarm_service import AlarmService


class FactoryRouter:
    EVENT_ERROR_CODES = {
        "PERIODIC": 0,
        "WARNING": 1,
        "CRITICAL": 2,
    }

    def __init__(self):
        """외부 보고서 전송에 사용할 Notion 클라이언트를 생성한다."""
        self.notion_client = NotionClient()

    def parse_and_route(self, raw_message):
        """수신 메시지를 해석하고 데이터 유형에 맞는 작업을 실행한다."""
        try:
            tokens = [token.strip() for token in raw_message.strip().split(",")]
            if len(tokens) != 4:
                print("⚠️ 잘못된 패킷 형식입니다.")
                return

            data_type = tokens[0]  # PERIODIC, WARNING, CRITICAL
            machine_id = tokens[1]
            vibration_val = tokens[2]
            error_code = tokens[3]

            if data_type not in self.EVENT_ERROR_CODES:
                print(f"⚠️ 알 수 없는 패킷 유형입니다: {data_type}")
                return

            machine_number = int(machine_id)
            vibration_number = int(vibration_val)
            received_error_code = int(error_code)
            expected_error_code = self.EVENT_ERROR_CODES[data_type]

            if machine_number <= 0 or vibration_number < 0:
                print("⚠️ 설비 번호 또는 진동값 범위가 올바르지 않습니다.")
                return

            if received_error_code != expected_error_code:
                print("⚠️ 패킷 유형과 오류 코드가 일치하지 않습니다.")
                return

            if data_type == "PERIODIC":
                print(
                    f"📊 [정기] {machine_id}호기 정상 가동 중 "
                    f"({vibration_val} μm/s)"
                )
                # 필요하면 DB에 저장하거나 처리를 생략한다.

            elif data_type == "WARNING":
                print(
                    f"🟡 [경고] {machine_id}호기 보수 필요 단계 "
                    f"({vibration_val} μm/s)"
                )
                # Notion 데일리 보고서에 기록한다.
                self.notion_client.send_to_notion_daily(
                    machine_id, vibration_val, error_code
                )

            elif data_type == "CRITICAL":
                print(
                    f"🚨 [위험] {machine_id}호기 즉시 중단 필요! "
                    f"({vibration_val} μm/s)"
                )
                # KakaoTalk 긴급 알림을 전송하고 Notion에 기록한다.
                self.notion_client.send_to_notion_daily(
                    machine_id, vibration_val, error_code
                )
                AlarmService.send_to_kakao_sos(
                    machine_id, vibration_val, error_code
                )

        except (AttributeError, IndexError, TypeError, ValueError) as error:
            print(f"❌ 라우팅 오류: {error}")
