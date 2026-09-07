from unittest.mock import Mock, call

from config.settings import Settings
from network.socket_server import SmartFactoryBridge


class FakeClientSocket:
    def __init__(self, chunks):
        """테스트에서 순서대로 반환할 수신 조각을 저장한다."""
        self.chunks = iter(chunks)
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.closed = True

    def recv(self, size):
        assert size == 4096
        return next(self.chunks, b"")


def create_server(router=None, max_message_bytes=65_536):
    return SmartFactoryBridge(
        settings=Settings(max_message_bytes=max_message_bytes),
        router=router or Mock(),
    )


def test_handle_client_combines_fragmented_message():
    router = Mock()
    server = create_server(router)
    client = FakeClientSocket([b"WARN", b"ING,4,550,1\n", b""])

    server.handle_client(client, ("127.0.0.1", 12345))

    router.parse_and_route.assert_called_once_with("WARNING,4,550,1")
    assert client.closed is True


def test_handle_client_routes_multiple_newline_delimited_messages():
    router = Mock()
    server = create_server(router)
    client = FakeClientSocket([b"PERIODIC,1,1.0,0\nCRITICAL,1,7.0,2\n", b""])

    server.handle_client(client, ("127.0.0.1", 12345))

    assert router.parse_and_route.call_args_list == [
        call("PERIODIC,1,1.0,0"),
        call("CRITICAL,1,7.0,2"),
    ]


def test_handle_client_rejects_oversized_payload(capsys):
    router = Mock()
    server = create_server(router, max_message_bytes=5)
    client = FakeClientSocket([b"123456", b""])

    server.handle_client(client, ("127.0.0.1", 12345))

    router.parse_and_route.assert_not_called()
    assert "초과" in capsys.readouterr().out


def test_handle_client_ignores_empty_payload():
    router = Mock()
    server = create_server(router)
    client = FakeClientSocket([b""])

    server.handle_client(client, ("127.0.0.1", 12345))

    router.parse_and_route.assert_not_called()
    assert client.closed is True
