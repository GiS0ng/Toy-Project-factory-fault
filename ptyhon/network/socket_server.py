import socket
import threading

from config import settings
from network.router import FactoryRouter


class SmartFactoryBridge:
    def __init__(self):
        """서버 주소를 설정하고 데이터 라우터를 생성한다."""
        self.host = settings.HOST
        self.port = settings.PORT
        self.router = FactoryRouter()

    def handle_client(self, client_socket, addr):
        """클라이언트 데이터를 UTF-8 문자열로 변환해 라우터에 전달한다."""
        try:
            with client_socket:
                data = client_socket.recv(1024)
                if data:
                    decoded_msg = data.decode("utf-8")
                    self.router.parse_and_route(decoded_msg)
        except (OSError, UnicodeDecodeError) as error:
            print(f"⚠️ 클라이언트 통신 오류 ({addr}): {error}")

    def start(self):
        """TCP 서버를 시작하고 클라이언트 연결을 계속 수신한다."""
        # TCP 스트림 소켓으로 서버를 실행한다.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.host, self.port))
            server_socket.listen(5)

            print("==================================================")
            print("🤖 Smart Factory Data Bridge Python Server")
            print(f"📡 수신 대기 주소 ➔ {self.host}:{self.port}")
            print("==================================================")

            while True:
                client_sock, addr = server_socket.accept()
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_sock, addr),
                    daemon=True,
                )
                client_thread.start()
