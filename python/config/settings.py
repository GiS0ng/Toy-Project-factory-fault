import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 9999
    notion_token: str | None = None
    database_id: str | None = None
    max_message_bytes: int = 65_536
    factory_db_path: str = "data/factory.db"
    web_host: str = "127.0.0.1"
    web_port: int = 8000
    # 대시보드 lifecycle 판정용. C++ 설비 프로필과 값을 맞춰 둔다.
    sample_interval_ms: int = 3_000
    consecutive_zone_d_limit: int = 4

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> "Settings":
        """환경 파일과 환경 변수에서 실행 설정을 읽고 검증한다."""
        if env_file is None:
            env_file = Path(__file__).resolve().parents[2] / ".env"
        load_dotenv(dotenv_path=env_file)

        settings = cls(
            host=os.getenv("FACTORY_HOST", "127.0.0.1"),
            port=int(os.getenv("FACTORY_PORT", "9999")),
            notion_token=os.getenv("NOTION_TOKEN"),
            database_id=os.getenv("DATABASE_ID"),
            max_message_bytes=int(os.getenv("MAX_MESSAGE_BYTES", "65536")),
            factory_db_path=os.getenv("FACTORY_DB_PATH", "data/factory.db"),
            web_host=os.getenv("WEB_HOST", "127.0.0.1"),
            web_port=int(os.getenv("WEB_PORT", "8000")),
            sample_interval_ms=int(os.getenv("SAMPLE_INTERVAL_MS", "3000")),
            consecutive_zone_d_limit=int(os.getenv("CONSECUTIVE_ZONE_D_LIMIT", "4")),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if not 1 <= self.port <= 65_535:
            raise ValueError("FACTORY_PORT는 1~65535 범위여야 합니다")
        if self.max_message_bytes <= 0:
            raise ValueError("MAX_MESSAGE_BYTES는 양수여야 합니다")
        if not self.factory_db_path:
            raise ValueError("FACTORY_DB_PATH는 비어 있을 수 없습니다")
        if not 1 <= self.web_port <= 65_535:
            raise ValueError("WEB_PORT는 1~65535 범위여야 합니다")
        if self.sample_interval_ms <= 0:
            raise ValueError("SAMPLE_INTERVAL_MS는 양수여야 합니다")
        if self.consecutive_zone_d_limit <= 0:
            raise ValueError("CONSECUTIVE_ZONE_D_LIMIT는 양수여야 합니다")
        if bool(self.notion_token) != bool(self.database_id):
            raise ValueError("NOTION_TOKEN과 DATABASE_ID는 함께 설정해야 합니다")

    @property
    def notion_enabled(self) -> bool:
        return bool(self.notion_token and self.database_id)
