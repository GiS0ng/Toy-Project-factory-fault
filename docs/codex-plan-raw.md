# Codex 원본 계획 (실시간 대시보드 구조 변경)

/ 출처: `/codex:rescue --fresh` 로 받은 Codex 병렬 계획 전문 (수정 없이 보관).
/ 종합·채택 결과는 `docs/plan-realtime-dashboard.md` 참고.
/ 요청 프롬프트: "Notion→SQLite 교체 + 학습 목적 실시간 웹 대시보드. 백엔드 프레임워크,
/   실시간 전송 방식, 프론트, 프로세스 구조, threading→asyncio, PERIODIC 저장/리텐션,
/   디렉토리 구조, 단계별 커밋 계획. 코드 말고 계획만, 트레이드오프 명시."

---

## 1. 백엔드 프레임워크 선택

### 결정

FastAPI를 선택한다. 단, 초기에는 ASGI 서버를 별도 애플리케이션 서버로 복잡하게 구성하지 않고 `uvicorn`으로 로컬 실행한다.

### 근거

현재 Python 진입점은 `python/main.py`이고, 브리지는 `SmartFactoryBridge.start()`에서 blocking TCP 서버를 직접 실행한다 (`python/main.py`, `python/network/socket_server.py:34-60`).

FastAPI는 다음 학습 목표에 적합하다.

- REST API와 타입 기반 요청·응답 모델
- SSE 스트리밍 응답
- 비동기 엔드포인트와 백그라운드 작업 경계
- 자동 API 문서화
- 테스트 가능한 애플리케이션 구조

SQLite는 Python 표준 라이브러리 `sqlite3`로 처리하므로 데이터베이스 의존성은 추가하지 않는다.

### 트레이드오프

- FastAPI 자체와 실행 서버 의존성이 추가된다.
- 현재 프로젝트보다 `pydantic`, ASGI, 이벤트 루프 개념을 더 배워야 한다.
- blocking TCP 브리지와 비동기 웹 서버를 함께 운영할 때 스레드-이벤트 루프 경계를 명확히 해야 한다.

### 대안

- Flask: 의존성과 개념 부담이 더 작고 학습 곡선이 낮다. 다만 SSE와 비동기 경계를 직접 설계해야 하며, 이번 학습 목표인 현대적인 비동기 웹 구조를 덜 경험한다.
- `http.server`: 의존성은 0이지만 라우팅, JSON 응답, SSE, 오류 처리, 테스트를 모두 직접 구현해야 하므로 학습 효율이 낮다.
- 별도 프레임워크 없음: 이 프로젝트에서는 권장하지 않는다. 실시간 연결과 보고서 API가 늘어날수록 직접 만든 웹 계층의 유지 비용이 커진다.

권장 의존성 증가는 `fastapi`, `uvicorn` 정도로 제한한다. 새 패키지 추가 전 사용자 확인이 필요하므로 실제 변경 단계에서 승인받는다.

---

## 2. 실시간 전송 방식

### 결정

브라우저에는 SSE(Server-Sent Events)를 사용한다.

### 근거

대시보드가 서버에서 브라우저로 전달해야 하는 정보는 다음과 같다.

- 장비별 현재 Zone
- 현재 진동값
- Zone D 연속 카운트
- 새 이벤트와 상태 변경

브라우저에서 서버로 지속적인 명령을 보낼 필요는 없다. SSE는 HTTP 기반 단방향 스트림이므로 브라우저의 `EventSource`만으로 구현할 수 있고 자동 재연결도 지원한다.

### 트레이드오프

- 서버에서 브라우저 방향만 지원한다.
- 다수의 브라우저가 연결되면 각 연결에 이벤트를 전달해야 한다.
- 연결 종료, 재연결, 느린 클라이언트에 대한 큐 정리가 필요하다.

### 대안

- 폴링: 가장 단순하고 의존성이 없지만 실시간성이 떨어지고 반복 요청이 많아진다. 초기 API 확인용 fallback으로는 유지할 수 있다.
- WebSocket: 양방향 통신과 낮은 지연이 장점이지만 연결 상태, 재연결, 프로토콜, 테스트 복잡도가 증가한다. 현재 요구에는 과하다.

