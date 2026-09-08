# 현재 데이터 흐름과 교체 경계

`docs/plan-realtime-dashboard.md` §5 1단계 산출물. Notion→SQLite 교체와 대시보드
도입에 앞서, **지금 코드가 실제로 주고받는 계약**과 **어디를 갈아끼우는지**를 고정한다.
코드 변경 없음. 기준 커밋: `79b8294` 시점의 `python/`, `cpp/`.

## 1. 전체 흐름

```text
센서 3개 → C++ MachineMonitor (측정·Zone 평가·로컬 CSV)
             │
             ├─ 로컬 CSV 저장 (periodic_*.csv / critical_*.csv)  ← 네트워크와 무관, 항상 수행
             │
             └─ TCP 소켓 1회 연결 → 페이로드 전송 → 연결 종료
                                   │
                        Python SmartFactoryBridge (network/socket_server.py)
                                   │  연결마다 스레드, 줄 단위 분리
                                   ▼
                        FactoryRouter.parse_and_route (network/router.py)
                                   │  TelemetryMessage.parse 로 검증
                                   ├─ PERIODIC → 콘솔 로그만
                                   ├─ WARNING  → 콘솔 로그 + _send_report
                                   └─ CRITICAL → 콘솔 로그 + _send_report + send_to_kakao_sos
                                                   │
                                        NotionClient.send_to_notion_daily (config/notion_client.py)
                                        services/alarm_service.send_to_kakao_sos (콘솔 스텁)
```

- C++는 각 샘플마다 소켓을 새로 열어 한 메시지를 보내고 닫는다(`TcpTelemetrySender`).
  전송 실패해도 로컬 CSV 수집·저장은 계속한다.
- Python 브리지에는 **재전송 큐가 없다.** 브리지가 꺼져 있는 동안 온 데이터는 유실된다
  (C++ 로컬 CSV에는 남는다).
- C++는 Zone D가 `consecutive_zone_d_limit`회 연속되면 버퍼를 저장하고 **정상 종료(exit 0)** 한다.
  이후 그 장비는 더 이상 메시지를 보내지 않는다.

## 2. 전송 형식

### CSV v1 (레거시, 계속 지원)

```text
<TYPE>,<machine_id>,<max_velocity_rms>,<error_code>
```

예: `WARNING,2,4.500,1` — 정확히 4개 필드. `timestamp`, `zone`, `standard`, 개별 센서값 **없음**.
`EventSerializer::toCsv`가 생성한다.

### JSON v1 (현행, 줄 단위, 끝에 개행)

```json
{"version":1,"type":"WARNING","timestamp":"2026-09-04T00:00:00Z","machine_id":1,"standard":"ISO 20816-3:2022","unit":"mm/s RMS","max_velocity_rms":4.5,"zone":"C","error_code":1,"readings":[{"sensor_id":1,"velocity_rms":4.5}]}
```

`EventSerializer::toJson`이 생성한다. 필드:

| 필드 | 타입 | 비고 |
|---|---|---|
| `version` | int | 항상 `1`. 다르면 거부 |
| `type` | str | `PERIODIC` \| `WARNING` \| `CRITICAL` |
| `timestamp` | str | C++ 측정 시각, UTC `%Y-%m-%dT%H:%M:%SZ` |
| `machine_id` | int | > 0 |
| `standard` | str | 프로필의 `standard` 문자열 그대로 |
| `unit` | str | 항상 `"mm/s RMS"`. 다르면 거부 |
| `max_velocity_rms` | float | ≥ 0. 세 센서 중 최댓값 |
| `zone` | str | `A`\|`B`\|`C`\|`D`. C++는 항상 채워 보냄 |
| `error_code` | int | `0`\|`1`\|`2` |
| `readings` | array | `{sensor_id>0, velocity_rms≥0}` 목록 |

### C++가 보내지 **않는** 것

- **Zone D 연속 카운트**: `MachineMonitor::consecutiveZoneDCount_` 내부 변수로만 존재.
  JSON·CSV 어디에도 없고 `VibrationEvent` 구조체에도 없다.
- **CSV의 timestamp**: CSV v1에는 시각 필드가 없다.
- 프로필 값(`consecutive_zone_d_limit`, `sample_interval_ms`, Zone 경계 등): C++ 설정 파일에만
  있고 Python은 모른다.

## 3. 검증 규칙 (`TelemetryMessage.parse`)

수신 문자열이 `{`로 시작하면 JSON, 아니면 CSV로 해석한다. 다음을 어기면
`MessageValidationError`를 던지고 **라우터가 그 메시지를 버린다**(외부로 내보내지 않음).

