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
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if not 1 <= self.port <= 65_535:
            raise ValueError("FACTORY_PORT는 1~65535 범위여야 합니다")
        if self.max_message_bytes <= 0:
            raise ValueError("MAX_MESSAGE_BYTES는 양수여야 합니다")
        if bool(self.notion_token) != bool(self.database_id):
            raise ValueError("NOTION_TOKEN과 DATABASE_ID는 함께 설정해야 합니다")

    @property
    def notion_enabled(self) -> bool:
        return bool(self.notion_token and self.database_id)
