import requests

from config import settings


class NotionClient:
    def __init__(self):
        """Notion API 주소와 인증 헤더를 초기화한다."""
        self.api_url = "https://api.notion.com/v1/pages"
        self.headers = {
            "Authorization": f"Bearer {settings.NOTION_TOKEN}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

    def send_to_notion_daily(self, machine_id, vibration_val, error_code):
        """C++에서 받은 실시간 데이터를 Notion 데이터베이스에 추가한다."""
        payload = {
            "parent": {"database_id": settings.DATABASE_ID},
            "properties": {
                "설비명": {
                    "title": [
                        {"text": {"content": f"공장 설비 {machine_id}호기"}}
                    ]
                },
                "진동값": {
                    # Notion 숫자 속성의 타입에 맞춰 정수로 변환한다.
                    "number": int(vibration_val)
                },
                "에러코드": {"number": int(error_code)},
            },
        }

        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=10,
            )
            if response.status_code == 200:
                print(
                    f"  ➔ 🟢 [Notion 성공] {machine_id}호기 데이터가 "
                    f"Notion에 등록되었습니다. (값: {vibration_val})"
                )
                return True

            print(
                f"  ➔ 🔴 [Notion API 오류] 상태코드: {response.status_code}, "
                f"내용: {response.text}"
            )
            return False
        except requests.RequestException as error:
            print(f"  ➔ ❌ Notion 전송 중 네트워크 오류 발생: {error}")
            return False
