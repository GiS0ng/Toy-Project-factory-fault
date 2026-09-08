#!/usr/bin/env bash
# main/master 브랜치에 직접 커밋하는 것을 막는다 (AGENTS.md 규칙).
# PreToolUse(Bash) 훅으로 등록한다. 차단할 때는 exit 2 + stderr 메시지.
set -euo pipefail

input=$(cat)
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""')

# git commit 호출이 아니면 통과
echo "$cmd" | grep -Eq 'git( +-[^ ]+)* +commit' || exit 0

root="${CLAUDE_PROJECT_DIR:-.}"
branch="${HOOK_BRANCH_OVERRIDE:-$(git -C "$root" rev-parse --abbrev-ref HEAD 2>/dev/null || true)}"

if [ "$branch" = "main" ] || [ "$branch" = "master" ]; then
    echo "⛔ '$branch' 브랜치에는 직접 커밋할 수 없습니다 (AGENTS.md)." >&2
    echo "   새 브랜치에서 작업하세요:  git switch -c feature/<이름>" >&2
    exit 2
fi

exit 0
