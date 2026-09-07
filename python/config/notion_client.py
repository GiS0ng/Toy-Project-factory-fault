from collections.abc import Callable
from typing import Any

import requests


class NotionClient:
    def __init__(
        self,
        token: str,
        database_id: str,
        post: Callable[..., Any] = requests.post,
    ):
        """인증값과 요청 함수를 주입받아 Notion 클라이언트를 초기화한다."""
        if not token or not database_id:
            raise ValueError("Notion 토큰과 데이터베이스 ID가 필요합니다")
        self.api_url = "https://api.notion.com/v1/pages"
        self.database_id = database_id
        self.post = post
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

    def send_to_notion_daily(
        self, machine_id: int, vibration_val: float, error_code: int
    ) -> bool:
        """검증된 진동 이벤트를 Notion 데이터베이스에 추가한다."""
        payload = {
            "parent": {"database_id": self.database_id},
            "properties": {
                "설비명": {
                    "title": [{"text": {"content": f"공장 설비 {machine_id}호기"}}]
                },
                "진동값": {"number": float(vibration_val)},
                "에러코드": {"number": int(error_code)},
            },
        }

        try:
            response = self.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=10,
            )
            if 200 <= response.status_code < 300:
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