- 빈 문자열 거부.
- JSON: `version == 1`, `unit == "mm/s RMS"` 필수.
- CSV: 정확히 4필드.
- `machine_id`는 int로 변환 가능하고 > 0.
- `vibration_value`(= `max_velocity_rms`)는 float로 변환 가능하고 ≥ 0.
- 유형 ↔ 에러코드 일치: `PERIODIC=0`, `WARNING=1`, `CRITICAL=2` (`EXPECTED_ERROR_CODES`).
  C++ `ErrorCode` enum과 항상 같아야 한다.
- 유형 ↔ Zone 조합 (`EXPECTED_ZONES`):
  - `PERIODIC` → `{None, "A", "B"}`
  - `WARNING` → `{None, "C"}`
  - `CRITICAL` → `{None, "D"}`
- JSON `readings`: 배열이어야 하고 각 원소는 `sensor_id > 0`, `velocity_rms ≥ 0`.

즉 **유형과 에러코드는 1:1**이고, Zone은 있으면 유형과 맞아야 하지만 없어도(`None`) 통과한다.
따라서 "연속 Zone D"는 `message_type == CRITICAL`로 판별하는 것이 CSV·JSON 모두에서 안전하다.

## 4. 라우터 동작 (`FactoryRouter.parse_and_route`)

| 유형 | 콘솔 로그 | `_send_report` (Notion) | `send_to_kakao_sos` |
|---|---|---|---|
| PERIODIC | O | — | — |
| WARNING | O | O | — |
| CRITICAL | O | O | O |

- `_send_report`는 `notion_client`가 `None`이면 "설정이 없어 생략" 로그만 남긴다.
- `send_to_kakao_sos(machine_id, vibration_value, error_code)`는 콘솔 미리보기만 하는 스텁.
- 반환값 `bool`: 검증 통과 여부. 소켓 계층은 이 값을 느슨하게만 쓴다.

## 5. 조립 (`main.create_bridge`)

```text
Settings.from_env()
  → notion_enabled 이면 NotionClient 생성, 아니면 None
  → FactoryRouter(notion_client=…)
  → SmartFactoryBridge(settings, router)
```

의존성은 모두 생성자 주입. `Settings`:

- `FACTORY_HOST`(기본 127.0.0.1), `FACTORY_PORT`(기본 9999, 1~65535),
  `MAX_MESSAGE_BYTES`(기본 65536, 양수)
- `NOTION_TOKEN` / `DATABASE_ID`: 둘 다 있거나 둘 다 없어야 함

## 6. 교체 경계

교체 대상과 유지 대상을 명확히 한다.

| 구성요소 | 조치 |
|---|---|
| `config/notion_client.py` | 데이터 경로에서 제거. 파일·테스트는 정리 단계에서 삭제 |
| `FactoryRouter._send_report` | `EventStore` 기록으로 대체 (`_record_event`) |
| `FactoryRouter.__init__(notion_client=…)` | `__init__(event_store)` 로 변경, 항상 주입 |
| `main.create_bridge` 의 `notion_enabled` 분기 | 제거. 저장소는 항상 생성 |
| `Settings.NOTION_*` | 정리 단계에서 제거. 그때까지는 미사용 상태로 둠 |
| `TelemetryMessage.parse` / `network/message.py` | **변경 없음.** 검증 계약 그대로 |
| `network/socket_server.py` | 1~3단계에서는 **변경 없음.** 4단계에서 큐로 분리 |
| `services/alarm_service.py` | **변경 없음.** CRITICAL 알림 채널로 유지 |
| Zone D 연속 카운트 | Python 라우터가 `machine_id`별로 재계산 (§3 근거로 `CRITICAL` 연속 수) |
| CSV 이벤트 시각 | `timestamp`가 없으므로 브리지 수신 시각을 `observed_at`으로 사용 |

## 7. 새로 들어오는 것 (2단계~)

- `config/database.py`: SQLite 연결(WAL, `busy_timeout`) + 스키마 생성.
- `persistence/event_store.py`: `EventStore` — `record_event()` + 기본 조회.
- 스키마 2테이블: `telemetry_events`, `machine_state` (상세는 `plan-realtime-dashboard.md` §3).
- `Settings.factory_db_path` (`FACTORY_DB_PATH`, 기본 `data/factory.db`).
- 저장 시각은 UTC ISO8601 고정, 대시보드 표시만 Asia/Seoul(5단계).
