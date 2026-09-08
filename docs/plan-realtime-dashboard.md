# 계획: Notion → SQLite 교체 + 실시간 웹 대시보드

/ 상태: 결정 확정됨 (§4 열린 질문 해소, 2026-09-08). §5 1단계부터 착수.
/ 작성 근거: Claude 계획 + Codex 병렬 계획(`/codex:rescue`)을 비교해 종합.

## 1. 목표와 배경

현재 구조: `C++ 엣지 → TCP(JSON v1 / CSV v1) → Python 브리지 → Notion(DB 대용) / KakaoTalk(스텁)`.
`NotionClient.send_to_notion_daily()`가 WARNING/CRITICAL 이벤트를 Notion DB에 append하고,
그걸로 데일리/위클리 보고서를 본다(보고서 생성 코드는 실제로 없음).

바꿀 것:

1. **Notion → SQLite** — 표준 라이브러리 `sqlite3`, 파일 하나, 서버 없음.
2. **실시간 웹 대시보드 추가** (학습 목적) — 장비별 현재 Zone/진동값/Zone D 연속카운트
   라이브 표시 + 이벤트 이력 테이블 + 진동 시계열 차트 + 데일리/위클리 보고서.

제약: Python, 단일 엣지 장비 + 단일 writer, 로컬/WSL, 의존성 최소화(현재
`requests`/`python-dotenv` 수준), 토이 프로젝트지만 "제대로 된 패턴"을 배우고 싶음.
구현은 ponytail 원칙(YAGNI, stdlib 우선, 요청 안 한 추상화 금지, 가장 얇게 시작).

## 2. Claude 계획 vs Codex 계획

### 2.1 완전히 일치한 결정

| 항목 | 결정 | 근거 |
|---|---|---|
| 백엔드 | **FastAPI + uvicorn** (로컬 실행) | REST·SSE·async·자동 문서·테스트 용이. Flask는 async/SSE 학습을 덜 함. `http.server`는 직접 구현 부담 |
| DB | **SQLite** (`sqlite3`, 의존성 0) | 단일 writer·낮은 쓰기량에 최적. 파일 복사로 백업. DuckDB/Timescale은 오버킬 |
| 실시간 전송 | **SSE** (폴링을 fallback으로) | 서버→브라우저 단방향이면 충분. `EventSource` 자동 재연결. WebSocket은 과함(양방향 필요해지면 그때) |
| 프론트 | **바닐라 JS + Chart.js**, 빌드 스텝 없음 | `fetch`/`EventSource`/DOM 학습. SPA는 Node·번들러 추가라 과함 |
| Chart.js | **로컬 vendor** (`web/static/vendor/`), CDN 금지 | WSL 오프라인 대비 |
| 프로세스 | **단일 프로세스** (브리지 + 웹). SQLite 파일 공유, IPC 없음 | 단일 장비라 프로세스 분리·IPC는 복잡도만 늘림 |
| PERIODIC | **저장한다** | 라이브 차트·정상상태 시계열 학습에 필요 |
| SQLite 운영 | WAL 모드, `busy_timeout`, 읽기/쓰기 연결 분리, 이벤트당 짧은 트랜잭션, DB 커밋 성공 후에만 SSE 발행 | |
| 커밋 | 단계별 독립 커밋, 각 단계가 이전 상태로 롤백 가능 | |

### 2.2 차이 나는 지점과 판정

