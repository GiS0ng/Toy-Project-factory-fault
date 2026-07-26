from datetime import date
from unittest.mock import Mock

from services.report_service import ReportService


def test_daily_report_uses_korean_standard_time_period():
    """데일리 보고서가 KST 하루 범위로 이벤트를 조회하는지 검증한다."""
    notion_client = Mock()
    notion_client.query_events.return_value = [
        {"properties": {"진동값": {"number": 500}, "에러코드": {"number": 1}}},
        {"properties": {"진동값": {"number": 700}, "에러코드": {"number": 2}}},
    ]
    notion_client.create_report_page.return_value = True
    service = ReportService(notion_client)

    result = service.create_daily_report(date(2026, 7, 26))

    assert result is True
    notion_client.query_events.assert_called_once_with(
        "2026-07-25T15:00:00+00:00", "2026-07-26T15:00:00+00:00"
    )
    title, blocks = notion_client.create_report_page.call_args.args
    assert title == "[데일리] 2026-07-26 설비 진동 보고서"
    assert "경고: 1건" in str(blocks)
    assert "위험: 1건" in str(blocks)
    assert "최대 진동값: 700 μm/s" in str(blocks)


def test_weekly_report_starts_on_monday():
    """위클리 보고서가 기준일이 속한 월요일부터 일요일까지 집계하는지 검증한다."""
    notion_client = Mock()
    notion_client.query_events.return_value = []
    notion_client.create_report_page.return_value = True
    service = ReportService(notion_client)

    result = service.create_weekly_report(date(2026, 7, 26))

    assert result is True
    notion_client.query_events.assert_called_once_with(
        "2026-07-19T15:00:00+00:00", "2026-07-26T15:00:00+00:00"
    )
    title, blocks = notion_client.create_report_page.call_args.args
    assert title == "[위클리] 2026-07-20~2026-07-26 설비 진동 보고서"
    assert "이벤트 수: 0건" in str(blocks)