SSE 이벤트는 `state`, `event`, `heartbeat` 유형으로 나누고, 연결 직후에는 현재 상태 스냅샷을 먼저 전달한다.

---

## 3. 프론트엔드 접근과 차트 라이브러리

### 결정

빌드 도구 없는 바닐라 JavaScript를 사용하고, Chart.js를 정적 파일로 포함한다.

### 근거

현재 프론트엔드가 없고 Python 의존성도 `requests`, `python-dotenv`, 테스트·포매터 수준이다 (`requirements.txt`).

바닐라 JS 구조는 다음 학습에 적합하다.

- `fetch` 기반 API 호출
- `EventSource` 기반 SSE 구독
- DOM 상태 갱신
- 페이지 상태와 차트 데이터 분리
- 빌드 과정 없이 로컬/WSL에서 즉시 실행

Chart.js는 진동 시계열과 Zone 기준선 표시를 빠르게 구현할 수 있다. `web/static/vendor/chart.min.js`처럼 버전을 고정해 저장하면 CDN 장애나 인터넷 연결에 의존하지 않는다.

### 트레이드오프

- React/Vue보다 컴포넌트 재사용성과 상태 관리가 약하다.
- 화면 규모가 커지면 DOM 코드 관리가 어려워진다.
- Chart.js 정적 파일의 라이선스와 버전 관리가 필요하다.

### 대안

- CDN Chart.js: 초기 구현은 빠르지만 로컬·WSL 오프라인 환경에 취약하다.
- React/Vue 등 SPA: 컴포넌트 학습 가치는 높지만 Node.js, package manager, 번들러가 추가된다. 현재 목표에는 과하다.
- SVG 직접 구현: 의존성은 없지만 축, 확대, 툴팁, 다운샘플링을 직접 구현해야 한다.

화면은 `현재 상태`, `이벤트 이력`, `진동 시계열`, `데일리/위클리 보고서`의 네 영역으로 시작한다.

---

## 4. 프로세스 구조와 SQLite 공유

### 결정

브리지와 웹서버를 한 Python 프로세스로 통합한다.

권장 흐름은 다음과 같다.

```text
C++ TCP
  → 수신 스레드
  → 검증된 도메인 이벤트
  → bounded queue
  → SQLite 전용 writer
  → 메모리 상태 허브 + SSE
  → FastAPI 읽기 API
```

### 근거

현재 C++는 `TcpTelemetrySender`가 매 이벤트마다 TCP 연결을 만들고 개행 JSON 또는 CSV를 전송한다 (`cpp/src/TelemetrySender.cpp`, `cpp/src/EventSerializer.cpp`).

Python은 단일 엣지 장비와 로컬/WSL 환경이므로 프로세스 간 IPC를 추가하는 것보다 한 프로세스 내 경계가 단순하다. 기존 `SmartFactoryBridge`와 `FactoryRouter`도 생성자 주입 구조이므로 저장소 구현을 삽입하기 쉽다 (`python/network/router.py`, `python/main.py`).

SQLite 운영 원칙은 다음과 같다.

- `PRAGMA journal_mode=WAL`
- `PRAGMA busy_timeout`
- 읽기와 쓰기 연결을 분리
- 한 번에 하나의 쓰기 트랜잭션만 실행
- 이벤트 1개마다 독립적인 짧은 트랜잭션
- 웹 요청에서 장시간 트랜잭션을 열지 않음
- DB 기록 성공 후에만 SSE 이벤트 발행
- queue는 bounded로 두고 overflow 정책을 명시

### 트레이드오프

- 한 프로세스 장애가 수신, DB, 웹 대시보드를 모두 중단시킨다.
- Python GIL과 blocking I/O 경계를 함께 관리해야 한다.
- SQLite는 단일 writer 구조이므로 높은 수집률에는 한계가 있다.

### 대안