| 항목 | Claude | Codex | 채택 |
|---|---|---|---|
| **threading→asyncio** | 브리지를 asyncio로 전환 | **부분 전환**: 수신 스레드는 blocking socket 유지, 웹만 async, 수신→루프는 `loop.call_soon_threadsafe()` | **Codex.** TCP 프레이밍·shutdown·기존 테스트 재작성 리스크 대비 이득 적음 |
| **수신→DB 경계** | 수신 → SQLite 저장 + broadcast (직접) | **bounded queue + 전용 writer worker + 인메모리 상태 허브** | **Codex.** 백프레셔·단일 writer 패턴이 학습 목표에 부합. 단, SQLite 도입과 같은 단계에서 함께 |
| **스키마 규모** | 1테이블 (`vibration_events`) | 8테이블 (`machines`/`telemetry_events`/`sensor_readings`/`machine_state`/`hourly_rollups`/`daily_reports`/`weekly_reports` + 뷰) | **절충: 2테이블로 시작** — `telemetry_events` + `machine_state`. 나머지는 필요해질 때 추가 |
| **디렉토리 구조** | 기존 `config/network/services`에 `persistence/`·`web/`만 추가 | 전면 계층화 (`domain/`·`ingestion/`·`persistence/`·`application/`·`web/`) | **Claude(최소 변경).** ponytail 원칙. 전면 계층화는 파일 수·import 호환 비용이 커서 보류 |
| **리텐션** | 미상세 | 원시 30일 → 시간별 롤업, WARNING/CRITICAL 장기 보존, 자동삭제는 사람 확인 필수 | **Codex 방향 채택하되 지금은 저장만.** 삭제 명령·롤업은 나중 단계, 자동삭제 없음(AGENTS.md) |
| 커밋 단계 수 | 4 | 9 (docs 먼저 + feature flag 전환 + 큐/SSE/리포트 분리) | **~6으로 병합** (§5). Codex의 "docs 먼저"와 "feature flag 전환"은 유지 |
| 테스트 전략 | 미상세 | 레이어별(파서/DB/API/SSE) + CI 확장 상세 | **Codex 채택** |

### 2.3 Codex가 짚은 리스크 (반드시 반영)

- **C++는 Zone D 연속 한도 도달 후 정상 종료한다** (`cpp/src/MachineMonitor.cpp`). 대시보드는
  "running / stopped / offline(last_seen)" 상태를 구분해 표시해야 한다.
- C++는 전송 실패 시 로컬 CSV를 계속 쌓지만 **Python 브리지에는 재전송 큐가 없다**.
  수신 장애 동안의 데이터 복구 정책을 정해야 한다(우선순위 낮음: 나중).
- CSV v1 메시지에는 `timestamp`가 없다 → CSV 이벤트는 수신 시각을 이벤트 시각으로 쓴다.
- 모든 PERIODIC 원시 저장 시 DB 증가 속도 확인 필요(§4).
- FastAPI 도입으로 프로세스 실행·종료 처리가 기존 단일 blocking 서버보다 복잡해진다.

## 3. 목표 아키텍처

```text
C++ 엣지 ──TCP(JSON/CSV v1)──▶ 수신 스레드 (blocking socket, 기존 유지)
                                   │  검증된 도메인 이벤트
                                   ▼
                              bounded queue
                                   ▼
                          SQLite writer (전용, 단일 writer)
                                   │  커밋 성공
                                   ├─▶ SQLite  (telemetry_events, machine_state)
                                   └─▶ 인메모리 상태 허브 ──▶ SSE 구독자들
                                                              ▲
FastAPI (asyncio):  REST 읽기 API + /api/stream(SSE) + 정적 대시보드 ──┘
```

- 수신 스레드 → 이벤트 루프 전달: `asyncio.run_coroutine_threadsafe` / `loop.call_soon_threadsafe`.
- 웹 요청의 DB 읽기가 이벤트 루프를 막지 않도록 `asyncio.to_thread` 또는 별도 읽기 연결.
- KakaoTalk: CRITICAL 알림 채널로 유지(현재 콘솔 스텁 그대로).
- Notion: 기본 경로에서 제거. 필요하면 나중에 "선택적 export"로만.

### 스키마 (시작 시점, 2테이블)

```sql
CREATE TABLE IF NOT EXISTS telemetry_events (
    id                        INTEGER PRIMARY KEY,
    observed_at               TEXT NOT NULL,   -- JSON은 원본 timestamp, CSV는 수신시각. UTC ISO8601
    received_at               TEXT NOT NULL,   -- 브리지 수신 UTC
    machine_id                INTEGER NOT NULL,
    message_type              TEXT NOT NULL,   -- PERIODIC | WARNING | CRITICAL
    zone                      TEXT,            -- A|B|C|D|NULL
    vibration_value           REAL NOT NULL,   -- max_velocity_rms
    error_code                INTEGER NOT NULL,
    zone_d_consecutive_count  INTEGER
);
CREATE INDEX IF NOT EXISTS ix_events_machine_time ON telemetry_events(machine_id, observed_at);
CREATE INDEX IF NOT EXISTS ix_events_type_time    ON telemetry_events(message_type, observed_at);

CREATE TABLE IF NOT EXISTS machine_state (
    machine_id                INTEGER PRIMARY KEY,
    updated_at                TEXT NOT NULL,
    last_event_id             INTEGER,
    zone                      TEXT,
    vibration_value           REAL,
    zone_d_consecutive_count  INTEGER,
    message_type              TEXT,
    lifecycle                 TEXT             -- running | stopped | offline
);
```

