from unittest.mock import Mock

import requests

from config.notion_client import NotionClient


def test_send_to_notion_daily_posts_expected_payload(monkeypatch):
    """정상 요청에서 올바른 Notion 페이로드를 전송하는지 검증한다."""
    response = Mock(status_code=200)
    post = Mock(return_value=response)
    monkeypatch.setattr("config.notion_client.requests.post", post)

    client = NotionClient()
    result = client.send_to_notion_daily("7", "456", "1")

    assert result is True
    post.assert_called_once_with(
        "https://api.notion.com/v1/pages",
        headers=client.headers,
        json={
            "parent": {"database_id": "test-database"},
            "properties": {
                "설비명": {
                    "title": [{"text": {"content": "공장 설비 7호기"}}]
                },
                "진동값": {"number": 456},
                "에러코드": {"number": 1},
            },
        },
        timeout=10,
    )


def test_send_to_notion_daily_returns_false_for_api_error(monkeypatch):
    """Notion API가 오류 상태를 반환하면 실패로 처리하는지 검증한다."""
    response = Mock(status_code=400, text="bad request")
    monkeypatch.setattr(
        "config.notion_client.requests.post", Mock(return_value=response)
    )

    assert NotionClient().send_to_notion_daily("1", "600", "2") is False


def test_send_to_notion_daily_returns_false_for_network_error(monkeypatch):
    """Notion 요청 중 네트워크 오류가 발생하면 실패로 처리하는지 검증한다."""
    post = Mock(side_effect=requests.RequestException("network unavailable"))
    monkeypatch.setattr("config.notion_client.requests.post", post)

    assert NotionClient().send_to_notion_daily("1", "600", "2") is False


def test_query_events_collects_all_pages(monkeypatch):
    """이벤트 조회가 다음 커서를 사용해 모든 결과를 수집하는지 검증한다."""
    first_response = Mock(
        status_code=200,
        json=Mock(return_value={"results": [{"id": "first"}], "has_more": True,
                                "next_cursor": "next-page"}),
    )
    second_response = Mock(
        status_code=200,
        json=Mock(return_value={"results": [{"id": "second"}], "has_more": False}),
    )
    post = Mock(side_effect=[first_response, second_response])
    monkeypatch.setattr("config.notion_client.requests.post", post)

    events = NotionClient().query_events(
        "2026-07-25T15:00:00+00:00", "2026-07-26T15:00:00+00:00"
    )

    assert events == [{"id": "first"}, {"id": "second"}]
    assert post.call_count == 2
    assert post.call_args.args[0].endswith("/v1/databases/test-database/query")
    assert post.call_args.kwargs["json"]["start_cursor"] == "next-page"


def test_create_report_page_posts_under_configured_parent(monkeypatch):
    """보고서가 설정된 Notion 부모 페이지 아래에 생성되는지 검증한다."""
    response = Mock(status_code=200)
    post = Mock(return_value=response)
    monkeypatch.setattr("config.notion_client.requests.post", post)
    monkeypatch.setattr("config.notion_client.settings.REPORT_PARENT_PAGE_ID", "parent-id")

    result = NotionClient().create_report_page("데일리 보고서", [])

    assert result is True
    assert post.call_args.kwargs["json"] == {
        "parent": {"page_id": "parent-id"},
        "properties": {
            "title": [{"text": {"content": "데일리 보고서"}}],
        },
        "children": [],
    }
