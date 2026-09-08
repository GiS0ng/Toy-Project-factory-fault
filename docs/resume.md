# 다른 PC에서 이어서 작업하기

이 저장소를 새 machine(집 PC 등)에서 clone해 이어 작업할 때의 체크리스트.
플러그인 설치·`.venv`·빌드 산출물은 git으로 따라오지 않으므로 아래를 재실행한다.

## 1. 코드 받기

```bash
git clone https://github.com/GiS0ng/Toy-Project-factory-fault.git
cd Toy-Project-factory-fault
git switch chore/project-setup      # clone 직후엔 main
```

인증은 새 machine에서 SSH 키나 credential helper로 설정한다.

## 2. 환경 구성

`CLAUDE.md`의 "환경 준비" 절과 동일하다.

```bash
python3 -m venv .venv
source .venv/bin/activate           # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

python -m pytest                    # 23 passed 확인
python -m black --check python

cmake -S . -B build -DBUILD_TESTING=ON -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build build --config Release
ctest --test-dir build -C Release --output-on-failure
ln -sf build/compile_commands.json .
```

## 3. LSP 언어 서버

```bash
npm install -g pyright              # 또는 pip install pyright
sudo apt install clangd             # sudo 불가 시 CLAUDE.md "LSP" 절의 정적 바이너리 방법
```

## 4. 플러그인 재설치 (machine별)

```bash
claude plugin marketplace add DietrichGebert/ponytail
claude plugin install ponytail@ponytail --scope project
claude plugin install pyright-lsp@claude-plugins-official --scope project
claude plugin install clangd-lsp@claude-plugins-official --scope project
```

`.claude/settings.json`의 `enabledPlugins`는 커밋돼 있으므로 설치만 하면 활성화된다.
codex 플러그인은 `openai/codex-plugin-cc` 마켓에서 별도 설치.

## 5. 작업 시작

```bash
claude                             # 프로젝트 폴더에서. CLAUDE.md 자동 로드
```

1. **결정 먼저**: `docs/plan-realtime-dashboard.md` §4 "착수 전 정할 것" 8개 항목을
   채운다(각 제안값 있음). 채운 뒤 `docs: 대시보드 전환 결정사항 확정`으로 커밋.
2. **그다음**: 같은 문서 §5 1단계(현재 계약 문서화) → 2단계(SQLite 저장소) → …
3. 참고: `docs/codex-plan-raw.md`(Codex 원본 계획), `CLAUDE.md` "구조 변경 작업 방식".

## git으로 안 따라오는 것

| 항목 | 대안 |
|------|------|
| 이전 세션 대화 | 결정과 근거는 `docs/plan-realtime-dashboard.md`에 있음 |
| Claude 로컬 메모리 | 커밋 규칙·fix 번호·구조 변경 워크플로는 `CLAUDE.md`에 있음 |
| `.venv/`, `build/`, `compile_commands.json` | 2단계로 재생성 (gitignore됨) |
| 플러그인 설치 상태 | 4단계로 재설치 |

## 현재 브랜치 상태

`chore/project-setup`은 `refactor/ponytail-simplify`의 `7235c27` 위에 스택돼 있다.
PR을 열 때 ponytail 커밋이 함께 보이면, ponytail PR을 먼저 머지한 뒤 이 브랜치를
`main` 기준으로 rebase한다.
