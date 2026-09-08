# .claude/hooks

Claude Code가 도구를 쓰기 전후에 하네스가 실행하는 스크립트 모음이다. 등록은
`.claude/settings.json` 의 `hooks` 항목에서 하고, 각 스크립트는
`$CLAUDE_PROJECT_DIR/.claude/hooks/<이름>.sh` 형태로 호출된다. 일부 AGENTS.md
규칙과 포맷·린트 검사를 보조할 뿐, 규칙 전체를 강제하거나 CI 를 대신 돌리지는
않는다.

훅을 켜고 끄거나 확인하려면 프롬프트에 `/hooks` 를 입력한다.

## 등록된 훅

| 스크립트 | 이벤트 / matcher | 동작 |
|----------|------------------|------|
| `block-dangerous-commands.sh` | PreToolUse / `Bash` | `rm -rf`, `git push --force`(단 `--force-with-lease` 는 허용), `DROP TABLE`, `dd if=` 패턴을 `exit 2` 로 차단한다. 실수 방지용 휴리스틱이며 완전한 방어가 아니다. |
| `guard-main-commit.sh` | PreToolUse / `Bash` | `git commit` 인데 현재 브랜치가 `main`·`master` 이면 `exit 2` 로 차단한다. 테스트용으로 `HOOK_BRANCH_OVERRIDE` 환경 변수로 브랜치 판정을 덮어쓸 수 있다. |
| `guard-env-file.sh` | PreToolUse / `Write\|Edit` | 자격 증명 파일(`*.pem *.key *.p12 *.pfx *.keystore *.jks id_rsa* id_ed25519 .env.local .env.*.local .env.production`) 편집을 `exit 2` 로 하드 차단한다. |
| `require-approval.sh` | PreToolUse / `Write\|Edit` | `.env`·`.env.<환경>`(템플릿 `.env.example` 등 제외), 패키지 관리 파일(`requirements*.txt`, `pyproject.toml`, `package.json`, 각종 lock 파일 등), `.git/` 내부 파일을 수정하려 하면 `permissionDecision: "ask"` JSON을 내보내 사용자 승인 프롬프트를 띄운다. 해당 없으면 조용히 통과. 프롬프트가 실제로 뜨는지는 세션 권한 모드에 달려 있다(기본 모드에서는 뜨고 `bypassPermissions` 에서는 무시된다). |
| `format-python.sh` | PostToolUse / `Write\|Edit` | `.py` 파일을 수정한 뒤 Black 으로 포맷한다. Black 을 찾지 못하면(`.venv/bin/black` → PATH `black` → `python3 -m black` 순으로 탐색) 조용히 통과하므로, `pip install -r requirements.txt` 전에는 아무 일도 하지 않는다. |
| `python-lint.sh` | PostToolUse / `Write\|Edit` | `.py` 파일을 수정한 뒤 Ruff(우선) 또는 flake8 로 린트해 에러가 있으면 출력을 `exit 2` 로 Claude 에게 피드백한다. 에러가 없으면 아무것도 출력하지 않는다. 실행기는 `.venv/bin` → PATH → `python3 -m` 순으로 ruff 먼저, 없으면 flake8 을 찾고, 둘 다 없으면 조용히 통과한다. `requirements.txt` 에는 아직 ruff/flake8 이 없으므로 설치 전에는 동작하지 않는다. |
| `eslint-check.sh` | PostToolUse / `Write\|Edit` | JS/TS 파일(`.js .jsx .mjs .cjs .ts .tsx .mts .cts`)을 수정한 뒤 ESLint 로 에러가 있으면 출력을 `exit 2` 로 Claude 에게 피드백한다. 실행기는 `node_modules/.bin/eslint` → PATH `eslint` 순으로 찾고, ESLint 나 설정 파일(`eslint.config.*` / `.eslintrc*`)이 없으면 조용히 통과한다. **현재 이 저장소에는 JS/TS 코드도 ESLint 설정도 없으므로 이 훅은 아무 일도 하지 않는다.** |

PostToolUse(`Write|Edit`) 실행 순서: `format-python.sh` → `python-lint.sh` → `eslint-check.sh`.

## 스크립트를 새로 만들 때

훅은 이벤트 정보를 **stdin 으로 JSON** 을 받는다. 그 JSON 을 다룰 때 규칙:

- **`grep`·`sed`·`awk` 로 JSON 을 파싱하지 않는다.** 중첩 구조와 이스케이프된
  따옴표에서 깨진다. `jq`(또는 Python `json`)를 쓴다.
- 문자열 값은 `jq -r` 로 뽑아 따옴표를 제거한다: `jq -r '.tool_input.command'`.
- 없을 수 있는 키는 기본값을 준다: `jq -r '.tool_input.command // ""'`.
- 차단은 `exit 2` + stderr 메시지로 한다. PreToolUse 에서 사용자 승인을 요구할
  때는 `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask",...}}`
  JSON 을 stdout 으로 내보내고 `exit 0`.
- `jq` 미설치 환경을 고려해야 하면 Python one-liner(`python3 -c "import sys,json; ..."`)를
  대안으로 쓴다.
- 등록 전에 합성한 입력으로 직접 파이프 테스트한다:

  ```bash
  echo '{"tool_name":"Bash","tool_input":{"command":"ls"}}' | bash .claude/hooks/<스크립트>.sh
  echo "exit=$?"
  ```

  종료 코드와 부수 효과(파일이 실제로 포맷됐는지 등)를 모두 확인한다.

예시 (`PreToolUse` 에서 위험한 삭제 명령 차단):

```bash
INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // ""')
if echo "$CMD" | grep -qE 'rm -rf|git clean -fdx'; then
    echo "위험한 명령 차단" >&2
    exit 2
fi
```
