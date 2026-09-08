#!/usr/bin/env bash
# 민감한 파일을 Write/Edit 하기 전에 사용자 승인을 받도록 한다.
# PreToolUse(Write|Edit) 훅으로 등록한다.
#
# 대상:
#   - .env 및 .env.<환경> (단, .env.example / .sample / .template / .dist 등 템플릿은 제외)
#   - 패키지 관리 파일 (requirements*.txt, pyproject.toml, package.json, lock 파일 등)
#   - .git/ 디렉터리 내부의 모든 파일
#
# 동작: 위에 해당하면 permissionDecision "ask" JSON을 내보내 Claude Code가
#       사용자에게 확인 프롬프트를 띄우게 한다. 해당 없으면 아무것도 출력하지 않고 통과.
set -euo pipefail

input=$(cat)
file=$(printf '%s' "$input" | jq -r '.tool_input.file_path // ""')
[ -n "$file" ] || exit 0

base=$(basename "$file")
reason=""

# 1) .env 계열 (템플릿 제외)
case "$base" in
    .env.example | .env.sample | .env.template | .env.dist | .env.*.example)
        ;;
    .env | .env.* | *.env)
        reason="환경 변수 파일($base) 수정" ;;
esac

# 2) .git 디렉터리 내부
case "$file" in
    */.git/* | .git/*)
        reason="Git 내부 파일(.git/) 수정" ;;
esac

# 3) 패키지 관리 파일
if [ -z "$reason" ]; then
    case "$base" in
        requirements.txt | requirements-*.txt | requirements.in | constraints.txt \
        | pyproject.toml | setup.py | setup.cfg | Pipfile | Pipfile.lock \
        | poetry.lock | pdm.lock | uv.lock \
        | package.json | package-lock.json | npm-shrinkwrap.json | yarn.lock | pnpm-lock.yaml \
        | Cargo.toml | Cargo.lock | go.mod | go.sum | Gemfile | Gemfile.lock)
            reason="패키지 관리 파일($base) 수정 (AGENTS.md: 의존성 추가 전 사용자 확인)" ;;
    esac
fi

[ -n "$reason" ] || exit 0

esc=$(printf '%s' "$reason" | jq -Rs .)
cat <<EOF
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":${esc}}}
EOF
exit 0
