def send_to_kakao_sos(machine_id, vibration_val, error_code):
    """KakaoTalk 알림 전송을 대신해 메시지 미리보기를 출력한다."""
    print("=" * 60)
    print("💬 [KakaoTalk 긴급 알림 전송 메시지 미리보기]")
    print(
        f"🚨 [설비 비상 중단 통보]\n"
        f"▶ 설비 번호: {machine_id}호기\n"
        f"▶ 최종 진동값: {vibration_val}\n"
        f"▶ 에러코드: {error_code}"
    )
    print("=" * 60)
