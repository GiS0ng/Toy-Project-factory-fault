import socket
import json
import os
from dotenv import load_dotenv
import requests  # 💡 실제 노션 전송을 위해 requests 추가

# 내 컴퓨터 내부에서 통신할 주소와 포트 설정
HOST = '127.0.0.1'
PORT = 9999

# ⭐ 회원님의 실제 유효한 토큰과 DB ID 세팅
load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")
def send_to_notion_daily(machine_id, vibration_val, error_code):
    """
    [Notion 연동 모듈]
    C++로부터 받은 실시간 데이터를 노션 데이터베이스 표에 실제로 한 줄 추가합니다.
    """
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    # 💡 노션 데이터베이스 속성(Property)명은 본인의 표 컬럼명과 일치해야 합니다.
    # 아래 구조는 가장 표준적인 '이름'(title)과 '숫자형 센서값' 구조입니다.
    payload = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "설비명": {  # 혹은 'Name'이나 '타이틀' 등 노션 표의 첫 번째 컬럼명
                "title": [
                    {
                        "text": {
                            "content": f"공장 설비 {machine_id}호기"
                        }
                    }
                ]
            },
            "진동값": {  # 노션 표에 있는 숫자나 텍스트 컬럼명에 맞추세요
                "number": int(vibration_val)
            },
            "에러코드": {
                "number": int(error_code)
            }
        }
    }

    try:
        response = requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload)
        if response.status_code == 200:
            print(f"  ➔ 🟢 [Notion 진짜 성공] {machine_id}호기 데이터가 노션 표에 안착했습니다! (값: {vibration_val})")
        else:
            print(f"  ➔ 🔴 [Notion API 오류] 상태코드: {response.status_code}, 내용: {response.text}")
    except Exception as e:
        print(f"  ➔ ❌ 노션 전송 중 네트워크 에러 발생: {e}")

def send_to_kakao_sos(machine_id, vibration_val, error_code):
    """[카카오톡 알림 모듈] 미구현 시뮬레이션 코드"""
    print("=" * 60)
    print("💬 [카카오톡 긴급 알림 전송 메시지 미리보기]")
    print(f"🚨 [설비 비상 중단 통보]\n▶ 설비 번호: {machine_id}호기\n▶ 최종 진동값: {vibration_val}\n▶ 에러코드: {error_code}")
    print("=" * 60)

def parse_and_route(raw_message):
    """C++이 보낸 문자열 패킷을 쪼개고 분석해서 제 길로 찾아보내는 라우터 함수"""
    try:
        tokens = raw_message.strip().split(',')
        if len(tokens) < 4:
            print(f"⚠️ 규격에 맞지 않는 데이터가 들어왔습니다: {raw_message}")
            return

        data_type = tokens[0]      # PERIODIC 또는 CRITICAL
        machine_id = tokens[1]     # 기계 ID
        vibration_val = tokens[2]  # 최종 진동값
        error_code = tokens[3]     # 에러 코드

        if data_type == "PERIODIC":
            print(f"\n📊 [정기 수신] {machine_id}호기 가동 데이터 취합 중...")
            send_to_notion_daily(machine_id, vibration_val, error_code)
        elif data_type == "CRITICAL":
            print(f"\n🚨 [긴급 수신] {machine_id}호기 위험 신호 포착!!!")
            send_to_kakao_sos(machine_id, vibration_val, error_code)

    except Exception as e:
        print(f"❌ 데이터 라우팅 중 예외 에러 발생: {e}")

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        
        print("==================================================")
        print("🤖 Smart Factory Data Bridge Python Server v3.1")
        print(f"📡 수신 대기 주소 ➔ {HOST}:{PORT}")
        print(" 현장 C++ 엔진의 소켓 연결을 기다리는 중... (종료: Ctrl+C)")
        print("==================================================")

        while True:
            try:
                client_socket, addr = server_socket.accept()
                with client_socket:
                    data = client_socket.recv(1024)
                    if not data:
                        continue
                    decoded_msg = data.decode('utf-8')
                    parse_and_route(decoded_msg)
            except Exception as e:
                print(f"⚠️ 연결 처리 중 에러 발생: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 파이썬 브릿지 서비스를 안전하게 종료합니다.")