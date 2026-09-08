from config.settings import Settings
from network.router import FactoryRouter
from network.socket_server import SmartFactoryBridge
from persistence.event_store import EventStore


def create_bridge() -> SmartFactoryBridge:
    """환경 설정을 읽어 실행 가능한 브리지를 조립한다."""
    settings = Settings.from_env()
    event_store = EventStore.open(settings.factory_db_path)
    return SmartFactoryBridge(
        settings=settings,
        router=FactoryRouter(event_store),
    )


if __name__ == "__main__":
    try:
        create_bridge().start()
    except (OSError, ValueError) as error:
        print(f"❌ 브리지 시작 실패: {error}")
        raise SystemExit(1) from error
    except KeyboardInterrupt:
        print("\n👋 파이썬 브릿지 서비스를 안전하게 종료합니다.")