- 브리지와 웹서버 분리: 장애 격리와 독립 배포가 좋아지지만 SQLite 파일 공유, 프로세스 간 락, 중복 설정, IPC가 추가된다.
- 파일 공유 대신 IPC/큐: 향후 확장성은 좋지만 현재 단일 장비에는 복잡도가 과하다.
- 웹서버가 직접 DB 쓰기: 구현은 간단하지만 수신 스레드와 HTTP 요청이 DB 쓰기를 경쟁하게 된다. 권장하지 않는다.

---

## 5. 브리지의 `threading`에서 `asyncio` 전환

### 결정

전체 전환은 하지 않고, 부분 전환을 권장한다.

- TCP 수신: 우선 기존 `threading + blocking socket` 유지
- DB 기록: 전용 writer thread 또는 직렬화된 작업 큐
- 웹 API/SSE: FastAPI의 asyncio 사용
- 수신 스레드에서 이벤트 루프로 상태 이벤트를 전달할 때 `loop.call_soon_threadsafe()` 사용

### 근거

현재 `socket.accept()`와 `recv()`가 blocking이고 연결마다 daemon thread를 만든다 (`python/network/socket_server.py:18-60`). C++는 매 전송 후 연결을 닫으므로 장기 연결 관리가 필요하지 않다.

현재 규모에서는 blocking socket을 asyncio로 바꾸는 것이 기능상 필수는 아니다. 대신 웹 계층만 asyncio로 두면 변경 범위와 장애 가능성을 줄이면서 비동기 설계를 학습할 수 있다.

### 트레이드오프

- 두 동시성 모델을 함께 이해해야 한다.
- thread-safe queue와 event-loop 전달 경계가 필요하다.
- blocking DB 쿼리를 async 엔드포인트에서 직접 실행하면 이벤트 루프가 막힐 수 있다.

### 대안

- 완전한 asyncio 전환: 장기적으로 일관되지만 TCP 프레이밍, shutdown, 기존 테스트를 함께 재작성해야 한다.
- 전부 threading 유지: 가장 단순하지만 SSE 연결과 웹 동시성 관리가 불편하다.
- `asyncio.to_thread()` 활용: 소규모 blocking 작업에는 적합하나 무제한 사용은 worker 관리가 불명확해질 수 있다.

---

## 6. `PERIODIC` 이벤트 저장 여부와 리텐션

### 결정

`PERIODIC` 이벤트도 저장한다. 다만 원시 데이터와 보고서 집계를 분리한다.

권장 기본값은 다음과 같다.

- 모든 이벤트 원시 보존: 30일
- `WARNING`, `CRITICAL`: 30일 이후에도 별도 장기 보존
- 원시 `PERIODIC`: 30일 이후 시간 단위 롤업으로 대체
- 일 단위·주 단위 집계: 장기 보존
- 리텐션 기간은 환경 설정으로 변경 가능
- 자동 삭제 기능은 별도 명시적 명령과 확인 없이는 활성화하지 않음

현재 `PERIODIC` 이벤트는 `FactoryRouter`에서 출력만 하고 외부 저장하지 않는다 (`python/network/router.py:16-24`). 반면 C++는 주기 데이터를 메모리 버퍼에 모은 뒤 일정 시간마다 CSV로 저장한다 (`cpp/src/MachineMonitor.cpp:107-127`, `savePeriodicLog()`).

### 트레이드오프

- 모든 원시 샘플 저장은 SQLite 파일 크기와 쓰기 횟수를 증가시킨다.
- 보존 기간이 짧으면 과거 차트의 정밀도가 떨어진다.
- 롤업은 원본과 동일한 재현성을 제공하지 않는다.

### 대안

- `WARNING`·`CRITICAL`만 저장: 저장 비용은 낮지만 정상 상태의 시계열 학습이 불가능하다.
- 원시 데이터 무기한 보존: 학습에는 좋지만 디스크와 성능 관리가 필요하다.
- 원시 데이터를 저장하지 않고 시간별 집계만 저장: 가장 가볍지만 이상 패턴 분석이 제한된다.

데이터 삭제·마이그레이션은 프로젝트 규칙상 사람의 확인을 받은 뒤 실행한다.

---

## 7. SQLite 스키마 초안

