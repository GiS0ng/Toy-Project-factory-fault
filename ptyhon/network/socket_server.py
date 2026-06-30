# ptyhon/network/socket_server.py
import socket
import threading
from config import settings
from network.router import FactoryRouter

class SmartFactoryBridge:
    def __init__(self):
        self.host = settings.HOST
        self.port = settings.PORT
        self.router = FactoryRouter()

    def handle_client(self, client_socket, addr):
        try:
            with client_socket:
                data = client_socket.recv(1024)
                if data:
                    decoded_msg = data.decode('utf-8')
                    self.router.parse_and_route(decoded_msg)
        except Exception as e:
            print(f"⚠️ 클라이언트 통신 에러 ({addr}): {e}")

    def start(self):
        # socket.SOCK_STREAM 으로 수정 (socket. 접두어 추가)
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
                client_thread = threading.Thread(target=self.handle_client, args=(client_sock, addr))
                client_thread.start()