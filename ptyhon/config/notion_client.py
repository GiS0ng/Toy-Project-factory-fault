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

    def query_events(self, start_time, end_time):
        """지정한 기간에 생성된 설비 이벤트를 모두 조회한다."""
        api_url = f"https://api.notion.com/v1/databases/{settings.DATABASE_ID}/query"
        payload = {
            "page_size": 100,
            "filter": {
                "and": [
                    {
                        "timestamp": "created_time",
                        "created_time": {"on_or_after": start_time},
                    },
                    {
                        "timestamp": "created_time",
                        "created_time": {"before": end_time},
                    },
                ]
            },
        }
        events = []

        try:
            while True:
                response = requests.post(
                    api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=10,
                )
                if response.status_code != 200:
                    print(
                        "  ➔ 🔴 [Notion API 오류] 이벤트 조회 실패: "
                        f"{response.status_code}, {response.text}"
                    )
                    return None

                result = response.json()
                events.extend(result.get("results", []))
                if not result.get("has_more"):
                    return events

                payload["start_cursor"] = result.get("next_cursor")
        except requests.RequestException as error:
            print(f"  ➔ ❌ Notion 이벤트 조회 중 네트워크 오류 발생: {error}")
            return None

    def create_report_page(self, title, children):
        """설정된 보고서 부모 페이지 아래에 보고서 하위 페이지를 생성한다."""
        if not settings.REPORT_PARENT_PAGE_ID:
            print("❌ NOTION_REPORT_PARENT_PAGE_ID가 설정되지 않았습니다.")
            return False

        payload = {
            "parent": {"page_id": settings.REPORT_PARENT_PAGE_ID},
            "properties": {
                "title": [{"text": {"content": title}}],
            },
            "children": children,
        }

        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=10,
            )
            if response.status_code == 200:
                print(f"  ➔ 🟢 [Notion 성공] 보고서가 생성되었습니다: {title}")
                return True

            print(
                "  ➔ 🔴 [Notion API 오류] 보고서 생성 실패: "
                f"{response.status_code}, {response.text}"
            )
            return False
        except requests.RequestException as error:
            print(f"  ➔ ❌ Notion 보고서 생성 중 네트워크 오류 발생: {error}")
            return False
