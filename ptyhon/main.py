import argparse
import os
import sys
from datetime import date

# 실행 위치와 관계없이 내부 모듈을 가져올 수 있도록 경로를 추가한다.
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from network.socket_server import SmartFactoryBridge
from services.report_service import ReportService


def parse_arguments():
    """브리지 서버 또는 보고서 생성 실행 옵션을 읽는다."""
    parser = argparse.ArgumentParser(description="스마트팩토리 브리지 및 보고서 도구")
    report_group = parser.add_mutually_exclusive_group()
    report_group.add_argument("--daily-report", action="store_true")
    report_group.add_argument("--weekly-report", action="store_true")
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        help="보고서 기준일 (YYYY-MM-DD, 생략 시 오늘)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_arguments()
    report_date = arguments.date or date.today()

    if arguments.daily_report:
        raise SystemExit(0 if ReportService().create_daily_report(report_date) else 1)

    if arguments.weekly_report:
        raise SystemExit(0 if ReportService().create_weekly_report(report_date) else 1)

    try:
        # 전체 브리지 서버를 생성하고 실행한다.
        bridge_server = SmartFactoryBridge()
        bridge_server.start()
    except KeyboardInterrupt:
        print("\n👋 파이썬 브릿지 서비스를 안전하게 종료합니다.")