이벤트 INSERT와 `machine_state` UPSERT는 한 트랜잭션.

### 디렉토리 (최소 변경)

```text
python/
├── main.py                     # 조립: settings → store → bridge → web app
├── config/
│   ├── settings.py             # NOTION_* 제거, FACTORY_DB_PATH 추가
│   └── database.py             # 연결·PRAGMA·스키마 생성
├── network/                    # 기존 유지
│   ├── message.py
│   ├── socket_server.py        # 수신 스레드 (거의 그대로)
│   └── router.py               # notion_client → event_store 주입
├── persistence/
│   ├── event_store.py          # record_event(), 조회 메서드
│   └── retention.py            # 나중 단계
├── services/
│   └── alarm_service.py        # 기존
├── web/
│   ├── app.py                  # FastAPI 앱 + lifespan(수신 스레드 기동/종료)
│   ├── api.py                  # REST 엔드포인트
│   ├── sse.py                  # /api/stream, 구독자 관리
│   └── static/
│       ├── index.html
│       ├── app.js
│       ├── styles.css
│       └── vendor/chart.min.js
└── tests/
```

## 4. 착수 전 정할 것 → 결정 확정 (2026-09-08)

- [x] **시간대**: 저장은 UTC ISO8601, 대시보드 **표시는 Asia/Seoul**. 변환은 표시 계층에서만.
- [x] **Zone D 연속 카운트 출처**: **Python 브리지가 재계산**한다. C++는 이 값을 전송하지
      않는 것으로 확인됨(`EventSerializer::toJson`/`toCsv`에 없고 `VibrationEvent` 구조체에도
      없음, `MachineMonitor` 내부 변수로만 존재). Python 상태 허브가 `machine_id`별로
      수신 이벤트 기준 연속 Zone D를 세고 `machine_state`에 기록한다(C++ `MachineMonitor`
      로직과 동일: Zone D면 +1, 아니면 0). 나중에 C++가 JSON에 실어 보내면 그 값으로 교체.
- [x] **장비 종료 상태 표시**: `running` / `stopped`(Zone D 한도 도달 후 정상 종료) /
      `offline`(last_seen 초과) 세 가지. offline 임계값 = 마지막 이벤트 후 `sample_interval_ms * 5`.
- [x] **CSV v1 계속 지원**: 유지 — C++가 아직 보냄. 파서 이미 있음. CSV는 `timestamp`가
      없으므로 수신 시각을 `observed_at`으로 쓴다.
- [x] **PERIODIC 저장량**: `sample_interval_ms=3000` → 장비당 하루 ~28,800행, 30일 ≈ 86만 행.
      SQLite 문제 없음. 리텐션·롤업은 이후 단계, 자동삭제 없음(AGENTS.md).
- [x] **Notion**: **코드 완전 제거**. `NotionClient`/`test_notion_client`/`Settings`의
      `NOTION_*` 삭제. 기존 Notion 데이터는 이관하지 않는다.
- [x] **KakaoTalk 실연동**: 이번 범위 밖. 콘솔 스텁(`send_to_kakao_sos`) 그대로 유지.
- [x] **FastAPI/uvicorn 의존성 추가**: **승인됨**. 5단계 착수 시 `requirements.txt`에 추가.

## 5. 실행 계획 (단계별 독립 커밋)

각 단계는 이전 상태로 롤백 가능하고, `pytest`/`black`/CTest 통과를 유지한다.
커밋 메시지는 한국어 Conventional Commits (CLAUDE.md "Git 규칙").

**진행 상황 (2026-09-08):** 1~4단계 완료 (`fef2bfa`, `81b7974`, `eda07f5`, +큐 분리).
- 3단계는 feature flag 없이 라우터를 바로 SQLite로 전환 — §4에서 Notion 완전 제거를
  확정했으므로 "되돌리기" 스위치는 불필요한 유연성(ponytail).
- 4단계는 큐 + 단일 writer까지만. **인메모리 상태 허브는 6단계로 미룸** (소비자 부재).
- `notion_client.py`/`test_notion_client.py`/`Settings.NOTION_*`는 미사용 상태로 남김,
  정리 단계에서 삭제.
- 다음: 5단계 (FastAPI 읽기 API + 폴링 대시보드).

