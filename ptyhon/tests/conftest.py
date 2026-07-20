import os
import sys
from pathlib import Path


PYTHON_APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PYTHON_APP_ROOT))

# 설정값이 없으면 config.settings가 프로세스를 종료하므로 테스트용 값을 사용합니다.
# 테스트에서는 모든 Notion 외부 요청을 모의 객체로 대체합니다.
os.environ.setdefault("NOTION_TOKEN", "test-token")
os.environ.setdefault("DATABASE_ID", "test-database")
