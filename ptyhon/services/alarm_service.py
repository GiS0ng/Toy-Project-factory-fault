class AlarmService:
    @staticmethod
    def send_to_kakao_sos(machine_id, vibration_val, error_code):
        """[카카오톡 알림 모듈] 미구현 시뮬레이션 코드"""
        print("=" * 60)
        print("💬 [카카오톡 긴급 알림 전송 메시지 미리보기]")
        print(f"🚨 [설비 비상 중단 통보]\n▶ 설비 번호: {machine_id}호기\n▶ 최종 진동값: {vibration_val}\n▶ 에러코드: {error_code}")
        print("=" * 60)