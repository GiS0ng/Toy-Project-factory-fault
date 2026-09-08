import json

import pytest

from network.message import MessageType, MessageValidationError, TelemetryMessage


def test_parse_legacy_csv_message():
    message = TelemetryMessage.parse("WARNING,2,4.5,1")

    assert message.message_type == MessageType.WARNING
    assert message.machine_id == 2
    assert message.vibration_value == 4.5
    assert message.error_code == 1


def test_parse_json_v1_message():
    payload = {
        "version": 1,
        "type": "CRITICAL",
        "timestamp": "2026-09-04T00:00:00Z",
        "machine_id": 3,
        "standard": "ISO 20816-3:2022",
        "unit": "mm/s RMS",
        "max_velocity_rms": 7.2,
        "zone": "D",
        "error_code": 2,
        "readings": [{"sensor_id": 1, "velocity_rms": 7.2}],
    }

    message = TelemetryMessage.parse(json.dumps(payload))

    assert message.message_type == MessageType.CRITICAL
    assert message.zone == "D"
    assert message.readings[0].velocity_rms == 7.2


@pytest.mark.parametrize(
    "raw_message",
    [
        "WARNING,1,4.5,2",
        "CRITICAL,0,7.0,2",
        '{"version":2,"type":"PERIODIC"}',
        '{"version":1,"type":"CRITICAL","unit":"g"}',
        # machine_id가 SQLite INTEGER(64비트) 범위를 넘으면 저장 전에 거른다
        f"PERIODIC,{2**63},1.0,0",
    ],
)
def test_invalid_messages_are_rejected(raw_message):
    with pytest.raises(MessageValidationError):
        TelemetryMessage.parse(raw_message)


def test_max_int64_machine_id_is_accepted():
    message = TelemetryMessage.parse(f"PERIODIC,{2**63 - 1},1.0,0")
    assert message.machine_id == 2**63 - 1
