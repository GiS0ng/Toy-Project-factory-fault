import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MessageValidationError(ValueError):
    """수신 메시지가 지원 형식 또는 값 제약을 위반했음을 나타낸다."""


class MessageType(str, Enum):
    PERIODIC = "PERIODIC"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


EXPECTED_ERROR_CODES = {
    MessageType.PERIODIC: 0,
    MessageType.WARNING: 1,
    MessageType.CRITICAL: 2,
}

EXPECTED_ZONES = {
    MessageType.PERIODIC: {None, "A", "B"},
    MessageType.WARNING: {None, "C"},
    MessageType.CRITICAL: {None, "D"},
}


@dataclass(frozen=True)
class SensorReading:
    sensor_id: int
    velocity_rms: float


@dataclass(frozen=True)
class TelemetryMessage:
    message_type: MessageType
    machine_id: int
    vibration_value: float
    error_code: int
    timestamp: str | None = None
    standard: str | None = None
    zone: str | None = None
    readings: tuple[SensorReading, ...] = field(default_factory=tuple)

    @classmethod
    def parse(cls, raw_message: str) -> "TelemetryMessage":
        """CSV v1 또는 JSON v1 메시지를 강타입 객체로 변환한다."""
        if not isinstance(raw_message, str) or not raw_message.strip():
            raise MessageValidationError("빈 메시지입니다")
        stripped = raw_message.strip()
        if stripped.startswith("{"):
            return cls._from_json(stripped)
        return cls._from_csv(stripped)

    @classmethod
    def _from_csv(cls, raw_message: str) -> "TelemetryMessage":
        tokens = [token.strip() for token in raw_message.split(",")]
        if len(tokens) != 4:
            raise MessageValidationError("CSV v1은 정확히 4개 필드가 필요합니다")
        return cls._validated(
            message_type=tokens[0],
            machine_id=tokens[1],
            vibration_value=tokens[2],
            error_code=tokens[3],
        )

    @classmethod
    def _from_json(cls, raw_message: str) -> "TelemetryMessage":
        try:
            payload: dict[str, Any] = json.loads(raw_message)
        except (json.JSONDecodeError, TypeError) as error:
            raise MessageValidationError("잘못된 JSON입니다") from error
        if payload.get("version") != 1:
            raise MessageValidationError("지원하지 않는 JSON 프로토콜 버전입니다")
        if payload.get("unit") != "mm/s RMS":
            raise MessageValidationError("JSON 진동 단위는 mm/s RMS여야 합니다")

        raw_readings = payload.get("readings", [])
        if not isinstance(raw_readings, list):
            raise MessageValidationError("readings는 배열이어야 합니다")
        try:
            readings = tuple(
                SensorReading(
                    sensor_id=int(reading["sensor_id"]),
                    velocity_rms=float(reading["velocity_rms"]),
                )
                for reading in raw_readings
            )
        except (KeyError, TypeError, ValueError) as error:
            raise MessageValidationError("센서 측정값 형식이 잘못되었습니다") from error
        if any(
            reading.sensor_id <= 0 or reading.velocity_rms < 0 for reading in readings
        ):
            raise MessageValidationError("센서 ID와 진동값 범위가 잘못되었습니다")

        return cls._validated(
            message_type=payload.get("type"),
            machine_id=payload.get("machine_id"),
            vibration_value=payload.get("max_velocity_rms"),
            error_code=payload.get("error_code"),
            timestamp=payload.get("timestamp"),
            standard=payload.get("standard"),
            zone=payload.get("zone"),
            readings=readings,
        )

    @classmethod
    def _validated(
        cls,
        *,
        message_type: object,
        machine_id: object,
        vibration_value: object,
        error_code: object,
        timestamp: object = None,
        standard: object = None,
        zone: object = None,
        readings: tuple[SensorReading, ...] = (),
    ) -> "TelemetryMessage":
        try:
            parsed_type = MessageType(str(message_type))
            parsed_machine_id = int(machine_id)
            parsed_vibration = float(vibration_value)
            parsed_error_code = int(error_code)
        except (TypeError, ValueError) as error:
            raise MessageValidationError("필수 필드의 타입이 잘못되었습니다") from error

        if parsed_machine_id <= 0 or parsed_vibration < 0:
            raise MessageValidationError("설비 ID와 진동값 범위가 잘못되었습니다")
        if parsed_error_code != EXPECTED_ERROR_CODES[parsed_type]:
            raise MessageValidationError("메시지 유형과 에러 코드가 일치하지 않습니다")

        zone_text = str(zone) if zone is not None else None
        if zone_text not in EXPECTED_ZONES[parsed_type]:
            raise MessageValidationError("메시지 유형과 ISO Zone이 일치하지 않습니다")

        return cls(
            message_type=parsed_type,
            machine_id=parsed_machine_id,
            vibration_value=parsed_vibration,
            error_code=parsed_error_code,
            timestamp=str(timestamp) if timestamp is not None else None,
            standard=str(standard) if standard is not None else None,
            zone=zone_text,
            readings=readings,
        )