DDL은 다음 수준으로 설계한다. 실제 컬럼 타입과 제약조건은 구현 단계에서 테스트와 함께 확정한다.

### `machines`

장비 기본 정보.

- `id` 또는 `machine_id`
- `name`
- `standard`
- `unit`
- `created_at`

### `telemetry_events`

모든 검증된 메시지의 대표 이벤트.

- `id`
- `machine_id`
- `observed_at`
- `received_at`
- `message_type`
- `zone`
- `vibration_value`
- `error_code`
- `zone_d_consecutive_count`
- `protocol_version`
- `raw_payload` 선택 저장

인덱스:

- `(machine_id, observed_at DESC)`
- `(machine_id, message_type, observed_at DESC)`
- `(zone, observed_at DESC)`
- `(observed_at)`

### `sensor_readings`

JSON의 개별 센서 측정값.

- `id`
- `event_id`
- `sensor_id`
- `velocity_rms`

인덱스:

- `(event_id)`
- `(sensor_id, event_id)`

### `machine_state`

대시보드가 즉시 읽을 현재 상태.

- `machine_id`를 primary key
- `last_event_id`
- `updated_at`
- `zone`
- `vibration_value`
- `zone_d_consecutive_count`
- `message_type`

### `hourly_telemetry_rollups`

원시 `PERIODIC` 삭제 후 차트와 보고서에 사용할 시간별 집계.

- `machine_id`
- `bucket_start`
- `sample_count`
- `min_value`
- `max_value`
- `avg_value`
- `zone_d_count`
- `warning_count`
- `critical_count`

복합 primary key:

- `(machine_id, bucket_start)`

### `daily_reports`, `weekly_reports`

재현 가능한 보고서 결과를 저장하는 선택적 집계 테이블.

- 기간 시작·종료
- 샘플 수
- Zone별 횟수
- 최대·평균·최소 진동값
- Zone D 최대 연속 횟수
- 경고·위험 이벤트 수
- `generated_at`
- 집계 버전

### 뷰

- `latest_machine_state`
- `recent_events`
- `daily_summary`
- `weekly_summary`

현재 상태는 이벤트 테이블에서 매번 계산하지 않고 `machine_state`에 별도 유지한다. 이벤트 기록과 상태 갱신은 하나의 트랜잭션으로 처리한다.

---

## 8. 데일리·위클리 보고서와 Notion/KakaoTalk

### 결정

보고서의 원천은 SQLite로 통일하고, 다음 3단계로 운영한다.

1. API 요청 시 기간 집계 조회
2. 반복 조회가 늘어나면 `daily_reports`, `weekly_reports`에 집계 결과 저장
3. 필요할 때 HTML 또는 JSON 보고서로 표시·다운로드

보고서 생성은 초기에는 온디맨드 쿼리로 시작하고, 주기 집계는 별도 scheduler 의존성 없이 애플리케이션 내부의 단순 작업 또는 명시적 CLI 명령으로 추가한다.

### 근거

현재 Notion은 `NotionClient.send_to_notion_daily()`에서 경고·위험 이벤트를 외부 DB처럼 저장한다 (`python/config/notion_client.py:27-68`, `python/network/router.py:40-51`). 목표는 Notion을 SQLite로 교체하는 것이므로 SQLite가 시스템의 기록 기준이 되어야 한다.

### 트레이드오프

- 온디맨드 쿼리는 구조가 단순하지만 큰 기간 조회 시 응답이 느려질 수 있다.
- 집계 테이블은 빠르지만 집계 재생성·버전 관리가 필요하다.
- 내부 scheduler는 의존성이 없지만 애플리케이션이 내려가면 실행되지 않는다.

### 대안

- APScheduler 추가: 예약 실행이 편하지만 의존성이 늘어난다. 현재는 권장하지 않는다.
- OS cron 또는 Windows 작업 스케줄러: 프로세스와 분리되어 안정적이지만 환경별 설정이 필요하다.
- Notion 병행 유지: SQLite를 기준 저장소로 하고 Notion은 선택적 export 대상으로만 유지한다.
- KakaoTalk 유지: `CRITICAL` 발생 시 알림 채널로 유지한다. 현재 구현은 실제 전송이 아니라 콘솔 미리보기 스텁이다 (`python/services/alarm_service.py:1-16`).

