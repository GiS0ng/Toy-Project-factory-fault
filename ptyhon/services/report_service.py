from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from config.notion_client import NotionClient


class ReportService:
    """Notion 이벤트를 집계해 정기 보고서를 생성한다."""

    TIMEZONE = ZoneInfo("Asia/Seoul")

    def __init__(self, notion_client=None):
        """이벤트 조회와 보고서 생성을 위한 Notion 클라이언트를 설정한다."""
        self.notion_client = notion_client or NotionClient()

    def create_daily_report(self, report_date):
        """지정한 날짜의 데일리 보고서를 생성한다."""
        title = f"[데일리] {report_date.isoformat()} 설비 진동 보고서"
        return self._create_report(title, report_date, report_date + timedelta(days=1))

    def create_weekly_report(self, report_date):
        """지정한 날짜가 속한 월요일~일요일 주간 보고서를 생성한다."""
        week_start = report_date - timedelta(days=report_date.weekday())
        week_end = week_start + timedelta(days=7)
        title = (
            f"[위클리] {week_start.isoformat()}~"
            f"{(week_end - timedelta(days=1)).isoformat()} 설비 진동 보고서"
        )
        return self._create_report(title, week_start, week_end)

    def _create_report(self, title, start_date, end_date):
        """기간 내 이벤트를 집계해 Notion 보고서 페이지를 생성한다."""
        start_time, end_time = self._to_utc_period(start_date, end_date)
        events = self.notion_client.query_events(start_time, end_time)
        if events is None:
            return False

        summary = self._summarize(events)
        children = self._build_report_blocks(start_date, end_date, summary)
        return self.notion_client.create_report_page(title, children)

    def _to_utc_period(self, start_date, end_date):
        """한국 시간 기준 기간을 Notion 조회용 UTC 시각으로 변환한다."""
        start_time = datetime.combine(start_date, time.min, self.TIMEZONE)
        end_time = datetime.combine(end_date, time.min, self.TIMEZONE)
        return (
            start_time.astimezone(timezone.utc).isoformat(),
            end_time.astimezone(timezone.utc).isoformat(),
        )

    @staticmethod
    def _summarize(events):
        """이벤트 목록에서 경고·위험 건수와 최대 진동값을 계산한다."""
        warning_count = 0
        critical_count = 0
        vibration_values = []

        for event in events:
            properties = event.get("properties", {})
            vibration = properties.get("진동값", {}).get("number")
            error_code = properties.get("에러코드", {}).get("number")

            if isinstance(vibration, (int, float)):
                vibration_values.append(vibration)
            if error_code == 1:
                warning_count += 1
            elif error_code == 2:
                critical_count += 1

        return {
            "total_count": len(events),
            "warning_count": warning_count,
            "critical_count": critical_count,
            "max_vibration": max(vibration_values, default=None),
        }

    @staticmethod
    def _build_report_blocks(start_date, end_date, summary):
        """Notion 페이지 본문에 넣을 보고서 블록을 구성한다."""
        period_end = end_date - timedelta(days=1)
        max_vibration = summary["max_vibration"]
        max_vibration_text = (
            f"{max_vibration} μm/s" if max_vibration is not None else "데이터 없음"
        )
        lines = [
            f"기간: {start_date.isoformat()} ~ {period_end.isoformat()} (KST)",
            f"이벤트 수: {summary['total_count']}건",
            f"경고: {summary['warning_count']}건",
            f"위험: {summary['critical_count']}건",
            f"최대 진동값: {max_vibration_text}",
        ]

        blocks = [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "집계 결과"}}]
                },
            }
        ]
        for line in lines:
            blocks.append(
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": line}}]
                    },
                }
            )
        return blocks
