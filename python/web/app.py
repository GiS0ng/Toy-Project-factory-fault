import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config.settings import Settings
from main import create_bridge
from persistence.event_store import EventStore
from web.api import router as api_router

_STATIC_DIR = Path(__file__).resolve().parent / "static"


def build_app(settings: Settings | None = None, *, run_bridge: bool = True) -> FastAPI:
    """대시보드 FastAPI 앱을 만든다.

    run_bridge=True 면 lifespan에서 수신 브리지(TCP 서버 + writer)를 백그라운드
    스레드로 돌린다. 테스트는 run_bridge=False 로 브리지 없이 조회 API만 띄운다.
    """
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        stop_event = threading.Event()
        thread: threading.Thread | None = None
        if run_bridge:
            bridge = create_bridge(settings)
            thread = threading.Thread(
                target=bridge.start,
                kwargs={"stop_event": stop_event},
                name="bridge",
                daemon=True,
            )
            thread.start()
        else:
            # 브리지 없이도 조회가 되도록 파일·스키마만 만들어 둔다.
            EventStore.open(settings.factory_db_path).close()

        app.state.settings = settings
        try:
            yield
        finally:
            stop_event.set()
            if thread is not None:
                thread.join(timeout=6)

    app = FastAPI(title="진동 모니터링 대시보드", lifespan=lifespan)
    app.include_router(api_router)
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(_STATIC_DIR / "index.html")

    return app


def main() -> None:
    """`python python/dashboard.py` 진입점. 브리지 + 대시보드를 함께 띄운다."""
    import uvicorn

    settings = Settings.from_env()
    uvicorn.run(build_app(settings), host=settings.web_host, port=settings.web_port)
