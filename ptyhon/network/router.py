from config.notion_client import NotionClient 
from services.alarm_service import AlarmService

class FactoryRouter:
    def __init__(self):
        # 라우터 내부 부품으로 노션 클라이언트를 생성하여 소유합니다.
        self.notion_client = NotionClient()

    def parse_and_route(self, raw_message):
        """C++이 보낸 문자열 패킷을 쪼개고 분석해서 제 길로 찾아보내는 라우터 메서드"""
        try:
            tokens = raw_message.strip().split(',')
            if len(tokens) < 4:
                print(f"⚠️ 규격에 맞지 않는 데이터가 들어왔습니다: {raw_message}")
                return

            data_type = tokens[0]      # PERIODIC 또는 CRITICAL
            machine_id = tokens[1]     # 기계 ID
            vibration_val = tokens[2]  # 최종 진동값
            error_code = tokens[3]     # 에러 코드

            if data_type == "PERIODIC":
                print(f"\n📊 [정기 수신] {machine_id}호기 가동 데이터 취합 중...")
                self.notion_client.send_to_notion_daily(machine_id, vibration_val, error_code)
            elif data_type == "CRITICAL":
                print(f"\n🚨 [긴급 수신] {machine_id}호기 위험 신호 포착!!!")
                AlarmService.send_to_kakao_sos(machine_id, vibration_val, error_code)

        except Exception as e:
            print(f"❌ 데이터 라우팅 중 예외 에러 발생: {e}")