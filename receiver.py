# receiver.py
import socket
import json

# 내 컴퓨터 내부에서 통신할 주소와 포트(문방구 번호) 설정
HOST = '127.0.0.1'
PORT = 9999

def send_to_notion_daily(machine_id, vibration_val, error_code):
    """
    [Notion 연동 모듈]
    나중에 발급받을 Notion API Token과 Database ID를 연동하여
    데일리 보고서 표(Database)에 한 줄을 자동으로 추가하는 로직이 들어갈 자리입니다.
    """
    print(f"  ➔ [Notion] {machine_id}호기 데일리 리포트 데이터베이스 전송 완료! (값: {vibration_val})")
    # TODO: requests.post("https://api.notion.com/v1/pages", ...) 실제 API 호출 구현 예정

def send_to_kakao_sos(machine_id, vibration_val, error_code):
    """
    [카카오톡 알림 모듈]
    카카오 디벨로퍼스 API를 통해 치명적 고장 위험(102) 발생 시
    관리자 스마트폰으로 즉시 카톡 SOS 푸시 알림을 쏘는 로직이 들어갈 자리입니다.
    """
    print("=" * 60)
    print("💬 [카카오톡 긴급 알림 전송 메시지 미리보기]")
    print(f"🚨 [설비 비상 중단 통보]")
    print(f"▶ 설비 번호: {machine_id}호기")
    print(f"▶ 최종 계산된 진동값: {vibration_val}")
    print(f"▶ 발생 에러코드: {error_code} (IMMEDIATE_STOP)")
    print(f"❗ 설비 보호를 위해 시스템이 셧다운되었습니다. 즉시 현장을 점검하십시오.")
    print("=" * 60)
    print("  ➔ [KakaoTalk] 최고 관리자 및 담당자 휴대폰으로 푸시 알림 발송 성공!")
    # TODO: requests.post("https://kapi.kakao.com/v2/api/talk/memo/default/send", ...) 실제 API 구현 예정

def parse_and_route(raw_message):
    """C++이 보낸 문자열 패킷을 쪼개고 분석해서 제 길로 찾아보내는 라우터 함수"""
    try:
        # 공백 제거 및 콤마 기준으로 데이터 분리 ("PERIODIC,1,4.25,0" -> 데이터셋 생성)
        tokens = raw_message.strip().split(',')
        if len(tokens) < 4:
            print(f"⚠️ 규격에 맞지 않는 데이터가 들어왔습니다: {raw_message}")
            return

        data_type = tokens[0]      # PERIODIC 또는 CRITICAL
        machine_id = tokens[1]     # 기계 ID (예: 1)
        vibration_val = tokens[2]  # 변환된 최종 진동/진폭 값 (예: 4.25)
        error_code = tokens[3]     # 에러 코드 (예: 0 또는 102)

        if data_type == "PERIODIC":
            print(f"\n📊 [정기 수신] {machine_id}호기 가동 데이터 취합 중...")
            send_to_notion_daily(machine_id, vibration_val, error_code)

        elif data_type == "CRITICAL":
            print(f"\n🚨 [긴급 수신] {machine_id}호기 위험 신호 포착!!!")
            send_to_kakao_sos(machine_id, vibration_val, error_code)

    except Exception as e:
        print(f"❌ 데이터 라우팅 중 예외 에러 발생: {e}")

def main():
    # TCP/IP 소켓 서버 오픈
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        # 프로그램 재시작 시 포트 고임(인증 에러) 방지 옵션
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        
        print("==================================================")
        print("🤖 Smart Factory Data Bridge Python Server v2.0")
        print(f"📡 수신 대기 주소 ➔ {HOST}:{PORT}")
        print(" 현장 C++ 엔진의 소켓 연결을 기다리는 중... (종료: Ctrl+C)")
        print("==================================================")

        while True:
            try:
                # C++ 클라이언트가 노크하면 연결 승인
                client_socket, addr = server_socket.accept()
                with client_socket:
                    # 데이터 수신 (최대 1024 바이트)
                    data = client_socket.recv(1024)
                    if not data:
                        continue
                    
                    # 인코딩 변환 후 라우터로 전달
                    decoded_msg = data.decode('utf-8')
                    parse_and_route(decoded_msg)
                    
            except Exception as e:
                print(f"⚠️ 연결 처리 중 에러 발생: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 파이썬 브릿지 서비스를 안전하게 종료합니다.")