from services.alarm_service import send_to_kakao_sos


def test_send_to_kakao_sos_prints_alarm_details(capsys):
    """긴급 알림 출력에 설비 번호와 진동값, 오류 코드가 포함되는지 검증한다."""
    send_to_kakao_sos("5", "750", "2")

    output = capsys.readouterr().out
    assert "5호기" in output
    assert "750" in output
    assert "2" in output
