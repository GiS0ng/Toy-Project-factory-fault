from config.notion_client import NotionClient
from services.alarm_service import AlarmService

class FactoryRouter:
    def __init__(self):
        self.notion_client = NotionClient()

    def parse_and_route(self, raw_message):
        try:
            tokens = raw_message.strip().split(',')
            if len(tokens) < 4: return

            data_type = tokens[0]      # PERIODIC, WARNING, CRITICAL
            machine_id = tokens[1]
            vibration_val = tokens[2]
            error_code = tokens[3]

            if data_type == "PERIODIC":
                print(f"📊 [정기] {machine_id}호기 정상 가동 중 ({vibration_val} μm/s)")
                # 필요 시 DB에만 저장하거나 생략 가능

            elif data_type == "WARNING":
                print(f"🟡 [경고] {machine_id}호기 보수 필요 단계 ({vibration_val} μm/s)")
                # 노션 데일리 보고서에 기록
                self.notion_client.send_to_notion_daily(machine_id, vibration_val, error_code)

            elif data_type == "CRITICAL":
                print(f"🚨 [위험] {machine_id}호기 즉시 중단 필요! ({vibration_val} μm/s)")
                # 카카오톡 긴급 SOS 및 노션 기록
                self.notion_client.send_to_notion_daily(machine_id, vibration_val, error_code)
                AlarmService.send_to_kakao_sos(machine_id, vibration_val, error_code)

        except Exception as e:
            print(f"❌ 라우팅 에러: {e}")