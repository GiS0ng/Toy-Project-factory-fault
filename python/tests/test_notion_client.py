from unittest.mock import Mock

import requests

from config.notion_client import NotionClient


def test_send_to_notion_daily_posts_expected_payload(monkeypatch):
    """정상 요청에서 올바른 Notion 페이로드를 전송하는지 검증한다."""
    response = Mock(status_code=201)
    post = Mock(return_value=response)
    client = NotionClient("test-token", "test-database", post=post)
    result = client.send_to_notion_daily(7, 456.0, 1)

    assert result is True
    post.assert_called_once_with(
        "https://api.notion.com/v1/pages",
        headers=client.headers,
        json={
            "parent": {"database_id": "test-database"},
            "properties": {
                "설비명": {"title": [{"text": {"content": "공장 설비 7호기"}}]},
                "진동값": {"number": 456.0},
                "에러코드": {"number": 1},
            },
        },
        timeout=10,
    )


def test_send_to_notion_daily_returns_false_for_api_error(monkeypatch):
    """Notion API가 오류 상태를 반환하면 실패로 처리하는지 검증한다."""
    response = Mock(status_code=400, text="bad request")
    client = NotionClient(
        "test-token", "test-database", post=Mock(return_value=response)
    )
    assert client.send_to_notion_daily(1, 600.0, 2) is False


def test_send_to_notion_daily_returns_false_for_network_error(monkeypatch):
    """Notion 요청 중 네트워크 오류가 발생하면 실패로 처리하는지 검증한다."""
    post = Mock(side_effect=requests.RequestException("network unavailable"))
    client = NotionClient("test-token", "test-database", post=post)
    assert client.send_to_notion_daily(1, 600.0, 2) is False
