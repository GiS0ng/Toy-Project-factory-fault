from config.notion_client import NotionClient
from config.settings import Settings
from network.router import FactoryRouter
from network.socket_server import SmartFactoryBridge


def create_bridge() -> SmartFactoryBridge:
    """환경 설정을 읽어 실행 가능한 브리지를 조립한다."""
    settings = Settings.from_env()
    notion_client = None
    if settings.notion_enabled:
        notion_client = NotionClient(
            token=settings.notion_token or "",
            database_id=settings.database_id or "",
        )
    return SmartFactoryBridge(
        settings=settings,
        router=FactoryRouter(notion_client=notion_client),
    )


if __name__ == "__main__":
    try:
        create_bridge().start()
    except (OSError, ValueError) as error:
        print(f"❌ 브리지 시작 실패: {error}")
        raise SystemExit(1) from error
    except KeyboardInterrupt:
        print("\n👋 파이썬 브릿지 서비스를 안전하게 종료합니다.")