권장 최종 역할은 다음과 같다.

```text
SQLite: 원천 데이터·현재 상태·보고서
웹 대시보드: 조회·시각화
KakaoTalk: 위험 알림
Notion: 기본 경로에서 제거, 필요 시 수동/선택적 export
```

---

## 9. 디렉토리·모듈 구조

현재 `python/config`, `python/network`, `python/services` 구조는 기능이 증가하면 경계가 모호해질 수 있다. 기존 import 경로와 테스트를 한 번에 깨뜨리지 않도록 단계적으로 이동한다.

제안 구조:

```text
python/
├── main.py
├── config/
│   ├── settings.py
│   └── database.py
├── domain/
│   ├── message.py
│   ├── event.py
│   └── state.py
├── ingestion/
│   ├── socket_server.py
│   ├── router.py
│   └── queue.py
├── persistence/
│   ├── sqlite_repository.py
│   ├── migrations.py
│   └── retention.py
├── application/
│   ├── event_service.py
│   ├── report_service.py
│   └── state_service.py
├── web/
│   ├── app.py
│   ├── api.py
│   ├── sse.py
│   └── static/
│       ├── index.html
│       ├── app.js
│       ├── styles.css
│       └── vendor/chart.min.js
├── services/
│   └── alarm_service.py
└── tests/
```

### 트레이드오프

- 계층이 명확해지지만 작은 프로젝트에 비해 파일 수가 늘어난다.
- 기존 `network.message` import와 신규 `domain.message`의 호환 전략이 필요하다.

### 대안

- 현재 구조 유지 후 `database.py`, `web/`만 추가: 가장 적은 변경이지만 라우터가 저장·알림·상태 갱신을 계속 책임질 위험이 있다.
- 완전한 육각형 구조: 학습 가치는 높지만 토이 프로젝트에 과할 수 있다.

핵심 경계는 다음처럼 둔다.

```text
TCP 수신 → 메시지 파싱/검증 → 애플리케이션 서비스 → Repository/Notifier
                                      └→ State Publisher
```

---

## 10. 독립적으로 커밋 가능한 실행 계획

각 단계는 이전 단계만으로도 실행 가능하고, 실패 시 이전 동작을 유지할 수 있게 한다.

1. **현재 동작 계약과 아키텍처 문서화**

   - 범위: 현재 TCP JSON/CSV v1, 메시지 검증, C++ 로컬 CSV, Notion/KakaoTalk 동작을 문서화한다.
   - 산출물: 아키텍처 결정 기록, 이벤트 필드 정의, 상태·보고서 요구사항 문서.
   - 검증: 기존 `pytest`, Black, CTest 통과.
   - 되돌리기: 문서만 되돌리면 된다.
   - 커밋 예시: `docs: 현재 데이터 흐름과 교체 경계 문서화`

2. **SQLite 연결·스키마·Repository 추가**

   - 범위: SQLite 초기화, WAL, busy timeout, 스키마 생성, 이벤트 저장·조회 API를 추가한다.
   - 산출물: `sqlite_repository`, 초기화 명령, Repository 단위 테스트.
   - 검증: 임시 DB에서 삽입·조회·트랜잭션·재실행 테스트.
   - 되돌리기: 기존 Notion 라우팅은 유지하고 새 Repository만 미사용 상태로 둘 수 있다.
   - 커밋 예시: `feat: SQLite 이벤트 저장소 추가`

3. **Notion 대신 SQLite로 이벤트 기록**

   - 범위: 검증된 `PERIODIC`, `WARNING`, `CRITICAL`을 SQLite에 기록한다.
   - 산출물: 라우터와 저장소 연결, 현재 상태 갱신, 실패 시 오류 처리.
   - 검증: 기존 라우터 테스트를 SQLite fixture 기반으로 확장.
   - 되돌리기: feature flag로 Notion 경로 또는 SQLite 경로를 선택한다.
   - 커밋 예시: `refactor: 이벤트 기록을 SQLite로 전환`

