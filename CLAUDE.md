# CLAUDE.md

## 프로젝트 개요

스마트팩토리 설비 진동 모니터링 예제. C++ 엣지 프로세스가 센서 3개의 진동
속도 RMS(`mm/s RMS`)를 수집·평가하고, Python 브리지가 검증된 이벤트를
Notion 보고와 KakaoTalk 알림 계층으로 전달한다.

데이터 흐름: `C++ (측정·ISO Zone 평가·로컬 CSV) → TCP(JSON v1 또는 CSV v1) → Python (검증·라우팅) → Notion / KakaoTalk`

배경과 상세 설명은 `README.md`, 협업 규칙은 `AGENTS.md`를 참고한다.

## 환경 준비

- Python 3.10 이상 (CI는 3.11), CMake 3.20 이상, C++17 컴파일러.
- 시스템에 노출된 인터프리터는 `python3` 하나뿐이다. `python` 이라는 이름은
  가상환경을 활성화해야 생긴다.

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

이하 명령은 venv 를 활성화한 상태를 전제로 한다. 활성화하지 않았다면 `python`
대신 `python3` 로 읽는다.

### LSP (선택)

`.claude/settings.json` 에 `pyright-lsp` / `clangd-lsp` 플러그인을 켜 두었다.
코드 인텔리전스를 쓰려면 언어 서버를 PATH 에 설치한다.

```bash
npm install -g pyright        # 또는 pip install pyright
sudo apt install clangd       # Ubuntu/WSL. sudo 불가 시 아래 참고
```

`sudo` 를 못 쓰는 환경이면 clangd 정적 바이너리를 홈에 둔다:
`clangd/clangd` 릴리스의 `clangd-linux-*.zip` 을 받아 `~/.local/opt/` 에 풀고
`~/.local/bin/clangd` 로 심링크한다 (PATH 에 `~/.local/bin` 필요).

clangd 정확도를 위해 CMake 를 `-DCMAKE_EXPORT_COMPILE_COMMANDS=ON` 으로 구성하고
`ln -sf build/compile_commands.json .` 로 루트에 링크한다.

## 자주 쓰는 명령

Python (저장소 루트에서):

```bash
python python/main.py                 # 브리지 서버만 실행 (C++ 프로그램보다 먼저)
python python/dashboard.py            # 브리지 + 웹 대시보드 (http://127.0.0.1:8000)
python -m pytest                       # 테스트 (pyproject.toml이 pythonpath=python 설정)
python -m black --check python         # 포맷 검사 (CI 기준)
python -m black python                 # 포맷 적용
```

C++:

```bash
cmake -S . -B build -DBUILD_TESTING=ON
cmake --build build --config Release
ctest --test-dir build -C Release --output-on-failure

# 실행 전에 프로필 파일을 만든다. 저장소에는 example만 있고, zone_* 등 경계값은
# 승인된 ISO 20816-3 값으로 교체해야 한다 (README "설정 파일" 절 참고).
cp config/machine_profile.example.conf config/machine_profile.conf

./build/factory_monitor config/machine_profile.conf                 # Linux/macOS
.\build\Release\factory_monitor.exe config\machine_profile.conf     # Windows
```

`pytest`는 `python/` 디렉터리를 import 경로로 쓰므로 `python/` 내부 모듈은
`network.message`처럼 `python.` 접두어 없이 임포트한다.

## 아키텍처

### C++ (`cpp/`)
- `include/` 인터페이스·구조체, `src/` 구현, `tests/` 외부 프레임워크 없는 CTest,
  `main.cpp` 조립부. 라이브러리 타깃은 `factory_core`.
- 플랫폼 독립 코어: `MachineMonitor`(샘플 루프·저장 정책), `VibrationEvaluator`
  (Zone 판정), `EventSerializer`(JSON/CSV 직렬화), `MachineProfile`(설정 파싱·검증).
- I/O 경계는 인터페이스로 분리: `IVibrationSensor`(→ `RmsAmplitudeSensor`),
  `ITelemetrySender`(→ `TcpTelemetrySender`). 테스트는 가짜 구현과 주입형
  `Clock`을 사용한다.
- Zone 경계값은 코드에 넣지 않고 설비 프로필 설정 파일에서 받는다.
- Zone D가 `consecutive_zone_d_limit`만큼 연속되면 버퍼를 저장하고 정상 종료한다.
  종료 코드: 정상 `0`, 저장 실패 `2`, 인자 개수 오류 `64`(`main.cpp`),
  초기화·실행 중 예외 `1`.

