import os

from dotenv import load_dotenv

# 실행 위치와 관계없이 프로젝트 루트의 .env 파일을 불러온다.
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")
REPORT_PARENT_PAGE_ID = os.getenv("NOTION_REPORT_PARENT_PAGE_ID")
HOST = "127.0.0.1"
PORT = 9999

# 필수 환경 변수가 정상적으로 로드되었는지 확인한다.
if not NOTION_TOKEN or not DATABASE_ID:
    print(
        "❌ [보안 오류] .env 파일에서 NOTION_TOKEN 또는 "
        "DATABASE_ID를 찾을 수 없습니다!"
    )
    raise SystemExit(1)
