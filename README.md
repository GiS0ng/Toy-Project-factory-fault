# 스마트팩토리 설비 진동 모니터링

C++ 엣지 프로세스가 세 센서의 진동 속도 RMS를 수집·평가하고, Python 브리지가 검증된 이벤트를 Notion 보고 및 알림 계층으로 전달하는 예제 프로젝트입니다.

## 설계 원칙

- 측정 단위는 `mm/s RMS`로 고정합니다.
- ISO Zone A–D 판정과 운전 조치 정책을 분리합니다.
- Zone 경계값은 코드에 넣지 않고 설비 프로필 설정 파일에서 받습니다.
- Zone D가 설정 횟수만큼 연속 발생하면 메모리 버퍼를 저장한 뒤 정상 종료합니다.
- 새 전송 형식은 줄 단위 JSON v1이며, 기존 4필드 CSV v1도 Python에서 계속 받습니다.
- 네트워크 전송에 실패해도 로컬 수집과 저장은 계속합니다.

> 이 저장소는 ISO 인증 도구가 아닙니다. `config/machine_profile.example.conf`의 경계값은 실행 예시일 뿐입니다. 실제 값은 보유한 ISO 20816-3:2022 문서, 설비 사양, 측정 위치와 담당 엔지니어의 판단에 따라 승인된 값으로 교체해야 합니다.

## 구조

```text
.
├── config/
│   └── machine_profile.example.conf
├── cpp/
│   ├── include/        # 판정·설정·전송 인터페이스
│   ├── src/            # 플랫폼 독립 코어와 TCP 구현
│   └── tests/          # 외부 테스트 프레임워크가 필요 없는 CTest
├── python/
│   ├── config/         # 환경 설정과 Notion 클라이언트
│   ├── network/        # CSV/JSON 파서, 라우터, TCP 서버
│   ├── services/       # 알림 서비스
│   └── tests/
├── CMakeLists.txt
└── requirements.txt
```

데이터 흐름은 다음과 같습니다.

```text
센서 3개 → C++ 측정 이벤트 → ISO Zone 평가 → 로컬 CSV
                                      └→ TCP(JSON/CSV) → Python 검증 → Notion/알림
```

## 준비

Python 3.10 이상과 CMake 3.20 이상, C++17 컴파일러가 필요합니다.

```bash
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Notion 연동이 필요하면 `.env.example`을 `.env`로 복사한 뒤 `NOTION_TOKEN`과 `DATABASE_ID`를 함께 입력합니다. 두 값이 없으면 로컬 수신과 알림 미리보기만 동작합니다.

## 실행

먼저 Python 브리지를 실행합니다.

```bash
python python/main.py
```

C++ 프로그램을 빌드합니다.

```bash
cmake -S . -B build -DBUILD_TESTING=ON
cmake --build build --config Release
```

승인된 Zone 값으로 설정 파일을 만든 뒤 실행 파일에 전달합니다.

Linux:

```bash
./build/factory_monitor config/machine_profile.conf
```

Windows:

```powershell
.\build\Release\factory_monitor.exe config\machine_profile.conf
```

## 설정 파일

형식은 주석과 `key=value` 행으로 구성됩니다. 다음 값은 필수입니다.

- 표준과 설비: `standard`, `machine_group`, `support_type`, `rated_power_kw`, `operating_speed_rpm`
- Zone 경계: `zone_ab_mm_s_rms`, `zone_bc_mm_s_rms`, `zone_cd_mm_s_rms`
- 정책: `consecutive_zone_d_limit`, `sample_interval_ms`, `save_interval_seconds`
- 전송·저장: `telemetry_host`, `telemetry_port`, `protocol`, `data_directory`

프로그램은 ISO 20816-3:2022 적용 범위에 맞춰 출력이 15 kW를 초과하는지, 회전수가 120~30,000 r/min인지, Zone 경계가 오름차순인지 시작 시 검증합니다.

## 통신 규약

JSON v1은 각 메시지 끝에 개행을 붙입니다.

```json
{"version":1,"type":"WARNING","timestamp":"2026-09-04T00:00:00Z","machine_id":1,"standard":"ISO 20816-3:2022","unit":"mm/s RMS","max_velocity_rms":4.5,"zone":"C","error_code":1,"readings":[{"sensor_id":1,"velocity_rms":4.5}]}
```

레거시 CSV도 계속 지원합니다.

```csv
WARNING,1,4.500,1
```

메시지 유형과 에러 코드는 `PERIODIC=0`, `WARNING=1`, `CRITICAL=2`로 일치해야 합니다. Python 브리지는 버전, 단위, 값 범위, Zone 조합이 잘못된 메시지를 외부 서비스에 전달하지 않습니다.

## 테스트

```bash
python -m black --check python
python -m pytest
ctest --test-dir build -C Release --output-on-failure
```

GitHub Actions는 Ubuntu와 Windows에서 C++ 빌드·CTest를 실행하고, Ubuntu에서 Python 포맷과 테스트를 확인합니다.