### Python (`python/`)
- `config/` 환경 설정(`Settings`)·SQLite 연결(`database.py`), `network/` 메시지 파서·
  라우터·TCP 서버, `persistence/` 이벤트 저장소·writer, `services/` 알림, `web/` 대시보드.
- 데이터 경로: `수신 스레드(FactoryRouter.parse_and_route: 파싱·검증·로그·긴급 알림)`
  → `EventWriter.submit()` bounded 큐 → `EventWriter` 단일 스레드 → `EventStore.record_event()`
  (SQLite `telemetry_events` INSERT + `machine_state` UPSERT, 한 트랜잭션).
- `main.py`는 브리지만, `dashboard.py`(→ `web/app.py`)는 브리지 + FastAPI 대시보드를 조립한다.
  의존성은 생성자 주입, `Settings.from_env()` 기준.
- `TelemetryMessage.parse()`가 CSV v1과 JSON v1을 모두 받고, 버전·단위(`mm/s RMS`)·
  값 범위·유형↔에러코드↔Zone 조합을 검증한다. 검증 실패 메시지는 저장·전달하지 않는다.
- 유형/에러코드 대응: `PERIODIC=0`, `WARNING=1`, `CRITICAL=2`. C++ `ErrorCode`와
  Python `EXPECTED_ERROR_CODES`가 항상 일치해야 한다.
- Zone D 연속 카운트는 C++가 보내지 않아 `FactoryRouter`가 연속 `CRITICAL` 수로 재계산한다.
- `send_to_kakao_sos`는 콘솔 미리보기만 하는 스텁, CRITICAL에서 큐와 무관하게 즉시 호출된다.
- 대시보드 조회 API(`web/api.py`)는 요청마다 읽기 전용 연결을 열고, `machine_state` +
  계산된 `lifecycle`(running/stopped/offline), 필터형 이벤트 이력, 진동 시계열을 제공한다.
- Notion 연동(`config/notion_client.py`)은 데이터 경로에서 빠졌고 미사용 상태다. `Settings`의
  `NOTION_*`도 마찬가지. 정리 단계에서 함께 삭제 예정(`docs/plan-realtime-dashboard.md`).

### 설정
- C++ 실행 프로필: `config/machine_profile.example.conf` (비인증 예시). `standard`는
  `ISO 20816-3:2022` 고정, `rated_power_kw > 15`, `operating_speed_rpm` 120~30000,
  Zone 경계 `0 < AB < BC < CD` 순서를 시작 시 검증한다.
- Python 런타임: `.env` (`.env.example` 복사). `NOTION_TOKEN`과 `DATABASE_ID`는
  둘 다 있거나 둘 다 없어야 한다.

## 코드 스타일 (AGENTS.md 발췌)

- Python은 PEP 8 + Black. 함수명·변수명은 영어, **주석은 한국어**로 작성한다.
- C++는 CMake에서 `-Wall -Wextra -Wpedantic` (MSVC `/W4 /permissive-`) 경고를 켠다.
- 새 패키지 추가는 사용자에게 먼저 확인하고, 의존성은 `requirements.txt`로 관리한다.

## 금지 사항 (AGENTS.md)

- 비밀키·토큰을 코드에 직접 쓰지 않는다. 환경 변수로 관리한다.
- 데이터 삭제·마이그레이션은 사람의 확인을 받은 후 실행한다.
- (Git 관련 금지 사항은 아래 "Git 규칙" 참조.)

## Git 규칙

`main` 직접 커밋 금지만 `AGENTS.md`에서 온 규칙이다. 나머지는 이 저장소에서
합의한 컨벤션으로, `AGENTS.md`에는 아직 반영돼 있지 않다. 자동 강제되는 것은
`main` 커밋 차단과 `--force` 차단뿐(`.claude/hooks/`)이고, 커밋 메시지 형식 등은
관례로 지킨다.

- **커밋 메시지는 한국어로** 쓴다.
- **형식은 Conventional Commits**: 제목 줄을 `<type>: <설명>` 으로 시작한다.
  `<type>` 은 영어 소문자로 두고 설명만 한국어로 쓴다.
  - 자주 쓰는 `<type>`: `feat`(기능), `fix`(버그 수정), `refactor`(동작 변화 없는
    구조 개선), `test`(테스트), `docs`(문서), `build`(빌드·CMake·의존성),
    `ci`(GitHub Actions), `chore`(잡일)
  - 제목 줄은 50자 안팎으로, 마침표 없이 끝낸다.
