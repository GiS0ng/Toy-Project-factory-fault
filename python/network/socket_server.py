import socket
import threading

from config.settings import Settings
from network.router import FactoryRouter


class SmartFactoryBridge:
    def __init__(self, settings: Settings, router: FactoryRouter):
        """서버 설정과 데이터 라우터를 주입받아 브리지를 구성한다."""
        self.settings = settings
        self.router = router

    def handle_client(self, client_socket: socket.socket, addr: tuple) -> None:
        """한 연결의 줄 단위 메시지를 끝까지 읽어 라우터에 전달한다."""
        buffer = bytearray()
        try:
            with client_socket:
                while True:
                    chunk = client_socket.recv(4096)
                    if not chunk:
                        break
                    buffer.extend(chunk)
                    if len(buffer) > self.settings.max_message_bytes:
                        raise ValueError("허용된 메시지 크기를 초과했습니다")

                if not buffer:
                    return
                decoded = buffer.decode("utf-8")
                messages = [line for line in decoded.splitlines() if line.strip()]
                for message in messages or [decoded]:
                    self.router.parse_and_route(message)
        except (OSError, UnicodeDecodeError, ValueError) as error:
            print(f"⚠️ 클라이언트 통신 오류 ({addr}): {error}")

    def start(self, stop_event: threading.Event | None = None) -> None:
        """중지 이벤트가 설정될 때까지 TCP 연결을 수신한다."""
        stop_event = stop_event or threading.Event()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.settings.host, self.settings.port))
            server_socket.listen(5)
            server_socket.settimeout(0.5)

            print("==================================================")
            print("🤖 Smart Factory Data Bridge Python Server")
            print(f"📡 수신 대기 주소 ➔ " f"{self.settings.host}:{self.settings.port}")
            print("==================================================")

            while not stop_event.is_set():
                try:
                    client_socket, addr = server_socket.accept()
                except socket.timeout:
                    continue
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, addr),
                    daemon=True,
                )
                client_thread.start()
