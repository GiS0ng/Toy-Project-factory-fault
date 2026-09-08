#!/usr/bin/env bash
# 파일을 수정한 뒤 JS/TS 파일에 ESLint를 돌리고, 에러가 있으면 Claude에게 피드백한다.
# PostToolUse(Write|Edit) 훅으로 등록한다.
#
# - JS/TS 파일에만 실행한다.
# - 에러가 없으면 아무것도 출력하지 않고 exit 0.
# - 에러가 있으면 ESLint 출력을 stderr로 내보내고 exit 2 → Claude에게 전달된다.
# - ESLint나 설정이 없으면 (아직 도입 전) 조용히 통과한다.
set -euo pipefail

input=$(cat)
file=$(printf '%s' "$input" | jq -r '.tool_input.file_path // .tool_response.filePath // empty')
[ -n "$file" ] || exit 0

case "$file" in
    *.js | *.jsx | *.mjs | *.cjs | *.ts | *.tsx | *.mts | *.cts) ;;
    *) exit 0 ;;
esac

# 삭제되었거나 존재하지 않는 경로는 건너뛴다.
[ -f "$file" ] || exit 0

root="${CLAUDE_PROJECT_DIR:-.}"

# 실행기 결정: 프로젝트 로컬 설치 > 전역 설치. (npx 자동 다운로드는 쓰지 않는다.)
if [ -x "$root/node_modules/.bin/eslint" ]; then
    eslint_bin="$root/node_modules/.bin/eslint"
elif command -v eslint >/dev/null 2>&1; then
    eslint_bin="eslint"
else
    exit 0
fi

# ESLint 설정 파일이 없으면 통과 (flat config 또는 legacy 둘 다 확인).
if ! ls "$root"/eslint.config.* >/dev/null 2>&1 &&
    ! ls "$root"/.eslintrc* >/dev/null 2>&1; then
    exit 0
fi

if output=$("$eslint_bin" "$file" 2>&1); then
    exit 0
fi

echo "ESLint가 ${file}에서 문제를 발견했습니다. 수정해 주세요:" >&2
echo "$output" >&2
exit 2