- 설명이 필요하면 제목 다음에 빈 줄을 두고 **본문을 `-` 불릿**으로 적는다.
  각 불릿은 "무엇을·왜" 바꿨는지 한국어로 한 줄씩.
- 하나의 커밋은 한 가지 주제만 담는다. 서로 다른 주제는 커밋을 나눈다.
- 브랜치명은 `<type>/<짧은-영문-설명>` (예: `refactor/ponytail-simplify`).
- `main` 에 직접 커밋·푸시하지 않는다. 항상 브랜치를 만들어 PR로 병합한다.
- `git push --force` 는 쓰지 않는다. 필요하면 `--force-with-lease` 를 쓴다.
  (두 규칙은 `.claude/hooks/` 훅으로도 강제한다.)

예시:

```text
refactor: ponytail 정리 - 단일 구현 추상화

- 죽은 설정 값 제거
- 간접 의존성 정리해 빌드 그래프 단순화

fix: 진동값 ISO 20816-3 기준으로 재계산

test: 메시지 파서 CSV/JSON 검증 케이스 추가
```

## fix 번호 주석 (리뷰용)

`git tag v1.0` 이후의 수정은 바뀐 블록 위에 `# fix <N>: 설명`(C++는 `//`)을 달아
리뷰 대상을 표시한다. `N` 은 `grep -rn "fix [0-9]" cpp python` 의 최댓값+1, 한
커밋의 여러 수정은 같은 번호를 쓰고 커밋 본문에도 `- fix <N>: …` 로 적는다.
`main` 머지 후 그 주석은 제거한다. **아직 `v1.0` 태그가 없어 규칙 미적용.**

## 구조 변경 작업 방식

여러 파일에 걸치는 아키텍처·구조 변경(저장소 백엔드 교체, 서비스 계층 추가,
대시보드 도입 등)은 다음 순서로 한다.

1. Claude가 계획안을 낸다.
2. 같은 요구사항으로 `/codex:rescue --fresh` 에 병렬 계획을 시킨다.
3. 두 계획을 표로 비교(일치점·차이·각자 우위)하고 종합 권고를 낸다.
4. 채택안을 `docs/plan-*.md` 로 문서화한다(열린 질문, 단계별 독립 커밋 포함).
5. 구현은 ponytail 원칙(YAGNI, stdlib 우선, 요청 안 한 추상화 금지, 가장 얇게
   시작)으로 한다. Codex 계획이 대체로 더 방어적이므로 리스크가 낮고 근거가
   분명한 항목만 취하고 나머지는 "필요해지면"으로 미룬다.

진행 중인 계획: `docs/plan-realtime-dashboard.md` (Notion→SQLite + 실시간 대시보드).

## Hook

`.claude/settings.json`에 훅을 등록해 일부 AGENTS.md 규칙과 포맷·린트 검사를
보조한다. 규칙 전체를 강제하지는 않고, CI 명령을 대신 돌리지도 않는다.

- PreToolUse(`Bash`): 위험한 명령(`rm -rf`, `git push --force`, `DROP TABLE`,
  `dd if=`) 차단, `main`·`master` 직접 커밋 차단.
- PreToolUse(`Write|Edit`) — **하드 차단(`exit 2`)** 과 **승인 요청(ask)** 이 다르다:
  - 자격 증명 파일(`*.pem *.key *.p12 *.pfx *.keystore *.jks id_rsa* id_ed25519`,
    `.env.local` / `.env.*.local` / `.env.production` / `.env.prod`) → 하드 차단.
  - 일반 `.env`·`.env.<환경>`(템플릿 제외), 패키지 관리 파일, `.git/` 내부 →
    사용자 승인 요청. (프롬프트가 실제로 뜨는지는 세션 권한 모드에 달림)
- PostToolUse(`Write|Edit`): `.py` → Black 포맷 후 Ruff 또는 flake8 린트,
  JS/TS → ESLint. **Ruff·flake8·ESLint 모두 현재 의존성에 없으며**, 설치돼
  있지 않으면(그리고 ESLint 설정이 없으면) 각 훅은 조용히 통과한다.

스크립트별 상세 동작, 새 훅을 만들 때의 JSON 파싱 규칙(요약: `grep`/`sed` 대신
`jq -r` 사용, 차단은 `exit 2` + stderr, 로직이 길면 스크립트로 분리)과 파이프
테스트 방법은 **`.claude/hooks/README.md`** 를 본다. 훅 확인·토글은 `/hooks`.

## CI

`.github/workflows/ci.yml`: Ubuntu/Windows에서 C++ 빌드 + CTest, Ubuntu에서
Python 3.11로 `black --check python` + `pytest`.
