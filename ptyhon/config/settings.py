import os
from dotenv import load_dotenv

# 루트 폴더에 있는 .env 파일 위치를 고려하여 로드합니다.
# python_bridge 안에서 실행하든 루트에서 실행하든 안전하게 찾도록 설정을 잡아둡니다.
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../.env'))

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")
HOST = '127.0.0.1'
PORT = 9999

# 보안 및 정상 로드 검증
if not NOTION_TOKEN or not DATABASE_ID:
    print("❌ [보안 에러] .env 파일에서 NOTION_TOKEN 또는 DATABASE_ID를 찾을 수 없습니다!")
    exit(1)