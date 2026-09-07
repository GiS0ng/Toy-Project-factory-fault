from unittest.mock import Mock

import pytest

from network.router import FactoryRouter


@pytest.fixture
def router():
    """외부 전송 기능을 모의 객체로 교체한 라우터를 제공한다."""
    return FactoryRouter(notion_client=Mock())


def test_periodic_message_does_not_send_external_notifications(router, monkeypatch):
    """정기 데이터가 외부 보고서나 긴급 알림을 전송하지 않는지 검증한다."""
    alarm = Mock()
    monkeypatch.setattr("network.router.AlarmService.send_to_kakao_sos", alarm)

    router.parse_and_route("PERIODIC,1,123,0")

    router.notion_client.send_to_notion_daily.assert_not_called()
    alarm.assert_not_called()


def test_warning_message_is_recorded_in_notion(router, monkeypatch):
    """경고 데이터가 Notion에 기록되고 긴급 알림은 생략되는지 검증한다."""
    alarm = Mock()
    monkeypatch.setattr("network.router.AlarmService.send_to_kakao_sos", alarm)

    router.parse_and_route("WARNING,2,450,1")

    router.notion_client.send_to_notion_daily.assert_called_once_with(2, 450.0, 1)
    alarm.assert_not_called()


def test_critical_message_records_and_sends_alarm(router, monkeypatch):
    """위험 데이터가 Notion에 기록되고 긴급 알림도 전송되는지 검증한다."""
    alarm = Mock()
    monkeypatch.setattr("network.router.AlarmService.send_to_kakao_sos", alarm)

    router.parse_and_route("CRITICAL,3,700,2")

    router.notion_client.send_to_notion_daily.assert_called_once_with(3, 700.0, 2)
    alarm.assert_called_once_with(3, 700.0, 2)


@pytest.mark.parametrize(
    "message",
    ["", "WARNING,1,500", "UNKNOWN,1,500,9", "CRITICAL,1,500,1"],
)
def test_invalid_or_unknown_messages_are_ignored(router, monkeypatch, message):
    """불완전하거나 알 수 없는 메시지가 안전하게 무시되는지 검증한다."""
    alarm = Mock()
    monkeypatch.setattr("network.router.AlarmService.send_to_kakao_sos", alarm)

    router.parse_and_route(message)

    router.notion_client.send_to_notion_daily.assert_not_called()
    alarm.assert_not_called()