4. **메모리 상태 허브와 이벤트 큐 추가**

   - 범위: 수신 스레드와 DB writer를 분리하고, 저장 성공 후 상태·이벤트를 발행한다.
   - 산출물: bounded queue, writer worker, shutdown 처리.
   - 검증: burst 입력, queue overflow, DB 오류, graceful shutdown 테스트.
   - 되돌리기: 큐를 우회해 기존 동기 저장 경로로 되돌릴 수 있게 한다.
   - 커밋 예시: `refactor: 수신과 저장을 이벤트 큐로 분리`

5. **FastAPI 읽기 API 추가**

   - 범위: 현재 상태, 최근 이벤트, 시계열, 일·주 보고서 조회 API를 추가한다.
   - 산출물: `/api/machines`, `/api/events`, `/api/timeseries`, `/api/reports/daily`, `/api/reports/weekly`.
   - 검증: FastAPI TestClient와 임시 SQLite를 이용한 API 테스트.
   - 되돌리기: 기존 브리지는 독립적으로 계속 실행 가능하다.
   - 커밋 예시: `feat: 진동 모니터링 조회 API 추가`

6. **SSE 실시간 채널 추가**

   - 범위: 상태 스냅샷, 새 이벤트, heartbeat, 재연결 처리를 추가한다.
   - 산출물: `/api/stream`, 연결별 subscriber 관리.
   - 검증: 테스트 클라이언트 연결, 이벤트 순서, 재연결, 느린 subscriber 정리.
   - 되돌리기: 프론트엔드가 SSE 대신 REST polling을 사용하도록 fallback한다.
   - 커밋 예시: `feat: 대시보드 SSE 이벤트 스트림 추가`

7. **바닐라 JS 대시보드 추가**

   - 범위: 현재 상태 카드, 이벤트 이력, Chart.js 시계열 차트, 보고서 화면을 추가한다.
   - 산출물: `web/static/index.html`, `app.js`, `styles.css`, 고정 버전 Chart.js.
   - 검증: 브라우저 수동 시나리오와 API/SSE mock 테스트.
   - 되돌리기: 정적 파일만 제거해도 백엔드 API는 유지된다.
   - 커밋 예시: `feat: 실시간 진동 대시보드 추가`

8. **보고서 집계·리텐션 추가**

   - 범위: 일·주 집계 테이블, 시간별 롤업, 보존 정책과 실행 명령을 추가한다.
   - 산출물: 보고서 집계 서비스, dry-run 리텐션 명령, 운영 문서.
   - 검증: 시간대 경계, 주 경계, 빈 기간, 재실행 idempotency 테스트.
   - 되돌리기: 자동 삭제는 비활성화하고 집계 기능만 유지할 수 있다.
   - 커밋 예시: `feat: 데일리 위클리 집계와 보존 정책 추가`

9. **CI 확장과 기존 Notion 경로 정리**

   - 범위: 새 테스트, Black, API 테스트, SQLite 임시 DB 테스트를 CI에 포함한다. Notion 코드는 선택적 export로 격리한다.
   - 산출물: CI 변경, 운영 실행 문서, 마이그레이션/전환 안내.
   - 검증: Ubuntu·Windows 기존 C++ CI와 Python 테스트 모두 통과.
   - 되돌리기: Notion export 모듈을 별도 유지해 필요 시 재활성화한다.
   - 커밋 예시: `ci: 웹 API와 SQLite 테스트 검증 추가`

---

## 11. 테스트 전략과 CI 확장

### 브리지·파서

기존 `test_message.py`, `test_socket_server.py`를 확장한다.

- JSON v1·CSV v1의 동일한 도메인 이벤트 변환
- fragmented TCP payload
- 여러 개행 메시지
- oversized payload
- 잘못된 Zone·error code
- 수신 스레드 종료와 재연결

현재 이 동작의 근거는 `TelemetryMessage.parse()`와 `SmartFactoryBridge.handle_client()`이다 (`python/network/message.py`, `python/network/socket_server.py`).

### DB 레이어

