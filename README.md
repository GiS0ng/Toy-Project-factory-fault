# 스마트팩토리 설비 진동 모니터링

설비 진동을 모의 센서에서 수집하고, 이상 상태를 판정한 뒤 C++ → Python → Notion으로 전달하는 프로젝트입니다. 위험 이벤트는 KakaoTalk 알림 인터페이스로도 전달하도록 구성되어 있습니다.

## 현재 구현 범위

- C++ 모니터링 엔진: 3개 센서의 최대 진동값을 기준으로 정상·경고·위험 상태를 판정합니다.
- 안전 정지: 진동값이 `600 μm/s` 이상인 위험 상태가 **4회 연속** 발생할 때만 종료합니다. 정상 또는 경고가 발생하면 연속 횟수는 초기화됩니다.
- 파일 보존: 정기 로그는 `data_queue/`에 CSV로 저장합니다. 위험 종료 시에는 버퍼의 이전 기록과 현재 위험 기록을 하나의 긴급 CSV에 저장합니다.
- TCP 브리지: C++은 줄바꿈으로 구분한 패킷을 `127.0.0.1:9999`로 전송하고, Python은 줄 단위로 수신·검증·분기합니다.
- 재전송 큐: 전송을 최대 3회 시도한 뒤 실패하면 `data_queue/network_retry/pending_*.packet`에 보관합니다. 다음 이벤트에서 최대 10건을 먼저 재전송하고, 성공한 파일은 삭제하지 않고 `sent_*.packet`으로 이름을 변경합니다.
- Notion 이벤트 기록: 경고와 위험 이벤트를 Notion 데이터베이스에 기록합니다. 정상 정기 이벤트는 콘솔에만 표시합니다.
- Notion 보고서: 데일리·위클리 보고서를 KST 기준으로 집계해 지정한 Notion 부모 페이지의 하위 페이지로 생성합니다.

> KakaoTalk 알림은 현재 콘솔 미리보기 단계입니다. 실제 KakaoTalk API 연동은 아직 구현하지 않았습니다.

## 구성

```text
.
├── cpp/                         # 센서 시뮬레이터와 모니터링 엔진
│   ├── include/
│   ├── src/
│   └── main.cpp
├── ptyhon/                      # Python 브리지 (기존 디렉터리명 유지)
│   ├── config/                  # 환경 변수와 Notion API 클라이언트
│   ├── network/                 # TCP 수신과 패킷 라우팅
│   ├── services/                # 알림·보고서 로직
│   ├── tests/
│   └── main.py
├── data_queue/                  # 실행 중 생성되는 로그·재전송 큐
├── requirements.txt
└── .env                         # 로컬 비밀 설정 (Git 제외)
```

## 데이터 흐름

```text
RmsAmplitudeSensor × 3
        ↓
MachineMonitor (C++)
        ├── data_queue/*.csv
        └── TCP 127.0.0.1:9999 (newline-delimited)
                    ↓
             SmartFactoryBridge (Python)
                    ├── Notion 이벤트 DB (경고·위험)
                    └── KakaoTalk 알림 미리보기 (위험)
                    ↓
          Notion 데일리·위클리 보고서
```

## 상태 기준과 패킷 규약

| 상태 | 진동 기준 | 오류 코드 | Python 처리 |
| --- | ---: | ---: | --- |
| `PERIODIC` | 400 미만 | `0` | 콘솔 출력 |
| `WARNING` | 400 이상, 600 미만 | `1` | Notion 이벤트 기록 |
| `CRITICAL` | 600 이상 | `2` | Notion 기록 및 KakaoTalk 미리보기 |

TCP 패킷은 다음 형식이며 마지막에 줄바꿈을 붙입니다.

```text
TYPE,machine_id,vibration,error_code\n
```

예시:

```text
WARNING,1,450,1
CRITICAL,1,620,2
```

Python 라우터는 필드 수, 패킷 유형, 설비 번호·진동값 범위, 유형과 오류 코드의 일치를 검증합니다.

## 설치와 설정

Python 3 환경에서 의존성을 설치합니다.

```bash
python3 -m pip install -r requirements.txt
```

프로젝트 루트에 `.env` 파일을 만들고 아래 **키 이름만** 설정합니다.

```dotenv
NOTION_TOKEN=...
DATABASE_ID=...
NOTION_REPORT_PARENT_PAGE_ID=...
```

- `NOTION_TOKEN`: Notion Integration 토큰
- `DATABASE_ID`: 경고·위험 이벤트를 저장할 Notion 데이터베이스 ID
- `NOTION_REPORT_PARENT_PAGE_ID`: 보고서 하위 페이지를 만들 Notion 부모 페이지 ID

Notion 데이터베이스와 보고서 부모 페이지 모두를 해당 Integration에 공유해야 합니다. 공유하지 않으면 `404 object_not_found` 오류가 발생할 수 있습니다.

이벤트 데이터베이스에는 다음 속성이 필요합니다.

| 속성명 | Notion 타입 | 용도 |
| --- | --- | --- |
| `설비명` | 제목(Title) | 설비 식별 |
| `진동값` | 숫자(Number) | 최대 진동값 집계 |
| `에러코드` | 숫자(Number) | 경고·위험 건수 집계 |

`.env`는 Git에 올리지 않습니다. 토큰이나 ID의 실제 값은 코드, 문서, 커밋 메시지에 넣지 마세요.

## 실행

먼저 Python 브리지를 실행합니다.

```bash
python3 ptyhon/main.py
```

다른 터미널에서 C++ 실행 파일을 빌드하고 실행합니다.

```bash
mkdir -p build
g++ -std=c++17 -Wall -Wextra -Wpedantic \
  cpp/main.cpp cpp/src/MachineMonitor.cpp cpp/src/RmsAmplitudeSensor.cpp \
  cpp/src/VibrationSensor.cpp -o build/factory_monitor
./build/factory_monitor
```

### 보고서 생성

기준일을 생략하면 실행한 날의 날짜를 사용합니다.

```bash
# 데일리 보고서
python3 ptyhon/main.py --daily-report

# 위클리 보고서
python3 ptyhon/main.py --weekly-report

# 특정 날짜 기준 데일리 보고서
python3 ptyhon/main.py --daily-report --date 2026-07-26
```

데일리 보고서는 지정일 00:00부터 다음 날 00:00 전까지, 위클리 보고서는 지정일이 속한 월요일부터 일요일까지를 KST 기준으로 집계합니다. 집계 대상은 Notion 데이터베이스에 기록된 이벤트의 생성 시각입니다.

## 테스트

```bash
PYTHONDONTWRITEBYTECODE=1 pytest -q ptyhon/tests
```

Python 테스트는 패킷 검증, 분할 TCP 수신, Notion 요청, 데일리·위클리 집계를 포함합니다.

## 다음 개선 후보

- 실제 KakaoTalk API 인증·메시지 전송 구현
- `sent_*.packet` 보존 기간 및 정리 정책 결정
- 실제 센서 연동과 현장 기준에 따른 진동 임계값 검증
- Notion 이벤트 DB 외의 장기 저장소와 운영 모니터링 추가
