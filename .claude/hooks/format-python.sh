#!/usr/bin/env bash
# Python 파일을 수정한 뒤 Black으로 자동 포맷한다 (CI의 `black --check python`과 정렬).
# PostToolUse(Write|Edit) 훅으로 등록한다. Black이 없으면 조용히 통과한다.
set -euo pipefail

input=$(cat)
file=$(printf '%s' "$input" | jq -r '.tool_input.file_path // .tool_response.filePath // empty')
[ -n "$file" ] || exit 0

case "$file" in
    *.py) ;;
    *) exit 0 ;;
esac

root="${CLAUDE_PROJECT_DIR:-.}"
if [ -x "$root/.venv/bin/black" ]; then
    "$root/.venv/bin/black" -q "$file"
elif command -v black >/dev/null 2>&1; then
    black -q "$file"
elif python3 -m black --version >/dev/null 2>&1; then
    python3 -m black -q "$file"
fi

exit 0
