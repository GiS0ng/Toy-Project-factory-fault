#!/usr/bin/env bash
# Python 파일을 수정한 뒤 Ruff(우선) 또는 flake8로 린트하고, 에러가 있으면 Claude에게 피드백한다.
# PostToolUse(Write|Edit) 훅으로 등록한다.
#
# - .py 파일에만 실행한다.
# - 에러가 없으면 아무것도 출력하지 않고 exit 0.
# - 에러가 있으면 린터 출력을 stderr로 내보내고 exit 2 → Claude에게 전달된다.
# - Ruff도 flake8도 없으면 (아직 도입 전) 조용히 통과한다.
set -euo pipefail

input=$(cat)
file=$(printf '%s' "$input" | jq -r '.tool_input.file_path // .tool_response.filePath // empty')
[ -n "$file" ] || exit 0

case "$file" in
    *.py) ;;
    *) exit 0 ;;
esac

# 삭제되었거나 존재하지 않는 경로는 건너뛴다.
[ -f "$file" ] || exit 0

root="${CLAUDE_PROJECT_DIR:-.}"

run_linter() {
    # Ruff 우선: 프로젝트 venv > PATH > python 모듈
    if [ -x "$root/.venv/bin/ruff" ]; then
        "$root/.venv/bin/ruff" check "$file" 2>&1
        return
    fi
    if command -v ruff >/dev/null 2>&1; then
        ruff check "$file" 2>&1
        return
    fi
    if python3 -m ruff --version >/dev/null 2>&1; then
        python3 -m ruff check "$file" 2>&1
        return
    fi
    # flake8 대체
    if [ -x "$root/.venv/bin/flake8" ]; then
        "$root/.venv/bin/flake8" "$file" 2>&1
        return
    fi
    if command -v flake8 >/dev/null 2>&1; then
        flake8 "$file" 2>&1
        return
    fi
    if python3 -m flake8 --version >/dev/null 2>&1; then
        python3 -m flake8 "$file" 2>&1
        return
    fi
    # 린터 없음 → 통과 신호
    return 3
}

set +e
output=$(run_linter)
status=$?
set -e

# 린터를 찾지 못함 (run_linter가 3 반환)
[ "$status" -eq 3 ] && exit 0
# 위반 없음
[ "$status" -eq 0 ] && exit 0

echo "Python 린터가 ${file}에서 문제를 발견했습니다. 수정해 주세요:" >&2
echo "$output" >&2
exit 2
