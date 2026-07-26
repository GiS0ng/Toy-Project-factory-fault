import socket
import threading

from config import settings
from network.router import FactoryRouter


class SmartFactoryBridge:
    MAX_MESSAGE_BYTES = 4096

    def __init__(self):
        """서버 주소를 설정하고 데이터 라우터를 생성한다."""
        self.host = settings.HOST
        self.port = settings.PORT
        self.router = FactoryRouter()

    def handle_client(self, client_socket, addr):
        """연결 종료까지 수신한 줄 단위 패킷을 라우터에 전달한다."""
        try:
            with client_socket:
                received_data = bytearray()
                while True:
                    chunk = client_socket.recv(1024)
                    if not chunk:
                        break

                    received_data.extend(chunk)
                    if len(received_data) > self.MAX_MESSAGE_BYTES:
                        raise OSError("수신 패킷 크기가 허용 범위를 초과했습니다.")

                decoded_messages = received_data.decode("utf-8").splitlines()
                for message in decoded_messages:
                    if message:
                        self.router.parse_and_route(message)
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
