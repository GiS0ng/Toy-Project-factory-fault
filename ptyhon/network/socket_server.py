import socket
from config import settings
from network.router import FactoryRouter

class SmartFactoryBridge:
    def __init__(self):
        self.host = settings.HOST
        self.port = settings.PORT
        self.router = FactoryRouter()

    def start(self):
        """서버 소켓을 열고 현장 C++ 엔진의 로그 데이터를 무한 루프로 대기합니다."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.host, self.port))
            server_socket.listen()
            
            print("==================================================")
            print("🤖 Smart Factory Data Bridge Python Server v5.0")
            print(f"📡 수신 대기 주소 ➔ {self.host}:{self.port}")
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
                        
                        # 라우터 객체에게 패킷 파싱 및 분기를 위임합니다.
                        self.router.parse_and_route(decoded_msg)
                except Exception as e:
                    print(f"⚠️ 연결 처리 중 에러 발생: {e}")