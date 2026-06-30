import requests
from config import settings

class NotionClient:
    def __init__(self):
        self.api_url = "https://api.notion.com/v1/pages"
        self.headers = {
            "Authorization": f"Bearer {settings.NOTION_TOKEN}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }

    def send_to_notion_daily(self, machine_id, vibration_val, error_code):
        """C++로부터 받은 실시간 데이터를 노션 데이터베이스 표에 실제로 한 줄 추가합니다."""
        payload = {
            "parent": {"database_id": settings.DATABASE_ID},
            "properties": {
                "설비명": {
                    "title": [
                        {
                            "text": {
                                "content": f"공장 설비 {machine_id}호기"
                            }
                        }
                    ]
                },
                "진동값": {  
                    # 어제 발견한 노션 타입 미스매치를 방지하기 위해 
                    # 표 컬럼 타입에 맞춰 안전하게 안전 처리를 해줍니다.
                    "number": int(vibration_val)
                },
                "에러코드": {
                    "number": int(error_code)
                }
            }
        }

        try:
            response = requests.post(self.api_url, headers=self.headers, json=payload)
            if response.status_code == 200:
                print(f"  ➔ 🟢 [Notion 진짜 성공] {machine_id}호기 데이터가 노션 표에 안착했습니다! (값: {vibration_val})")
                return True
            else:
                print(f"  ➔ 🔴 [Notion API 오류] 상태코드: {response.status_code}, 내용: {response.text}")
                return False
        except Exception as e:
            print(f"  ➔ ❌ 노션 전송 중 네트워크 에러 발생: {e}")
            return False