- 임시 SQLite 파일 또는 `:memory:` fixture
- 스키마 초기화 재실행
- WAL 설정 확인
- 이벤트와 센서 readings 원자적 저장
- `machine_state` 일관성
- 동시 읽기와 직렬 쓰기
- DB 오류 후 queue 재처리 정책
- 집계 중복 실행 방지

### 웹 API

- 상태 조회
- 기간·장비·이벤트 유형 필터
- 빈 결과
- 잘못된 날짜 범위
- 보고서 집계
- JSON 응답 스키마
- 404/422/500 처리

### 실시간 채널

- 연결 직후 초기 snapshot
- 새 이벤트 broadcast
- DB commit 이전 broadcast 금지
- heartbeat
- subscriber 종료
- 재연결 시 최신 상태 수신
- 느린 클라이언트 queue 제한

### CI

기존 기준은 `python -m black --check python`, `python -m pytest`, C++ CTest이다 (`README.md:125-130`, `.github/workflows/ci.yml`).

확장 방향:

- FastAPI·uvicorn·Chart.js 관련 의존성 설치
- Python 테스트에 웹·DB 테스트 포함
- Black 검사 범위에 신규 Python 모듈 포함
- 가능하면 별도 `pytest -m integration` 구분
- 실제 포트 대신 TestClient 사용
- SQLite 파일을 CI artifact로 남기지 않음
- C++ 빌드·CTest는 변경하지 않고 회귀 검증 유지

---

## 12. 리스크와 열린 질문

### 리스크

- 현재 C++는 Zone D 연속 한도 도달 후 정상 종료한다 (`cpp/src/MachineMonitor.cpp:136-151`). 대시보드는 장비 종료 상태와 마지막 상태를 별도로 표시해야 한다.
- C++는 전송 실패 시 로컬 CSV를 계속 저장하지만, Python 브리지는 재전송 큐가 없다 (`cpp/src/MachineMonitor.cpp:89-92`). SQLite 전환 시 수신 장애 동안의 데이터 복구 정책이 필요하다.
- SQLite WAL은 읽기 동시성을 개선하지만 writer 충돌 자체를 제거하지 않는다.
- `timestamp`가 현재 문자열로만 검증된다 (`python/network/message.py:52-58`). 시간대와 잘못된 timestamp 처리 규칙을 명확히 해야 한다.
- 모든 `PERIODIC` 원시 데이터를 저장하면 샘플 주기에 따라 DB가 빠르게 커질 수 있다.
- SSE subscriber가 많아지면 메모리 큐가 증가한다.
- FastAPI 도입은 기존 단일 blocking 서버보다 실행 방식과 종료 처리가 복잡해진다.
- Notion을 완전히 제거하면 기존 보고서 이용 방식과 수동 공유 방식이 사라진다.
- 자동 리텐션 삭제는 되돌리기 어려우므로 사람의 확인 없이 활성화하면 안 된다.

### 열린 질문

- `PERIODIC` 샘플 주기는 실제로 얼마이며, 30일 원시 보존 시 예상 DB 크기는 얼마인가?
- Zone D 연속 카운트의 기준은 Python 수신 이벤트 기준인가, C++ 측 누적 상태 기준인가?
- `WARNING`·`CRITICAL` 이벤트를 무기한 보존할 것인가, 별도 최대 보존 기간을 둘 것인가?
- 장비가 종료된 뒤 대시보드에 `offline`, `stopped`, `last_seen` 중 어떤 상태를 표시할 것인가?
- 보고서의 시간대는 UTC인가, Asia/Seoul인가?
- CSV v1은 계속 지원할 것인가, JSON v1로 전환할 것인가?
- Notion은 완전히 제거할 것인가, SQLite 보고서의 선택적 export 대상으로 유지할 것인가?
- KakaoTalk 실제 연동은 이번 범위에 포함하는가? 현재 구현은 콘솔 미리보기 스텁이다.
- 브리지 프로세스 재시작 시 미처리 queue 또는 C++ 로컬 CSV를 자동 복구할 것인가?
- 실제 환경에서 FastAPI·uvicorn 의존성 추가를 승인할 것인가?