### 1단계 — 현재 계약 문서화 + 결정 확정  ✅ 완료
- 이 문서의 §4 열린 질문을 채운다. 현재 데이터 흐름/필드/검증을 `docs/`에 정리.
- 코드 변경 없음. `docs: 현재 데이터 흐름과 교체 경계 문서화` → `docs/current-contract.md`

### 2단계 — SQLite 저장소 추가 (미사용)  ✅ 완료
- `config/database.py`(연결·WAL·`busy_timeout`·스키마), `persistence/event_store.py`
  (`record_event()` + 기본 조회). `Settings`에 `FACTORY_DB_PATH`(기본 `data/factory.db`).
- `.gitignore`에 `data/*.db*` 추가. 단위 테스트(`:memory:`).
- 라우터는 아직 Notion. `feat: SQLite 이벤트 저장소 추가`

### 3단계 — Notion → SQLite 전환  ✅ 완료 (feature flag 생략, 위 진행 상황 참고)
- `FactoryRouter`가 `notion_client` 대신 `event_store` 주입받음. PERIODIC/WARNING/CRITICAL
  모두 기록 + `machine_state` UPSERT(같은 트랜잭션).
- `main.create_bridge()`에서 저장소 항상 생성(“설정 없으면 스킵” 분기 제거).
- 전환 스위치(env 또는 팩토리)로 Notion 경로 되돌리기 가능하게. 라우터 테스트를 SQLite fixture로.
- `notion_client.py` / `test_notion_client.py`는 아직 삭제 안 함. `refactor: 이벤트 기록을 SQLite로 전환`

### 4단계 — 수신/저장 분리: 큐 + writer  ✅ 완료 (상태 허브 제외)
- `FactoryRouter`가 검증·로그·긴급 알림만 수신 스레드에서 처리하고 `IngestedEvent`를
  `EventWriter.submit()`으로 bounded queue에 넣는다. `socket_server.py`는 그대로.
- `persistence/event_writer.py`: 단일 writer 스레드가 큐 소비 → `EventStore.record_event`.
  overflow 정책 = reject-newest(누적 유실 카운트). `stop()`은 큐를 비운 뒤 join.
- Zone D 연속 카운트는 라우터가 락으로 보호하며 계산(여러 수신 스레드 대응).
- `SmartFactoryBridge`가 accept 루프 앞뒤로 writer를 start/stop.
- burst/overflow/DB오류/종료/이중start 테스트 + 라우터 통합 테스트.
- **상태 허브는 보류.** 소비자(SSE)가 6단계에 생긴다. 그때까지 "현재 상태"는
  `machine_state` 테이블이 담당하고, 5단계 REST는 이 테이블을 읽는다. 인메모리
  허브 + 발행/구독은 6단계에서 추가한다(YAGNI).
- `refactor: 수신과 저장을 이벤트 큐로 분리`

### 5단계 — FastAPI 읽기 API + 정적 대시보드(폴링)
- `fastapi`/`uvicorn` 추가(승인 후). `web/app.py` lifespan에서 수신 스레드 기동/정지.
- `GET /api/machines`, `/api/events`(필터), `/api/timeseries`, `/api/reports/daily|weekly`.
- `web/static/` 대시보드: 상태 카드 + 이벤트 테이블 + Chart.js 차트(우선 폴링).
- FastAPI TestClient + 임시 SQLite 테스트. `feat: 진동 모니터링 조회 API와 대시보드 추가`

### 6단계 — SSE 실시간 채널
- `/api/stream`: 연결 즉시 상태 스냅샷 → 이후 `state`/`event`/`heartbeat`. 구독자 관리,
  느린 구독자 큐 상한, 재연결. 프론트를 `EventSource`로 전환(폴링은 fallback 유지).
- `feat: 대시보드 SSE 실시간 스트림 추가`

### 이후 (별도, 선택)
- 보고서 집계 테이블 + 시간별 롤업 + `retention.py`(dry-run, 자동삭제 없음).
- Notion 코드 제거 / 선택적 export로 격리. CI에 웹·DB 테스트 추가.
- 운영자 상호작용(알람 ACK 등) → 이때 WebSocket 검토.

## 6. 참고
- 커밋/브랜치 규칙: `CLAUDE.md` "Git 규칙"
- 이 계획 수립 방식(내 계획 + Codex 병렬 계획 비교): 이 저장소의 구조 변경 표준 절차
- Codex 원본 계획 전문: `docs/codex-plan-raw.md`
