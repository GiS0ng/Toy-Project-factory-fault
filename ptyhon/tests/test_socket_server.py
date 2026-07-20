from unittest.mock import Mock

from network.socket_server import SmartFactoryBridge


class FakeClientSocket:
    def __init__(self, payload):
        """테스트에서 반환할 가짜 수신 데이터를 저장한다."""
        self.payload = payload
        self.closed = False

    def __enter__(self):
        """컨텍스트 관리자 진입 시 현재 가짜 소켓을 반환한다."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """컨텍스트 관리자 종료 시 소켓이 닫힌 상태임을 기록한다."""
        self.closed = True

    def recv(self, size):
        """요청한 버퍼 크기를 확인하고 준비된 데이터를 반환한다."""
        assert size == 1024
        return self.payload


def test_handle_client_decodes_and_routes_message():
    """수신 데이터를 문자열로 변환해 라우터에 전달하는지 검증한다."""
    server = SmartFactoryBridge()
    server.router = Mock()
    client = FakeClientSocket(b"WARNING,4,550,1")

    server.handle_client(client, ("127.0.0.1", 12345))

    server.router.parse_and_route.assert_called_once_with("WARNING,4,550,1")
    assert client.closed is True


def test_handle_client_ignores_empty_payload():
    """수신 데이터가 비어 있으면 라우터를 호출하지 않는지 검증한다."""
    server = SmartFactoryBridge()
    server.router = Mock()
    client = FakeClientSocket(b"")

    server.handle_client(client, ("127.0.0.1", 12345))

    server.router.parse_and_route.assert_not_called()
    assert client.closed is True
